"""tools/live_check.py: verdict rules, expected sources, the network policy (redirects, DNS pinning), the Deploy
workflow's data rules and the browser check.

Nothing here uses the internet. Sites, Git repositories, a simulated GitHub API and stub files are built in pytest's
tmp_path and served on loopback; the tool runs in loopback-strict mode (an http:// site URL), where it refuses every
non-loopback destination. The browser tests (marked browser) start a generated site with the game's startup contract,
not the real game (whose CDN dependencies would need the internet); test_startup_contract_in_game keeps the two in
step. Run offline to prove it: unshare -rn sh -c 'ip link set lo up && python3 -m pytest tests/test_live_check.py'
"""
import ast, gzip, http.server, importlib.util, json, os, re, socket, subprocess, sys, threading, time, urllib.parse, uuid
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / 'tools' / 'live_check.py'
sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location('live_check', TOOL)
lc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lc)

GOOD = {
    'data/b.json': json.dumps({'ts': 10, 'types': [], 'cols': [], 'tiles': {'0,0': []}, 'lod': {}}).encode(),
    'data/r.json': json.dumps({'nodes': [0, 0, 1, 1], 'edges': [[0, 1]], 'names': [], 'tiles': {'0,0': []}}).encode(),
    'data/m.json': json.dumps({'water': [], 'pois': [], 'cats': [], 'gkind': [], 'rail': [], 'railt': [], 'aero': [],
                               'green': {}, 'trees': {}}).encode(),
}
DEP = 'https://cdn.example.invalid/dep.js'
# Chromium's own Local Network Access check refuses page requests to a name mapped to loopback before any connection,
# which would hide a leak from the sink tests; switching it off (test-only) makes the sink a real detector.
NO_LNA = '--disable-features=LocalNetworkAccessChecks,PrivateNetworkAccessRespectPreflightResults'
LOOP = ['--confirm-window', '0', '--interval', '0']


# ---------------------------------------------------------------- helpers: Git repositories, sites, the tool

def git(repo, *a):
    env = {**os.environ, 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_AUTHOR_NAME': 't',
           'GIT_AUTHOR_EMAIL': 't@example.invalid', 'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@example.invalid',
           'GIT_AUTHOR_DATE': '2026-01-01T00:00:00Z', 'GIT_COMMITTER_DATE': '2026-01-01T00:00:00Z'}
    return subprocess.run(['git', '-C', str(repo), *a], check=True, capture_output=True, env=env).stdout.decode().strip()


def commit(repo, files, links=()):
    """Make the throwaway repository hold exactly these files (and symbolic links) and commit; returns the SHA."""
    repo.mkdir(exist_ok=True)
    if not (repo / '.git').exists():
        git(repo, 'init', '-q', '-b', 'main')
    else:
        git(repo, 'rm', '-rq', '--ignore-unmatch', '.')
    for p, data in files.items():
        f = repo / p
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
    for p, dest in links:
        (repo / p).parent.mkdir(parents=True, exist_ok=True)
        os.symlink(dest, repo / p)
    git(repo, 'add', '-A')
    git(repo, 'commit', '-q', '--allow-empty', '-m', 'c')
    return git(repo, 'rev-parse', 'HEAD')


def page(datafiles, extra='', head=''):
    """A generated game page with the real game's startup contract (see STARTUP_MARKERS)."""
    return f'''<!doctype html><html><head><meta charset="utf-8"><link rel="icon" href="data:,">{head}
<script src="{DEP}"></script></head>
<body><section class="stage" id="stage"></section><div class="loading" id="loading">Loading</div><div id="modalRoot"></div>
<script>
(async () => {{
  if (!window.DEP_OK) throw new Error('dependency missing');
  const st = document.getElementById('stage');
  const c = document.createElement('canvas'); st.appendChild(c);
  if (!(c.getContext('webgl2') || c.getContext('webgl'))) {{ const n = document.createElement('div'); n.className = 'nogl'; n.textContent = 'Your browser could not start 3D graphics (WebGL)'; st.appendChild(n) }}
  let ok = true;
  for (const f of {json.dumps(datafiles)}) {{ try {{ const r = await fetch(f); if (!r.ok) throw 0; await r.arrayBuffer() }} catch (e) {{ if (/\\/(b|r|m)\\.json$/.test(f)) ok = false }} }}
  if (!ok) {{ const n = document.createElement('div'); n.className = 'nogl'; n.textContent = 'Could not load the city data from the data/ folder'; st.appendChild(n) }}
  {extra}
  document.getElementById('loading').remove();
  document.getElementById('modalRoot').innerHTML = '<button id="go">Go</button>';
}})();
</script></body></html>'''.encode()


def game_files(data=None, extra='', head=''):
    data = dict(GOOD if data is None else data)
    return {'index.html': page(sorted(data), extra, head), **data}


class Site:
    """A loopback web server. files: path -> bytes; hooks: path -> fn(handler) that answers instead (return True)."""

    def __init__(self, files, gzip_transport=False):
        self.files, self.hooks, self.log, self.gz = dict(files), {}, [], gzip_transport
        site = self

        class H(http.server.BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *a):
                pass

            def do_GET(self):
                u = urllib.parse.urlsplit(self.path)
                path = urllib.parse.unquote(u.path.lstrip('/'))
                site.log.append({'path': path, 'query': u.query, 'ua': self.headers.get('User-Agent', ''),
                                 'host': self.headers.get('Host'), 'peer': self.client_address[0],
                                 'auth': self.headers.get('Authorization')})
                hook = site.hooks.get(path)
                if hook and hook(self):
                    return
                if path in site.files:
                    body = site.files[path]
                    body = body(self) if callable(body) else body
                    ct = 'text/html; charset=utf-8' if path.endswith('.html') else 'application/json' if path.endswith('.json') \
                        else 'text/plain; charset=utf-8'
                    send(self, 200, body, {'Content-Type': ct, 'Cache-Control': 'max-age=600'}, site.gz)
                else:
                    send(self, 404, b'not found')

        self.srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.port = self.srv.server_address[1]
        self.url = f'http://127.0.0.1:{self.port}/'

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()

    def hits(self, path):
        return [x for x in self.log if x['path'] == path]


def send(h, status, body=b'', headers=None, gz=False):
    headers = dict(headers or {})
    if gz and 'gzip' in h.headers.get('Accept-Encoding', ''):
        body = gzip.compress(body)
        headers['Content-Encoding'] = 'gzip'
    h.send_response(status)
    for k, v in headers.items():
        h.send_header(k, v)
    h.send_header('Content-Length', str(len(body)))
    h.end_headers()
    h.wfile.write(body)
    return True


def redirect(to, code=302):
    return lambda h: send(h, code, b'', {'Location': to})


def browser_ua(h):
    return 'Mozilla' in h.headers.get('User-Agent', '')


@pytest.fixture
def site_for(tmp_path):
    """site_for(files) -> (repo, sha, Site) with the files committed and published, version.txt included."""
    made = []

    def make(files, links=(), gzip_transport=False, repo_name='repo'):
        repo = tmp_path / repo_name
        sha = commit(repo, files, links)
        s = Site({**files, 'version.txt': f'{sha}\n'.encode()}, gzip_transport)
        made.append(s)
        return repo, sha, s
    yield make
    for s in made:
        s.close()


def stubs_env(tmp_path, with_dep=True):
    dep = tmp_path / 'dep.js'
    dep.write_text('window.DEP_OK = true;')
    f = tmp_path / f'stubs-{uuid.uuid4().hex[:6]}.json'
    f.write_text(json.dumps({DEP: str(dep)} if with_dep else {}))
    return {'SL_LIVE_EXTERNAL_STUBS': str(f)}


def run_tool(tmp_path, *args, env=None, timeout=300):
    """Run the tool as a real process (no inherited SL_LIVE_* or tokens). Returns (exit code, report or None, output)."""
    out = tmp_path / f'report-{uuid.uuid4().hex[:8]}.json'
    e = {k: v for k, v in os.environ.items() if not k.startswith('SL_LIVE_') and k not in ('GITHUB_TOKEN', 'GH_TOKEN')}
    e.pop('PYTHONDONTWRITEBYTECODE', None)          # the tool must not need it to leave no __pycache__
    e.update(env or {})
    p = subprocess.run([sys.executable, str(TOOL), *args, '--json', str(out)], capture_output=True, text=True,
                       env=e, timeout=timeout)
    rep = json.loads(out.read_text()) if out.exists() else None
    return p.returncode, rep, p.stdout + p.stderr


