"""Save safety (KNOWN_ISSUES H3, H5, M6, M19, M20): failed saves are reported, unreadable saves are kept, the placeholder and
ended lives are never written, half-finished actions are not saved, and a stale tab that can see a newer save stops. Tabs can still race (M20 (2)).

Faults are injected by wrapping Storage.prototype in an init script. Regular expressions in window.__F name the keys that fail.
Run on an older index.html with SL_INDEX_HTML=<file> for the negative control.
Not provable here: a really hidden tab and the real back/forward cache are simulated (headless browsers do not produce them)."""
import json
import time
import pytest
import game

pytestmark = [pytest.mark.browser, pytest.mark.hook]

V4, V3 = 'stockholm-life-v4', 'stockholm-life-v3'
LIFE = {'name': 'Real', 'bg': 'newcomer', 'day': 3, 'hour': 10, 'money': 1200, 'energy': 70, 'mood': 50, 'social': 10, 'svenska': 5,
        'skill': 40, 'queue': 0, 'home': 'rinkebyRoom', 'loc': 'tc', 'job': None, 'flags': {'started': 1}, 'log': [], 'applied': {}}
PLACEHOLDER = {**LIFE, 'name': 'Alex', 'day': 1, 'flags': {}}
OLD_LIFE = {**LIFE, 'name': 'Old', 'flags': {}}
ONLY_V4, BOTH_KEYS, BACKUPS = f'^{V4}$', f'^{V4}$|^{V3}$', '-corrupt-'
READ, WRITE = 'could not be read', 'could not be saved'

INIT = """(() => {
  const seed = %s, faults = %s, P = Storage.prototype, get = P.getItem, set = P.setItem, rem = P.removeItem;
  if (get.call(localStorage, '__seeded') === null) { for (const k in seed) set.call(localStorage, k, seed[k]); set.call(localStorage, '__seeded', '1') }
  const F = window.__F = {get: faults.get || null, set: faults.set || null, remove: faults.remove || null, writes: []};
  const hit = (re, k) => re && new RegExp(re).test(k);
  P.getItem = function (k) { if (this === localStorage && hit(F.get, k)) throw new DOMException('test', 'SecurityError'); return get.call(this, k) };
  P.setItem = function (k, v) { if (this === localStorage) { if (hit(F.set, k)) throw new DOMException('test', 'QuotaExceededError'); F.writes.push(k) } return set.call(this, k, v) };
  P.removeItem = function (k) { if (this === localStorage && hit(F.remove, k)) throw new DOMException('test', 'SecurityError'); return rem.call(this, k) };
})()"""


