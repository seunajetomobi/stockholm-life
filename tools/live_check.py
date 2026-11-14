#!/usr/bin/env python3
"""Read-only check that a Stockholm Life site serves exactly the files of one commit, and that the game starts.

    python3 tools/live_check.py --expect <full 40-character commit SHA> [options]

It compares every published file (index.html, everything under data/, and the generated version.txt) with the
commit by Git blob ID, repeats the comparison in rounds so that CDN caching cannot be mistaken for a bad deployment,
checks the data files with the same rules as the Deploy workflow, and starts the game in headless Chromium with
every same-origin request intercepted and hashed. How to use it and what it cannot see: tests/README.md.

Exit codes: 0 PASS, 1 FAIL, 2 INCONCLUSIVE (could not check; nothing proven wrong), 3 usage or local error.

The tool only reads. It never deploys, pushes, fetches or changes Git refs, never writes into the repository unless
--allow-repo-output is given (and never into .git or tests/output), and never reads or sends credentials.
An http:// site URL switches on loopback-strict mode, used by the tests: every connection must go to a loopback
address, host names are resolved once and pinned, redirects are checked hop by hop, and nothing leaves the machine.
"""
import argparse
import calendar
import email.utils
import gzip
import hashlib
import html.parser
import http.client
import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_URL = 'https://seunajetomobi.github.io/stockholm-life/'
DEFAULT_SLUG = 'seunajetomobi/stockholm-life'
GITHUB_API = 'https://api.github.com'
UA = 'stockholm-life-live-check/1'

PASS, FAIL, INCONCLUSIVE, SKIP = 'PASS', 'FAIL', 'INCONCLUSIVE', 'SKIP'
EXIT = {PASS: 0, FAIL: 1, INCONCLUSIVE: 2}
USAGE_EXIT = 3
MATCH, DIFF, MISSING, UNAVAILABLE = 'MATCH', 'DIFF', 'MISSING', 'UNAVAILABLE'
MAX_BYTES = 64 << 20          # per file
MAX_HOPS = 3                  # redirects followed at most
DEFAULT_WINDOW = 600          # s; GitHub Pages sends Cache-Control: max-age=600
MAX_WINDOW = 3600
MAX_SPAN = 4 * 3600
SHA_RE = re.compile(r'^[0-9a-f]{40}$')
SLUG_RE = re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')

# The game-file rules of .github/workflows/deploy.yml ("Check the game files"). tests/test_live_check.py runs both
# versions on the same inputs and fails if they ever differ, so update them together.
ESSENTIAL = ['b', 'r', 'm']
OPTIONAL = ['x', 't', 'o', 'e', 'people', 'vehicles', 'trees']

# What the browser check reads in index.html; tests/test_live_check.py checks that the game still has these.
STARTUP_MARKERS = ['id="stage"', 'id="loading"', 'id="modalRoot"', 'id="go"', "className='nogl'",
                   'Could not load the city data', 'could not start 3D graphics']

# Test-only settings, honoured only in loopback-strict mode (an http:// site URL)
TEST_ENV = ['SL_LIVE_GITHUB_API', 'SL_LIVE_EXTERNAL_STUBS', 'SL_LIVE_TEST_RESOLVER', 'SL_LIVE_TEST_SINK',
            'SL_LIVE_FAULT', 'SL_LIVE_TEST_CHROME_ARGS']


class UsageError(Exception):
    """Bad arguments or local problem (exit 3)."""


class SourceUnavailable(Exception):
    """The expected file list could not be established (exit 2)."""


class Blocked(Exception):
    """A destination refused by the network policy. Deliberately not an OSError, so urllib does not wrap it."""

    def __init__(self, url, reason):
        super().__init__(f'{url}: {reason}')
        self.url, self.reason = url, reason


class Redirected(Exception):
    """A redirect for a request that must be answered directly."""

    def __init__(self, url, dest, code):
        super().__init__(f'{url} redirected ({code}) to {dest}')
        self.url, self.dest, self.code = url, dest, code


def blob_id(data):
    """Git's object ID for a file with these bytes, the same as `git hash-object`."""
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- network policy, DNS pinning and the HTTP client

def ip_literal(host):
    try:
        return ipaddress.ip_address(host.strip('[]'))
    except ValueError:
        return None


class Policy:
    """Where requests may go.

    https:// site URL: production. Site requests stay on the site's host and path, API requests on the API host,
    always https. http:// site URL: loopback-strict. Every destination must be a loopback address; a host name is
    resolved exactly once, accepted only if every address is loopback, and pinned: all later connections go to the
    pinned address (urllib, Playwright's route.fetch and Chromium's resolver rules), so nothing resolves it again.
    Only `localhost` and names the given resolver knows are looked up at all; any other name is refused unresolved,
    so not even a DNS query leaves the machine."""

    def __init__(self, site_url, api_url, resolver=None, names=()):
        u = urllib.parse.urlsplit(site_url)
        self.loopback = u.scheme == 'http'
        self.site = u
        self.base = urllib.parse.urlunsplit((u.scheme, u.netloc, u.path, '', ''))
        self.api = urllib.parse.urlsplit(api_url)
        self.resolver = resolver or socket.getaddrinfo
        self.names = {'localhost', *names}  # the only names that may be resolved in loopback mode
        self.pins = {}               # host -> {'ip', 'all'}
        self.resolver_calls = {}     # host -> number of lookups (always 1 per host)
        self.connections = []        # [host, port, ip] for every connection made by the urllib client

    def pin(self, host, port):
        if not host:
            raise Blocked('', 'no host')
        if host in self.pins:
            return self.pins[host]['ip']
        lit = ip_literal(host)
        if lit is not None:
            if not lit.is_loopback:
                raise Blocked(host, 'not a loopback address')
            ip, addrs = str(lit), [str(lit)]
        else:
            if re.fullmatch(r'[0-9.]+|0x[0-9a-fA-F.x]+', host):
                raise Blocked(host, 'numeric host that is not a canonical IP address')
            if host.lower() not in self.names:
                raise Blocked(host, 'host name not allowed in loopback mode (use an IP literal or localhost); not resolved')
            self.resolver_calls[host] = self.resolver_calls.get(host, 0) + 1
            try:
                infos = self.resolver(host, port, type=socket.SOCK_STREAM)
            except Exception as e:
                raise Blocked(host, f'cannot resolve: {e}')
            addrs = []
            for info in infos:
                a = info[4][0]
                if a not in addrs:
                    addrs.append(a)
            if not addrs:
                raise Blocked(host, 'resolves to no address')
            bad = [a for a in addrs if not (ip_literal(a) and ip_literal(a).is_loopback)]
            if bad:
                raise Blocked(host, f'resolves to non-loopback addresses {bad} (all: {addrs}); cannot pin to a loopback address')
            ip = next((a for a in addrs if ':' not in a), addrs[0])
        self.pins[host] = {'ip': ip, 'all': addrs}
        return ip

    def allow(self, url, kind):
        """Check a destination before any connection. Returns the pinned IP (loopback mode) or None. Raises Blocked."""
        u = urllib.parse.urlsplit(url)
        if u.username is not None or u.password is not None or '@' in u.netloc:
            raise Blocked(url, 'credentials in the URL')
        try:
            port = u.port
        except ValueError:
            raise Blocked(url, 'invalid port')
        if self.loopback:
            if u.scheme != 'http':
                raise Blocked(url, f'{u.scheme or "no"} scheme in loopback mode (only http to loopback is allowed)')
            return self.pin(u.hostname, port or 80)
        if u.scheme != 'https':
            raise Blocked(url, 'only https is allowed in production mode')
        if kind == 'site':
            if (u.hostname, port) != (self.site.hostname, self.site.port) or not u.path.startswith(self.site.path):
                raise Blocked(url, 'outside the site')
        elif kind == 'api':
            if (u.hostname, port) != (self.api.hostname, self.api.port):
                raise Blocked(url, 'outside the GitHub API')
        else:
            raise Blocked(url, f'unknown request kind {kind}')
        return None

    def literal_url(self, url, ip):
        """The same URL with the host replaced by its pinned address (for Playwright's HTTP client)."""
        u = urllib.parse.urlsplit(url)
        host = f'[{ip}]' if ':' in ip else ip
        netloc = f'{host}:{u.port}' if u.port else host
        return urllib.parse.urlunsplit((u.scheme, netloc, u.path, u.query, ''))

    def chromium_rules(self, sink=None):
        """--host-resolver-rules for loopback mode: pinned names to their addresses, every other name to NOTFOUND."""
        rules = []
        if sink:
            rules.append(f'MAP {sink[0]} {sink[1]}')
        for host, p in sorted(self.pins.items()):
            if ip_literal(host) is None:
                rules.append(f'MAP {host} {p["ip"]}')
        rules += ['MAP * ~NOTFOUND', 'EXCLUDE 127.0.0.1', 'EXCLUDE [::1]']
        return ', '.join(rules)


