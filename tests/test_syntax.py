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


def test_flights_worker():
    node_check((ROOT / 'tools/flights-worker.js').read_text(encoding='utf-8'), '.mjs')  # an ES module


def test_python_tools():
    for f in sorted((ROOT / 'tools').glob('*.py')):
        compile(f.read_text(encoding='utf-8'), str(f), 'exec')  # in memory, so no __pycache__ is written


if __name__ == '__main__':
    import pytest
    sys.exit(pytest.main([__file__, '-q']))