class Tab:
    def __init__(self, ctx):
        self.page = ctx.new_page()
        self.err = game.Errors(self.page)

    def boot(self):
        game.boot(self.page)
        return self

    def press(self, selector):
        """Run a button's handler in a tab that is not in front. Playwright's click stalled for its full 30 s there in about 1 run in 30, with the button present."""
        self.js("s => document.querySelector(s).click()", selector)

    def sees(self, other):
        """Wait until this tab reads what the other stored. Tabs share storage through the browser, so a write can take a moment to arrive; KNOWN_ISSUES M20 (2). Both are read each time because the other tab keeps saving as it plays. The limit is long because, with software WebGL, one read here took up to 40 s while the other tab built its city."""
        t0 = time.time()
        while self.raw() != other.raw():
            assert time.time() - t0 < 120, 'the write never reached this tab'
            time.sleep(0.1)

    def go(self, name=None, behind=False):
        """Finish character creation; the name tells lives apart."""
        if name:
            self.page.evaluate("n => { const e = document.querySelector('#modalRoot input[type=text]'); if (e) { e.value = n; e.dispatchEvent(new Event('input', {bubbles: true})) } }", name)
        if behind:
            self.press('#modalRoot #go')
        else:
            self.page.click('#modalRoot #go')
        assert game.wait_for(self.page, "!document.querySelector('#modalRoot #go')", 30)
        time.sleep(2)
        game.clear_overlays(self.page)

    def js(self, code, arg=None):
        return self.page.evaluate(code, arg)

    def store(self):
        return self.js("() => Object.fromEntries(Object.keys(localStorage).filter(k => k !== '__seeded').map(k => [k, Storage.prototype.getItem.call(localStorage, k)]))")

    def raw(self, key=V4):
        return self.store().get(key)

    def life(self):
        r = self.raw()
        return json.loads(r) if r else None

    def backups(self):
        return {k: v for k, v in self.store().items() if BACKUPS in k}

    def status(self):
        return self.js("() => { const e = document.getElementById('saveStatus'); return e && !e.hidden ? e.textContent : '' }")

    def intro(self):
        return game.intro_shown(self.page)

    def record_status(self):
        """Keep every message #saveStatus shows, because a short one can be gone before the test looks."""
        self.js("() => { const e = document.getElementById('saveStatus'); window.__msgs = []; new MutationObserver(() => { if (e.textContent) window.__msgs.push(e.textContent) }).observe(e, {childList: true, characterData: true, subtree: true}) }")

    def status_seen(self):
        return self.js("() => window.__msgs")

    def faults(self, **kw):
        self.js("k => Object.assign(window.__F, k)", kw)

    def v4_writes(self):
        return self.js("k => window.__F.writes.filter(w => w === k).length", V4)

    def change(self):
        """Change the life without moving and try to save it. Returns the new money."""
        return self.js("() => { const T = window.__TS; T.S.money += 7; T.save(); return T.S.money }")

    def hide(self):
        self.js("() => { Object.defineProperty(document, 'visibilityState', {value: 'hidden', configurable: true}); document.dispatchEvent(new Event('visibilitychange')); delete document.visibilityState }")

    def leave(self):
        """Real navigation, so a real pagehide, to a same-origin file where storage can still be read."""
        self.page.goto(game.BASE + '/data/e.json', wait_until='load', timeout=120000)

    def reload(self):
        self.page.reload(wait_until='load', timeout=120000)
        self.page.wait_for_function("() => !document.getElementById('loading')", timeout=180000)
        time.sleep(2)
        return self


@pytest.fixture
def game_ctx(browser):
    made = []

    def make(seed=None, **faults):
        ctx = browser.new_context(viewport={'width': 960, 'height': 600})
        ctx.add_init_script(INIT % (json.dumps(seed or {}), json.dumps(faults)))
        body = game.hooked_html()
        ctx.route('**/index.html', lambda route: route.fulfill(status=200, content_type='text/html; charset=utf-8', body=body))
        made.append(ctx)
        return ctx
    yield make
    for c in made:
        c.close()


def tab(game_ctx, seed=None, **faults):
    return Tab(game_ctx(seed, **faults)).boot()


def seeded():
    return {V4: json.dumps(LIFE)}


# ---------- requirements 1-3: messages ----------
def test_save_failure_is_reported(game_ctx):
    t = tab(game_ctx, seeded())
    t.faults(set=ONLY_V4)
    t.change()
    assert WRITE in t.status()
    assert t.err.uncaught == []


def test_repeated_failures_one_message(game_ctx):
    t = tab(game_ctx, seeded())
    t.faults(set=ONLY_V4)
    t.js("() => { window.__toasts = 0; new MutationObserver(l => { for (const m of l) for (const n of m.addedNodes) if (n.classList && n.classList.contains('toast') && /sav/i.test(n.textContent)) window.__toasts++ }).observe(document.body, {childList: true}) }")
    first = None
    for _ in range(20):
        t.change()
        first = first or t.status()
    assert WRITE in first and t.status() == first
    assert t.js("() => document.querySelectorAll('#saveStatus').length") == 1
    assert t.js("() => window.__toasts") == 0, 'failures must not stack toasts'


def test_recovery_reported_while_standing_still(game_ctx):
    t = tab(game_ctx, seeded())
    t.faults(set=ONLY_V4)
    money = t.change()
    assert WRITE in t.status()
    t.faults(set=None)
    assert game.wait_for(t.page, "document.getElementById('saveStatus').textContent.includes('works again')", 45), 'recovery was not reported without further play'
    assert t.life()['money'] == money
    assert game.wait_for(t.page, "document.getElementById('saveStatus').hidden", 10), 'the recovery message should go away'


# ---------- requirements 4-6: no save, unreadable saves, copies ----------
def test_no_save_shows_no_message(game_ctx):
    t = tab(game_ctx)
    assert t.intro() and t.status() == '' and t.backups() == {}