class PinnedHTTPConnection(http.client.HTTPConnection):
    """Connects to the policy's pinned address, never to a name; the Host header keeps the original name."""
    policy = None

    def connect(self):
        ip = self.policy.pin(self.host, self.port)
        if not ipaddress.ip_address(ip).is_loopback:     # pin() guarantees this; checked again at the connection
            raise Blocked(self.host, f'pinned address {ip} is not loopback')
        self.policy.connections.append([self.host, self.port, ip])
        self.sock = socket.create_connection((ip, self.port), self.timeout, self.source_address)


class PinnedHTTPHandler(urllib.request.HTTPHandler):
    def __init__(self, policy):
        super().__init__()
        self.conn_class = type('BoundPinnedHTTPConnection', (PinnedHTTPConnection,), {'policy': policy})

    def http_open(self, req):
        return self.do_open(self.conn_class, req)


class CheckedRedirects(urllib.request.HTTPRedirectHandler):
    """Checks every redirect destination before urllib requests it; at most MAX_HOPS hops."""
    max_redirections = MAX_HOPS

    def __init__(self, policy, kind, follow):
        super().__init__()
        self.policy, self.kind, self.follow, self.chain = policy, kind, follow, []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        dest = urllib.parse.urljoin(req.full_url, newurl)
        if not self.follow:
            raise Redirected(req.full_url, dest, code)
        if len(self.chain) >= MAX_HOPS:
            raise Blocked(dest, f'more than {MAX_HOPS} redirects')
        self.policy.allow(dest, self.kind)       # raises Blocked before any request to dest
        self.chain.append(dest)
        return super().redirect_request(req, fp, code, msg, headers, dest)


class Resp:
    def __init__(self, url, status=None, headers=None, body=b'', error=None, chain=None):
        self.url, self.status, self.headers, self.body, self.error, self.chain = url, status, headers or {}, body, error, chain or []


def _read(fp, encoding):
    raw = fp.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError(f'response larger than {MAX_BYTES} bytes')
    if encoding in ('', 'identity'):
        return raw
    if encoding == 'gzip':
        d = zlib.decompressobj(16 + zlib.MAX_WBITS)
        out = d.decompress(raw, MAX_BYTES + 1)
        if len(out) > MAX_BYTES or d.unconsumed_tail:
            raise ValueError(f'decoded response larger than {MAX_BYTES} bytes')
        if not d.eof:
            raise ValueError('truncated gzip response')
        return out
    raise ValueError(f'unsupported Content-Encoding {encoding!r}')


REQUEST_TIMEOUT = [20]       # seconds per request; --request-timeout


def http_get(policy, url, kind, follow=False, headers=None, timeout=None, attempts=3):
    """GET through the policy. Network errors, timeouts and short reads are retried and end in Resp(error=...).
    Raises Blocked (policy) or Redirected (follow=False and the server redirected)."""
    policy.allow(url, kind)
    timeout = timeout or REQUEST_TIMEOUT[0]
    waits = [0.05, 0.05] if policy.loopback else [1, 3]
    last = None
    for attempt in range(attempts):
        rh = CheckedRedirects(policy, kind, follow)
        handlers = [rh]
        if policy.loopback:
            handlers += [urllib.request.ProxyHandler({}), PinnedHTTPHandler(policy)]
        opener = urllib.request.build_opener(*handlers)
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Encoding': 'gzip', **(headers or {})})
        try:
            with opener.open(req, timeout=timeout) as r:
                h = {k.lower(): v for k, v in r.headers.items()}
                return Resp(url, r.status, h, _read(r, h.get('content-encoding', '').strip().lower()), chain=rh.chain)
        except urllib.error.HTTPError as e:
            if 300 <= e.code < 400:
                raise Blocked(url, f'redirect refused: {e.reason}')
            h = {k.lower(): v for k, v in (e.headers or {}).items()}
            try:
                body = _read(e, h.get('content-encoding', '').strip().lower())
            except Exception:
                body = b''
            return Resp(url, e.code, h, body, chain=rh.chain)
        except (Blocked, Redirected):
            raise
        except (urllib.error.URLError, OSError, http.client.HTTPException, ValueError) as e:
            reason = getattr(e, 'reason', e)
            if isinstance(reason, (Blocked, Redirected)):
                raise reason
            last = f'{type(e).__name__}: {reason}'
            if attempt < attempts - 1:
                time.sleep(waits[min(attempt, len(waits) - 1)])
    return Resp(url, error=last)


# ---------------------------------------------------------------- the expected files

GIT_ALLOWED = {'cat-file', 'ls-tree', 'rev-parse', 'merge-base'}


def git_ro(repo, *args):
    """Read-only Git: only these subcommands, no optional locks, never a prompt or a shell."""
    if args[0] not in GIT_ALLOWED:
        raise UsageError(f'internal error: git {args[0]} is not allowed')
    env = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0'}
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, env=env, timeout=120)


def published(path):
    return path == 'index.html' or path.startswith('data/') or path.startswith('src/')


def check_entry(path, mode, typ):
    if typ == 'commit' or mode == '160000':
        raise UsageError(f'{path} is a submodule; cannot model what the deployment would publish')
    if mode == '120000':
        raise UsageError(f'{path} is a symbolic link; cannot model what the deployment would publish')
    if typ != 'blob' or mode not in ('100644', '100755'):
        raise UsageError(f'{path}: unsupported entry (mode {mode}, type {typ})')


def finish_expected(sha, files, source, detail):
    """files: {path: (blob, size)} for index.html and data/**. Adds the generated version.txt (deploy.yml)."""
    if 'index.html' not in files:
        raise UsageError(f'{sha} has no index.html: not a game commit')
    if not any(p.startswith('data/') for p in files):
        raise UsageError(f'{sha} has no files under data/: not a game commit')
    version = f'{sha}\n'.encode()
    targets = {'version.txt': {'blob': blob_id(version), 'size': len(version), 'generated': True}}
    for p in sorted(files):
        targets[p] = {'blob': files[p][0], 'size': files[p][1], 'generated': False}
    return {'sha': sha, 'source': source, 'detail': detail, 'targets': targets}


