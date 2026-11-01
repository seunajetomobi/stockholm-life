"""Pendeltåg camera regression (df54793): the camera stays inside the car and out of posts, poles and cab walls,
"Eyes" view is unchanged, standing resets pitch, getting off restores the city camera, the phone HUD fits.
Ported from the audit's traincam.py and traincam2.py. Geometry only: this says nothing about how the camera feels."""
import time
import pytest
import game

pytestmark = [pytest.mark.browser, pytest.mark.hook]

# runs inside the page: every seat in the middle and end cars x 24 yaw angles x 3 pitches, then standing spots x 24 yaws
SWEEP_JS = r"""
() => {
  const T = window.__T, {IW, HALF, JRC} = T, B = T.jrBlockers(), JRS = T.JRS, JR = T.JR;
  const R = {seated: 0, standing: 0, samples: 0, problems: []};
  const inBox = (x, z) => B.some(([x0, x1, z0, z1]) => x > x0 + 1e-6 && x < x1 - 1e-6 && z > z0 + 1e-6 && z < z1 - 1e-6);
  const inside = (c, minY) => Math.abs(c.x) <= IW - JRC.r + 1e-6 && Math.abs(c.z) <= HALF - 0.08 - JRC.r + 1e-6 && c.y <= JRC.top + 1e-6 && c.y >= minY - 1e-6;
  const yaws = [...Array(24).keys()].map(i => i * Math.PI / 12), f2 = v => +v.toFixed(2);
  const want = [];
  for (const k of [2, 0]) for (const zb of [0, 7.31, -7.31]) for (const f of [1, -1]) for (const x of [-1.17, -0.72, -0.27, 0.77, 1.22]) {
    const z = T.zcOf(k) + zb - f * 0.42, s = JRS.seats.find(q => q.k === k && Math.abs(q.x - x) < 1e-6 && Math.abs(q.z - z) < 1e-6 && q.f === f);
    if (s) want.push(s);
  }
  for (const s of want) {
    const prev = s.taken; if (prev === 'npc') s.taken = null;
    if (T.CS.sit) T.jrStand(true);
    T.jrSit(s); R.seated++;
    if (JR.cam !== 'you') R.problems.push(['seat-default-not-you', s.x, s.f, JR.cam]);
    for (const p of [-0.08, -0.3, -0.6]) for (const y of yaws) {
      JR.yaw = y; JR.pitch = p; T.jrCam(T.av.position); const c = T.icam.position; R.samples++;
      if (!inside(c, 1.3)) R.problems.push(['seat-out', s.x, s.f, f2(y), p, f2(c.x), f2(c.y), f2(c.z - s.z)]);
      if (inBox(c.x, c.z)) R.problems.push(['seat-in-blocker', s.x, s.f, f2(y), p]);
      if (!T.av.visible) R.problems.push(['seat-avatar-hidden', s.x, s.f, f2(y)]);
    }
    T.jrStand(true); if (prev === 'npc') s.taken = prev;
  }
  const k = 2, zc = T.zcOf(k), z0 = zc - T.CARM / 2, z1 = zc + T.CARM / 2, spots = [];
  for (const z of [z0 + 0.35, z0 - 0.35, z1 - 0.35, z1 + 0.35, zc, zc + 2.5, zc - 6]) spots.push([0.25, z]);
  for (const dz of [zc - T.DOORZ, zc + T.DOORZ]) for (const x of [-1.15, -0.6, 0.25, 0.9, 1.2]) spots.push([x, dz]);
  for (const [x, z] of spots) {
    T.av.position.set(x, 0, z); R.standing++;
    for (const y of yaws) {
      JR.yaw = y; JR.pitch = -0.04; JR.camA = 0; T.jrCam(T.av.position); const c = T.icam.position; R.samples++;
      if (!T.av.visible) continue;  // fell back to eyes view where there is no room: allowed
      if (!inside(c, 0)) R.problems.push(['stand-out', x, f2(z - zc), f2(y), f2(c.x), f2(c.y), f2(c.z - zc)]);
      if (inBox(c.x, c.z)) R.problems.push(['stand-in-blocker', x, f2(z - zc), f2(y)]);
    }
  }
  T.av.position.set(0.25, 0, zc);
  return R;
}
"""


