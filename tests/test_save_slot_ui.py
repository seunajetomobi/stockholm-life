"""Save slots, part B (M1c): managing the five slots from the Save file window (index.html, docs/KNOWN_ISSUES.md M20).

Part A (test_save_slots.py) is the storage; this file checks what the player can do with it:
  - the window lists five slots (name, day, money; Active, Empty, Ended, Unreadable) and offers only fitting actions;
  - opening another slot saves and reads back the current life, checks the target, updates the index, reloads; it is refused during
    a journey, an arrest, a driving lesson or a train ride, when storage cannot take the save or the index, or when another tab changed the slots;
  - a new life in an empty slot, rename (the name lives in the index, validated and escaped), delete (typed name, verified copy first, active slot refused);
  - start over, per-slot export and import, and restoring a kept copy (the slot's current life is copied first, the chosen copy is never touched);
  - copies: the newest 3 per category and slot, pruned only after the action succeeded; -corrupt- evidence is never pruned or overwritten;
  - storage that fails at each step, and an interrupted action followed by a reload, leave every life as it was; other slots stay byte for byte.
Faults are injected as in test_save_safety.py. Negative controls: run on a scratch copy with SL_INDEX_HTML=<file> (see tests/README.md)."""
import json
import time
import pytest
import game
from test_save_safety import Tab, game_ctx, tab, seeded, LIFE, V4, V3  # noqa: F401  (game_ctx is a fixture)

pytestmark = [pytest.mark.browser, pytest.mark.hook]

IDX = 'stockholm-life-slots-v1'
SLOT2, SLOT3, SLOT4 = 'stockholm-life-v4-slot-2', 'stockholm-life-v4-slot-3', 'stockholm-life-v4-slot-4'
SECOND = {**LIFE, 'name': 'Second', 'day': 5, 'money': 777}
THIRD = {**LIFE, 'name': 'Third', 'day': 8, 'money': 55}
J = json.dumps


def two(active=1, extra=None):
    idx = {'v': 1, 'active': active, 'slots': [{'id': 1, 'name': 'Real', 'day': 3}, {'id': 2, 'name': 'Second', 'day': 5}]}
    return {**seeded(), SLOT2: J(SECOND), IDX: J(idx), **(extra or {})}


def index(t):
    r = t.raw(IDX)
    return json.loads(r) if r else None


# the game's functions are inside its inline script, so they are reached through the test hook window.__TS (tests/game.py SAVE_HOOK), as in the other save tests
SCOPE = "new Function('T', 'with (T) { return (' + e + ') }')(window.__TS)"


def ev(t, expr):
    """Evaluate an expression whose names (slotSwitch, slotInfo, ...) are looked up on the test hook window.__TS."""
    return t.js("e => " + SCOPE, expr)


def settle(t):
    t.page.wait_for_function("() => !document.getElementById('loading')", timeout=180000)
    time.sleep(2)


def leave(t, expr):
    """Run an action that ends in a page reload; wait for the new page."""
    with t.page.expect_navigation(wait_until='load', timeout=120000):
        t.js("e => setTimeout(() => " + SCOPE + ", 0)", expr)
    settle(t)


def keys(t, cat):
    return sorted(k for k in t.store() if f'-{cat}-' in k)


def untouched(t, before, *changed, flushed=False):
    """Every save key except those named is byte for byte what it was. The game's own settings (sl-*) are not saves and are ignored.
    flushed=True: the life in the slot being left may have been rewritten by the save a switch makes first; it must still be the same life."""
    now = t.store()
    if flushed:
        a, b = json.loads(before[V4]), json.loads(now[V4])
        assert (a['name'], a['day']) == (b['name'], b['day']), 'the life left behind is the same life'
        changed = changed + (V4,)
    diff = {k for k in set(now) | set(before) if k.startswith('stockholm-life') and now.get(k) != before.get(k)} - set(changed)
    assert not diff, f'these keys changed: {sorted(diff)}'


def rows(t):
    t.js("() => window.__TS.openSaveFile()")
    return t.js("() => [...document.querySelectorAll('.slrow')].map(r => ({id: +r.dataset.slot, text: r.innerText, btns: [...r.querySelectorAll('button')].map(b => b.dataset.a)}))")