def expected_from_git(repo, sha):
    r = git_ro(repo, 'rev-parse', '--git-dir')
    if r.returncode:
        raise UsageError(f'{repo} is not a Git repository')
    if git_ro(repo, 'cat-file', '-e', f'{sha}^{{commit}}').returncode:
        raise UsageError(f'commit {sha} is not in {repo}. Run `git fetch origin` there yourself (this tool never fetches), '
                         'or use --source github')
    r = git_ro(repo, 'ls-tree', '-r', '-l', '-z', sha, '--', 'index.html', 'data', 'src')
    if r.returncode:
        raise UsageError(f'git ls-tree failed: {r.stderr.decode(errors="replace").strip()}')
    files = {}
    for rec in r.stdout.split(b'\0'):
        if not rec:
            continue
        meta, path = rec.decode().split('\t', 1)
        mode, typ, obj, size = meta.split()
        if not published(path):
            continue
        check_entry(path, mode, typ)
        files[path] = (obj, int(size))
    on_main = git_ro(repo, 'merge-base', '--is-ancestor', sha, 'refs/remotes/origin/main').returncode
    detail = {'repo': str(Path(repo).resolve()), 'on_local_origin_main': {0: 'yes', 1: 'no'}.get(on_main, 'unknown')}
    return finish_expected(sha, files, 'local-git', detail)


def api_json(policy, url):
    r = http_get(policy, url, 'api', follow=True, headers={'Accept': 'application/vnd.github+json'})
    if r.error:
        raise SourceUnavailable(f'GitHub API not reachable: {r.error}')
    if r.status in (403, 429) and (r.headers.get('x-ratelimit-remaining') == '0' or 'retry-after' in r.headers):
        reset = r.headers.get('x-ratelimit-reset')
        when = time.strftime('%Y-%m-%d %H:%M:%S Z', time.gmtime(int(reset))) if reset and reset.isdigit() else 'unknown'
        raise SourceUnavailable(f'GitHub API rate limit reached (HTTP {r.status}; resets {when}; '
                                f'Retry-After {r.headers.get("retry-after", "-")})')
    return r


def expected_from_github(policy, api, slug, sha, simulated):
    base = api.rstrip('/') + f'/repos/{slug}'
    try:
        r = api_json(policy, f'{base}/git/commits/{sha}')
        if r.status in (404, 422):
            raise UsageError(f'commit {sha} not found on GitHub ({slug}, HTTP {r.status}); no other commit is tried')
        if r.status != 200:
            raise SourceUnavailable(f'GitHub API answered HTTP {r.status} for the commit')
        commit = json.loads(r.body)
        if commit.get('sha') != sha:
            raise UsageError(f'GitHub returned commit {commit.get("sha")!r} for {sha}; refusing to use another commit')
        tree = commit['tree']['sha']
        requests = 1

        def get_tree(tsha, recursive):
            nonlocal requests
            requests += 1
            if requests > 60:
                raise SourceUnavailable('too many tree requests')
            t = api_json(policy, f'{base}/git/trees/{tsha}' + ('?recursive=1' if recursive else ''))
            if t.status != 200:
                raise SourceUnavailable(f'GitHub API answered HTTP {t.status} for tree {tsha}')
            return json.loads(t.body)

        files = {}

        def add(path, e):
            if not published(path):
                return
            check_entry(path, e.get('mode'), e.get('type'))
            files[path] = (e['sha'], int(e['size']))

        top = get_tree(tree, True)
        if not top.get('truncated'):
            for e in top['tree']:
                if e.get('type') == 'tree':
                    continue
                add(e['path'], e)
        else:                                            # walk the folders one request at a time
            def walk(tsha, prefix):
                t = get_tree(tsha, False)
                if t.get('truncated'):
                    raise SourceUnavailable(f'the tree of {prefix or "/"} is truncated even without recursion; '
                                            'cannot establish the complete expected file list')
                for e in t['tree']:
                    p = prefix + e['path']
                    if e.get('type') == 'tree':
                        if p in ('data', 'src') or p.startswith(('data/', 'src/')):
                            walk(e['sha'], p + '/')
                    else:
                        add(p, e)
            walk(tree, '')
    except Blocked as e:
        raise SourceUnavailable(f'GitHub API request blocked by the network policy: {e}')
    except (KeyError, TypeError, ValueError) as e:
        raise SourceUnavailable(f'unexpected GitHub API response: {e}')
    detail = {'api': api, 'repository': slug, 'tree': tree, 'simulated': simulated, 'tree_requests': requests}
    return finish_expected(sha, files, 'simulated-github' if simulated else 'github', detail)


# ---------------------------------------------------------------- the Deploy workflow's game-file rules

def parse_data(raw):
    if raw[:2] == b'\x1f\x8b':                     # the game also accepts gzip (gunzipFetch)
        raw = gzip.decompress(raw)
    return json.loads(raw)


def structure(name, d):
    """Only what index.html reads without a guard once the city is loaded. Extra keys are allowed."""
    err = []
    if not isinstance(d, dict):
        return [f'{name}.json: top level is not an object']

    def need(key, typ, nonempty=False):
        v = d.get(key)
        if isinstance(v, bool) or not isinstance(v, typ):
            err.append(f'{name}.json: "{key}" missing or of the wrong type')
            return None
        if nonempty and not v:
            err.append(f'{name}.json: "{key}" is empty')
        return v
    if name == 'b':
        ts = need('ts', (int, float))
        if ts is not None and ts <= 0:
            err.append('b.json: "ts" is not positive')
        need('types', list); need('cols', list); need('tiles', dict, True); need('lod', dict)
    elif name == 'r':
        nodes, edges = need('nodes', list, True), need('edges', list, True)
        need('names', list); need('tiles', dict, True)
        if nodes is not None and len(nodes) % 2:
            err.append('r.json: "nodes" has odd length (x,z pairs expected)')
        if nodes and edges:
            n = len(nodes) // 2
            bad = sum(1 for e in edges if not (isinstance(e, list) and len(e) >= 2
                      and all(isinstance(i, int) and not isinstance(i, bool) and 0 <= i < n for i in e[:2])))
            if bad:
                err.append(f'r.json: {bad} edges without two valid node indices')
    elif name == 'm':
        for k in ('water', 'pois', 'cats', 'gkind', 'rail', 'railt', 'aero'):
            need(k, list)
        for k in ('green', 'trees'):
            need(k, dict)
        for k in ('land', 'lakes'):  # read behind a guard: may be absent, must be a list if present
            if k in d and not isinstance(d[k], list):
                err.append(f'm.json: "{k}" is present but not a list')
    return err


def validate_data(targets, matched):
    """deploy.yml's checks on the bytes that matched the commit exactly. Returns (errors, notes, checked)."""
    errors, notes, checked = [], [], []
    if 'index.html' in matched and not matched['index.html']:
        errors.append('index.html is missing or empty')
    for n in ESSENTIAL + OPTIONAL:
        f = f'data/{n}.json'
        if f not in targets:
            (errors if n in ESSENTIAL else notes).append(
                f'{f} is missing (essential)' if n in ESSENTIAL else f'{f} is missing (optional; the game runs without it)')
            continue
        if f not in matched:
            continue
        checked.append(f)
        try:
            d = parse_data(matched[f])
        except Exception as e:
            errors.append(f'{f} is present but not valid JSON: {str(e)[:120]}')
            continue
        if n in ESSENTIAL:
            errors += structure(n, d)
    return errors, notes, checked


# ---------------------------------------------------------------- observations and the verdict

EDGE_HEADERS = ('cache-control', 'age', 'x-cache', 'x-served-by', 'etag', 'last-modified', 'content-length', 'content-encoding')