def check(tmp_path, repo, sha, site, *extra, env=None, browser=False):
    args = ['--expect', sha, '--url', site.url, '--repo', str(repo), *LOOP, *extra]
    if not browser:
        args.append('--no-browser')
    return run_tool(tmp_path, *args, env=env)


class Guard:
    """Records every lookup and connection in this process and refuses anything that is not loopback."""

    def __init__(self, monkeypatch):
        self.bad, self.lookups = [], []
        real_cc, real_gai = socket.create_connection, socket.getaddrinfo

        def cc(addr, *a, **k):
            ip = lc.ip_literal(str(addr[0]))
            if not (ip and ip.is_loopback):
                self.bad.append(('connect', addr))
                raise OSError('guard: non-loopback connection refused')
            return real_cc(addr, *a, **k)

        def gai(host, *a, **k):
            self.lookups.append(host)
            ip = lc.ip_literal(str(host))
            if not (host == 'localhost' or (ip and ip.is_loopback)):
                self.bad.append(('lookup', host))
                raise OSError('guard: lookup refused')
            return real_gai(host, *a, **k)
        monkeypatch.setattr(socket, 'create_connection', cc)
        monkeypatch.setattr(socket, 'getaddrinfo', gai)


def fake_resolver(table):
    calls = {}

    def resolve(host, port, type=0, **kw):
        if host not in table:
            raise OSError(f'unknown host {host}')
        i = calls[host] = calls.get(host, -1) + 1
        ans = table[host]
        addrs = ans[min(i, len(ans) - 1)]
        return [(socket.AF_INET6 if ':' in a else socket.AF_INET, socket.SOCK_STREAM, 6, '', (a, port)) for a in addrs]
    return resolve, calls


# ---------------------------------------------------------------- verdict rules (no network)

def obs(value, t, blob=None, source='round 1', error=None):
    return {'target': 'f', 'source': source, 't': t, 'value': value, 'blob': blob, 'error': error, 'edge': {}}


@pytest.mark.parametrize('series,window,want', [
    ([obs('MATCH', 0)], 600, 'PASS'),                                                        # V1
    ([obs('MATCH', 0), obs('MATCH', 300), obs('MATCH', 600)], 600, 'PASS'),
    ([obs('DIFF', 0, 'x'), obs('DIFF', 300, 'x'), obs('DIFF', 600, 'x')], 600, 'FAIL'),      # confirmed
    ([obs('DIFF', 0, 'x'), obs('MATCH', 300), obs('MATCH', 900)], 600, 'PASS'),              # transient then match
    ([obs('DIFF', 0, 'x'), obs('MATCH', 300), obs('MATCH', 500)], 600, 'INCONCLUSIVE'),      # still converging
    ([obs('DIFF', 0, 'x'), obs('MATCH', 300), obs('DIFF', 600, 'x')], 600, 'INCONCLUSIVE'),  # edges disagree
    ([obs('MATCH', 0), obs('UNAVAILABLE', 300), obs('MATCH', 600)], 600, 'PASS'),           # failure mid-run
    ([obs('MATCH', 0), obs('MATCH', 300), obs('UNAVAILABLE', 600)], 600, 'INCONCLUSIVE'),   # failure at the end
    ([obs('DIFF', 0, 'x')], 600, 'INCONCLUSIVE'),                                            # one round, unconfirmed
    ([obs('DIFF', 0, 'x'), obs('DIFF', 300, 'x')], 600, 'INCONCLUSIVE'),                     # V3 span < W
    ([obs('DIFF', 0, 'x'), obs('DIFF', 300, 'y'), obs('DIFF', 700, 'y')], 600, 'INCONCLUSIVE'),  # V4 changing IDs
    ([obs('MISSING', 0), obs('MISSING', 700)], 600, 'FAIL'),
    ([obs('MATCH', 0), obs('MATCH', 1), obs('DIFF', 2, 'x', 'browser')], 600, 'INCONCLUSIVE'),   # V5 browser differs
    ([obs('MATCH', 0), obs('MATCH', 2, source='browser')], 600, 'PASS'),                        # V6
    ([obs('DIFF', 0, 'x'), obs('DIFF', 700, 'x', 'browser')], 600, 'FAIL'),                     # V7
    ([obs('DIFF', 0, 'x'), obs('DIFF', 20, 'x', 'browser')], 600, 'INCONCLUSIVE'),              # V8 no double counting
    ([obs('MATCH', 0), obs('MATCH', 600), obs('UNAVAILABLE', 601, source='browser')], 600, 'INCONCLUSIVE'),  # V9
    ([obs('DIFF', 0, 'x')], 0, 'FAIL'),                                                      # W = 0 (loopback tests)
])
def test_verdict_rules(series, window, want):
    assert lc.content_verdict({'f': series}, window)['verdict'] == want


def test_verdict_reports_transients():
    v = lc.content_verdict({'f': [obs('DIFF', 0, 'x'), obs('MATCH', 300), obs('MATCH', 900)]}, 600)
    assert v['verdict'] == 'PASS' and v['transients'] and v['transients'][0]['value'] == 'DIFF'


# ---------------------------------------------------------------- arguments and the confirmation window (W1-W4, S5)

@pytest.mark.parametrize('argv', [
    ['--expect', 'a' * 40, '--url', 'https://example.invalid/', '--confirm-window', '0'],     # W1
    ['--expect', 'a' * 40, '--url', 'https://example.invalid/', '--confirm-window', '599'],
    ['--expect', 'a' * 40, '--rounds', '0'], ['--expect', 'a' * 40, '--rounds', '21'],       # W3
    ['--expect', 'a' * 40, '--url', 'https://example.invalid/', '--interval', '10'],
    ['--expect', 'a' * 40, '--rounds', '20', '--interval', '3600'],
    ['--expect', 'main'], ['--expect', 'abc1234'], ['--expect', 'z' * 40], ['--expect', ''],  # S5
    ['--expect', 'a' * 40, '--url', 'ftp://127.0.0.1/'], ['--expect', 'a' * 40, '--url', 'http://u:p@127.0.0.1/'],
])
def test_bad_arguments_exit_3_without_network(argv, monkeypatch, capsys):
    g = Guard(monkeypatch)
    assert lc.main(argv) == 3
    assert g.bad == [] and g.lookups == [], 'a usage error must stop before any lookup or connection'


@pytest.mark.parametrize('var', lc.TEST_ENV)
def test_test_settings_refused_on_real_sites(monkeypatch, capsys, var):
    g = Guard(monkeypatch)
    head = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    monkeypatch.setenv(var, 'http://127.0.0.1:9/')          # the only thing wrong with this run
    assert lc.main(['--expect', head, '--url', 'https://example.invalid/', '--no-browser']) == 3
    assert 'test-only settings' in capsys.readouterr().err
    assert g.bad == [] and g.lookups == []


def test_short_span_warns(tmp_path, site_for):
    repo, sha, site = site_for(game_files())
    code, rep, out = run_tool(tmp_path, '--expect', sha, '--url', site.url, '--repo', str(repo), '--rounds', '2',
                              '--interval', '0', '--no-browser')                                # W4
    assert code == 0 and any('cannot confirm a mismatch' in w for w in rep['warnings']), out


# ---------------------------------------------------------------- expected sources and targets (T1, T2, G1-G7, S6)

def test_targets_follow_the_commit(tmp_path):                                                    # T1
    repo = tmp_path / 'repo'
    s1 = commit(repo, game_files())
    s2 = commit(repo, game_files({**GOOD, 'data/extra.json': b'{}'}))
    assert len(lc.expected_from_git(repo, s1)['targets']) == 5
    assert len(lc.expected_from_git(repo, s2)['targets']) == 6


def test_targets_of_this_repository():                                                          # T2
    sha = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    n = len(subprocess.run(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', sha, '--', 'index.html', 'data'],
                           capture_output=True, text=True).stdout.split())
    exp = lc.expected_from_git(ROOT, sha)
    assert len(exp['targets']) == n + 1 and exp['targets']['version.txt']['blob'] == lc.blob_id(f'{sha}\n'.encode())


