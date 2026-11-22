"""The page tells search engines what it is, and the site has a sitemap (index.html head, sitemap.xml)."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = (ROOT / 'index.html').read_text(encoding='utf-8')
HEAD = HTML.split('</head>')[0]


def test_head_has_description_canonical_and_social_tags():
    assert re.search(r'<meta name="description" content="[^"]{60,300}">', HEAD)
    assert '<link rel="canonical" href="https://stockholmsliv.app/">' in HEAD
    for p in ('og:title', 'og:description', 'og:url', 'og:type'):
        assert f'property="{p}"' in HEAD, p


def test_structured_data_is_valid_json_about_the_game():
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', HEAD, re.S)
    assert m, 'no JSON-LD'
    d = json.loads(m.group(1))
    assert d['@type'] == 'VideoGame' and d['name'] == 'Stockholmsliv' and d['url'] == 'https://stockholmsliv.app/'


def test_sitemap_lists_the_game():
    x = (ROOT / 'sitemap.xml').read_text(encoding='utf-8')
    assert '<loc>https://stockholmsliv.app/</loc>' in x