def make_obs(target, source, url, t, **kw):
    o = {'target': target, 'source': source, 'url': url, 't': round(t, 3), 'wall': time.strftime('%H:%M:%S', time.gmtime()),
         'value': UNAVAILABLE, 'blob': None, 'sha256': None, 'size': None, 'status': None, 'error': None,
         'blocked': False, 'chain': [], 'stage': None, 'edge': {}}
    o.update(kw)
    return o


def classify(o, expected, status, body):
    """Fill in value from an HTTP status and body (status None means a network failure)."""
    o['status'] = status
    if status == 200:
        o.update(blob=blob_id(body), sha256=sha256(body), size=len(body))
        o['value'] = MATCH if o['blob'] == expected['blob'] else DIFF
    elif status in (404, 410):
        o['value'] = MISSING
    else:
        o['value'] = UNAVAILABLE
        o['error'] = o['error'] or (f'HTTP {status}' if status else 'no response')
    return o


def observe_file(policy, expected, path, round_no, t0, nonce):
    url = urllib.parse.urljoin(policy.base, path) + (f'?lc={nonce}' if path == 'version.txt' else '')
    o = make_obs(path, f'round {round_no}', url, time.monotonic() - t0)
    try:
        r = http_get(policy, url, 'site', follow=False)
    except Redirected as e:
        o.update(error=f'redirected ({e.code}) to {e.dest}; expected files must be served directly', chain=[e.dest])
        return o, None
    except Blocked as e:
        o.update(error=f'blocked: {e.reason}', blocked=True, chain=[e.url])
        return o, None
    if r.error:
        o['error'] = r.error
        return o, None
    o['edge'] = {k: r.headers[k] for k in EDGE_HEADERS if k in r.headers}
    classify(o, expected, r.status, r.body)
    if path == 'version.txt' and o['value'] == DIFF:
        o['error'] = f'version.txt says {r.body[:80]!r}'
    return o, (r.body if o['value'] == MATCH else (r.body if r.status == 200 else None))


def series_key(o):
    return (o['value'], o['blob'] if o['value'] == DIFF else None)


def target_verdict(obs, window):
    """One target's observations in time order -> ('match'|'mismatch'|'open', reason, transients)."""
    if not obs:
        return 'open', 'not observed', []
    newest = obs[-1]
    seen = [o for o in obs if o['value'] != UNAVAILABLE]
    transients = [o for o in seen[:-1] if o['value'] != MATCH]
    if newest['value'] == UNAVAILABLE:
        return 'open', f'newest observation ({newest["source"]}) unavailable: {newest["error"]}', transients
    if newest['value'] in (DIFF, MISSING):
        if all(series_key(o) == series_key(newest) for o in seen):
            span = seen[-1]['t'] - seen[0]['t']
            if span >= window:
                return 'mismatch', f'{newest["value"]} in every observation over {span:.0f} s (window {window} s)', []
            return 'open', (f'unconfirmed mismatch: {newest["value"]} seen over {span:.0f} s, shorter than the '
                            f'{window} s confirmation window; re-run with more rounds (e.g. --rounds 3 --interval 300)'), []
        return 'open', 'inconsistent responses (different content in different observations: CDN edges disagree)', []
    if all(o['value'] == MATCH for o in seen):
        return 'match', '', []
    run = []
    for o in reversed(seen):
        if o['value'] != MATCH:
            break
        run.append(o)
    span = run[0]['t'] - run[-1]['t']
    if span >= window:
        return 'match', '', transients
    return 'open', f'still converging: matching for only {span:.0f} s after earlier differences (window {window} s)', []


def content_verdict(series, window):
    """series: {target: [observations in time order]}. Confirmation depends on the time span, never on the count."""
    out = {'verdict': None, 'targets': {}, 'transients': []}
    states = {}
    for t, obs in series.items():
        state, reason, transients = target_verdict(obs, window)
        states[t] = state
        out['targets'][t] = {'state': state, 'reason': reason}
        out['transients'] += [{'target': t, 'source': o['source'], 'value': o['value'], 'blob': o['blob'],
                               'edge': o['edge'].get('x-served-by')} for o in transients]
    if any(s == 'mismatch' for s in states.values()):
        out['verdict'] = FAIL
    elif states and all(s == 'match' for s in states.values()):
        out['verdict'] = PASS
    else:
        out['verdict'] = INCONCLUSIVE
    return out


# ---------------------------------------------------------------- the browser check

class ScriptSrc(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.srcs = []

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            src = dict(attrs).get('src')
            if src:
                self.srcs.append(src)


def startup_scripts(index_bytes, base):
    p = ScriptSrc()
    p.feed(index_bytes.decode('utf-8', 'replace'))
    out = [urllib.parse.urljoin(base, s) for s in p.srcs]
    return [s for s in out if not s.startswith(base)]


def load_chrome():
    """chrome_path() and CHROME_ARGS from tests/game.py, imported without writing __pycache__."""
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT / 'tests'))
    try:
        import game
    finally:
        sys.path.pop(0)
    return game.chrome_path(), list(game.CHROME_ARGS)