# ---------- the window ----------
def test_window_lists_five_slots_with_fitting_actions(game_ctx):
    t = tab(game_ctx, two(1, {SLOT3: '{not a life', SLOT4: ''}))
    t.js("() => { const i = JSON.parse(localStorage.getItem('stockholm-life-slots-v1')); i.slots.push({id: 4, ended: true}); localStorage.setItem('stockholm-life-slots-v1', JSON.stringify(i)); localStorage.removeItem('stockholm-life-v4-slot-4') }")
    r = {x['id']: x for x in rows(t)}
    assert sorted(r) == [1, 2, 3, 4, 5]
    assert 'active' in r[1]['text'].lower() and 'Real' in r[1]['text'] and 'day 3' in r[1]['text']  # CSS shows the status label in capitals
    assert 'Second' in r[2]['text'] and 'day 5' in r[2]['text'] and '777' in r[2]['text'].replace(' ', '').replace('\xa0', '').replace(' ', '')
    assert 'switch' not in r[1]['btns'] and 'delete' not in r[1]['btns'], 'the active slot cannot be opened or deleted'
    assert {'switch', 'export', 'rename', 'restart', 'delete', 'import'} <= set(r[2]['btns'])
    assert 'unreadable' in r[3]['text'].lower() and 'switch' not in r[3]['btns'] and 'export' not in r[3]['btns'] and 'restart' not in r[3]['btns']
    assert 'ended' in r[4]['text'].lower() and 'switch' not in r[4]['btns'] and {'import', 'delete'} <= set(r[4]['btns'])
    assert 'empty' in r[5]['text'].lower() and 'switch' in r[5]['btns'] and 'import' in r[5]['btns'] and 'delete' not in r[5]['btns']
    assert t.err.uncaught == []


# ---------- switching ----------
def test_switch_persists_after_reload_and_leaves_both_lives_alone(game_ctx):
    t = tab(game_ctx, two())
    before = t.store()
    leave(t, 'slotSwitch(2)')
    assert not t.intro() and t.js("() => window.__TS.S.name") == 'Second'
    assert index(t)['active'] == 2
    t.reload()
    assert t.js("() => window.__TS.S.name") == 'Second' and index(t)['active'] == 2
    life = json.loads(t.raw(V4))
    assert (life['name'], life['day'], life['money']) == ('Real', 3, 1200), 'slot 1 still holds the same life (it is rewritten by the save made before leaving)'
    leave(t, 'slotSwitch(1)')
    assert t.js("() => window.__TS.S.name") == 'Real' and index(t)['active'] == 1
    assert json.loads(t.raw(SLOT2))['name'] == 'Second' and t.err.uncaught == []


def test_switch_saves_the_current_life_first(game_ctx):
    t = tab(game_ctx, two())
    t.js("() => { window.__TS.S.money += 50 }")
    assert json.loads(t.raw(V4))['money'] == 1200
    leave(t, 'slotSwitch(2)')
    assert json.loads(t.raw(V4))['money'] == 1250, 'the unsaved change was written before leaving'


@pytest.mark.parametrize('why,setup', [
    ('journey or arrest', "window.__TS.busy = true"),
    ('driving lesson', "window.__TS.COACH.mode = 'lesson'"),
    ('train ride', "window.__T.CS.mode = 'ride'"),
])
def test_switch_is_refused_while_busy(game_ctx, why, setup):
    t = tab(game_ctx, two())
    t.js("s => { window.__marker = 1; eval(s) }", setup)
    before = t.store()
    msg = ev(t, 'slotSwitch(2)')
    assert isinstance(msg, str) and msg, f'switching must be refused during a {why}'
    assert t.js("() => window.__marker") == 1, 'the page must not reload'
    untouched(t, before)
    assert index(t)['active'] == 1


def test_switch_refuses_a_target_that_cannot_be_opened(game_ctx):
    t = tab(game_ctx, two(1, {SLOT3: '{not a life'}))
    t.js("() => { const i = JSON.parse(localStorage.getItem('stockholm-life-slots-v1')); i.slots.push({id: 4, ended: true}); localStorage.setItem('stockholm-life-slots-v1', JSON.stringify(i)) }")
    before = t.store()
    assert 'cannot be read' in ev(t, 'slotSwitch(3)')
    assert 'ended' in ev(t, 'slotSwitch(4)')
    assert 'already' in ev(t, 'slotSwitch(1)')
    untouched(t, before)


def test_switch_is_refused_when_the_current_life_cannot_be_saved(game_ctx):
    t = tab(game_ctx, two())
    t.js("() => { window.__TS.S.money += 50 }")
    before = t.store()
    t.faults(set=r'^stockholm-life-v4$')
    msg = ev(t, 'slotSwitch(2)')
    assert 'could not be saved' in msg
    untouched(t, before)
    assert index(t)['active'] == 1


def test_switch_is_refused_when_the_index_cannot_be_written(game_ctx):
    t = tab(game_ctx, two())
    before = t.store()
    t.faults(set=r'^stockholm-life-slots-v1$')
    msg = ev(t, 'slotSwitch(2)')
    assert 'could not be updated' in msg and t.js("() => window.__TS.SV.mode") == 'active', 'this tab keeps saving'
    untouched(t, before, flushed=True)
    t.faults(set=None)
    assert ev(t, "window.__TS.save(), window.__TS.S.name") == 'Real'


def test_switch_is_refused_when_another_tab_changed_the_slots(game_ctx):
    ctx = game_ctx(two())
    a = Tab(ctx).boot()
    b = Tab(ctx).boot()
    leave(b, 'slotSwitch(2)')
    assert index(a)['active'] == 2
    before = a.store()
    assert 'another tab' in ev(a, 'slotSwitch(2)')
    untouched(a, before)