def test_blob_id_is_git():
    data = b'Stockholm \xc3\xa5\xc3\xa4\xc3\xb6\n'
    want = subprocess.run(['git', 'hash-object', '--stdin'], input=data, capture_output=True).stdout.decode().strip()
    assert lc.blob_id(data) == want


@pytest.mark.parametrize('files,links,why', [
    ({'README': b'x', **GOOD}, (), 'no index.html'),
    ({'index.html': b'x'}, (), 'no files under data/'),
    (game_files(), (('data/link.json', 'b.json'),), 'symbolic link'),
])
def test_unmodellable_commits(tmp_path, files, links, why):                                     # G5, G7
    sha = commit(tmp_path / 'repo', files, links)
    with pytest.raises(lc.UsageError, match=why):
        lc.expected_from_git(tmp_path / 'repo', sha)


def test_sha_not_in_repository(tmp_path, site_for):                                              # S6
    repo, sha, site = site_for(game_files())
    refs = git(repo, 'for-each-ref')
    code, rep, out = run_tool(tmp_path, '--expect', 'b' * 40, '--url', site.url, '--repo', str(repo), *LOOP)
    assert code == 3 and 'git fetch origin' in out and git(repo, 'for-each-ref') == refs
    assert site.log == []


class FakeAPI(Site):
    """The parts of GitHub's REST API the tool uses, answered from a throwaway repository."""

    def __init__(self, repo, slug='o/r', truncate=False, truncate_all=False):
        super().__init__({})
        self.repo, self.slug, self.truncate, self.truncate_all = repo, slug, truncate, truncate_all
        api = self
        base = f'repos/{slug}/git/'

        def answer(h):
            u = urllib.parse.urlsplit(h.path)
            path = u.path.lstrip('/')
            if path.startswith(base + 'commits/'):
                sha = path.rsplit('/', 1)[1]
                try:
                    tree = git(repo, 'rev-parse', f'{sha}^{{tree}}')
                except subprocess.CalledProcessError:
                    return send(h, 404, b'{"message":"Not Found"}')
                return send(h, 200, json.dumps({'sha': api.claim or sha, 'tree': {'sha': tree}}).encode())
            if path.startswith(base + 'trees/'):
                tsha, rec = path.rsplit('/', 1)[1], 'recursive=1' in u.query
                out = git(repo, 'ls-tree', '-l', *(['-r', '-t'] if rec else []), tsha)
                tree = []
                for line in out.splitlines():
                    meta, p = line.split('\t', 1)
                    mode, typ, obj, size = meta.split()
                    e = {'path': p, 'mode': mode, 'type': typ, 'sha': obj}
                    if typ == 'blob':
                        e['size'] = int(size)
                    tree.append(e)
                return send(h, 200, json.dumps({'sha': tsha, 'tree': tree,
                                                'truncated': (rec and api.truncate) or api.truncate_all}).encode())
            return send(h, 404, b'{"message":"Not Found"}')
        self.claim = None
        self.answer = answer
        self.hooks = _AllHooks(answer)
        self.api = self.url.rstrip('/')


class _AllHooks(dict):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def get(self, path, default=None):
        return super().get(path) or self.fn


def loop_policy(api_url='http://127.0.0.1:9', **kw):
    return lc.Policy('http://127.0.0.1:9/', api_url, **kw)


@pytest.mark.parametrize('truncate', [False, True])
def test_github_source_equals_local_git(tmp_path, truncate):                                     # G1, G2''
    repo = tmp_path / 'repo'
    sha = commit(repo, game_files({**GOOD, 'data/sub/deep.json': b'{}'}))
    api = FakeAPI(repo, truncate=truncate)
    try:
        exp = lc.expected_from_github(loop_policy(api.api), api.api, 'o/r', sha, True)
        assert exp['targets'] == lc.expected_from_git(repo, sha)['targets']
        assert exp['source'] == 'simulated-github'
    finally:
        api.close()


def test_github_tree_truncated_even_without_recursion(tmp_path):                                 # G2'
    repo = tmp_path / 'repo'
    sha = commit(repo, game_files())
    api = FakeAPI(repo, truncate_all=True)
    try:
        with pytest.raises(lc.SourceUnavailable, match='truncated even without recursion'):
            lc.expected_from_github(loop_policy(api.api), api.api, 'o/r', sha, True)
        code, rep, out = run_tool(tmp_path, '--expect', sha, '--url', 'http://127.0.0.1:9/', '--source', 'github',
                                  '--github-repo', 'o/r', *LOOP, env={'SL_LIVE_GITHUB_API': api.api})
        assert code == 2, out
    finally:
        api.close()


def test_github_commit_not_found_and_other_commit(tmp_path):                                    # G3, G6
    repo = tmp_path / 'repo'
    sha = commit(repo, game_files())
    api = FakeAPI(repo)
    try:
        with pytest.raises(lc.UsageError, match='not found on GitHub'):
            lc.expected_from_github(loop_policy(api.api), api.api, 'o/r', 'c' * 40, True)
        assert len(api.log) == 1, 'no other commit or branch may be tried'
        api.claim = 'd' * 40
        with pytest.raises(lc.UsageError, match='refusing to use another commit'):
            lc.expected_from_github(loop_policy(api.api), api.api, 'o/r', sha, True)
    finally:
        api.close()


@pytest.mark.parametrize('status,headers', [(403, {'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': '1900000000'}),
                                            (429, {'Retry-After': '30'})])
def test_github_rate_limit(tmp_path, status, headers):                                           # G4
    api = Site({})
    api.hooks = _AllHooks(lambda h: send(h, status, b'{}', headers))
    try:
        with pytest.raises(lc.SourceUnavailable, match='rate limit'):
            lc.expected_from_github(loop_policy(api.url), api.url.rstrip('/'), 'o/r', 'a' * 40, True)
        assert len(api.log) == 1, 'no further requests after a rate limit'
    finally:
        api.close()


def test_github_source_sends_no_token(tmp_path, site_for):                                       # S4
    repo, sha, site = site_for(game_files())
    api = FakeAPI(repo)
    try:
        code, rep, out = run_tool(tmp_path, '--expect', sha, '--url', site.url, '--source', 'github', '--github-repo', 'o/r',
                                  '--no-browser', *LOOP, env={'SL_LIVE_GITHUB_API': api.api, 'GITHUB_TOKEN': 'test-token-not-real',
                                                               'GH_TOKEN': 'test-token-not-real'})
        assert code == 0, out
        assert api.log and all(x['auth'] is None for x in api.log), 'an Authorization header was sent'
        assert 'SIMULATED GITHUB API' in out and rep['expected']['source'] == 'simulated-github'
    finally:
        api.close()


# ---------------------------------------------------------------- file checks against a loopback site (F1-F12, R3)

def test_exact_files_pass(tmp_path, site_for):                                                   # F1
    repo, sha, site = site_for(game_files())
    code, rep, out = check(tmp_path, repo, sha, site)
    assert code == 0 and rep['result'] == 'PASS', out
    assert 'LOCAL GIT' in out and 'Targets: 5' in out


SINGLE = 'PASS from one complete observation round'


def test_single_round_pass_warns(tmp_path, site_for):
    repo, sha, site = site_for(game_files())
    code, rep, out = check(tmp_path, repo, sha, site)
    assert code == 0 and SINGLE in out and 'stale content on other edges cannot be ruled out' in out, out
    assert any(w.startswith(SINGLE) for w in rep['warnings'])


def test_single_complete_round_after_a_failed_round_warns(tmp_path, site_for):
    repo, sha, site = site_for(game_files())
    n, body = [0], site.files['data/m.json']

    def first_fails(h):
        n[0] += 1
        return send(h, 503, b'') if n[0] == 1 else send(h, 200, body, {'Content-Type': 'application/json'})
    site.hooks['data/m.json'] = first_fails
    code, rep, out = check(tmp_path, repo, sha, site, '--rounds', '2')
    assert code == 0 and SINGLE in out, out


def test_two_complete_rounds_do_not_warn(tmp_path, site_for):
    repo, sha, site = site_for(game_files())
    code, rep, out = check(tmp_path, repo, sha, site, '--rounds', '2')
    assert code == 0 and SINGLE not in out, out
    code, rep, out = check(tmp_path, repo, sha, site, '--rounds', '2', '--confirm-window', '600')
    assert code == 0 and SINGLE not in out and 'cannot confirm a mismatch' in out, out