def browser_check(policy, expected, base, index_bytes, opts, t0):
    """Start the game with every same-origin request intercepted, hashed and fulfilled with exactly those bytes."""
    res = {'ran': True, 'verdict': None, 'reason': '', 'category': None, 'observations': [], 'other_same_origin': [],
           'external': [], 'page_errors': [], 'console_errors': [], 'websockets_blocked': [], 'webgl_probe': None,
           'signals': {}, 'resolver_rules': None, 'interception_failures': []}
    try:
        from playwright.sync_api import sync_playwright, Error as PWError
    except ImportError:
        raise UsageError('Playwright is not installed (python3 -m pip install -r tests/requirements.txt), or use --no-browser')
    chrome, args = load_chrome()
    if policy.loopback:
        res['resolver_rules'] = policy.chromium_rules(opts.get('sink'))
        args += [f'--host-resolver-rules={res["resolver_rules"]}', '--no-proxy-server']
    args += opts.get('chrome_args', [])
    stubs, fault = opts.get('stubs', {}), opts.get('fault')
    required = startup_scripts(index_bytes, base) if index_bytes is not None else []
    targets = expected['targets']
    pending = [0]

    def rel(url):
        u = urllib.parse.urlsplit(url)
        return urllib.parse.urlunsplit((u.scheme, u.netloc, u.path, '', ''))[len(base):]

    def record_target(o):
        res['observations'].append(o)
        if o['value'] == UNAVAILABLE and o['stage'] in ('fetch', 'fulfill', 'handler', 'redirect'):
            res['interception_failures'].append({'url': o['url'], 'stage': o['stage'], 'error': o['error']})

    def same_origin(route, req):
        url, path = req.url, rel(req.url)
        tgt = targets.get(path)
        o = make_obs(path, 'browser', url, time.monotonic() - t0, resource_type=req.resource_type)
        fetched = None
        cur, chain, stage = url, [], 'fetch'
        try:
            for hop in range(MAX_HOPS + 1):
                ip = policy.allow(cur, 'site')
                headers = dict(req.headers)
                if ip:
                    headers['host'] = urllib.parse.urlsplit(cur).netloc
                fetched = route.fetch(url=policy.literal_url(cur, ip) if ip else cur, headers=headers,
                                      max_redirects=0, timeout=30000)
                loc = fetched.headers.get('location')
                if not (300 <= fetched.status < 400 and loc):
                    break
                dest = urllib.parse.urljoin(cur, loc)
                stage = 'redirect'
                if tgt:
                    raise Redirected(cur, dest, fetched.status)
                if hop == MAX_HOPS:
                    raise Blocked(dest, f'more than {MAX_HOPS} redirects')
                policy.allow(dest, 'site')                # raises before dest is requested
                chain.append(cur)
                cur = dest
            body = fetched.body()
        except Redirected as e:
            o.update(stage='redirect', error=f'redirected ({e.code}) to {e.dest}; expected files must be served directly',
                     chain=chain + [e.dest])
            (record_target(o) if tgt else res['other_same_origin'].append(o))
            route.abort('blockedbyclient')
            return
        except Blocked as e:
            o.update(stage=stage, blocked=True, error=f'blocked: {e.reason}',
                     chain=chain + [e.url])
            (record_target(o) if tgt else res['other_same_origin'].append(o))
            route.abort('blockedbyclient')
            return
        except Exception as e:
            o.update(stage='fetch', error=f'{type(e).__name__}: {str(e)[:300]}')
            (record_target(o) if tgt else res['other_same_origin'].append(o))
            try:
                route.abort('failed')
            except Exception:
                pass
            return
        o['chain'] = chain + ([cur] if chain else [])
        o['edge'] = {k: fetched.headers[k] for k in EDGE_HEADERS if k in fetched.headers}
        if tgt:
            classify(o, tgt, fetched.status, body)
        else:
            o.update(status=fetched.status, size=len(body), value='OTHER')
        try:
            if fault == f'fulfill:{path}':
                raise RuntimeError('injected fulfill failure (SL_LIVE_FAULT)')
            route.fulfill(response=fetched, body=body)
        except Exception as e:
            o.update(value=UNAVAILABLE, stage='fulfill', error=f'fulfill failed: {type(e).__name__}: {str(e)[:300]}')
            try:
                route.abort('failed')
            except Exception:
                pass
        (record_target(o) if tgt else res['other_same_origin'].append(o))

    def on_route(route):
        req = route.request
        pending[0] += 1
        try:
            if req.url.startswith(base):
                same_origin(route, req)
            elif req.url.split('#')[0] in stubs:
                data = Path(stubs[req.url.split('#')[0]]).read_bytes()
                route.fulfill(status=200, body=data, headers={'content-type': 'application/javascript'})
                res['external'].append({'url': req.url, 'result': 'stub', 'required': req.url in required})
            elif policy.loopback:
                res['external'].append({'url': req.url, 'result': 'blocked (loopback mode)', 'required': req.url in required})
                route.abort('blockedbyclient')
            else:
                route.fallback()
        except Exception as e:
            res['interception_failures'].append({'url': req.url, 'stage': 'handler', 'error': f'{type(e).__name__}: {e}'})
            try:
                route.abort('failed')
            except Exception:
                pass
        finally:
            pending[0] -= 1

    def on_ws(ws):
        res['websockets_blocked'].append(ws.url)
        try:
            ws.close()
        except Exception:
            pass

    deadline = time.monotonic() + opts['timeout']
    timed_out = False
    try:
        with sync_playwright() as p:
            try:
                br = p.chromium.launch(executable_path=chrome, headless=True, args=args)
            except PWError as e:
                res.update(verdict=INCONCLUSIVE, reason=f'browser failed to start: {str(e).splitlines()[0]}')
                return res
            try:
                probe = br.new_context(service_workers='block')
                pg = probe.new_page()
                pg.set_content('<canvas id="c"></canvas>')
                res['webgl_probe'] = pg.evaluate("() => { const c = document.getElementById('c'); "
                                                 "return !!(c.getContext('webgl2') || c.getContext('webgl')) }")
                probe.close()
                ctx = br.new_context(viewport={'width': 1366, 'height': 768}, service_workers='block')
                ctx.route_web_socket('**', on_ws)
                ctx.route('**/*', on_route)
                page = ctx.new_page()
                page.on('pageerror', lambda e: res['page_errors'].append({'message': str(e)[:300], 'stack': (getattr(e, 'stack', '') or '')[:600]}))
                page.on('console', lambda m: res['console_errors'].append(m.text[:300]) if m.type == 'error' else None)
                page.on('requestfailed', lambda r: res['external'].append({'url': r.url, 'result': f'failed: {r.failure}', 'required': r.url in required})
                        if not r.url.startswith(base) and not policy.loopback else None)
                page.on('response', lambda r: res['external'].append({'url': r.url, 'result': f'HTTP {r.status}', 'required': r.url in required})
                        if r.status >= 400 and not r.url.startswith(base) and not policy.loopback else None)
                nav = base + f'index.html?lc={opts["nonce"]}'
                try:
                    page.goto(nav, wait_until='load', timeout=max(1000, (deadline - time.monotonic()) * 1000))
                    early = None
                    while True:            # until #loading is gone, the time is up, or startup has clearly failed
                        if page.evaluate("() => !document.getElementById('loading')"):
                            break
                        now = time.monotonic()
                        if now >= deadline:
                            timed_out = True
                            break
                        dep = [x for x in res['external'] if x['required'] and x['result'] != 'stub']
                        if (dep or res['page_errors']) and early is None:
                            early = now
                        if early is not None and now - early > 3:
                            res['signals']['stopped_early'] = 'a required script failed' if dep else 'uncaught error during startup'
                            break
                        page.wait_for_timeout(250)
                except PWError as e:
                    msg = str(e).splitlines()[0]
                    timed_out = 'Timeout' in msg or 'timeout' in msg
                    res['signals']['navigation_error'] = msg[:300]
                # let late same-origin loads (the 3D models) finish: until nothing is pending for 1.5 s
                quiet = time.monotonic()
                while time.monotonic() < min(deadline, quiet + 30):
                    page.wait_for_timeout(250)
                    if pending[0]:
                        quiet = time.monotonic()
                    elif time.monotonic() - quiet > 1.5:
                        break
                try:
                    res['signals'].update(page.evaluate("""() => ({
                        loading_gone: !document.getElementById('loading'),
                        canvas: !!document.querySelector('#stage canvas'),
                        nogl: [...document.querySelectorAll('.nogl')].map(e => e.textContent.slice(0, 160)),
                        intro: !!document.querySelector('#modalRoot #go') })"""))
                except PWError as e:
                    res['signals']['evaluate_error'] = str(e).splitlines()[0][:300]
                if opts.get('screenshot'):
                    res['screenshot_png'] = page.screenshot()
            finally:
                br.close()
    except UsageError:
        raise
    except Exception as e:
        res.update(verdict=INCONCLUSIVE, reason=f'browser infrastructure failure: {type(e).__name__}: {str(e)[:300]}')
        return res
    decide_startup(res, base, required, timed_out)
    return res