def test_new_life_in_an_empty_slot_leaves_the_others_alone(game_ctx):
    t = tab(game_ctx, two())
    before = t.store()
    leave(t, 'slotSwitch(3)')
    assert t.intro(), 'an empty slot starts the normal introduction'
    assert index(t)['active'] == 3 and t.raw(SLOT3) is None
    t.go('Newbie')
    t.js("() => window.__TS.save()")
    assert json.loads(t.raw(SLOT3))['name'] == 'Newbie'
    assert {s['id']: s.get('name') for s in index(t)['slots']} == {1: 'Real', 2: 'Second', 3: 'Newbie'}
    untouched(t, before, SLOT3, IDX, flushed=True)


def test_switch_interrupted_before_the_index_leaves_the_old_life_active(game_ctx):
    t = tab(game_ctx, two())
    before = t.store()
    t.faults(set=r'^stockholm-life-slots-v1$')
    assert ev(t, 'slotSwitch(2)')
    t.reload()
    assert t.js("() => window.__TS.S.name") == 'Real'
    untouched(t, before, flushed=True)


# ---------- renaming ----------
def test_rename_is_stored_in_the_index_not_the_life_and_survives_saving(game_ctx):
    t = tab(game_ctx, two())
    life = t.raw(SLOT2)
    assert ev(t, "slotRename(2, '  The   second  life ')") is None
    assert {s['id']: s.get('label') for s in index(t)['slots']}[2] == 'The second life'
    assert t.raw(SLOT2) == life, 'the saved life is not changed'
    t.change(); t.reload()
    assert {s['id']: s.get('label') for s in index(t)['slots']}[2] == 'The second life', 'saving the active slot must keep its name'
    leave(t, 'slotSwitch(2)')
    t.change()
    assert {s['id']: s.get('label') for s in index(t)['slots']}[2] == 'The second life'


@pytest.mark.parametrize('bad', ['', '   ', 'x' * 31, '\u0000\u0007'])
def test_rename_rejects_empty_and_too_long_names(game_ctx, bad):
    t = tab(game_ctx, two())
    before = t.store()
    assert ev(t, f'slotRename(2, {J(bad)})')
    untouched(t, before)


def test_rename_text_is_escaped_where_it_is_shown(game_ctx):
    t = tab(game_ctx, two())
    assert ev(t, "slotRename(2, '<img src=x onerror=__x=1>')") is None
    r = {x['id']: x for x in rows(t)}
    assert '<img' in r[2]['text'] and t.js("() => document.querySelectorAll('.slrow img').length") == 0 and t.js("() => window.__x") is None


def test_malformed_label_in_the_index_is_treated_as_a_corrupt_index(game_ctx):
    bad = J({'v': 1, 'active': 1, 'slots': [{'id': 1, 'name': 'Real', 'day': 3, 'label': {'x': 1}}]})
    t = tab(game_ctx, {**seeded(), IDX: bad})
    assert not t.intro() and [v for k, v in t.store().items() if k.startswith('stockholm-life-slots-corrupt-')] == [bad]
    assert 'label' not in index(t)['slots'][0]


# ---------- deleting ----------
def test_delete_needs_the_exact_name_and_never_the_active_slot(game_ctx):
    t = tab(game_ctx, two())
    before = t.store()
    assert 'does not match' in ev(t, "slotDelete(2, 'second')")
    assert 'does not match' in ev(t, "slotDelete(2, '')")
    assert 'in this slot' in ev(t, "slotDelete(1, 'Real')")
    untouched(t, before)


def test_delete_makes_a_verified_copy_then_removes_the_slot(game_ctx):
    t = tab(game_ctx, two(1, {SLOT3: J(THIRD)}))
    before = t.store()
    assert ev(t, "slotDelete(2, 'Second')") is None
    assert t.raw(SLOT2) is None and 2 not in {s['id'] for s in index(t)['slots']}
    assert [t.raw(k) for k in keys(t, 'before-delete')] == [before[SLOT2]], 'the copy is the exact life'
    untouched(t, before, SLOT2, IDX, *keys(t, 'before-delete'))
    assert not t.intro()


def test_delete_with_a_failed_copy_leaves_the_slot_untouched(game_ctx):
    t = tab(game_ctx, two())
    before = t.store()
    t.faults(set='-before-delete-')
    assert 'Nothing was deleted' in ev(t, "slotDelete(2, 'Second')")
    untouched(t, before)


def test_delete_that_cannot_remove_keeps_the_copy_and_the_life(game_ctx):
    t = tab(game_ctx, two())
    before = t.store()
    t.faults(remove=r'^stockholm-life-v4-slot-2$')
    assert 'could not be cleared' in ev(t, "slotDelete(2, 'Second')")
    assert t.raw(SLOT2) == before[SLOT2] and len(keys(t, 'before-delete')) == 1
    t.reload()
    assert not t.intro()


