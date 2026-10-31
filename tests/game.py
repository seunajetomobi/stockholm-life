"""Shared helpers for the browser tests: paths, the test hook, page set-up and small DOM measurements."""
import json, os, shutil, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'tests' / 'output'           # screenshots; ignored by git
PORT = int(os.environ.get('SL_PORT', '8000'))  # the flights relay's CORS only allows port 8000
BASE = f'http://127.0.0.1:{PORT}'
CHROME_ARGS = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
SAVE_KEY = 'stockholm-life-v4'


def chrome_path():
    """The browser to drive: $CHROME, else the system Google Chrome, else Playwright's own Chromium (None)."""
    p = os.environ.get('CHROME') or '/usr/bin/google-chrome'
    return p if shutil.which(p) or Path(p).is_file() else None


# ---------- test hook ----------
# buildWorld() keeps the station, the train and the cameras in a closure. The hooked tests serve a copy of
# index.html in which the closure's last statement, `return API;`, also puts references to these names on
# window.__T. The copy exists only in the test browser (Playwright's route()); index.html on disk and the
# published game are never changed. A name that no longer exists makes buildWorld throw, and the tests fail
# at boot with a ReferenceError naming it.
HOOK_NAMES = ['csEnter', 'CS_DOORS', 'ptNext', 'csClk', 'csLine', 'promptSet',
              'jrStart', 'jrSit', 'jrStand', 'jrAlight', 'jrSkipNext', 'jrSkipStop',
              'icam', 'av', 'camera', 'controls', 'scene', 'ring', 'IW', 'IH', 'HALF', 'CARM', 'zcOf', 'DOORZ']
HOOK_LIVE = ['CS', 'JR', 'JRS', 'avHidden']  # reassigned during play, so read through getters


def hooked_html():
    # SL_INDEX_HTML=<file> runs the hooked tests on another version (e.g. `git show <rev>:index.html > old.html`)
    html = Path(os.environ.get('SL_INDEX_HTML') or ROOT / 'index.html').read_text(encoding='utf-8')
    n = html.count('return API;')
    assert n == 1, f'test hook: expected one "return API;" in index.html, found {n}'
    hook = 'window.__T={' + ','.join(HOOK_NAMES + [f'get {k}(){{return {k}}}' for k in HOOK_LIVE]) + '};return API;'
    return html.replace('return API;', hook)


# ---------- pages ----------
class Errors:
    """What a page reported: uncaught errors fail tests; console errors and failed requests are kept for the report."""

    def __init__(self, page):
        self.uncaught, self.console, self.failed, self.http = [], [], [], []
        same = lambda url: url.startswith(BASE)
        page.on('pageerror', lambda e: self.uncaught.append(str(e)[:400]))
        page.on('console', lambda m: self.console.append(m.text[:300]) if m.type == 'error' else None)
        page.on('requestfailed', lambda r: self.failed.append((same(r.url), f'{r.url[:150]} {r.failure}')))
        page.on('response', lambda r: self.http.append((same(r.url), f'{r.status} {r.url[:150]}')) if r.status >= 400 else None)

    def local_failures(self):
        """Failed or 4xx/5xx requests to the local server (the game's own files). External services may be offline."""
        return [m for s, m in self.failed + self.http if s]

    def external_failures(self):
        return [m for s, m in self.failed + self.http if not s]


def new_page(browser, width=1366, height=768, mobile=False, hook=False, init_script=None):
    opts = {'viewport': {'width': width, 'height': height}}
    if mobile:
        opts.update(is_mobile=True, has_touch=True, device_scale_factor=2)
    ctx = browser.new_context(**opts)
    if init_script:
        ctx.add_init_script(init_script)
    if hook:
        body = hooked_html()
        ctx.route('**/index.html', lambda route: route.fulfill(status=200, content_type='text/html; charset=utf-8', body=body))
    page = ctx.new_page()
    return ctx, page, Errors(page)


def boot(page, timeout=180):
    """Open the game and wait until the city has loaded. Returns the load time in seconds."""
    t0 = time.time()
    page.goto(BASE + '/index.html', wait_until='load', timeout=120000)
    page.wait_for_function("() => !document.getElementById('loading')", timeout=timeout * 1000)
    secs = round(time.time() - t0, 1)
    time.sleep(2)
    return secs


def intro_shown(page):
    return page.evaluate("() => !!document.querySelector('#modalRoot #go')")


def start_life(page, mobile=False):
    """Press "Go" on the character-creation screen (default life: born in Stockholm)."""
    (page.tap if mobile else page.click)('#modalRoot #go')
    time.sleep(6)
    clear_overlays(page)


def clear_overlays(page):
    """Close whatever modal, call screen, notification or drawer the game opened by itself (random calls, tips)."""
    page.evaluate("""() => { const m = document.querySelector('#modalRoot'); if (m) m.innerHTML = '';
      document.querySelectorAll('.callscr,.ringing,.toast,.notif').forEach(e => e.remove());
      const d = document.getElementById('drawer'), c = document.getElementById('dclose'); if (d && !d.hidden && c) c.click() }""")


def modal_text(page):
    return page.evaluate("() => { const m = document.querySelector('#modalRoot'); return m ? m.innerText.trim().slice(0, 140).replace(/\\n+/g, ' | ') : '' }")


def saved(page):
    raw = page.evaluate(f"() => localStorage.getItem('{SAVE_KEY}')")
    return json.loads(raw) if raw else None


def overflow_x(page):
    return page.evaluate("() => document.documentElement.scrollWidth - innerWidth")


def wait_for(page, js, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if page.evaluate(js):
            return True
        time.sleep(0.4)
    return False


def shot(page, name):
    OUT.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(OUT / f'{name}.png'))


# box of each visible element as {key: [left, top, right, bottom]}
BOXES_JS = """(sel) => { const r = {}; for (const [k, s] of Object.entries(sel)) { const e = document.querySelector(s); if (!e) continue;
  const c = getComputedStyle(e), b = e.getBoundingClientRect(); if (c.display === 'none' || c.visibility === 'hidden' || !b.width || !b.height) continue;
  r[k] = [b.left, b.top, b.right, b.bottom] } return r }"""


def boxes(page, sel):
    return page.evaluate(BOXES_JS, sel)


def overlap(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


# ---------- station and train (hooked pages only) ----------
def enter_station(page):
    page.evaluate("() => __T.csEnter(__T.CS_DOORS[0])")
    assert wait_for(page, "() => __T.CS.mode === 'station'", 90), 'did not enter Stockholm Central'
    time.sleep(2)


def board_train(page):
    """Board the next pendeltåg from Stockholm City (as if you had walked onto it)."""
    page.evaluate("() => { const d = __T.ptNext('S', __T.csClk(), 1)[0]; __T.jrStart(d, 10) }")
    assert wait_for(page, "() => __T.CS.mode === 'ride' && !!__T.JR && !!__T.JRS && __T.JRS.ppl !== undefined", 120), 'did not board the train'
    time.sleep(2)
