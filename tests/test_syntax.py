"""Static checks, no browser (a few seconds). Run alone with: python3 tests/test_syntax.py"""
import re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def inline_scripts():
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    return re.findall(r'<script>(.*?)</script>', html, re.S)


def node_check(code, suffix):
    node = shutil.which('node')
    if not node:
        import pytest
        pytest.skip('node is not installed')
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / f'check{suffix}'
        f.write_text(code, encoding='utf-8')
        r = subprocess.run([node, '--check', str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_index_inline_script():
    scripts = inline_scripts()
    assert scripts, 'no inline <script> found in index.html'
    for code in scripts:
        node_check(code, '.js')


def local_scripts():
    """The game's own script files that index.html loads (<script src> without a scheme), in order."""
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    return [s for s in re.findall(r'<script src="([^"]+)"', html) if '://' not in s]


def test_src_modules():
    """Every module under src/ (nested folders too) parses, exists, is loaded by index.html, and is read there with the
    same path (docs/MODULES.md). A .js file under src/ that index.html does not load fails here."""
    files = sorted(f.relative_to(ROOT).as_posix() for f in (ROOT / 'src').rglob('*.js'))
    for f in files:
        node_check((ROOT / f).read_text(encoding='utf-8'), '.js')  # a classic script, like the inline one
    loaded = [s for s in local_scripts() if s.startswith('src/')]
    for s in local_scripts():
        assert (ROOT / s).is_file(), f'index.html loads {s}, which is not in the repository'
    assert files == sorted(loaded), f'src/ holds {files}, index.html loads {sorted(loaded)}'
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    for s in loaded:
        rel = s[len('src/'):]
        name = Path(rel).stem
        calls = re.findall(r"useModule\('%s'(?:,\s*'([^']+)')?\)" % re.escape(name), html)
        assert calls, f'index.html loads {s} but never reads it with useModule({name!r})'
        assert [c or f'{name}.js' for c in calls] == [rel] * len(calls), f'useModule({name!r}) names {calls}, the script tag is {s}'


def test_local_scripts_are_published():
    """A script index.html loads must be among the files the Deploy workflow publishes and tools/live_check.py
    verifies; otherwise the published game stops at startup ("could not load src/….js")."""
    wf = (ROOT / '.github/workflows/deploy.yml').read_text(encoding='utf-8')
    m = re.search(r'^\s*cp -R (.+) _site/\s*$', wf, re.M)
    assert m, 'deploy.yml: no "cp -R … _site/" line found; update this test with the workflow'
    copied = m.group(1).split()
    import importlib.util
    spec = importlib.util.spec_from_file_location('live_check', ROOT / 'tools/live_check.py')
    lc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lc)
    missing = [s for s in local_scripts() if s.split('/')[0] not in copied]
    assert missing == [], f'deploy.yml publishes only {copied}; index.html also loads {missing}'
    unchecked = [s for s in local_scripts() if not lc.published(s)]
    assert unchecked == [], f'tools/live_check.py does not verify {unchecked}'


def test_flights_worker():
    node_check((ROOT / 'tools/flights-worker.js').read_text(encoding='utf-8'), '.mjs')  # an ES module


def test_python_tools():
    for f in sorted((ROOT / 'tools').glob('*.py')):
        compile(f.read_text(encoding='utf-8'), str(f), 'exec')  # in memory, so no __pycache__ is written


if __name__ == '__main__':
    import pytest
    sys.exit(pytest.main([__file__, '-q']))
