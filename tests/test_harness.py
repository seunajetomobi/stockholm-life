"""The test harness itself: every browser context a test makes has the game's start-up preferences (tests/game.py new_context).

Regression (PR #56, CI run 45375413224): ten test files called browser.new_context() directly. Once the game opened on the
title page and ran on real Stockholm time by default, those tests met the title page instead of the intro and the real
clock instead of the game clock, and 51 set-ups and most of 44 tests failed for that reason alone."""
import os, re, subprocess, sys
from pathlib import Path
import pytest
import game

TESTS = Path(__file__).resolve().parent


@pytest.mark.parametrize('env,want', [
    ({'SL_PORT': '8126'}, 8126),
    ({'SL_PORT': '8000', 'GITHUB_ACTIONS': 'true'}, 8000),
    ({'GITHUB_ACTIONS': 'true'}, 8000),
    ({}, None), ({'SL_PORT': '8000'}, None), ({'SL_PORT': ''}, None), ({'SL_PORT': 'x'}, None),
    ({'GITHUB_ACTIONS': 'false'}, None)])
def test_the_local_port_must_be_given_and_is_never_8000(env, want):
    """Owner, 2026-11-26: on a developer machine the tests refuse to run without SL_PORT, or on port 8000 (the owner's own
    ./start.sh server); GitHub Actions keeps 8000 as its default."""
    if want is None:
        with pytest.raises(SystemExit, match='set SL_PORT'):
            game.server_port(env)
    else:
        assert game.server_port(env) == want


@pytest.mark.parametrize('env,ok', [({}, False), ({'SL_PORT': '8000'}, False), ({'SL_PORT': '8137'}, True), ({'GITHUB_ACTIONS': 'true'}, True)])
def test_loading_the_harness_enforces_the_port(env, ok):
    """The rule runs when tests/game.py is imported (as conftest.py and the fixture scripts do), not only when called."""
    base = {k: v for k, v in os.environ.items() if k not in ('SL_PORT', 'GITHUB_ACTIONS')}
    r = subprocess.run([sys.executable, '-c', 'import game; print(game.PORT)'], cwd=TESTS, env={**base, **env}, capture_output=True, text=True, timeout=60)
    if ok:
        assert r.returncode == 0 and r.stdout.strip() == env.get('SL_PORT', '8000'), (r.returncode, r.stdout, r.stderr)
    else:
        assert r.returncode != 0 and 'set SL_PORT' in r.stderr, (r.returncode, r.stdout, r.stderr)


def test_no_test_makes_a_browser_context_without_the_start_preferences():
    direct = []
    for f in sorted(TESTS.glob('test_*.py')):
        if f.name == Path(__file__).name:
            continue  # this file names the call in its own text
        for n, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            if re.search(r'\bbrowser\.new_context\(', line):
                direct.append(f'{f.name}:{n}')
    assert direct == [], f'use game.new_context(browser, ...) instead of browser.new_context(...): {direct}'