@pytest.mark.parametrize('raw', ['{not json', '{}', '[]', 'null'])
def test_unreadable_variants_backed_up(game_ctx, raw):
    t = tab(game_ctx, {V4: raw})
    assert t.intro(), 'an unreadable save leads to character creation'
    assert READ in t.status()
    assert list(t.backups().values()) == [raw]
    assert t.raw() == raw, 'nothing has been overwritten yet'


def test_storage_unreadable_at_boot_writes_nothing(game_ctx):
    t = tab(game_ctx, get=BOTH_KEYS)
    assert t.intro() and 'cannot be read' in t.status()
    t.go()
    assert t.v4_writes() == 0
    t.faults(get=None)
    t.js("() => window.__TS.save()")
    assert t.life(), 'with storage readable again and empty, the life can be saved'


def test_storage_unreadable_then_existing_save_is_not_overwritten(game_ctx):
    raw = json.dumps(LIFE)
    t = tab(game_ctx, {V4: raw}, get=BOTH_KEYS)
    t.go()
    t.faults(get=None)
    t.js("() => window.__TS.save()")
    assert t.raw() == raw and 'another tab' in t.status()


def test_corrupt_preserved_before_new_life(game_ctx):
    t = tab(game_ctx, {V4: '{not json'})
    assert list(t.backups().values()) == ['{not json']
    t.go()
    assert list(t.backups().values()) == ['{not json']
    assert t.life() and t.life()['flags']['started'] == 1, 'the new life is saved once the old one is safe'


def test_earlier_backup_not_overwritten(game_ctx):
    t = tab(game_ctx, {V4: '{second', V4 + '-corrupt-1': '{first'})
    assert sorted(t.backups().values()) == ['{first', '{second']


def test_identical_backup_not_duplicated(game_ctx):
    t = tab(game_ctx, {V4: '{not json'}).reload()
    assert list(t.backups().values()) == ['{not json']


def test_backup_failure_never_overwrites(game_ctx):
    t = tab(game_ctx, {V4: '{not json'}, set=BACKUPS)
    assert 'will not be overwritten' in t.status()
    t.go()
    t.change()
    t.hide()
    assert t.raw() == '{not json' and t.v4_writes() == 0
    assert 'will not be overwritten' in t.status()
    t.leave()
    assert t.raw() == '{not json', 'not even on leaving the page'


def test_backup_retry_succeeds_then_saves(game_ctx):
    t = tab(game_ctx, {V4: '{not json'}, set=BACKUPS)
    t.go()
    t.change()
    t.faults(set=None)
    money = t.change()
    assert list(t.backups().values()) == ['{not json']
    assert t.life()['money'] == money and 'works again' in t.status()


def test_message_clears_when_first_save_succeeds_after_backup_failure(game_ctx):
    """Storage recovers before the first save of the new life, so no save ever failed: the warning must still go."""
    t = tab(game_ctx, {V4: '{not json'}, set=BACKUPS)
    assert 'will not be overwritten' in t.status()
    t.record_status()
    t.faults(set=None)
    t.go()
    assert list(t.backups().values()) == ['{not json'] and t.life()
    assert any('works again' in m for m in t.status_seen()), t.status_seen()
    assert 'will not be overwritten' not in t.status(), 'the warning must not stay'


def test_message_clears_when_first_save_succeeds_after_unreadable_storage(game_ctx):
    t = tab(game_ctx, get=BOTH_KEYS)
    assert 'cannot be read' in t.status()
    t.record_status()
    t.faults(get=None)
    t.go()
    assert t.life()
    assert any('works again' in m for m in t.status_seen()), t.status_seen()
    assert 'cannot be read' not in t.status(), 'the warning must not stay'


def test_corrupt_v3_kept_and_new_life_uses_v4(game_ctx):
    t = tab(game_ctx, {V3: '{not json'})
    assert t.intro() and READ in t.status()
    assert list(t.backups().values()) == ['{not json']
    t.go()
    assert t.raw(V3) == '{not json' and t.life()
    assert not t.reload().intro(), 'v4 is loaded from now on'


def test_corrupt_v4_does_not_fall_back_to_v3(game_ctx):
    t = tab(game_ctx, {V4: '{not json', V3: json.dumps(OLD_LIFE)})
    assert t.intro() and list(t.backups().values()) == ['{not json']