def decide_startup(res, base, required, timed_out):
    sig = res['signals']
    obs = res['observations']
    all_match = bool(obs) and all(o['value'] == MATCH for o in obs)
    nav = [o for o in obs if o['target'] == 'index.html' and o.get('resource_type') == 'document']
    dep_missing = [e['url'] for e in res['external'] if e['required'] and e['result'] != 'stub' and not e['result'].startswith('HTTP 2')]
    # optional outside services that failed (weather, SL, the flights relay, news...): a game error at the same time may be
    # their consequence (an unhandled failed fetch is reported as a page error), so it is not attributed to the commit
    optional_failed = [e for e in res['external'] if not e['required'] and e['result'] != 'stub' and not e['result'].startswith('HTTP 2')]
    res['external_failures'] = [{'host': urllib.parse.urlsplit(e['url']).hostname, 'url': e['url'][:150], 'result': e['result']}
                                for e in optional_failed]
    game_errors = [e for e in res['page_errors'] if base in e['stack'] or base in e['message']
                   or not re.search(r'https?://', e['stack'] + e['message'])]
    nogl = sig.get('nogl') or []
    webgl_msg = [t for t in nogl if '3D graphics' in t]
    data_msg = [t for t in nogl if '3D graphics' not in t]
    ok_signals = sig.get('loading_gone') and sig.get('canvas') and not nogl and sig.get('intro')
    problems = []
    if game_errors:
        problems.append(f'uncaught error: {game_errors[0]["message"]}')
    if data_msg:
        problems.append(f'the game reports missing city data: {data_msg[0]}')
    if webgl_msg:
        problems.append(f'the game reports no WebGL: {webgl_msg[0]}')
    if not ok_signals and not timed_out:
        missing = [k for k in ('loading_gone', 'canvas', 'intro') if not sig.get(k)]
        if missing:
            problems.append('startup signals missing: ' + ', '.join(missing))
    if res['interception_failures']:
        f = res['interception_failures'][0]
        res.update(verdict=INCONCLUSIVE, reason=f'tool-side interception failure at {f["url"]} ({f["stage"]}): {f["error"]}')
    elif not nav:
        res.update(verdict=INCONCLUSIVE, reason='navigation not intercepted: no document observation for index.html')
    elif res['webgl_probe'] is False:
        res.update(verdict=INCONCLUSIVE, reason='environment has no WebGL (probe in a blank page failed)')
    elif dep_missing:
        res.update(verdict=INCONCLUSIVE, reason=f'dependency unavailable: cannot test startup without {dep_missing[0]}')
    elif problems:
        if all_match and game_errors and optional_failed and not (data_msg or webgl_msg):
            hosts = sorted({x['host'] or '?' for x in res['external_failures']})
            res.update(verdict=INCONCLUSIVE, category='external-outage-associated-game-error',
                       reason=f'game error while optional outside services failed ({", ".join(hosts)}); it may be caused by '
                       'the outage and cannot be attributed to the commit: ' + '; '.join(problems))
        elif all_match:
            res.update(verdict=FAIL, category='game-defect',
                       reason='the expected commit itself fails to start (every same-origin file matched): ' + '; '.join(problems))
        else:
            bad = [o['target'] for o in obs if o['value'] != MATCH]
            res.update(verdict=INCONCLUSIVE, reason=f'startup failed with non-matching resources ({", ".join(bad)}): '
                       'CDN inconsistency, not attributed to the commit; ' + '; '.join(problems))
    elif timed_out or not ok_signals:
        res.update(verdict=INCONCLUSIVE, reason=f'timeout: {sig.get("navigation_error", "startup did not finish in time")}')
    elif not all_match:
        bad = [o['target'] for o in obs if o['value'] != MATCH]
        res.update(verdict=INCONCLUSIVE, reason=f'the game started, but these files differed for the browser: {", ".join(bad)}')
    else:
        res.update(verdict=PASS, reason='city loaded, WebGL canvas, character creation shown, served files matched')


# ---------------------------------------------------------------- deployment identity (evidence only)

def identity_check(policy, api, slug, index_obs):
    base = api.rstrip('/') + f'/repos/{slug}'
    try:
        r = api_json(policy, f'{base}/deployments?environment=github-pages&per_page=1')
        if r.status != 200 or not json.loads(r.body):
            return {'verdict': SKIP, 'reason': f'no deployment record (HTTP {r.status})'}
        d = json.loads(r.body)[0]
        s = api_json(policy, f'{base}/deployments/{d["id"]}/statuses')
        states = json.loads(s.body) if s.status == 200 else []
    except (SourceUnavailable, Blocked, KeyError, ValueError) as e:
        return {'verdict': SKIP, 'reason': f'unavailable: {e}'}
    ok = next((x for x in states if x.get('state') == 'success'), None)
    out = {'deployment': d.get('id'), 'deployment_sha': d.get('sha'), 'state': states[0].get('state') if states else None,
           'note': 'GitHub records the commit the workflow was started from here, not the commit it published: evidence only'}
    if not ok:
        return {**out, 'verdict': 'WARN', 'reason': 'the latest github-pages deployment has no success status'}
    out['success_at'] = ok.get('created_at')
    lm = next((o['edge'].get('last-modified') for o in reversed(index_obs) if o['edge'].get('last-modified')), None)
    if not lm:
        return {**out, 'verdict': 'INFO', 'reason': 'no Last-Modified header to compare'}
    try:
        t_ok = calendar.timegm(time.strptime(ok['created_at'], '%Y-%m-%dT%H:%M:%SZ'))
        t_lm = email.utils.parsedate_to_datetime(lm).timestamp()
    except Exception:
        return {**out, 'verdict': 'INFO', 'reason': 'could not parse the times'}
    out['last_modified'] = lm
    if abs(t_ok - t_lm) <= 900:
        return {**out, 'verdict': 'INFO', 'reason': f'files Last-Modified {lm} fits the success status at {ok["created_at"]}'}
    return {**out, 'verdict': 'WARN', 'reason': f'files Last-Modified {lm} does not fit the success status at {ok["created_at"]}'}


# ---------------------------------------------------------------- output files