def test_delete_keeps_the_newest_three_copies_and_never_the_corrupt_evidence(game_ctx):
    olds = {f'{SLOT2}-before-delete-{n}000': J({**SECOND, 'name': f'old{n}'}) for n in range(1, 6)}
    evidence = {f'{SLOT2}-corrupt-1': '{a', 'stockholm-life-slots-corrupt-1': '{b'}
    t = tab(game_ctx, two(1, {**olds, **evidence}))
    assert ev(t, "slotDelete(2, 'Second')") is None
    ks = keys(t, 'before-delete')
    assert len(ks) == 3
    assert f'{SLOT2}-before-delete-1000' not in ks and f'{SLOT2}-before-delete-2000' not in ks and f'{SLOT2}-before-delete-3000' not in ks
    assert t.raw(f'{SLOT2}-corrupt-1') == '{a' and t.raw('stockholm-life-slots-corrupt-1') == '{b'


def test_delete_of_an_unreadable_slot_keeps_it_as_corrupt_evidence(game_ctx):
    t = tab(game_ctx, two(1, {SLOT3: '{not a life'}))
    assert ev(t, "slotDelete(3, 'Slot 3')") is None
    assert t.raw(SLOT3) is None and [t.raw(k) for k in keys(t, 'corrupt') if 'slot-3' in k] == ['{not a life']
    assert keys(t, 'before-delete') == [], 'unreadable data goes to the never-pruned evidence, not to a prunable copy'


def test_delete_of_an_ended_slot_clears_it(game_ctx):
    t = tab(game_ctx, two())
    t.js("() => { const i = JSON.parse(localStorage.getItem('stockholm-life-slots-v1')); i.slots = i.slots.filter(s => s.id !== 2); i.slots.push({id: 2, ended: true}); localStorage.setItem('stockholm-life-slots-v1', JSON.stringify(i)); localStorage.removeItem('stockholm-life-v4-slot-2') }")
    assert ev(t, 'slotInfo(2).st') == 'ended'
    assert ev(t, "slotDelete(2, 'Slot 2')") is None
    assert ev(t, 'slotInfo(2).st') == 'empty' and 2 not in {s['id'] for s in index(t)['slots']}


def test_delete_asks_for_the_name_in_the_window(game_ctx):
    t = tab(game_ctx, two())
    t.js("() => window.__TS.openSaveFile()")
    t.page.click('[data-slot="2"] [data-a="delete"]')
    assert t.js("() => document.getElementById('yes').disabled") is True
    t.page.fill('#slw', 'Secon')
    assert t.js("() => document.getElementById('yes').disabled") is True
    t.page.fill('#slw', 'Second')
    assert t.js("() => document.getElementById('yes').disabled") is False
    t.page.click('#yes')
    assert t.raw(SLOT2) is None and len(keys(t, 'before-delete')) == 1
    assert 'deleted' in t.js("() => document.getElementById('impmsg').textContent")


# ---------- start over (replace with a new life) ----------
def test_start_over_copies_the_life_then_starts_a_new_one(game_ctx):
    t = tab(game_ctx, two())
    before = t.store()
    assert 'does not match' in ev(t, "slotRestart(2, 'x')")
    untouched(t, before)
    leave(t, "slotRestart(2, 'Second')")
    assert t.intro() and t.raw(SLOT2) is None and index(t)['active'] == 2
    assert [t.raw(k) for k in keys(t, 'before-replace')] == [before[SLOT2]]
    assert t.raw(V4) == before[V4]


def test_start_over_with_a_failed_copy_changes_nothing(game_ctx):
    t = tab(game_ctx, two())
    before = t.store()
    t.faults(set='-before-replace-')
    assert 'Nothing was changed' in ev(t, "slotRestart(2, 'Second')")
    untouched(t, before)
    assert t.js("() => window.__TS.SV.mode") == 'active'


# ---------- a new life from the title page over the life being played ----------
SEEN = {'stockholmsliv-intro-seen': '1'}  # the short introduction is not shown, so the form starts the life at once
# The title buttons animate, so Playwright's click waits for them to be "stable" and, on a loaded machine at 1-2 fps,
# ran out of its 30 s on #tPlay (2026-11-25). Each title card is drawn at once (titleGo), so these tests press the
# buttons through their handlers (Tab.press) instead.


def title_new_life(t):
    """Title page → Start → Start a new life, with a life being played."""
    t.js("() => window.__T.showTitle(false)")
    assert game.wait_for(t.page, "() => { const e = document.getElementById('title'); return !!e && !e.hidden }", 30)
    t.press('#tPlay')
    t.press('#cNew')
    return t.js("() => document.getElementById('titleCard').innerText")