# ---------- requirement 9: the placeholder ----------
def test_placeholder_never_saved(game_ctx):
    t = tab(game_ctx)
    t.hide()
    t.js("() => window.__TS.save()")
    assert t.raw() is None and t.v4_writes() == 0
    assert t.reload().intro(), 'character creation must come back'
    assert t.raw() is None
    t.leave()
    assert t.raw() is None


def test_old_placeholder_shows_intro(game_ctx):
    t = tab(game_ctx, {V4: json.dumps(PLACEHOLDER)})
    assert t.intro() and t.status() == '' and t.backups() == {}
    t.go()
    assert t.life()['flags']['started'] == 1


def test_v4_without_started_past_day_1_is_preserved(game_ctx):
    raw = json.dumps({**PLACEHOLDER, 'day': 5})
    t = tab(game_ctx, {V4: raw})
    assert t.intro() and READ in t.status() and list(t.backups().values()) == [raw]


# ---------- requirements 7-8: deportation and restart ----------
def test_pagehide_does_not_resurrect(game_ctx):
    t = tab(game_ctx, seeded())
    t.js("() => window.__TS.deported()")
    t.page.click('#modalRoot #again')
    t.page.wait_for_function("() => !document.getElementById('loading') && document.querySelector('#modalRoot #go')", timeout=180000)
    assert t.intro() and t.raw() is None


def test_deportation_takes_effect_on_screen(game_ctx):
    t = tab(game_ctx, seeded())
    t.js("() => window.__TS.deported()")
    assert t.raw() is None, 'the save goes as soon as the screen appears'
    t.leave()
    assert t.raw() is None, 'closing the screen must not bring the life back'
    assert t.boot().intro()


def test_deportation_removes_v4_and_v3(game_ctx):
    t = tab(game_ctx, {**seeded(), V3: json.dumps(OLD_LIFE)})
    t.js("() => window.__TS.deported()")
    assert t.raw() is None and t.raw(V3) is None
    assert t.reload().intro(), 'the old v3 life must not come back'


def test_failed_removal_uses_tombstone(game_ctx):
    t = tab(game_ctx, {**seeded(), V3: json.dumps(OLD_LIFE)}, remove=BOTH_KEYS)
    t.js("() => window.__TS.deported()")
    assert t.raw().startswith('ENDED:') and t.raw(V3).startswith('ENDED:')
    assert t.page.inner_text('#modalRoot #again') .lower() == 'start a new life'
    assert t.reload().intro() and t.status() == ''
    t.go()
    assert t.life()['flags']['started'] == 1


def test_tombstone_blocks_v3_fallback(game_ctx):
    t = tab(game_ctx, {V4: 'ENDED:1', V3: json.dumps(OLD_LIFE)})
    assert t.intro() and t.status() == '' and t.backups() == {}


def test_total_failure_stays_on_screen_no_reload(game_ctx):
    raw = json.dumps(LIFE)
    t = tab(game_ctx, {V4: raw}, remove=BOTH_KEYS, set=BOTH_KEYS)
    t.js("() => { window.__TS.deported(); window.__same = 1 }")
    assert t.page.inner_text('#modalRoot #again').lower() == 'try again'
    assert 'could not be removed' in t.page.inner_text('#modalRoot #endNote')
    t.page.click('#modalRoot #again')
    time.sleep(1)
    assert t.js("() => window.__same") == 1, 'the game must not reload into the deported life'
    assert 'still could not be removed' in t.page.inner_text('#modalRoot #endNote')
    assert t.raw() == raw, 'storage refused'
    t.change()
    t.hide()
    assert t.v4_writes() == 0 and t.raw() == raw, 'and this tab never writes it again'


def test_try_again_succeeds_then_reloads(game_ctx):
    t = tab(game_ctx, seeded(), remove=BOTH_KEYS, set=BOTH_KEYS)
    t.js("() => window.__TS.deported()")
    t.faults(remove=None, set=None)
    t.page.click('#modalRoot #again')
    t.page.wait_for_function("() => !document.getElementById('loading') && document.querySelector('#modalRoot #go')", timeout=180000)
    assert t.raw() is None