def within(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def safe_output(p, repos, allow_repo):
    """Resolve an output path (following symbolic links in its folder) and refuse unsafe places. Nothing is written here."""
    p = Path(p).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p
    if p.name in ('', '.', '..'):
        raise UsageError(f'{p}: not a file name')
    try:
        folder = p.parent.resolve(strict=True)
    except OSError:
        raise UsageError(f'{p.parent}: folder does not exist')
    target = folder / p.name
    for repo in repos:
        r = Path(repo).resolve()
        if within(target, r / '.git') or within(target, r / 'tests' / 'output'):
            raise UsageError(f'{target}: refusing to write into .git or tests/output')
        if within(target, r) and not allow_repo:
            raise UsageError(f'{target}: inside the repository; choose a path outside it (or pass --allow-repo-output)')
    if os.path.lexists(target):
        raise UsageError(f'{target}: already exists (the tool never overwrites)')
    return target


def write_new(target, data):
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(data)


# ---------------------------------------------------------------- command line

def parse_args(argv):
    a = argparse.ArgumentParser(prog='live_check.py', description=__doc__.split('\n\n')[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument('--expect', required=True, help='the full 40-character SHA of the commit that should be live')
    a.add_argument('--url', default=DEFAULT_URL, help=f'site to check (default {DEFAULT_URL}); http:// means loopback test mode')
    a.add_argument('--source', choices=['git', 'github'], default='git', help='where the expected files come from')
    a.add_argument('--repo', default=str(ROOT), help='Git repository for --source git (default: this repository)')
    a.add_argument('--github-repo', default=DEFAULT_SLUG, help=f'owner/name on GitHub (default {DEFAULT_SLUG})')
    a.add_argument('--rounds', type=int, default=1, help='file-check rounds, 1-20 (default 1)')
    a.add_argument('--interval', type=int, default=300, help='seconds between rounds (default 300)')
    a.add_argument('--confirm-window', type=int, default=None,
                   help=f'seconds a mismatch must persist to count as confirmed (default and minimum on real sites: '
                        f'{DEFAULT_WINDOW} or the CDN max-age, whichever is larger)')
    a.add_argument('--no-browser', action='store_true', help='skip the browser startup check')
    a.add_argument('--browser-anyway', action='store_true', help='run the browser check even if the files did not match')
    a.add_argument('--browser-timeout', type=int, default=180, help='seconds for the game to start (default 180)')
    a.add_argument('--request-timeout', type=int, default=20, help='seconds per HTTP request, 1-120 (default 20)')
    a.add_argument('--require-identity', action='store_true', help='make missing or odd deployment evidence INCONCLUSIVE')
    a.add_argument('--json', help='write the full report as JSON to this new file (outside the repository)')
    a.add_argument('--screenshot', help='write a PNG of the started game to this new file (outside the repository)')
    a.add_argument('--allow-repo-output', action='store_true', help='allow --json/--screenshot inside the repository')
    a.add_argument('--quiet', action='store_true', help='print only the result line')
    a.add_argument('--verbose', action='store_true', help='print every observation')
    return a.parse_args(argv)


def check_args(args):
    if not SHA_RE.match(args.expect or ''):
        raise UsageError('--expect must be a full 40-character lower-case commit SHA (never a branch, tag or short SHA)')
    u = urllib.parse.urlsplit(args.url)
    if u.scheme not in ('http', 'https') or not u.hostname or u.query or u.fragment:
        raise UsageError('--url must be an http(s) URL without query or fragment')
    if u.username is not None or u.password is not None:
        raise UsageError('--url must not contain credentials')
    if not u.path.endswith('/'):
        args.url = urllib.parse.urlunsplit((u.scheme, u.netloc, u.path + '/', '', ''))
    loopback = u.scheme == 'http'
    if loopback and not (ip_literal(u.hostname) or re.fullmatch(r'[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*', u.hostname)):
        raise UsageError('--url host is not a valid name or address')
    if not 1 <= args.rounds <= 20:
        raise UsageError('--rounds must be 1-20')
    lo = 0 if loopback else 30
    if not lo <= args.interval <= 3600:
        raise UsageError(f'--interval must be {lo}-3600 seconds' + ('' if loopback else ' on a real site'))
    if (args.rounds - 1) * args.interval > MAX_SPAN:
        raise UsageError('rounds x interval must not exceed 4 hours')
    if args.confirm_window is not None:
        if args.confirm_window < 0:
            raise UsageError('--confirm-window must be 0 or more')
        if not loopback and args.confirm_window < DEFAULT_WINDOW:
            raise UsageError(f'a confirmation window below the CDN cache time ({DEFAULT_WINDOW} s) is only allowed for '
                             'loopback test servers')
    if not 1 <= args.browser_timeout <= 600:
        raise UsageError('--browser-timeout must be 1-600 seconds')
    if not 1 <= args.request_timeout <= 120:
        raise UsageError('--request-timeout must be 1-120 seconds')
    REQUEST_TIMEOUT[0] = args.request_timeout
    if not SLUG_RE.match(args.github_repo):
        raise UsageError('--github-repo must be owner/name')
    used = [k for k in TEST_ENV if os.environ.get(k)]
    if used and not loopback:
        raise UsageError(f'{", ".join(used)} are test-only settings and are honoured only for loopback (http://) URLs')
    api = os.environ.get('SL_LIVE_GITHUB_API') or GITHUB_API
    if used and 'SL_LIVE_GITHUB_API' in used:
        au = urllib.parse.urlsplit(api)
        if au.scheme != 'http':
            raise UsageError('SL_LIVE_GITHUB_API must be an http:// loopback URL')
    return loopback, api


def test_resolver():
    """SL_LIVE_TEST_RESOLVER: {"host": [["addr", ...], ...]}, one answer per lookup (the last one repeats)."""
    path = os.environ.get('SL_LIVE_TEST_RESOLVER')
    if not path:
        return None, ()
    table = json.loads(Path(path).read_text())
    calls = {}

    def resolve(host, port, type=0, **kw):
        if host not in table:
            return socket.getaddrinfo(host, port, type=type)
        i = calls[host] = calls.get(host, -1) + 1
        answers = table[host]
        addrs = answers[min(i, len(answers) - 1)]
        return [(socket.AF_INET6 if ':' in a else socket.AF_INET, socket.SOCK_STREAM, 6, '', (a, port)) for a in addrs]
    return resolve, tuple(table)


def effective_window(args, loopback, observations):
    ages = []
    for o in observations:
        m = re.search(r'max-age=(\d+)', o['edge'].get('cache-control', ''))
        if m:
            ages.append(int(m.group(1)))
    notes = []
    if loopback and args.confirm_window is not None:
        w = args.confirm_window
    else:
        w = max([args.confirm_window or DEFAULT_WINDOW, DEFAULT_WINDOW] + ages)
    if w > MAX_WINDOW:
        notes.append(f'CDN max-age {w} s capped to {MAX_WINDOW} s')
        w = MAX_WINDOW
    return w, notes


def run(args):
    loopback, api = check_args(args)
    repo = Path(args.repo)
    outputs = {k: safe_output(getattr(args, k), {ROOT, repo}, args.allow_repo_output) for k in ('json', 'screenshot') if getattr(args, k)}
    resolver, names = test_resolver() if loopback else (None, ())
    policy = Policy(args.url, api, resolver=resolver, names=names)
    simulated = loopback and bool(os.environ.get('SL_LIVE_GITHUB_API'))
    report = {'tool': 'tools/live_check.py', 'expect': args.expect, 'url': args.url,
              'network_policy': 'loopback-strict' if loopback else 'production', 'notes': [], 'warnings': []}
    t0 = time.monotonic()
    report['started'] = time.strftime('%Y-%m-%d %H:%M:%S Z', time.gmtime())
    if args.source == 'git':
        exp = expected_from_git(repo, args.expect)
    else:
        if loopback and not simulated:
            raise UsageError('--source github with an http:// site needs SL_LIVE_GITHUB_API (no internet in loopback mode)')
        exp = expected_from_github(policy, api, args.github_repo, args.expect, simulated)
    report['expected'] = exp
    targets = exp['targets']
    plan_span = (args.rounds - 1) * args.interval
    planned_w = args.confirm_window if (loopback and args.confirm_window is not None) else max(args.confirm_window or 0, DEFAULT_WINDOW)
    if args.rounds > 1 and plan_span < planned_w:
        report['warnings'].append(f'this run cannot confirm a mismatch: its rounds span {plan_span} s, less than the '
                                  f'{planned_w} s confirmation window; a mismatch will be INCONCLUSIVE '
                                  f'(e.g. --rounds 3 --interval {max(30, -(-planned_w // 2))})')
    series = {t: [] for t in targets}
    matched = {}
    rounds = []
    for k in range(1, args.rounds + 1):
        if k > 1:
            time.sleep(args.interval)
        nonce = f'{int(time.time())}-{k}'
        rows = []
        for path in targets:
            o, body = observe_file(policy, targets[path], path, k, t0, nonce)
            series[path].append(o)
            rows.append(o)
            if o['value'] == MATCH:
                matched[path] = body
        rounds.append({'round': k, 'complete': all(o['value'] != UNAVAILABLE for o in rows), 'observations': rows})
    report['rounds'] = rounds
    window, wnotes = effective_window(args, loopback, [o for r in rounds for o in r['observations']])
    report['confirm_window'] = window
    report['notes'] += wnotes
    pre = content_verdict(series, window)
    # data validation on bytes identical to the commit
    errors, dnotes, checked = validate_data(targets, matched)
    report['data'] = {'verdict': FAIL if errors else (PASS if checked else SKIP), 'errors': errors, 'notes': dnotes, 'checked': checked}
    if errors:
        report['data']['category'] = 'data-invalid'
        report['data']['explanation'] = ("The expected commit's own data fails the Deploy workflow's validation. Either the "
                                         "workflow's rules changed after this commit was deployed, or the commit was published "
                                         "without passing them. Do not treat this deployment as good.")
    # browser
    if args.no_browser:
        report['browser'] = {'ran': False, 'verdict': SKIP, 'reason': '--no-browser'}
    elif pre['verdict'] != PASS and not args.browser_anyway:
        report['browser'] = {'ran': False, 'verdict': SKIP,
                             'reason': 'skipped: the files did not match the expected commit (use --browser-anyway to diagnose)'}
    else:
        stubs = {}
        if os.environ.get('SL_LIVE_EXTERNAL_STUBS'):
            stubs = json.loads(Path(os.environ['SL_LIVE_EXTERNAL_STUBS']).read_text())
        sink = None
        if os.environ.get('SL_LIVE_TEST_SINK'):
            host, _, dest = os.environ['SL_LIVE_TEST_SINK'].partition('=')
            if not ip_literal(dest.rsplit(':', 1)[0]) or not ip_literal(dest.rsplit(':', 1)[0]).is_loopback:
                raise UsageError('SL_LIVE_TEST_SINK must map to a loopback address')
            sink = (host, dest)
        opts = {'timeout': args.browser_timeout, 'nonce': f'{int(time.time())}-b', 'stubs': stubs, 'sink': sink,
                'fault': os.environ.get('SL_LIVE_FAULT'), 'screenshot': bool(outputs.get('screenshot')),
                'chrome_args': (os.environ.get('SL_LIVE_TEST_CHROME_ARGS') or '').split()}
        b = browser_check(policy, exp, policy.base, matched.get('index.html'), opts, t0)
        png = b.pop('screenshot_png', None)
        if png is not None and outputs.get('screenshot'):
            write_new(outputs['screenshot'], png)
        report['browser'] = b
        for o in b.get('observations', []):
            if o['target'] in series:
                series[o['target']].append(o)
    final = content_verdict(series, window)
    if final['verdict'] == FAIL:
        final['category'] = 'content-mismatch'
    report['content'] = final
    # identity
    if loopback and not simulated:
        report['identity'] = {'verdict': SKIP, 'reason': 'disabled in loopback mode'}
    else:
        report['identity'] = identity_check(policy, api, args.github_repo, series.get('index.html', []))
    report['network'] = {'pins': policy.pins, 'resolver_calls': policy.resolver_calls, 'connections': policy.connections}
    # overall
    parts = [final['verdict'], report['data']['verdict'], report['browser']['verdict']]
    if args.require_identity and report['identity']['verdict'] in (SKIP, 'WARN'):
        parts.append(INCONCLUSIVE)
    if FAIL in parts:
        overall = FAIL
    elif INCONCLUSIVE in parts:
        overall = INCONCLUSIVE
    else:
        overall = PASS
    report['categories'] = [c for c in (final.get('category'), report['data'].get('category'), report['browser'].get('category')) if c]
    report['result'] = overall
    complete_matching = [r for r in rounds if r['complete'] and all(o['value'] == MATCH for o in r['observations'])]
    if overall == PASS and len(complete_matching) == 1:
        report['warnings'].append('PASS from one complete observation round: each request reaches a single CDN edge, so '
                                  'stale content on other edges cannot be ruled out; after a deployment use '
                                  '--rounds 3 --interval 300 or more')
    report['exit'] = EXIT[overall]
    report['finished'] = time.strftime('%Y-%m-%d %H:%M:%S Z', time.gmtime())
    if outputs.get('json'):
        write_new(outputs['json'], json.dumps(report, indent=1, default=str).encode())
    return report


def print_report(r, quiet, verbose):
    e = r['expected']
    out = []
    if not quiet:
        out.append(f'Stockholm Life live check: {r["url"]}  ({r["network_policy"]})')
        dt = e['detail']
        if e['source'] == 'local-git':
            src = f'LOCAL GIT {dt["repo"]} - commit {e["sha"]} present (on local origin/main: {dt["on_local_origin_main"]})'
        else:
            src = (('SIMULATED GITHUB API' if e['source'] == 'simulated-github' else 'GITHUB API') + f' {dt["api"]}'
                   + (' (TEST ONLY)' if e['source'] == 'simulated-github' else '') + f' - commit {e["sha"]}, tree {dt["tree"]}')
        out.append(f'Expected source: {src}')
        n = len(e['targets'])
        out.append(f'Targets: {n} (index.html, {n - 2} data files, version.txt); confirmation window {r["confirm_window"]} s')
        for w in r['warnings'] + r['notes']:
            out.append(f'  note: {w}')
        for rd in r['rounds']:
            obs = rd['observations']
            bad = [o for o in obs if o['value'] != MATCH]
            out.append(f'[round {rd["round"]}] {len(obs) - len(bad)} of {len(obs)} match' + ('' if rd['complete'] else ' (incomplete)'))
            for o in (obs if verbose else bad):
                out.append(f'    {o["value"]:11} {o["target"]}  {o["error"] or ""} {o["blob"] or ""}'.rstrip()
                           + (f'  edge {o["edge"].get("x-served-by")}' if o['edge'].get('x-served-by') else ''))
        c = r['content']
        out.append(f'[{c["verdict"]}] content')
        for t, s in c['targets'].items():
            if s['state'] != 'match':
                out.append(f'    {t}: {s["reason"]}')
        for tr in c['transients']:
            out.append(f'    WARN transient: {tr["target"]} was {tr["value"]} in {tr["source"]}' + (f' (edge {tr["edge"]})' if tr['edge'] else ''))
        d = r['data']
        out.append(f'[{d["verdict"]}] data validation ({len(d["checked"])} files checked with the Deploy workflow rules)')
        for x in d['errors']:
            out.append(f'    error: {x}')
        if d.get('explanation'):
            out.append(f'    {d["explanation"]}')
        b = r['browser']
        out.append(f'[{b["verdict"]}] browser startup: {b.get("reason", "")}')
        if b.get('ran'):
            ext = b.get('external', [])
            if ext:
                out.append(f'    external requests: ' + '; '.join(f'{x["url"][:70]} {x["result"]}' for x in ext[:8]))
            for x in b.get('other_same_origin', []):
                out.append(f'    WARN unexpected same-origin request: {x["url"]} -> {x["status"] or x["error"]}')
            for x in b.get('external_failures', [])[:10]:
                out.append(f'    outside service failed: {x["host"]} {x["url"]} ({x["result"]})')
            for x in b.get('console_errors', [])[:5]:
                out.append(f'    console error: {x}')
        i = r['identity']
        out.append(f'[{i["verdict"]}] deployment identity: {i.get("reason", "")}')
    why = ', '.join(r['categories']) if r['categories'] else ''
    out.append(f'RESULT: {r["result"]}' + (f' ({why})' if why else '') + f'   exit {r["exit"]}')
    print('\n'.join(out))


def main(argv=None):
    try:
        args = parse_args(argv)
        report = run(args)
    except UsageError as e:
        print(f'live_check: {e}', file=sys.stderr)
        return USAGE_EXIT
    except SourceUnavailable as e:
        print(f'RESULT: INCONCLUSIVE (expected files): {e}   exit 2')
        return EXIT[INCONCLUSIVE]
    except Exception:                               # an internal error is never reported as PASS or FAIL
        import traceback
        traceback.print_exc()
        print('live_check: internal error (exit 3); nothing was verified', file=sys.stderr)
        return USAGE_EXIT
    print_report(report, args.quiet, args.verbose)
    return report['exit']


if __name__ == '__main__':
    sys.exit(main())
