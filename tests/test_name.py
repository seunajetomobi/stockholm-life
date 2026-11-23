"""The game's name is Stockholmsliv (owner decision, 2026-11-21): the title, the board, the loading box and the start screen say so."""
import game

HTML = (game.ROOT / 'index.html').read_text(encoding='utf-8')


def test_title_and_visible_names_say_stockholmsliv():
    assert '<title>Stockholmsliv</title>' in HTML
    assert '<div class="brand">Stockholms<span>liv</span></div>' in HTML
    assert '<b>Stockholms<span>liv</span></b>' in HTML and '<h2 class="hero">Stockholmsliv</h2>' in HTML


def test_no_visible_text_still_says_stockholm_life():
    body = HTML
    left = [l.strip()[:100] for l in body.split('\n') if 'Stockholm Life' in l]
    assert left == [], left