def test_timers_after_deportation_do_not_write(game_ctx):
    t = tab(game_ctx, seeded())
    t.js("""() => { const T = window.__TS; T.S.crime = T.S.crime || {heat: 0, rec: [], pending: [], gains: 0}; T.deported(); window.__F.writes.length = 0; const before = T.S.crime.rec.length;
      T.busy = false; T.save(); T.sentence({c: 'olovlig', day: 0}); T.save(); window.__after = T.S.crime.rec.length - before }""")
    assert t.js("() => window.__after") == 0, 'a second due case must not run after the life has ended'
    assert t.v4_writes() == 0 and t.raw() is None


def test_restart_commits_at_go(game_ctx):
    t = tab(game_ctx, seeded())
    t.js("() => document.getElementById('restart').click()")
    t.page.click('#modalRoot #yes')
    assert t.intro()
    t.hide()
    assert t.life()['name'] == 'Real', 'until Go is pressed the life is still there'
    assert not t.reload().intro()
    assert t.js("() => window.__TS.S.name") == 'Real'
    t.js("() => document.getElementById('restart').click()")
    t.page.click('#modalRoot #yes')
    t.go()
    assert t.life()['name'] != 'Real'
    t.leave()
    assert t.life()['name'] != 'Real', 'the old life cannot come back'


# ---------- requirement 10 and M6: lifecycle saves ----------
def test_pagehide_saves_progress(game_ctx):
    t = tab(game_ctx, seeded())
    money = t.js("() => { const T = window.__TS; T.S.money += 7; return T.S.money }")
    t.leave()
    assert t.life()['money'] == money


def test_hidden_tab_saves_progress(game_ctx):
    t = tab(game_ctx, seeded())
    money = t.js("() => { const T = window.__TS; T.S.money += 7; return T.S.money }")
    t.hide()
    assert t.life()['money'] == money


def test_duplicate_events_write_once(game_ctx):
    t = tab(game_ctx, seeded())
    money = t.js("""() => { const T = window.__TS; T.S.money += 7; window.__F.writes.length = 0;
      Object.defineProperty(document, 'visibilityState', {value: 'hidden', configurable: true}); document.dispatchEvent(new Event('visibilitychange')); delete document.visibilityState;
      dispatchEvent(new Event('pagehide')); dispatchEvent(new Event('pagehide')); return T.S.money }""")
    assert t.js("k => window.__F.writes.filter(w => w === k).length", V4) == 1
    assert t.life()['money'] == money


# ---------- half-finished actions ----------
def test_no_save_while_busy_then_saved_after(game_ctx):
    t = tab(game_ctx, seeded())
    before = t.raw()
    money = t.js("() => { const T = window.__TS; T.busy = true; T.S.money -= 43; T.save(); return T.S.money }")
    t.hide()
    assert t.raw() == before, 'a journey in progress must not be saved'
    t.js("() => { const T = window.__TS; T.busy = false }")
    t.hide()
    assert t.life()['money'] == money


def test_no_save_during_lesson(game_ctx):
    t = tab(game_ctx, seeded())
    before = t.raw()
    money = t.js("() => { const T = window.__TS; T.COACH.mode = 'lesson'; T.S.money -= 750; T.save(); const m = T.S.money; return m }")
    saved_during = t.raw()
    t.js("() => { const T = window.__TS; T.COACH.mode = null; T.save() }")
    assert saved_during == before, 'a lesson in progress must not be saved'
    assert t.life()['money'] == money


COURT = """() => { const T = window.__TS; T.S.crime = {heat: 0, rec: [], pending: [{c: 'olovlig', day: 1}], gains: 0}; %s }"""


def test_court_case_survives_until_sentenced(game_ctx):
    t = tab(game_ctx, seeded())
    pending = t.js(COURT % "T.crimeDaily(); T.save(); return JSON.parse(localStorage.getItem('stockholm-life-v4')).crime.pending.length")
    assert pending == 1, 'a save before the sentence must still hold the case'
    assert game.wait_for(t.page, "window.__TS.S.crime.pending.length === 0", 10)
    assert [r['c'] for r in t.js("() => window.__TS.S.crime.rec")] == ['olovlig']


def test_court_case_not_sentenced_twice(game_ctx):
    t = tab(game_ctx, seeded())
    t.js(COURT % "T.crimeDaily(); T.crimeDaily(); T.crimeDaily()")
    assert game.wait_for(t.page, "window.__TS.S.crime.pending.length === 0", 10)
    time.sleep(1)
    assert [r['c'] for r in t.js("() => window.__TS.S.crime.rec")] == ['olovlig']