def fill_form(t, name):
    t.press('#tYes')
    t.page.fill('#nfName', name)
    t.page.select_option('#nfAge', '30')
    t.page.select_option('#nfGender', 'woman')
    t.press('#nfGo')
    assert 'step 2 / 2' in t.js("() => document.getElementById('titleCard').innerText").lower()


def test_title_new_life_asks_first_and_keeps_a_copy(game_ctx):
    """Regression (save review of PR #56, 2026-11-25): "Start a new life" on the title page replaced the life being
    played, with no warning and no copy. It must ask first; "Keep playing" changes nothing; going on keeps a verified
    before-replace copy of that life (as Start over does), and the other slots stay byte for byte."""
    t = tab(game_ctx, two(extra=SEEN))
    before = t.store()
    card = title_new_life(t)
    assert 'will be replaced' in card and 'copy' in card.lower(), card
    t.press('#tNo')
    assert game.wait_for(t.page, "() => document.getElementById('title').hidden", 30), 'Keep playing must go back to the life'
    assert t.js("() => window.__TS.S.name") == 'Real' and keys(t, 'before-replace') == []
    untouched(t, before, flushed=True)
    title_new_life(t)
    fill_form(t, 'Newer')
    t.press('#nfGo')
    assert game.wait_for(t.page, "() => window.__TS.S && window.__TS.S.name === 'Newer'", 60), 'the new life did not start'
    copies = keys(t, 'before-replace')
    assert len(copies) == 1 and copies[0].startswith(V4 + '-before-replace-'), copies
    kept = json.loads(t.raw(copies[0]))
    assert (kept['name'], kept['day'], kept['money']) == ('Real', 3, 1200), 'the copy is the life that was replaced'
    assert ev(t, "slotBackups(1).map(b => b.ok && b.name)") == ['Real'], 'the copy can be restored from Saves'
    assert json.loads(t.raw(V4))['name'] == 'Newer'
    assert t.raw(SLOT2) == before[SLOT2] and index(t)['active'] == 1
    assert t.err.uncaught == []


def test_title_new_life_with_a_failed_copy_changes_nothing(game_ctx):
    t = tab(game_ctx, two(extra=SEEN))
    title_new_life(t)
    fill_form(t, 'Newer')
    t.faults(set='-before-replace-')
    before = t.store()
    t.press('#nfGo')
    assert game.wait_for(t.page, "() => /Nothing was changed/.test(document.getElementById('nfErr').textContent)", 30), \
        t.js("() => document.getElementById('titleCard').innerText")
    assert t.js("() => window.__TS.S.name") == 'Real'
    untouched(t, before, flushed=True)
    assert keys(t, 'before-replace') == [] and t.js("() => window.__TS.SV.mode") == 'active'
    assert t.err.uncaught == []


def test_panel_start_over_keeps_a_copy(game_ctx):
    """The panel's "Start a new life" (#restart) warned but kept no copy before the new life replaced this one (same
    save review, 2026-11-25; on main too). It now keeps the same verified before-replace copy as the title page."""
    t = tab(game_ctx, two(extra=SEEN))
    before = t.store()
    t.press('#restart')
    assert 'copy is kept' in t.js("() => document.getElementById('modalRoot').innerText")
    t.press('#modalRoot #yes')
    assert game.wait_for(t.page, "() => !!document.querySelector('#modalRoot #go')", 30), 'the new-life form did not open'
    copies = keys(t, 'before-replace')
    assert len(copies) == 1 and json.loads(t.raw(copies[0]))['name'] == 'Real', copies
    t.go('Newer')
    assert game.wait_for(t.page, "() => window.__TS.S && window.__TS.S.name === 'Newer'", 60), 'the new life did not start'
    assert json.loads(t.raw(V4))['name'] == 'Newer' and t.raw(SLOT2) == before[SLOT2]
    assert t.err.uncaught == []


def test_panel_start_over_with_a_failed_copy_changes_nothing(game_ctx):
    t = tab(game_ctx, two(extra=SEEN))
    t.faults(set='-before-replace-')
    before = t.store()
    t.press('#restart')
    t.press('#modalRoot #yes')
    assert game.wait_for(t.page, "() => { const e = document.getElementById('rsErr'); return !!e && /Nothing was changed/.test(e.textContent) }", 30), \
        'a failed copy must stop here with "Nothing was changed"'
    assert t.js("() => !document.querySelector('#modalRoot #go') && window.__TS.S.name") == 'Real'
    untouched(t, before, flushed=True)
    assert keys(t, 'before-replace') == []
    assert t.err.uncaught == []


