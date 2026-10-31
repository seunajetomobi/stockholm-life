"""pytest fixtures: the local web server and one headless browser shared by all browser tests."""
import subprocess, sys, time, urllib.request
import pytest
import game


def pytest_report_header(config):
    """First lines of every run: which browser binary the tests drive, so a log shows it (CI pins Chromium 145)."""
    path = game.chrome_path()
    if not path:
        return "browser: Playwright's own Chromium (CHROME not set and no system Google Chrome)"
    try:
        version = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception as e:
        version = f'version unknown: {e}'
    return f'browser: {path} ({version})'


def _serving():
    """True when something on the port serves this repo's index.html; fails if it serves something else."""
    try:
        body = urllib.request.urlopen(game.BASE + '/index.html', timeout=3).read()
    except Exception:
        return False
    if body != (game.ROOT / 'index.html').read_bytes():
        pytest.exit(f'{game.BASE} serves a different index.html than {game.ROOT}. Stop that server or set SL_PORT.', 2)
    return True


@pytest.fixture(scope='session')
def server():
    """Use a server already running on the port (e.g. ./start.sh), or start `python3 -m http.server` for the session."""
    if _serving():
        yield game.BASE
        return
    proc = subprocess.Popen([sys.executable, '-m', 'http.server', str(game.PORT), '--bind', '127.0.0.1'],
                            cwd=game.ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        if _serving():
            break
        time.sleep(0.2)
    else:
        proc.terminate()
        pytest.exit(f'could not start a local server on port {game.PORT}', 2)
    yield game.BASE
    proc.terminate()
    proc.wait(10)


@pytest.fixture(scope='session')
def browser(server):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.exit('Playwright is not installed: python3 -m pip install -r tests/requirements.txt', 2)
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path=game.chrome_path(), headless=True, args=game.CHROME_ARGS)
        yield br
        br.close()
