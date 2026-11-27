"""Negative controls for tests/test_save_fixtures.py: do the tests notice a broken migration or import?

    SL_PORT=8124 python3 tests/fixtures/negative_controls.py [--only NAME ...] [--all-selectors]

For each mutation this writes a copy of index.html with one deliberate fault into a temporary folder, runs the fixture tests on that copy
(SL_INDEX_HTML=<copy>, the same switch the other hooked tests use) and reports whether at least one test failed. The first row runs the
unmutated game: it must pass, otherwise a later "failed" proves nothing. index.html in the repository is never modified, and nothing
here is ever applied to it. Exit status 0 only if the control passes and every mutation is detected.

Run it with the same port you give the tests (not 8000). It runs the fast tests (-k "migration or refuses", about 30 s each) and, for
the mutations marked "load", also the browser test of one fixture (about 3 minutes), but only when --all-selectors is given or the fast tests did
not already detect the fault."""
import argparse, os, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FAST = 'migration or refuses'
LOAD = 'loads_saves_reloads and 870fe30'
# name, what the fault is, text to find in index.html (exactly once), replacement, which tests to run
MUTATIONS = [
    ('control', 'none: the unmutated game must pass', None, None, [FAST]),
    ('migrate-resets-docs', 'migrate() overwrites the documents of every life',
     "if(!s.docs){s.docs=s.bg==='local'?{...BG.local.docs}:{...NODOCS};if(s.queue>0&&s.bg!=='local')s.docs.queue=1}", "s.docs={...NODOCS};", [FAST, LOAD]),
    ('lifeinit-resets-people', 'lifeInit() empties the list of people on every load', "if(!s.people)s.people=[];", "s.people=[];", [FAST, LOAD]),
    ('migrate-forgets-version', 'migrate() no longer sets the version to 5', "s.v=5;return s}", "return s}", [FAST]),
    ('migrate-not-idempotent', 'migrate() changes the life every time it runs (adds a point)', "s.v=5;return s}", "s.points=(s.points||0)+1;s.v=5;return s}", [FAST]),
    ('inbox-resets-todo', 'inboxInit() replaces the to-do list on every load', "if(!s.todo)s.todo={day:s.day||1,items:[]};", "s.todo={day:s.day||1,items:[]};", [FAST, LOAD]),
    ('import-skips-migrate', 'importCheck() hands back the file without migrating it', "m=migrate(JSON.parse(JSON.stringify(g)))", "m=JSON.parse(JSON.stringify(g))", [FAST]),
    ('import-ignores-hash', 'importCheck() accepts a file whose hash does not match', "e.sha256!==await saveHash(g)", "false", [FAST]),
    ('import-accepts-newer', 'importCheck() accepts a file from a newer version', "if(e.v>5)", "if(e.v>9)", [FAST]),
]


def run(name, html, selectors, port, all_selectors=False):
    env = {**os.environ, 'SL_PORT': str(port)}
    if html is not None:
        env['SL_INDEX_HTML'] = str(html)
    else:
        env.pop('SL_INDEX_HTML', None)
    worst = 0
    notes = []
    for sel in selectors:
        t0 = time.time()
        r = subprocess.run([sys.executable, '-m', 'pytest', str(ROOT / 'tests' / 'test_save_fixtures.py'), '-q', '-k', sel, '-x'],
                           cwd=ROOT, env=env, capture_output=True, text=True)
        tail = [l for l in r.stdout.splitlines() if l.startswith(('FAILED', 'ERROR')) or ' passed' in l or ' failed' in l]
        notes.append(f"[{sel}] {'failed' if r.returncode else 'passed'} in {time.time() - t0:.0f}s: {(tail[-2:] or [''])[0][:110]}")
        worst = max(worst, r.returncode)
        if r.returncode and not all_selectors:
            break   # detected; the slower test need not run
    return worst, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', nargs='*')
    ap.add_argument('--all-selectors', action='store_true', help='run every test group even after a fault is detected')
    args = ap.parse_args()
    v = os.environ.get('SL_PORT', '')  # required, as for the tests (tests/game.py server_port; owner, 2026-11-26)
    if not v.strip().isdigit() or int(v) == 8000:
        sys.exit(f'set SL_PORT to a free port other than 8000, for example SL_PORT=8124 (got {v!r})')
    port = int(v)
    source = (ROOT / 'index.html').read_text(encoding='utf-8')
    bad = False
    with tempfile.TemporaryDirectory() as d:
        for name, what, find, repl, selectors in MUTATIONS:
            if args.only and name not in args.only and name != 'control':
                continue
            html = None
            if find is not None:
                assert source.count(find) == 1, f'{name}: the text to mutate was found {source.count(find)} times in index.html; update this tool'
                html = Path(d) / f'{name}.html'
                html.write_text(source.replace(find, repl), encoding='utf-8')
            code, notes = run(name, html, selectors, port, args.all_selectors)
            ok = (code == 0) if find is None else (code != 0)
            bad |= not ok
            print(f"{'OK ' if ok else 'BAD'} {name:26} {'passes' if find is None else ('DETECTED' if code else 'NOT DETECTED')}  {what}")
            for n in notes:
                print('      ', n)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