def test_title_new_life_keeps_the_newest_three_copies(game_ctx):
    """Codex review, 2026-11-25: the copies this path makes are pruned like Start over's (SLOT_KEEP = 3, newest kept,
    only after the copy was verified), and those kept can still be restored."""
    olds = {f'{V4}-before-replace-{1000 + i}': J({**LIFE, 'name': f'Old{i}'}) for i in range(3)}
    t = tab(game_ctx, two(extra={**SEEN, **olds}))
    title_new_life(t)
    fill_form(t, 'Newer')
    t.press('#nfGo')
    assert game.wait_for(t.page, "() => window.__TS.S && window.__TS.S.name === 'Newer'", 60), 'the new life did not start'
    assert len(keys(t, 'before-replace')) == 3 and t.raw(f'{V4}-before-replace-1000') is None, keys(t, 'before-replace')
    assert ev(t, "slotBackups(1).map(b => b.ok && b.name)") == ['Real', 'Old2', 'Old1'], 'newest first, the oldest pruned'
    assert t.err.uncaught == []


# ---------- export and import per slot ----------
def test_export_any_readable_slot(game_ctx):
    t = tab(game_ctx, two())
    with t.page.expect_download() as d:
        t.js("() => { window.__TS.exportSlot(2) }")
    env = json.loads(open(d.value.path(), encoding='utf-8').read())
    assert env['format'] == 'stockholmsliv-save' and env['v'] == 5 and env['game']['name'] == 'Second'
    assert ev(t, 'saveHash(' + J(env['game']) + ')') is not None
    assert t.js("e => window.__TS.importCheck(e).then(r => r.err || 'ok')", J(env)) == 'ok', 'the file passes the same checks as any export'
    assert t.js("() => window.__TS.exportSlot(5)") is False


def test_import_into_an_empty_slot_leaves_the_others_byte_for_byte(game_ctx):
    t = tab(game_ctx, two())
    before = t.store()
    g = {**SECOND, 'name': 'Carried', 'v': 5, 'pos': {'x': 1, 'z': 1}}
    assert t.js("g => window.__TS.importApply(g, 3)", g) is None
    assert json.loads(t.raw(SLOT3))['name'] == 'Carried' and 3 in {s['id'] for s in index(t)['slots']}
    untouched(t, before, SLOT3, IDX)
    assert keys(t, 'before-import') == [], 'an empty slot has nothing to copy'
    assert t.js("() => window.__TS.SV.mode") == 'active', 'the tab in slot 1 is not disturbed'


def test_import_into_an_occupied_slot_copies_it_first_and_keeps_three(game_ctx):
    olds = {f'{SLOT2}-before-import-{n}000': J({**SECOND, 'name': f'old{n}'}) for n in range(1, 5)}
    t = tab(game_ctx, two(1, {**olds, f'{SLOT2}-corrupt-5': '{c'}))
    before = t.store()
    assert t.js("g => window.__TS.importApply(g, 2)", {**SECOND, 'name': 'Carried', 'pos': {'x': 1, 'z': 1}}) is None
    assert json.loads(t.raw(SLOT2))['name'] == 'Carried'
    ks = keys(t, 'before-import')
    assert len(ks) == 3 and before[SLOT2] in [t.raw(k) for k in ks], 'the replaced life is among the newest three'
    assert t.raw(f'{SLOT2}-corrupt-5') == '{c' and t.raw(V4) == before[V4]


def test_import_with_a_failed_copy_changes_nothing(game_ctx):
    t = tab(game_ctx, two())
    before = t.store()
    t.faults(set='-before-import-')
    assert 'Nothing was changed' in t.js("g => window.__TS.importApply(g, 2)", {**SECOND, 'name': 'Carried'})
    untouched(t, before)


def test_import_that_cannot_be_written_puts_the_old_life_back(game_ctx):
    t = tab(game_ctx, two())
    before = t.store()
    t.faults(set=r'^stockholm-life-v4-slot-2$')
    assert 'could not be imported' in t.js("g => window.__TS.importApply(g, 2)", {**SECOND, 'name': 'Carried'})
    assert t.raw(SLOT2) == before[SLOT2]


def test_import_of_an_unreadable_slot_keeps_it_as_corrupt_evidence(game_ctx):
    t = tab(game_ctx, two(1, {SLOT3: '{not a life'}))
    assert t.js("g => window.__TS.importApply(g, 3)", {**THIRD, 'pos': {'x': 1, 'z': 1}}) is None
    assert ['{not a life'] == [t.raw(k) for k in keys(t, 'corrupt') if 'slot-3' in k] and keys(t, 'before-import') == []


# ---------- copies: listing and restoring ----------
def test_copies_are_listed_newest_first_with_their_category(game_ctx):
    seed = two(1, {f'{SLOT2}-before-delete-3000': J({**SECOND, 'name': 'D'}), f'{SLOT2}-before-import-1000': J({**SECOND, 'name': 'I'}),
                   f'{SLOT2}-before-restore-2000': J({**SECOND, 'name': 'R'}), f'{SLOT2}-before-replace-4000': J({**SECOND, 'name': 'P'}),
                   f'{SLOT2}-corrupt-5000': '{bad', f'{V4}-before-import-9000': J(LIFE)})
    t = tab(game_ctx, seed)
    got = ev(t, 'slotBackups(2).map(b => [b.cat, b.ok, b.name])')
    assert got == [['corrupt', False, ''], ['before-replace', True, 'P'], ['before-delete', True, 'D'], ['before-restore', True, 'R'], ['before-import', True, 'I']]
    assert [b[0] for b in ev(t, 'slotBackups(1).map(b => [b.cat])')] == ['before-import'], "slot 2's copies are not slot 1's"


