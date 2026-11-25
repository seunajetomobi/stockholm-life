"""The game is never seen half-built: the loading screen covers everything (including the dock and panels) until the title page is painted under it."""
import re
import game

READY = "() => { const t = document.getElementById('title'); return t && !t.hidden && /Start/.test(t.innerText) }"
HTML = (game.ROOT / 'index.html').read_text(encoding='utf-8')


def test_loader_is_on_top_of_the_whole_game_and_preloads_its_picture():
    head, body = HTML.split('</head>')
    # the loader is a direct child of the page, not inside the stage (the stage is its own layer, below the dock and panels)
    stage = body[body.index('<section class="stage"'):body.index('</section>')]
    assert 'id="loading"' not in stage and 'class="loading" id="loading"' in body
    assert body.index('class="loading" id="loading"') < body.index('class="title" id="title"')
    css = re.search(r'\.loading\{[^}]*\}', HTML).group(0)
    assert 'position:fixed' in css and 'inset:0' in css
    z = int(re.search(r'z-index:(\d+)', css).group(1))
    for name, rule in (('dock', r'\.dock\{[^}]*\}'), ('drawer', r'\.drawer\{[^}]*\}')):
        zz = int(re.search(r'z-index:(\d+)', re.search(rule, HTML).group(0)).group(1))
        assert z > zz, (name, z, zz)
    assert z > int(re.search(r'\.title\{[^}]*?z-index:(\d+)', HTML).group(1))            # and above the title page, which is painted underneath
    # the picture is preloaded (small, normal and 4K versions, matched to the same screen sizes as the CSS)
    assert len(re.findall(r'<link rel="preload" as="image" href="assets/title/stadshuset-(1280|1920|3840)\.jpg" media=', head)) == 3
    # text is held back until the font is ready instead of flashing a fallback font
    assert 'display=block' in head and 'display=swap' not in head


def test_nothing_of_the_game_shows_above_the_loading_screen(browser, server):
    """While the city loads (made slow on purpose), whatever is on top at the dock, the panel and the board is the loading screen."""
    slow = "(() => { const f = window.fetch; window.fetch = (u, ...a) => /\\/data\\//.test(String(u)) ? new Promise(r => setTimeout(r, 7000)).then(() => f(u, ...a)) : f(u, ...a); })();"
    ctx, page, err = game.new_page(browser, hook=True, realtime=True, title=True, width=1100, height=700, init_script=slow)
    page.set_default_timeout(120000)
    try:
        page.goto(game.BASE + '/index.html', wait_until='commit')
        samples = []
        probe = """() => { const pts = {dock: '.dock', drawer: '#drawer', board: '#board', places: '#places', center: null};
          const out = {};
          for (const [k, sel] of Object.entries(pts)) {
            const e = sel ? document.querySelector(sel) : null, r = e ? e.getBoundingClientRect() : {left: innerWidth / 2 - 1, top: innerHeight / 2 - 1, width: 2, height: 2};
            if (!r.width) { out[k] = 'n/a'; continue }
            const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            const ld = document.getElementById('loading'), tt = document.getElementById('title');
            out[k] = !top ? 'none' : (ld && ld.contains(top)) ? 'loading' : (tt && tt.contains(top)) ? 'title' : 'GAME:' + (top.id || top.className || top.tagName);
          }
          return {out, loading: !!document.getElementById('loading'), title: !!document.getElementById('title') && !document.getElementById('title').hidden} }"""
        for _ in range(40):
            try:
                st = page.evaluate(probe)
            except Exception:
                break
            samples.append(st)
            if st['title'] and not st['loading']:
                break
            page.wait_for_timeout(350)
        assert len(samples) >= 3, samples
        bad = [s for s in samples if any(str(v).startswith('GAME:') for v in s['out'].values())]
        assert bad == [], bad[:3]
        assert game.wait_for(page, READY, 120)
        assert err.uncaught == [], err.uncaught
    finally:
        ctx.close()