def test_version_mismatch(tmp_path, site_for):                                                   # F2
    repo, sha, site = site_for(game_files())
    site.files['version.txt'] = ('e' * 40 + '\n').encode()
    code, rep, out = check(tmp_path, repo, sha, site)
    assert code == 1 and rep['categories'] == ['content-mismatch'] and 'version.txt says' in out
    code, rep, out = run_tool(tmp_path, '--expect', sha, '--url', site.url, '--repo', str(repo), '--interval', '0', '--no-browser')
    assert code == 2 and 'unconfirmed mismatch' in out                                           # default window


def test_right_version_wrong_index(tmp_path, site_for):                                         # F3
    repo, sha, site = site_for(game_files())
    site.files['index.html'] = page(sorted(GOOD), extra='/* an older build */')
    code, rep, out = check(tmp_path, repo, sha, site)
    assert code == 1 and rep['content']['targets']['index.html']['state'] == 'mismatch'
    assert rep['content']['targets']['version.txt']['state'] == 'match', 'version.txt alone must not be trusted'


def test_missing_and_corrupted_data(tmp_path, site_for):                                        # F4, F5
    repo, sha, site = site_for(game_files())
    del site.files['data/r.json']
    site.files['data/b.json'] = b'{"ts": 1'
    code, rep, out = check(tmp_path, repo, sha, site)
    assert code == 1
    assert rep['content']['targets']['data/r.json']['state'] == 'mismatch'
    assert [o['value'] for o in rep['rounds'][0]['observations'] if o['target'] == 'data/b.json'] == ['DIFF']


@pytest.mark.parametrize('content', ['{sha}', '{sha}\r\n', '{sha}\nextra\n', ' {sha}\n'])
def test_version_format_is_exact(tmp_path, site_for, content):                                  # F6
    repo, sha, site = site_for(game_files())
    site.files['version.txt'] = content.format(sha=sha).encode()
    code, rep, out = check(tmp_path, repo, sha, site)
    assert code == 1 and 'version.txt says' in out


def test_gzip_in_transit_and_gzip_files(tmp_path, site_for):                                    # F7, R3
    data = {**GOOD, 'data/x.json': gzip.compress(b'{"x": "\xc3\xa5"}')}                       # a file that is itself gzip
    repo, sha, site = site_for(game_files(data), gzip_transport=True)
    code, rep, out = check(tmp_path, repo, sha, site)
    assert code == 0, out
    x = [o for o in rep['rounds'][0]['observations'] if o['target'] == 'data/x.json'][0]
    assert x['blob'] == lc.blob_id(data['data/x.json']) and x['edge'].get('content-encoding') == 'gzip'


@pytest.mark.parametrize('kind', ['refused', 'stall', '503'])
def test_network_problems_are_inconclusive(tmp_path, site_for, kind):                          # F8
    repo, sha, site = site_for(game_files())
    if kind == 'refused':
        site.close()
        url = site.url
    elif kind == 'stall':
        site.hooks['data/m.json'] = lambda h: time.sleep(3) or True
        url = site.url
    else:
        site.hooks['data/m.json'] = lambda h: send(h, 503, b'busy')
        url = site.url
    code, rep, out = run_tool(tmp_path, '--expect', sha, '--url', url, '--repo', str(repo), *LOOP, '--no-browser',
                              '--request-timeout', '1')
    assert code == 2 and rep['result'] == 'INCONCLUSIVE', out


def test_alternating_edges_are_inconclusive(tmp_path, site_for):                               # F9
    repo, sha, site = site_for(game_files())
    new, old, n = site.files['index.html'], page(sorted(GOOD), extra='/* old */'), [0]

    def alternate(h):
        n[0] += 1
        return send(h, 200, new if n[0] % 2 else old, {'Content-Type': 'text/html'})
    site.hooks['index.html'] = alternate
    code, rep, out = run_tool(tmp_path, '--expect', sha, '--url', site.url, '--repo', str(repo), '--rounds', '3',
                              '--interval', '0', '--no-browser')
    assert code == 2 and len(rep['rounds']) == 3
    assert [o['value'] for r in rep['rounds'] for o in r['observations'] if o['target'] == 'index.html'] == ['MATCH', 'DIFF', 'MATCH']


def test_transient_then_converged(tmp_path, site_for):                                          # F10
    repo, sha, site = site_for(game_files())
    new, n = site.files['index.html'], [0]

    def first_old(h):
        n[0] += 1
        return send(h, 200, page(sorted(GOOD), extra='/* old */') if n[0] == 1 else new, {'Content-Type': 'text/html'})
    site.hooks['index.html'] = first_old
    code, rep, out = run_tool(tmp_path, '--expect', sha, '--url', site.url, '--repo', str(repo), '--rounds', '3',
                              '--interval', '1', '--confirm-window', '1', '--no-browser')
    assert code == 0 and 'WARN transient: index.html was DIFF in round 1' in out, out


@pytest.mark.parametrize('fail_round,want', [(2, 0), (3, 2)])
def test_failure_in_one_round(tmp_path, site_for, fail_round, want):                           # F11, F12
    repo, sha, site = site_for(game_files())
    n, body = [0], site.files['data/m.json']

    def flaky(h):
        n[0] += 1
        return send(h, 503, b'') if n[0] == fail_round else send(h, 200, body, {'Content-Type': 'application/json'})
    site.hooks['data/m.json'] = flaky
    code, rep, out = run_tool(tmp_path, '--expect', sha, '--url', site.url, '--repo', str(repo), '--rounds', '3',
                              '--interval', '0', '--confirm-window', '0', '--no-browser')
    assert code == want, out
    assert [r['complete'] for r in rep['rounds']] == [k != fail_round for k in (1, 2, 3)]


# ---------------------------------------------------------------- data rules (J1-J3) and drift from deploy.yml (D14)

@pytest.mark.parametrize('data,want,msg', [
    ({**GOOD, 'data/b.json': json.dumps({'ts': 1, 'types': [], 'cols': [], 'tiles': {}, 'lod': {}}).encode()}, 1, '"tiles" is empty'),
    ({**GOOD, 'data/x.json': b'not json'}, 1, 'data/x.json is present but not valid JSON'),
    (dict(GOOD), 0, None),
])
def test_data_validation_on_matching_bytes(tmp_path, site_for, data, want, msg):              # J1, J2, J3
    repo, sha, site = site_for(game_files(data))
    code, rep, out = check(tmp_path, repo, sha, site)
    assert code == want, out
    assert rep['content']['verdict'] == 'PASS', 'content identity is reported separately from data validation'
    if msg:
        assert rep['data']['verdict'] == 'FAIL' and 'data-invalid' in rep['categories'] and any(msg in e for e in rep['data']['errors'])
    else:
        assert any('data/x.json is missing (optional' in n for n in rep['data']['notes'])


def deploy_rules():
    text = (ROOT / '.github/workflows/deploy.yml').read_text()
    step = text.split('- name: Check the game files', 1)[1]
    code = step.split("python3 - <<'PY'\n", 1)[1].split('\n          PY\n', 1)[0]
    code = '\n'.join(line[10:] if line.startswith(' ' * 10) else line for line in code.splitlines())
    tree = ast.parse(code)
    keep = [n for n in tree.body if isinstance(n, (ast.Import, ast.FunctionDef)) or
            (isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id in ('ESSENTIAL', 'OPTIONAL'))]
    ns = {}
    exec(compile(ast.Module(body=keep, type_ignores=[]), 'deploy.yml', 'exec'), ns)
    return ns, text