def test_restore_copies_the_current_life_first_and_keeps_the_chosen_copy(game_ctx):
    chosen = f'{SLOT2}-before-delete-3000'
    old = J({**SECOND, 'name': 'Older', 'day': 2})
    t = tab(game_ctx, two(1, {chosen: old}))
    before = t.store()
    assert ev(t, f"slotRestore(2, {J(chosen)})") is None
    assert t.raw(SLOT2) == old and t.raw(chosen) == old, 'restored, and the copy itself is untouched'
    assert [t.raw(k) for k in keys(t, 'before-restore')] == [before[SLOT2]], 'what the slot held was copied first'
    assert {s['id']: s.get('name') for s in index(t)['slots']}[2] == 'Older', 'metadata follows the verified data'
    untouched(t, before, SLOT2, IDX, *keys(t, 'before-restore'))


def test_restore_into_an_emptied_slot(game_ctx):
    t = tab(game_ctx, two())
    ev(t, "slotDelete(2, 'Second')")
    k = keys(t, 'before-delete')[0]
    assert ev(t, f"slotRestore(2, {J(k)})") is None
    assert t.raw(SLOT2) == t.raw(k) and keys(t, 'before-restore') == [] and ev(t, 'slotInfo(2).name') == 'Second'


def test_restore_refuses_an_unreadable_copy_and_changes_nothing(game_ctx):
    bad = f'{SLOT2}-corrupt-5000'
    t = tab(game_ctx, two(1, {bad: '{bad'}))
    before = t.store()
    assert 'cannot be restored' in ev(t, f"slotRestore(2, {J(bad)})")
    assert 'cannot be restored' in ev(t, "slotRestore(2, 'stockholm-life-v4')"), 'only a listed copy of this slot'
    untouched(t, before)


def test_restore_can_use_a_readable_corrupt_category_copy(game_ctx):
    k = f'{SLOT2}-corrupt-5000'
    t = tab(game_ctx, two(1, {k: J({**SECOND, 'name': 'Saved'})}))
    assert ev(t, f"slotRestore(2, {J(k)})") is None and json.loads(t.raw(SLOT2))['name'] == 'Saved' and t.raw(k) == J({**SECOND, 'name': 'Saved'})


def test_restore_with_a_failed_pre_copy_changes_nothing(game_ctx):
    k = f'{SLOT2}-before-delete-3000'
    t = tab(game_ctx, two(1, {k: J({**SECOND, 'name': 'Older'})}))
    before = t.store()
    t.faults(set='-before-restore-')
    assert 'Nothing was changed' in ev(t, f"slotRestore(2, {J(k)})")
    untouched(t, before)


def test_restore_that_cannot_be_written_changes_nothing(game_ctx):
    k = f'{SLOT2}-before-delete-3000'
    t = tab(game_ctx, two(1, {k: J({**SECOND, 'name': 'Older'})}))
    before = t.store()
    t.faults(set=r'^stockholm-life-v4-slot-2$')
    assert 'Nothing was changed' in ev(t, f"slotRestore(2, {J(k)})")
    assert t.raw(SLOT2) == before[SLOT2] and t.raw(k) == before[k]
    t.reload()
    assert not t.intro()


def test_restore_keeps_three_copies_and_never_prunes_the_one_chosen(game_ctx):
    seed = {f'{SLOT2}-before-restore-{n}000': J({**SECOND, 'name': f'r{n}'}) for n in range(1, 5)}
    t = tab(game_ctx, two(1, {**seed, f'{SLOT2}-corrupt-9': '{c'}))
    chosen = f'{SLOT2}-before-restore-1000'
    assert ev(t, f"slotRestore(2, {J(chosen)})") is None
    assert t.raw(chosen) is not None, 'the copy the player chose is never pruned by the restore that used it'
    assert t.raw(f'{SLOT2}-corrupt-9') == '{c'
    assert ev(t, "slotRestore(2, " + J(keys(t, 'before-restore')[-1]) + ")") is None
    assert len(keys(t, 'before-restore')) == 3, 'the newest three are kept; the copy that was chosen is among them'


def test_restore_in_the_window_asks_for_the_name_when_the_slot_is_occupied(game_ctx):
    k = f'{SLOT2}-before-delete-3000'
    t = tab(game_ctx, two(1, {k: J({**SECOND, 'name': 'Older', 'day': 2})}))
    t.js("() => window.__TS.openSlotBackups(2)")
    t.page.click('#modalRoot [data-i="0"]')
    assert t.js("() => document.getElementById('yes').disabled") is True
    t.page.fill('#slw', 'Second')
    t.page.click('#yes')
    assert json.loads(t.raw(SLOT2))['name'] == 'Older'


