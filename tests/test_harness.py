"""The test harness itself: every browser context a test makes has the game's start-up preferences (tests/game.py new_context).

Regression (PR #56, CI run 45375413224): ten test files called browser.new_context() directly. Once the game opened on the
title page and ran on real Stockholm time by default, those tests met the title page instead of the intro and the real
clock instead of the game clock, and 51 set-ups and most of 44 tests failed for that reason alone."""
import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent


def test_no_test_makes_a_browser_context_without_the_start_preferences():
    direct = []
    for f in sorted(TESTS.glob('test_*.py')):
        if f.name == Path(__file__).name:
            continue  # this file names the call in its own text
        for n, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            if re.search(r'\bbrowser\.new_context\(', line):
                direct.append(f'{f.name}:{n}')
    assert direct == [], f'use game.new_context(browser, ...) instead of browser.new_context(...): {direct}'