def test_cs_pend_not_saved(game_ctx):
    """Known limitation, KNOWN_ISSUES M19: station and train time not yet flushed is not in the save. Not a goal; this records it."""
    t = tab(game_ctx, seeded())
    hour, clock = t.js("() => { const T = window.__T, TS = window.__TS; T.CS.pend = 30; TS.S.money += 7; TS.save(); const r = [TS.S.hour, T.csClk()]; T.CS.pend = 0; return r }")
    assert t.life()['hour'] == hour
    assert clock == pytest.approx(hour * 60 + 30)


# ---------- several tabs: the same context shares storage ----------
def two(game_ctx, seed=None):
    ctx = game_ctx(seed)
    return Tab(ctx).boot(), Tab(ctx).boot()


def test_other_tab_restart_stops_stale_tab(game_ctx):
    a, b = two(game_ctx, seeded())
    b.js("() => document.getElementById('restart').click()")
    b.page.click('#modalRoot #yes')
    b.go('Bee')
    assert b.life()['name'] == 'Bee'
    a.sees(b)
    a.change()
    assert a.life()['name'] == 'Bee' and 'another tab' in a.status()
    a.leave()
    assert b.life()['name'] == 'Bee'


def test_other_tab_creation_blocks_stale_go(game_ctx):
    a, b = two(game_ctx)
    b.go('Bee')
    assert b.life()['name'] == 'Bee'
    a.sees(b)
    a.go('Ann', behind=True)
    assert b.life()['name'] == 'Bee', 'the first life created wins'
    assert 'another tab' in a.status()


def test_other_tab_deported_cannot_resurrect(game_ctx):
    a, b = two(game_ctx, {**seeded(), V3: json.dumps(OLD_LIFE)})
    b.js("() => window.__TS.deported()")
    a.sees(b)
    a.change()
    assert a.raw() is None and a.raw(V3) is None and 'another tab' in a.status()
    a.leave()
    assert b.raw() is None and b.raw(V3) is None


def test_stale_tab_deported_leaves_newer_life_alone(game_ctx):
    a, b = two(game_ctx, seeded())
    b.js("() => { const T = window.__TS; T.S.name = 'Bee'; T.save() }")
    a.sees(b)
    a.js("() => window.__TS.deported()")
    assert (b.life() or {}).get('name') == 'Bee', 'the stored save belongs to the other tab'
    a.press('#modalRoot #again')
    a.page.wait_for_function("() => !document.getElementById('loading')", timeout=180000)
    assert (b.life() or {}).get('name') == 'Bee', 'and clicking through the screen must not remove it either'


def test_stale_page_after_return_cannot_write(game_ctx):
    """Simulated: automated browsers do not use the back/forward cache, so this is a page that kept its old state and fires pageshow."""
    a, b = two(game_ctx, seeded())
    b.js("() => { const T = window.__TS; T.S.name = 'Bee'; T.save() }")
    a.sees(b)
    a.js("() => { dispatchEvent(new PageTransitionEvent('pageshow', {persisted: true})); window.__TS.S.money += 7; dispatchEvent(new PageTransitionEvent('pagehide', {persisted: true})) }")
    assert b.life()['name'] == 'Bee'


def test_close_saves_converge_to_one_writer(game_ctx):
    """Interleaved, not truly simultaneous: whichever tab loses a comparison stops, and the other keeps saving."""
    a, b = two(game_ctx, seeded())
    a.change()
    b.sees(a)
    b.change()
    assert 'another tab' in b.status() and a.status() == ''
    money = a.change()
    b.sees(a)
    b.change()
    assert a.life()['money'] == money


def test_two_tabs_v3_first_writer_wins(game_ctx):
    raw = json.dumps(OLD_LIFE)
    a, b = two(game_ctx, {V3: raw})
    money = a.change()
    b.sees(a)
    b.change()
    assert a.life()['money'] == money and 'another tab' in b.status()
    assert a.raw(V3) == raw, 'v3 is never written'


def test_placeholder_v4_with_valid_v3_loads_v3(game_ctx):
    t = tab(game_ctx, {V4: json.dumps(PLACEHOLDER), V3: json.dumps(OLD_LIFE)})
    assert not t.intro() and t.js("() => window.__TS.S.name") == 'Old'
    t.change()
    assert t.life()['name'] == 'Old' and t.life()['flags']['started'] == 1