@pytest.fixture(scope='module')
def train(browser):
    ctx, page, err = game.new_page(browser, 960, 600, hook=True)
    game.boot(page)
    if game.intro_shown(page):
        game.start_life(page)
    game.clear_overlays(page)
    game.enter_station(page)
    game.board_train(page)
    yield page, err
    ctx.close()


def test_sweep_inside_car(train):
    page, err = train
    r = page.evaluate(SWEEP_JS)
    assert r['seated'] >= 60 and r['standing'] >= 17, r  # 60 seats and 17 spots at df54793
    assert r['problems'] == [], r['problems'][:20]
    assert err.uncaught == []
    print(f"{r['seated']} seats, {r['standing']} standing spots, {r['samples']} camera samples")


def test_you_eyes_and_standing(train):
    page, err = train
    page.evaluate("() => { const s = __T.JRS.seats.find(q => !q.taken && q.k === 2 && q.x === -1.17); __T.jrSit(s) }")
    time.sleep(3)
    you = page.evaluate("() => ({cam: __T.JR.cam, av: __T.av.visible, label: document.getElementById('jrView').textContent})")
    assert you['cam'] == 'you' and you['av'], you
    game.shot(page, 'traincam-seat-you')

    page.evaluate("() => document.getElementById('jrView').click()")
    time.sleep(3)
    # the eyes position of the camera before df54793, from the seat
    eyes = page.evaluate("""() => { const s = __T.CS.sit, e = [s.x + (0.25 - s.x) * 0.18 + Math.sin(s.yaw) * 0.1, 1.26, s.z + Math.cos(s.yaw) * 0.1];
      return {cam: __T.JR.cam, av: __T.av.visible, same: __T.icam.position.toArray().every((v, i) => Math.abs(v - e[i]) < 1e-6)} }""")
    assert eyes == {'cam': 'eyes', 'av': False, 'same': True}, eyes
    game.shot(page, 'traincam-seat-eyes')

    page.evaluate("() => document.getElementById('jrView').click()")
    time.sleep(2)
    back = page.evaluate("() => ({cam: __T.JR.cam, av: __T.av.visible, hiddenPpl: __T.JRS.ppl.filter(q => !q.visible).length})")
    assert back['cam'] == 'you' and back['av'], back

    page.evaluate("() => { __T.JR.pitch = -0.5 }")  # as if dragged to look down, then stand up
    page.evaluate("() => document.getElementById('jrSit').click()")
    time.sleep(3)
    stood = page.evaluate("() => ({sit: !!__T.CS.sit, pitch: __T.JR.pitch, av: __T.av.visible, hiddenPpl: __T.JRS.ppl.filter(q => !q.visible).length})")
    assert stood == {'sit': False, 'pitch': -0.04, 'av': True, 'hiddenPpl': 0}, stood
    assert err.uncaught == []


def test_gangway_below_header(train):
    """Back to the gangway between cars: the camera stays below the gangway header (from y 2.0) and inside the car."""
    page, err = train
    page.evaluate("() => { const T = __T, z0 = T.zcOf(2) - T.CARM / 2; T.av.position.set(0.25, 0, z0 + 0.45); T.JR.yaw = 0; T.JR.camA = 0 }")
    time.sleep(4)
    c = page.evaluate("() => ({y: __T.icam.position.y, x: __T.icam.position.x, top: __T.JRC.top, IW: __T.IW, av: __T.av.visible})")
    game.shot(page, 'traincam-gangway')
    assert c['y'] <= c['top'] + 1e-6 and abs(c['x']) <= c['IW'], c
    assert err.uncaught == []