def test_restore_of_the_active_slot_reloads_into_the_restored_life(game_ctx):
    k = f'{V4}-before-import-3000'
    t = tab(game_ctx, two(1, {k: J({**LIFE, 'name': 'Earlier', 'day': 2})}))
    leave(t, f"slotRestore(1, {J(k)})")
    assert t.js("() => window.__TS.S.name") == 'Earlier'
    assert json.loads(t.raw(keys(t, 'before-restore')[0]))['name'] == 'Real'


# ---------- ended, unreadable, evidence ----------
def test_ended_slot_is_listed_with_its_ending_and_after_a_reload(game_ctx):
    t = tab(game_ctx, two(2))
    t.js("() => window.__TS.deported()")
    t.reload()
    r = {x['id']: x for x in rows(t)}
    assert 'ended' in r[2]['text'].lower() and 'deported' in r[2]['text'] and 'switch' not in r[2]['btns'] and 'restart' not in r[2]['btns']
    assert 'Real' in r[1]['text']


def test_unreadable_slot_is_not_hidden_or_destroyed(game_ctx):
    t = tab(game_ctx, two(1, {SLOT3: '{not a life', f'{SLOT3}-corrupt-7': '{earlier'}))
    r = {x['id']: x for x in rows(t)}
    assert 'unreadable' in r[3]['text'].lower() and 'backups' in r[3]['btns'] and 'Nothing has been deleted' in r[3]['text']
    assert t.raw(SLOT3) == '{not a life' and t.raw(f'{SLOT3}-corrupt-7') == '{earlier'


def test_no_slot_action_ever_removes_corrupt_evidence(game_ctx):
    evid = {f'{SLOT2}-corrupt-1': '{a', f'{V4}-corrupt-2': '{b', f'{V3}-corrupt-3': '{c', 'stockholm-life-slots-corrupt-4': '{d'}
    t = tab(game_ctx, two(1, {**evid, **{f'{SLOT2}-before-delete-{n}000': J(SECOND) for n in range(1, 6)}}))
    ev(t, "slotRename(2, 'Renamed')")
    t.js("g => window.__TS.importApply(g, 2)", {**SECOND, 'name': 'Carried'})
    ev(t, "slotDelete(2, 'Renamed')")
    ev(t, f"slotRestore(2, {J(keys(t, 'before-delete')[-1])})")
    for k, v in evid.items():
        assert t.raw(k) == v, f'{k} was changed or removed'


# ---------- interrupted actions and reloads ----------
def test_interrupted_delete_leaves_the_life_and_its_copy(game_ctx):
    t = tab(game_ctx, two())
    before = t.store()
    t.faults(remove=r'^stockholm-life-v4-slot-2$')
    ev(t, "slotDelete(2, 'Second')")
    t.reload()
    assert t.raw(SLOT2) == before[SLOT2] and not t.intro() and index(t)['active'] == 1


def test_delete_followed_by_reload_stays_deleted_and_restorable(game_ctx):
    t = tab(game_ctx, two())
    before = t.store()
    ev(t, "slotDelete(2, 'Second')")
    t.reload()
    assert t.raw(SLOT2) is None and index(t)['active'] == 1
    k = keys(t, 'before-delete')[0]
    assert ev(t, f"slotRestore(2, {J(k)})") is None and t.raw(SLOT2) == before[SLOT2]


def test_every_failing_step_of_a_switch_leaves_every_key_unchanged(game_ctx):
    for fault in ({'set': r'^stockholm-life-v4$'}, {'set': r'^stockholm-life-slots-v1$'}, {'get': r'^stockholm-life-v4-slot-2$'}):
        t = tab(game_ctx, two())
        t.js("() => { window.__TS.S.money += 1 }")
        before = t.store()
        t.faults(**fault)
        assert ev(t, 'slotSwitch(2)')
        t.faults(get=None, set=None)  # the check below reads storage itself, so the fault must be lifted first
        untouched(t, before, flushed=True)
        t.reload()
        assert t.js("() => window.__TS.S.name") == 'Real'


def test_no_uncaught_errors_in_the_window(game_ctx):
    t = tab(game_ctx, two(1, {SLOT3: '{x', f'{SLOT2}-before-delete-3000': J(SECOND), f'{SLOT2}-corrupt-1': '{bad'}))
    t.js("() => window.__TS.openSaveFile()")
    t.page.click('[data-slot="2"] [data-a="backups"]')
    t.page.click('#no')
    t.page.click('[data-slot="2"] [data-a="rename"]')
    t.page.fill('#rn', 'Hello')
    t.page.click('#yes')
    assert 'renamed' in t.js("() => document.getElementById('impmsg').textContent")
    assert t.err.uncaught == []