def test_rules_match_deploy_workflow(tmp_path):                                                 # D14
    ns, text = deploy_rules()
    assert ns['ESSENTIAL'] == lc.ESSENTIAL and ns['OPTIONAL'] == lc.OPTIONAL
    variants = []
    for name, good in (('b', json.loads(GOOD['data/b.json'])), ('r', json.loads(GOOD['data/r.json'])), ('m', json.loads(GOOD['data/m.json']))):
        variants += [(name, good), (name, []), (name, 'x')]
        for k in good:
            variants += [(name, {kk: v for kk, v in good.items() if kk != k}), (name, {**good, k: True}),
                         (name, {**good, k: 7}), (name, {**good, k: [] if isinstance(good[k], dict) else {}}),
                         (name, {**good, k: type(good[k])()})]
    variants += [('b', {**json.loads(GOOD['data/b.json']), 'ts': 0}), ('b', {**json.loads(GOOD['data/b.json']), 'ts': -1.5}),
                 ('r', {**json.loads(GOOD['data/r.json']), 'nodes': [0, 0, 1]}),
                 ('r', {**json.loads(GOOD['data/r.json']), 'edges': [[0, 5], [0], 'x', [True, 1]]}),
                 ('m', {**json.loads(GOOD['data/m.json']), 'land': {}}), ('m', {**json.loads(GOOD['data/m.json']), 'lakes': []})]
    for name, d in variants:
        assert lc.structure(name, d) == ns['structure'](name, d), (name, d)
    for i, raw in enumerate((b'{}', gzip.compress(b'{"a": [1, 2]}'), '{"s": "åäö"}'.encode(), b'not json', b'\x1f\x8bbroken')):
        f = tmp_path / f'parse-{i}.json'
        f.write_bytes(raw)
        def outcome(fn, arg):
            try:
                return ('ok', fn(arg))
            except Exception as e:
                return ('error', type(e).__name__)
        assert outcome(lc.parse_data, raw) == outcome(ns['parse'], str(f)), raw
    collect = text.split('- name: Collect the game files only', 1)[1].split('- uses:', 1)[0]
    assert 'cp -R index.html data _site/' in collect, 'deploy.yml publishes other files now: update live_check.published()'
    assert """printf '%s\\n' "$SHA" > _site/version.txt""" in collect, 'version.txt format changed: update finish_expected()'


def test_startup_contract_in_game():                                                            # C1
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    missing = [m for m in lc.STARTUP_MARKERS if m not in html]
    assert not missing, f'the browser check reads these from the game; update live_check and the generated page: {missing}'


# ---------------------------------------------------------------- output paths and leaving nothing behind (S1-S3)