def test_walking_camera_follows(train):
    """Standing in the aisle, hold W (real key presses): you walk along the car and the camera comes with you, staying
    inside the car, out of the blockers and below the ceiling, with you visible and on screen."""
    page, err = train
    game.clear_overlays(page)
    page.evaluate("() => { const T = __T; if (T.CS.sit) T.jrStand(true); T.av.position.set(0.25, 0, T.zcOf(2) - 3); T.JR.yaw = 0; T.JR.pitch = -0.04; T.JR.camA = 0 }")
    time.sleep(3)
    pos = "() => ({p: __T.av.position.toArray(), c: __T.icam.position.toArray()})"
    before = page.evaluate(pos)
    page.keyboard.down('w')
    time.sleep(4)
    page.keyboard.up('w')
    time.sleep(2)
    after = page.evaluate("""() => { const T = __T, c = T.icam.position, p = T.av.position, r = T.JRC.r;
      const inBox = T.jrBlockers().some(([x0, x1, z0, z1]) => c.x > x0 + 1e-6 && c.x < x1 - 1e-6 && c.z > z0 + 1e-6 && c.z < z1 - 1e-6);
      const head = new THREE.Vector3(p.x, 1.6, p.z).project(T.icam);
      return {p: p.toArray(), c: c.toArray(), av: T.av.visible, sit: !!T.CS.sit,
        inside: Math.abs(c.x) <= T.IW - r + 1e-6 && Math.abs(c.z) <= T.HALF - 0.08 - r + 1e-6 && c.y <= T.JRC.top + 1e-6,
        inBox, headOnScreen: head.z < 1 && Math.abs(head.x) <= 1 && Math.abs(head.y) <= 1} }""")
    game.shot(page, 'traincam-walked')
    walked = after['p'][2] - before['p'][2]
    followed = after['c'][2] - before['c'][2]
    assert not after['sit'] and walked > 0.3, (before, after)            # you walked forward along the car
    assert abs(followed - walked) < 0.75, (walked, followed, before, after)  # and the camera came with you
    assert after['inside'] and not after['inBox'], after
    assert after['av'] and after['headOnScreen'], after
    assert err.uncaught == []


def test_get_off_restores_city_camera(train):
    """Shortcut: as if the train had arrived at its first stop (a real arrival is not reached in a test run)."""
    page, err = train
    page.evaluate("() => { __T.JR.si = 1; __T.jrAlight() }")
    assert game.wait_for(page, "() => !__T.CS.mode && !__T.JR", 60), 'still in the train'
    time.sleep(3)
    city = page.evaluate("""() => ({avInScene: __T.av.parent === __T.scene, av: __T.av.visible, controls: __T.controls.enabled,
      hud: getComputedStyle(document.getElementById('csHud')).display, inside: document.body.classList.contains('inside')})""")
    game.shot(page, 'traincam-city-after')
    assert city == {'avInScene': True, 'av': True, 'controls': True, 'hud': 'none', 'inside': False}, city
    assert err.uncaught == []


@pytest.mark.xfail(reason='KNOWN_ISSUES L10: the place label often stays on the train after getting off (seen with this shortcut only)', strict=False)
def test_place_label_after_getting_off(train):
    page, _ = train
    where = page.evaluate("() => document.getElementById('where').textContent")
    assert not where.startswith('Pendeltåg'), where


def test_phone_hud_seated(browser):
    """390x844: seated with the train running, the ride HUD fits in three rows and the view button uses its short label."""
    ctx, page, err = game.new_page(browser, 390, 844, mobile=True, hook=True)
    try:
        game.boot(page)
        if game.intro_shown(page):
            game.start_life(page, mobile=True)
        game.clear_overlays(page)
        game.enter_station(page)
        game.board_train(page)
        page.evaluate("() => { const s = __T.JRS.seats.find(q => !q.taken && q.k === 2 && q.x === 0.77); __T.jrSit(s); __T.jrSkipStop() }")
        assert game.wait_for(page, "() => getComputedStyle(document.getElementById('csLine')).display === 'none'", 90), 'boarding message did not go away'
        time.sleep(3)
        hud = page.evaluate("""() => { const h = document.getElementById('csHud').getBoundingClientRect(), vis = [...document.querySelectorAll('#csHud > *')].filter(e => getComputedStyle(e).display !== 'none');
          const rows = []; for (const e of vis) { const r = e.getBoundingClientRect(), c = (r.top + r.bottom) / 2; if (!rows.some(y => Math.abs(y - c) < 10)) rows.push(c) }
          return {phase: __T.JR.phase, rows: rows.length, right: h.right, label: document.getElementById('jrView').textContent} }""")
        game.shot(page, 'traincam-phone-hud')
        assert hud['phase'] == 'run', hud
        assert hud['rows'] <= 3, hud
        assert hud['label'] == '🧍 You', hud
        assert hud['right'] <= 390 and game.overflow_x(page) == 0, hud
        assert err.uncaught == []
    finally:
        ctx.close()
