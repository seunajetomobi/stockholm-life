"""Generates the save fixtures in tests/fixtures/saves/ (docs: tests/fixtures/saves/README.md). Run by hand, never by pytest:

    SL_PORT=8123 python3 tests/fixtures/generate_saves.py [--only ID ...]

Each authentic fixture is a save written by the real game at a named commit. The generator extracts that commit's index.html with
`git show`, starts it in headless Chrome, creates a life named "Fixture Anna" through the character-creation form, plays a few real
actions through the buttons (requests public documents three times, adds a to-do, joins a list), and for the v5 fixtures enters a
place. What the game wrote to localStorage is stored as it was: no field is edited, added or removed. The game uses unseeded
random numbers, so running this again gives different files; the committed files are the evidence, with their hashes in manifest.json.
The one synthetic fixture (v3-legacy) is written by hand from the shape the migration expects, and is labelled as such.

Needs the full git history (git show of old commits), Playwright and Chrome, as the tests do. The old builds read the current data/ folder
(a superset of what they read)."""
import argparse, hashlib, json, os, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / 'saves'
sys.path.insert(0, str(ROOT / 'tests'))
import game  # noqa: E402  (reads SL_PORT)

NAME = 'Fixture Anna'
SAVE_KEY = 'stockholm-life-v4'
# Real actions, through the buttons, the same in every build: time passes and needs drop, the log fills, a to-do is added,
# a civic list is joined.
ACTIONS = [('civic', 'Request public documents')] * 3 + [('here', '+ Find a job'), ('civic', 'Bostadslistan')]
CLICK = """([tab, text]) => { const t = document.querySelector('#dock button[data-tab=' + tab + ']'); if (t) t.click();
  const b = [...document.querySelectorAll('.pane:not([hidden]) button')].find(x => (x.innerText||'').trim().replace(/\\s+/g,' ').startsWith(text));
  if (!b) return false; b.click(); return true }"""
# id, source commit, place to enter before saving (None = on the street), whether the build has the test hook (window.__T and __TS)
SPECS = [
    ('v4-55c196b', '55c196b', None, False),
    ('v4-870fe30', '870fe30', None, False),
    ('v5-3eb5711-street', '3eb5711', 'street', True),
    ('v5-3eb5711-station', '3eb5711', 'station', True),
    ('v5-3eb5711-train', '3eb5711', 'train', True),
    ('v5-3eb5711-interior', '3eb5711', 'interior', True),
]
# the v3 life of tests/test_save.py, kept as a file: written by hand, not by any build (no build in the history ever wrote the v3 key)
V3_LEGACY = {'name': 'Old', 'bg': 'newcomer', 'day': 3, 'hour': 10, 'money': 1200, 'energy': 70, 'mood': 50, 'social': 10,
             'svenska': 5, 'skill': 40, 'queue': 0, 'home': 'rinkebyRoom', 'loc': 'tc', 'job': None, 'flags': {}, 'log': [], 'applied': {}}


def git(*args):
    return subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, text=True, check=True).stdout


def sha256(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def enter_place(page, place):
    if place == 'station':
        game.enter_station(page)
    elif place == 'train':
        game.enter_station(page)
        game.board_train(page)
        page.evaluate("() => { __T.JR.depAt = Infinity }")
    elif place == 'interior':
        name = page.evaluate("""() => { const W = window.__TS.W; for (let i = 0; i < 50000; i++) { const p = W.poi(i); if (!p) break;
            if (p.type === 'cafe' && p.name) { W.enterPlace(p); return p.name } } return null }""")
        assert name, 'no café in the city data'
        assert game.wait_for(page, "() => window.__TS.W.inside()", 30), 'did not go inside'
    time.sleep(1)


def generate(br, fid, sha, place, hooked):
    html = git('show', f'{sha}:index.html')
    if hooked:
        with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html)
        os.environ['SL_INDEX_HTML'] = f.name   # tests/game.py hooks this file instead of the current index.html
        ctx, page, err = game.new_page(br, 1366, 768, hook=True)
    else:
        ctx = br.new_context(viewport={'width': 1366, 'height': 768})
        ctx.route('**/index.html', lambda route, _request: route.fulfill(status=200, content_type='text/html; charset=utf-8', body=html))
        page = ctx.new_page()
        err = game.Errors(page)
    try:
        game.boot(page, timeout=240)
        assert game.intro_shown(page), 'no character creation on a fresh profile'
        page.fill('#modalRoot [data-f=name]', NAME)
        game.start_life(page)
        for tab, text in ACTIONS:
            assert page.evaluate(CLICK, [tab, text]), f'button not found: {tab} / {text}'
            time.sleep(1.2)
            game.clear_overlays(page)
            time.sleep(0.5)
        if place and place != 'street':
            enter_place(page, place)
        if hooked:
            page.evaluate("() => window.__TS.save()")
        else:
            page.evaluate("() => window.dispatchEvent(new Event('pagehide'))")   # the game saves when the page is hidden
        time.sleep(1)
        raw = page.evaluate(f"() => localStorage.getItem('{SAVE_KEY}')")
        assert raw, 'nothing was saved'
        s = json.loads(raw)
        assert s.get('name') == NAME and s.get('flags', {}).get('started') and err.uncaught == [], (s.get('name'), err.uncaught)
        if place:
            assert (s.get('place') or {}).get('kind', 'street') == place, s.get('place')
        return raw, s
    finally:
        ctx.close()
        os.environ.pop('SL_INDEX_HTML', None)