def repo_state():
    def g(*a):
        return subprocess.run(['git', '-C', str(ROOT), *a], capture_output=True, text=True,
                              env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'}).stdout
    gitdir = Path(g('rev-parse', '--git-dir').strip())
    gitdir = gitdir if gitdir.is_absolute() else ROOT / gitdir
    out = ROOT / 'tests' / 'output'
    listing = sorted((str(p.relative_to(out)), p.stat().st_size, p.stat().st_mtime_ns) for p in out.rglob('*')) if out.exists() else []
    caches = sorted(str(p) for p in ROOT.rglob('__pycache__') if '.git' not in p.parts)
    return {'status': g('status', '--porcelain=v1', '--ignored', '--untracked-files=all'), 'refs': g('for-each-ref'),
            'worktrees': g('worktree', 'list', '--porcelain'), 'stash': g('stash', 'list'),
            'index': (gitdir / 'index').stat().st_mtime_ns if (gitdir / 'index').exists() else None,
            'output': listing, 'caches': caches}


@pytest.mark.browser
def test_run_changes_nothing(tmp_path, site_for):                                              # S1
    pytest.importorskip('playwright')
    repo, sha, site = site_for(game_files())
    before, cwd_before = repo_state(), sorted(os.listdir(tmp_path))
    code, rep, out = check(tmp_path, repo, sha, site, env=stubs_env(tmp_path), browser=True)
    assert code == 0, out
    assert repo_state() == before
    new = set(os.listdir(tmp_path)) - set(cwd_before)
    assert all(n.startswith(('report-', 'stubs-', 'dep.js')) for n in new), new


@pytest.mark.parametrize('where', ['repo', 'tests-output', 'link-into-repo', 'existing', 'dangling'])
def test_unsafe_output_paths(tmp_path, where):                                                 # S2
    if where == 'repo':
        p = ROOT / f'report-{uuid.uuid4().hex[:6]}.json'
    elif where == 'tests-output':
        p = ROOT / 'tests' / 'output' / 'report.json'     # refused whether or not the folder exists
    elif where == 'link-into-repo':
        (tmp_path / 'link').symlink_to(ROOT)
        p = tmp_path / 'link' / 'report.json'
    elif where == 'existing':
        p = tmp_path / 'exists.json'
        p.write_text('keep')
    else:
        p = tmp_path / 'dangling.json'
        p.symlink_to(tmp_path / 'nowhere.json')
    before = repo_state()
    assert lc.main(['--expect', 'a' * 40, '--url', 'http://127.0.0.1:9/', '--json', str(p)]) == 3
    assert repo_state() == before
    if where == 'existing':
        assert p.read_text() == 'keep'
    if where == 'dangling':
        assert not (tmp_path / 'nowhere.json').exists()


def test_safe_output_outside_repo(tmp_path, site_for):                                         # S3
    repo, sha, site = site_for(game_files())
    code, rep, out = check(tmp_path, repo, sha, site)
    assert code == 0
    files = list(tmp_path.glob('report-*.json'))
    assert files and all(oct(f.stat().st_mode & 0o777) == '0o600' for f in files)


# ---------------------------------------------------------------- redirects in the HTTP client (RD1-RD8)

def test_redirect_within_loopback(monkeypatch):                                                # RD1
    g = Guard(monkeypatch)
    site = Site({'b': b'final'})
    site.hooks['a'] = redirect('/b')
    try:
        p = lc.Policy(site.url, 'http://127.0.0.1:9')
        r = lc.http_get(p, site.url + 'a', 'site', follow=True)
        assert r.status == 200 and r.body == b'final' and r.chain == [site.url + 'b']
        assert len(p.connections) == len(site.log) == 2, 'every request went through PinnedHTTPConnection'
        assert g.bad == []
    finally:
        site.close()


def test_expected_file_redirect_is_unavailable(tmp_path, site_for):                            # RD2
    repo, sha, site = site_for(game_files())
    site.hooks['data/m.json'] = redirect('/elsewhere/m.json')
    site.files['elsewhere/m.json'] = GOOD['data/m.json']
    code, rep, out = check(tmp_path, repo, sha, site)
    m = [o for o in rep['rounds'][0]['observations'] if o['target'] == 'data/m.json'][0]
    assert code == 2 and m['value'] == 'UNAVAILABLE' and 'redirected' in m['error']
    assert site.hits('elsewhere/m.json') == []


@pytest.mark.parametrize('dest', ['http://public.test/x', 'http://2130706433/', 'http://127.0.0.1.example/',
                                  'http://user@127.0.0.1@public.test/', 'file:///etc/passwd', 'https://127.0.0.1/',
                                  'http://192.0.2.10/', 'http://[2001:db8::1]/'])
def test_redirect_out_of_loopback_is_blocked(monkeypatch, dest):                                # RD3, RD4
    g = Guard(monkeypatch)
    site = Site({})
    site.hooks['c'] = redirect(dest)
    try:
        p = lc.Policy(site.url, 'http://127.0.0.1:9')
        with pytest.raises(lc.Blocked) as e:
            lc.http_get(p, site.url + 'c', 'site', follow=True)
        assert e.value.url and e.value.reason
        assert g.bad == [] and 'public.test' not in g.lookups and [x['path'] for x in site.log] == ['c']
    finally:
        site.close()


def test_redirect_limit(monkeypatch):                                                           # RD5
    Guard(monkeypatch)
    site = Site({'h5': b'never'})
    for i in range(1, 5):
        site.hooks[f'h{i}'] = redirect(f'/h{i + 1}')
    try:
        with pytest.raises(lc.Blocked, match='more than 3 redirects'):
            lc.http_get(lc.Policy(site.url, 'http://127.0.0.1:9'), site.url + 'h1', 'site', follow=True)
        assert site.hits('h5') == []
    finally:
        site.close()


def test_production_policy():                                                                   # RD6
    p = lc.Policy('https://site.example/x/', 'https://api.github.com')
    assert p.allow('https://site.example/x/data/b.json', 'site') is None
    assert p.allow('https://api.github.com/repos/o/r', 'api') is None
    for url, kind in [('http://site.example/x/a', 'site'), ('https://other.example/x/a', 'site'),
                      ('https://site.example/y/a', 'site'), ('https://site.example/x/a', 'api'),
                      ('http://api.github.com/repos', 'api'), ('https://u@site.example/x/a', 'site')]:
        with pytest.raises(lc.Blocked):
            p.allow(url, kind)


@pytest.mark.parametrize('to,want', [('http://public.test/repos/o/r/git/commits/', 2), ('/moved/', 0)])
def test_api_redirects(tmp_path, site_for, monkeypatch, to, want):                              # RD7, RD8
    repo, sha, site = site_for(game_files())
    api = FakeAPI(repo)
    inner = api.answer

    def moved(h):
        if h.path.startswith('/moved/'):
            h.path = h.path[len('/moved'):]
            return inner(h)
        if '/commits/' in h.path:
            return send(h, 301, b'', {'Location': (to + sha) if to.startswith('http') else '/moved' + h.path})
        return inner(h)
    api.hooks = _AllHooks(moved)
    try:
        code, rep, out = run_tool(tmp_path, '--expect', sha, '--url', site.url, '--source', 'github', '--github-repo', 'o/r',
                                  '--no-browser', *LOOP, env={'SL_LIVE_GITHUB_API': api.api})
        assert code == want, out
        if want == 2:
            assert 'blocked' in out and all('public.test' not in (x['host'] or '') for x in api.log)
    finally:
        api.close()


# ---------------------------------------------------------------- DNS pinning (DNS1-DNS7)

def test_pinned_names(monkeypatch):                                                             # DNS1, DNS7
    g = Guard(monkeypatch)
    site = Site({'x': b'ok', 'y': b'ok'})
    resolve, calls = fake_resolver({'pinned.test': [['127.0.0.1']], 'localhost': [['127.0.0.1', '::1']]})
    try:
        p = lc.Policy(f'http://pinned.test:{site.port}/', 'http://127.0.0.1:9', resolver=resolve, names=['pinned.test'])
        for path in ('x', 'y', 'x'):
            assert lc.http_get(p, f'http://pinned.test:{site.port}/{path}', 'site').status == 200
        assert lc.http_get(p, f'http://localhost:{site.port}/y', 'site').status == 200
        assert calls == {'pinned.test': 0, 'localhost': 0}, 'each name resolved exactly once'
        assert [c[2] for c in p.connections] == ['127.0.0.1'] * 4 and len(site.log) == 4
        assert {x['host'] for x in site.log} == {f'pinned.test:{site.port}', f'localhost:{site.port}'}
        assert {x['peer'] for x in site.log} == {'127.0.0.1'} and g.bad == []
        assert all(lc.ip_literal(h) for h in g.lookups), f'a name was looked up: {g.lookups}'  # literals only (create_connection)
    finally:
        site.close()


@pytest.mark.parametrize('answers,why', [([['127.0.0.1', '192.0.2.10']], 'non-loopback'), ([[]], 'no address'),
                                         ([['2001:db8::1']], 'non-loopback')])
def test_unpinnable_names(monkeypatch, answers, why):                                           # DNS2, DNS5
    g = Guard(monkeypatch)
    site = Site({'x': b'ok'})
    resolve, calls = fake_resolver({'mixed.test': answers})
    try:
        p = lc.Policy(f'http://mixed.test:{site.port}/', 'http://127.0.0.1:9', resolver=resolve, names=['mixed.test'])
        with pytest.raises(lc.Blocked, match=why):
            lc.http_get(p, f'http://mixed.test:{site.port}/x', 'site')
        assert site.log == [] and g.bad == [] and p.connections == []
    finally:
        site.close()


def test_resolver_error_and_unknown_names(monkeypatch):                                        # DNS5
    g = Guard(monkeypatch)
    p = lc.Policy('http://127.0.0.1:9/', 'http://127.0.0.1:9', resolver=lambda *a, **k: (_ for _ in ()).throw(OSError('boom')),
                  names=['err.test'])
    with pytest.raises(lc.Blocked, match='cannot resolve'):
        p.allow('http://err.test/x', 'site')
    with pytest.raises(lc.Blocked, match='not allowed in loopback mode'):
        p.allow('http://public.test/x', 'site')
    assert g.lookups == [] and g.bad == []


def test_changing_answers_cannot_redirect_connections(monkeypatch):                            # DNS3
    g = Guard(monkeypatch)
    site = Site({'x': b'ok', 'z': b'ok'})
    site.hooks['y'] = lambda h: send(h, 302, b'', {'Location': f'http://flip.test:{site.port}/z'})
    resolve, calls = fake_resolver({'flip.test': [['127.0.0.1'], ['192.0.2.10']]})
    try:
        p = lc.Policy(f'http://flip.test:{site.port}/', 'http://127.0.0.1:9', resolver=resolve, names=['flip.test'])
        for path in ('x', 'y', 'x'):
            lc.http_get(p, f'http://flip.test:{site.port}/{path}', 'site', follow=True)
        assert calls == {'flip.test': 0} and {c[2] for c in p.connections} == {'127.0.0.1'} and g.bad == []
    finally:
        site.close()


@pytest.mark.parametrize('host', ['192.0.2.10', '10.0.0.1', '[2001:db8::1]', '[::ffff:192.0.2.10]', '0.0.0.0', '2130706433'])
def test_non_loopback_literals(monkeypatch, host):                                              # DNS4
    g = Guard(monkeypatch)
    with pytest.raises(lc.Blocked):
        loop_policy().allow(f'http://{host}/x', 'site')
    assert g.bad == [] and g.lookups == []


def test_chromium_rules_from_pins():                                                            # DNS6
    resolve, _ = fake_resolver({'pinned.test': [['127.0.0.1']]})
    p = lc.Policy('http://pinned.test:8/', 'http://127.0.0.1:9', resolver=resolve, names=['pinned.test'])
    p.pin('pinned.test', 8)
    p.pin('127.0.0.1', 8)
    assert p.chromium_rules() == 'MAP pinned.test 127.0.0.1, MAP * ~NOTFOUND, EXCLUDE 127.0.0.1, EXCLUDE [::1]'


def test_only_route_fetch_bodies_are_hashed():                                                  # R2 guard
    src = TOOL.read_text()
    calls = re.findall(r'(\w+)\.body\(\)', src)
    assert calls and set(calls) == {'fetched'}, 'only route.fetch() responses may be hashed (response.body() is lossy for binary JSON)'


# ---------------------------------------------------------------- the browser check (generated site, no internet)

browser = pytest.mark.browser


def bcheck(tmp_path, repo, sha, site, *extra, env=None, with_dep=True):
    pytest.importorskip('playwright')
    e = {**stubs_env(tmp_path, with_dep), **(env or {})}
    return check(tmp_path, repo, sha, site, '--browser-timeout', '60', *extra, env=e, browser=True)


@browser
def test_browser_pass(tmp_path, site_for):                                                      # B1', B9'
    repo, sha, site = site_for(game_files())
    code, rep, out = bcheck(tmp_path, repo, sha, site)
    assert code == 0 and rep['browser']['verdict'] == 'PASS', out
    b = rep['browser']
    assert {o['target'] for o in b['observations']} == {'index.html', *GOOD}
    assert all(e['result'] in ('stub', 'blocked (loopback mode)') for e in b['external'])
    assert rep['network_policy'] == 'loopback-strict' and 'MAP * ~NOTFOUND' in b['resolver_rules']


@browser
def test_navigation_is_intercepted(tmp_path, site_for):                                        # N1
    marker = f'marker-{uuid.uuid4().hex[:8]}'
    repo, sha, site = site_for(game_files(extra=f"document.title = '{marker}';"))
    code, rep, out = bcheck(tmp_path, repo, sha, site, '--verbose')
    docs = [o for o in rep['browser']['observations'] if o.get('resource_type') == 'document']
    assert code == 0 and len(docs) == 1 and docs[0]['target'] == 'index.html'
    assert docs[0]['blob'] == lc.blob_id(page(sorted(GOOD), extra=f"document.title = '{marker}';"))
    assert len([x for x in site.log if x['path'] == 'index.html' and x['query'].startswith('lc=') and browser_ua_log(x)]) == 1


def browser_ua_log(x):
    return 'Mozilla' in x['ua']


@browser
def test_navigation_gets_exactly_the_hashed_bytes(tmp_path, site_for):                        # N2
    repo, sha, site = site_for(game_files())
    other = page(sorted(GOOD), extra="document.title = 'served-to-browser';")
    good = site.files['index.html']
    site.hooks['index.html'] = lambda h: send(h, 200, other if browser_ua(h) else good, {'Content-Type': 'text/html'})
    code, rep, out = bcheck(tmp_path, repo, sha, site)
    doc = [o for o in rep['browser']['observations'] if o.get('resource_type') == 'document'][0]
    assert doc['value'] == 'DIFF' and doc['blob'] == lc.blob_id(other) and code == 2


@browser
def test_expected_file_redirect_in_the_browser(tmp_path, site_for):                            # RD2 (browser)
    repo, sha, site = site_for(game_files())
    good = site.files['data/m.json']
    site.files['elsewhere/m.json'] = good
    site.hooks['data/m.json'] = lambda h: send(h, 302, b'', {'Location': '/elsewhere/m.json'}) if browser_ua(h) \
        else send(h, 200, good, {'Content-Type': 'application/json'})
    code, rep, out = bcheck(tmp_path, repo, sha, site)
    m = [o for o in rep['browser']['observations'] if o['target'] == 'data/m.json'][0]
    assert code == 2 and m['value'] == 'UNAVAILABLE' and m['stage'] == 'redirect' and 'redirected' in m['error']
    assert site.hits('elsewhere/m.json') == [], 'an expected file must not be taken from a redirect'


@browser
def test_game_defect(tmp_path, site_for):                                                       # B2', M1 (2)
    repo, sha, site = site_for(game_files(extra="setTimeout(() => { throw new Error('boom from the game') }, 0);"))
    code, rep, out = bcheck(tmp_path, repo, sha, site)
    assert code == 1 and rep['browser']['category'] == 'game-defect' and 'boom' in rep['browser']['reason'], out
    assert rep['browser']['external_failures'] == [], 'no outside service failed, so the error is the game\'s own'


# a live-data call without a handler: when the service is down, Chromium reports "TypeError: Failed to fetch" as a
# page error from the game's own script (checked with Playwright 1.58), exactly what an outage looks like
OUTAGE = "fetch('https://api.example.invalid/weather').then(r => r.json());"


@browser
def test_outside_outage_is_not_a_game_defect(tmp_path, site_for):                               # M1 (1)
    repo, sha, site = site_for(game_files(extra=OUTAGE + " await new Promise(r => setTimeout(r, 300));"))
    code, rep, out = bcheck(tmp_path, repo, sha, site)
    b = rep['browser']
    assert code == 2 and b['verdict'] == 'INCONCLUSIVE' and b['category'] == 'external-outage-associated-game-error', out
    assert 'game-defect' not in rep['categories'] and any('Failed to fetch' in e['message'] for e in b['page_errors'])
    assert [x['host'] for x in b['external_failures']] == ['api.example.invalid'] and 'api.example.invalid' in b['reason']
    assert 'outside service failed: api.example.invalid' in out and rep['content']['verdict'] == 'PASS'


@browser
def test_required_dependency_wins_over_outage(tmp_path, site_for):                              # M1 (4)
    repo, sha, site = site_for(game_files(extra=OUTAGE))
    code, rep, out = bcheck(tmp_path, repo, sha, site, with_dep=False)
    assert code == 2 and 'dependency unavailable' in rep['browser']['reason'] and rep['browser']['category'] is None, out


@browser
def test_outage_does_not_hide_a_content_mismatch(tmp_path, site_for):                           # M1 (5)
    repo, sha, site = site_for(game_files(extra=OUTAGE + " await new Promise(r => setTimeout(r, 300));"))
    site.files['version.txt'] = ('e' * 40 + '\n').encode()
    code, rep, out = bcheck(tmp_path, repo, sha, site, '--browser-anyway')
    assert code == 1 and rep['content']['verdict'] == 'FAIL', out
    assert rep['categories'] == ['content-mismatch', 'external-outage-associated-game-error']


def startup(external=(), errors=(), nogl=(), match=True):
    base = 'https://site.example/x/'
    res = {'verdict': None, 'reason': '', 'category': None,           # as browser_check() starts it
           'signals': {'loading_gone': True, 'canvas': True, 'nogl': list(nogl), 'intro': True}, 'webgl_probe': True,
           'interception_failures': [], 'external': list(external),
           'page_errors': [{'message': m, 'stack': f'Error: {m}\n    at {base}index.html?lc=1:9:9'} for m in errors],
           'observations': [{'target': 'index.html', 'resource_type': 'document', 'value': 'MATCH' if match else 'DIFF'}]}
    lc.decide_startup(res, base, [], False)
    return res


@pytest.mark.parametrize('external,errors,nogl,want', [
    ([{'url': 'https://api.sr.se/x', 'result': 'failed: net::ERR_NAME_NOT_RESOLVED', 'required': False}], ['Failed to fetch'], [],
     ('INCONCLUSIVE', 'external-outage-associated-game-error')),                                 # production: failed request
    ([{'url': 'https://relay.example/flights', 'result': 'HTTP 503', 'required': False}], ['boom'], [],
     ('INCONCLUSIVE', 'external-outage-associated-game-error')),                                 # production: 5xx response
    ([], ['boom'], [], ('FAIL', 'game-defect')),
    ([{'url': 'https://api.sr.se/x', 'result': 'HTTP 503', 'required': False}], [], [], ('PASS', None)),     # M1 (3)
    ([{'url': 'https://api.sr.se/x', 'result': 'HTTP 503', 'required': False}], ['boom'], ['Could not load the city data'],
     ('FAIL', 'game-defect')),                                                                   # the game reports its own data
    ([{'url': 'https://cdn.example/three.js', 'result': 'failed: x', 'required': True}], ['THREE is not defined'], [],
     ('INCONCLUSIVE', None)),                                                                    # required dependency
])
def test_startup_classification(external, errors, nogl, want):
    res = startup(external, errors, nogl)
    assert (res['verdict'], res['category']) == want, res['reason']


def test_outage_with_differing_files_stays_a_cdn_question():                                     # M1 (5), unit
    res = startup([{'url': 'https://api.sr.se/x', 'result': 'HTTP 503', 'required': False}], ['boom'], match=False)
    assert res['verdict'] == 'INCONCLUSIVE' and 'CDN inconsistency' in res['reason']


@browser
def test_error_with_a_differing_file_is_not_a_game_defect(tmp_path, site_for):                 # B3'
    repo, sha, site = site_for(game_files(extra="setTimeout(() => { throw new Error('boom') }, 0);"))
    good = site.files['data/r.json']
    site.hooks['data/r.json'] = lambda h: send(h, 200, b'{"other": 1}' if browser_ua(h) else good, {'Content-Type': 'application/json'})
    code, rep, out = bcheck(tmp_path, repo, sha, site)
    assert code == 2 and rep['browser']['verdict'] == 'INCONCLUSIVE' and 'CDN inconsistency' in rep['browser']['reason']
    assert 'game-defect' not in rep['categories']


@browser
def test_missing_dependency(tmp_path, site_for):                                                # B4'
    repo, sha, site = site_for(game_files())
    code, rep, out = bcheck(tmp_path, repo, sha, site, with_dep=False)
    assert code == 2 and 'dependency unavailable' in rep['browser']['reason'], out


@browser
def test_unneeded_external_and_unexpected_same_origin(tmp_path, site_for):                     # B5', B8'
    repo, sha, site = site_for(game_files(extra="fetch('https://api.example.invalid/x').catch(() => {}); "
                                                "await fetch('data/not-published.json').catch(() => {});"))
    code, rep, out = bcheck(tmp_path, repo, sha, site)
    assert code == 0 and rep['browser']['category'] is None, out                                   # M1 (3)
    assert [x['host'] for x in rep['browser']['external_failures']] == ['api.example.invalid']
    assert any(e['url'].startswith('https://api.example.invalid') and not e['required'] for e in rep['browser']['external'])
    assert [o['status'] for o in rep['browser']['other_same_origin'] if o['url'].endswith('not-published.json')] == [404]
    assert 'unexpected same-origin request' in out


@browser
def test_no_webgl_is_environment(tmp_path, site_for):                                          # B6'
    repo, sha, site = site_for(game_files())
    code, rep, out = bcheck(tmp_path, repo, sha, site, env={'SL_LIVE_TEST_CHROME_ARGS': '--disable-3d-apis'})
    assert code == 2 and 'no WebGL' in rep['browser']['reason'], out


@browser
def test_timeout(tmp_path, site_for):                                                           # B7'
    repo, sha, site = site_for(game_files(extra='await new Promise(() => {});'))
    pytest.importorskip('playwright')
    code, rep, out = check(tmp_path, repo, sha, site, '--browser-timeout', '4', env=stubs_env(tmp_path), browser=True)
    assert code == 2 and rep['browser']['reason'].startswith('timeout'), out


@browser
def test_gzip_bytes_reach_the_browser_exactly(tmp_path, site_for):                             # R1, R2
    data = {**GOOD, 'data/x.json': gzip.compress(json.dumps({'s': 'Södermalm'}).encode())}
    repo, sha, site = site_for(game_files(data), gzip_transport=True)
    code, rep, out = bcheck(tmp_path, repo, sha, site)
    assert code == 0, out
    x = [o for o in rep['browser']['observations'] if o['target'] == 'data/x.json'][0]
    assert x['value'] == 'MATCH' and x['blob'] == lc.blob_id(data['data/x.json'])


@browser
def test_fetch_failure_in_the_route(tmp_path, site_for):                                       # H1
    repo, sha, site = site_for(game_files({**GOOD, 'data/t.json': b'{}'}))
    good = site.files['data/t.json']

    def drop(h):
        if browser_ua(h):
            h.close_connection = True
            h.connection.shutdown(socket.SHUT_RDWR)
            return True
        return send(h, 200, good, {'Content-Type': 'application/json'})
    site.hooks['data/t.json'] = drop
    code, rep, out = bcheck(tmp_path, repo, sha, site)
    t = [o for o in rep['browser']['observations'] if o['target'] == 'data/t.json'][0]
    assert code == 2 and t['value'] == 'UNAVAILABLE' and t['stage'] == 'fetch'
    assert 'interception failure' in rep['browser']['reason'] and 'game-defect' not in rep['categories']


@browser
def test_fulfill_failure(tmp_path, site_for):                                                   # H2
    repo, sha, site = site_for(game_files({**GOOD, 'data/t.json': b'{}'}))
    code, rep, out = bcheck(tmp_path, repo, sha, site, env={'SL_LIVE_FAULT': 'fulfill:data/t.json'})
    t = [o for o in rep['browser']['observations'] if o['target'] == 'data/t.json'][0]
    assert code == 2 and t['value'] == 'UNAVAILABLE' and t['stage'] == 'fulfill' and t['blob'] == lc.blob_id(b'{}')


@browser
def test_interception_failure_with_a_confirmed_mismatch(tmp_path, site_for):                  # H3
    repo, sha, site = site_for(game_files({**GOOD, 'data/t.json': b'{}'}))
    site.files['version.txt'] = ('e' * 40 + '\n').encode()
    code, rep, out = bcheck(tmp_path, repo, sha, site, '--browser-anyway', env={'SL_LIVE_FAULT': 'fulfill:data/t.json'})
    assert code == 1 and rep['categories'] == ['content-mismatch'], out


@browser
def test_browser_redirects(tmp_path, site_for):                                                 # RD9, RD10, RD11
    sink = Site({})
    try:
        extra = (f"await fetch('/r1').catch(() => {{}}); await fetch('/r2').catch(() => {{}}); "
                 f"await fetch('http://public.test:{sink.port}/z').catch(() => {{}}); "
                 f"const i = new Image(); i.src = 'http://public.test:{sink.port}/img'; await new Promise(r => setTimeout(r, 800));")
        repo, sha, site = site_for(game_files(extra=extra))
        site.files['b2'] = b'final'
        site.hooks['r1'] = redirect('/b2')
        site.hooks['r2'] = redirect(f'http://public.test:{sink.port}/y')
        code, rep, out = bcheck(tmp_path, repo, sha, site, env={'SL_LIVE_TEST_SINK': f'public.test=127.0.0.1:{sink.port}',
                                                                'SL_LIVE_TEST_CHROME_ARGS': NO_LNA})
        assert code == 0, out
        other = {o['url'].rsplit('/', 1)[1]: o for o in rep['browser']['other_same_origin']}
        assert other['r1']['status'] == 200 and other['r1']['chain'][-1].endswith('/b2')
        assert other['r2']['blocked'] and 'public.test' in other['r2']['chain'][-1]
        assert len(site.hits('r1')) == len(site.hits('b2')) == 1, 'Chromium must never follow a redirect itself'
        assert sink.log == [], 'a refused destination received a request'
    finally:
        sink.close()


RULES_PROBE = r"""
import json, sys
from playwright.sync_api import sync_playwright, Error
chrome, args, url_ok, urls_bad = json.loads(sys.argv[1])
out = {'control': None, 'bad': {}}
with sync_playwright() as p:
    br = p.chromium.launch(executable_path=chrome, headless=True, args=args)
    try:
        pg = br.new_page()
        try:
            pg.goto(url_ok)
            out['control'] = 'loaded'
        except Error as e:
            out['control'] = str(e).splitlines()[0]
        for u in urls_bad:
            try:
                pg.goto(u)
                out['bad'][u] = 'loaded'
            except Error as e:
                out['bad'][u] = str(e).splitlines()[0]
    finally:
        br.close()
print(json.dumps(out))
"""


@browser
def test_resolver_rules_stop_every_other_name():                                               # RD12
    """Preconnects and other connections Chromium makes outside the route handler can only use names its resolver
    rules allow. Headless Chromium did not preconnect at all in our runs (so a preconnect page proves nothing);
    instead Chromium is started with the tool's rules and no route at all: a mapped name reaches the sink (control),
    any other name is never resolved and the sink sees nothing. Runs in its own process: conftest's session-wide
    Playwright cannot be nested."""
    pytest.importorskip('playwright')
    sink = Site({'x': b'control', 'y': b'leak'})
    try:
        rules = loop_policy().chromium_rules(sink=('public.test', f'127.0.0.1:{sink.port}'))
        chrome, args = lc.load_chrome()
        bad = [f'http://{h}:{sink.port}/y' for h in ('other.test', 'example.com', 'localhost.example')]
        spec = [chrome, args + [f'--host-resolver-rules={rules}', '--no-proxy-server', NO_LNA], f'http://public.test:{sink.port}/x', bad]
        p = subprocess.run([sys.executable, '-c', RULES_PROBE, json.dumps(spec)], capture_output=True, text=True, timeout=180,
                           env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        assert p.returncode == 0, p.stderr[-800:]
        res = json.loads(p.stdout.strip().splitlines()[-1])
        assert res['control'] == 'loaded' and sink.hits('x'), f'control failed: {res}'
        assert all('ERR_NAME_NOT_RESOLVED' in v for v in res['bad'].values()), res
        assert sink.hits('y') == [], f'an unmapped name reached the sink: {sink.log}'
        assert {x['host'] for x in sink.log} == {f'public.test:{sink.port}'}, 'only the mapped control name may arrive'
        assert rules.endswith('MAP * ~NOTFOUND, EXCLUDE 127.0.0.1, EXCLUDE [::1]')
    finally:
        sink.close()


@browser
def test_stub_only_for_listed_urls(tmp_path, site_for):                                        # RD13
    repo, sha, site = site_for(game_files(extra="await fetch('https://cdn.example.invalid/other.js').catch(() => {});"))
    code, rep, out = bcheck(tmp_path, repo, sha, site)
    ext = {e['url']: e['result'] for e in rep['browser']['external']}
    assert code == 0 and ext[DEP] == 'stub' and ext['https://cdn.example.invalid/other.js'] == 'blocked (loopback mode)'
    assert rep['network_policy'] == 'loopback-strict'                                          # RD14


@browser
def test_pinned_site_name_in_the_browser(tmp_path, site_for):                                  # DNS3 (browser), DNS6, DNS7
    repo, sha, site = site_for(game_files())
    table = tmp_path / 'resolver.json'
    table.write_text(json.dumps({'flip.test': [['127.0.0.1'], ['192.0.2.10']]}))
    pytest.importorskip('playwright')
    code, rep, out = run_tool(tmp_path, '--expect', sha, '--url', f'http://flip.test:{site.port}/', '--repo', str(repo),
                              *LOOP, '--browser-timeout', '60',
                              env={**stubs_env(tmp_path), 'SL_LIVE_TEST_RESOLVER': str(table)})
    assert code == 0, out
    assert rep['network']['resolver_calls'] == {'flip.test': 1}
    assert rep['browser']['resolver_rules'].startswith('MAP flip.test 127.0.0.1, MAP * ~NOTFOUND')
    assert {x['peer'] for x in site.log} == {'127.0.0.1'} and {x['host'] for x in site.log} == {f'flip.test:{site.port}'}
    assert len([x for x in site.log if browser_ua_log(x)]) == len(rep['browser']['observations'])