def entry(fid, raw, s, **provenance):
    return {'id': fid, 'file': f'{fid}.json', 'storage_key': provenance.pop('storage_key', SAVE_KEY), 'save_version': s.get('v'),
            'sha256': sha256(raw), 'bytes': len(raw.encode('utf-8')), 'keys': len(s), 'name': s.get('name'), **provenance}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', nargs='*', help='ids to (re)generate; default: all')
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    mpath = OUT / 'manifest.json'
    manifest = json.loads(mpath.read_text(encoding='utf-8')) if mpath.exists() else {'fixtures': []}
    by_id = {e['id']: e for e in manifest['fixtures']}
    head = git('rev-parse', 'HEAD').strip()
    want = lambda fid: not args.only or fid in args.only
    if want('v3-legacy'):
        raw = json.dumps(V3_LEGACY, ensure_ascii=False, separators=(',', ':'))
        (OUT / 'v3-legacy.json').write_text(raw, encoding='utf-8')
        by_id['v3-legacy'] = entry('v3-legacy', raw, {**V3_LEGACY}, storage_key='stockholm-life-v3', save_version=None, authenticity='synthetic',
                                   source='none: written by hand from the shape migrate() expects; no build wrote the v3 key',
                                   generator='tests/fixtures/generate_saves.py (V3_LEGACY)', place=None)
        by_id['v3-legacy']['save_version'] = None   # v3 saves had no version field
    todo = [sp for sp in SPECS if want(sp[0])]
    if todo:
        import urllib.error
        srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(game.PORT), '--bind', '127.0.0.1'], cwd=ROOT,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(50):
                try:
                    urllib.request.urlopen(game.BASE + '/index.html', timeout=3).read(10)
                    break
                except Exception:
                    time.sleep(0.3)
            else:
                raise SystemExit(f'could not start a server on port {game.PORT}')
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                br = p.chromium.launch(executable_path=game.chrome_path(), headless=True, args=game.CHROME_ARGS)
                for fid, sha, place, hooked in todo:
                    raw, s = generate(br, fid, sha, place, hooked)
                    (OUT / f'{fid}.json').write_text(raw, encoding='utf-8')
                    by_id[fid] = entry(fid, raw, s, authenticity='authentic: written by the real game at the source commit; the life and its actions through the game's UI, place entry and the save trigger through test hooks (see README)',
                                       source_commit=git('rev-parse', sha).strip(), source_date=git('show', '-s', '--format=%cs', sha).strip(),
                                       generator='tests/fixtures/generate_saves.py', generator_commit=head,
                                       actions=['{} / {}'.format(*a) for a in ACTIONS], place=(s.get('place') or {}).get('kind', 'none'))
                    print(f'{fid}: v{s.get("v")}, {len(s)} keys, {len(raw)} bytes, place {by_id[fid]["place"]}, sha256 {by_id[fid]["sha256"][:12]}')
                br.close()
        finally:
            srv.terminate()
    order = ['v3-legacy'] + [sp[0] for sp in SPECS]
    manifest['fixtures'] = [by_id[i] for i in order if i in by_id]
    manifest['note'] = ('Synthetic lives named "Fixture Anna" (v3-legacy: "Old"), made by the game or by hand; no real player data. '
                        'See tests/fixtures/saves/README.md.')
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('manifest written:', len(manifest['fixtures']), 'fixtures')


if __name__ == '__main__':
    main()
