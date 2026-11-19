"""Save slots, part A (M1c, docs/MODULES.md and KNOWN_ISSUES M20): the slot index and the active slot, with no slot management yet.

Slot 1 is the existing key stockholm-life-v4 and is never moved; stockholm-life-slots-v1 is metadata about the slots. What is checked:
  - every existing fixture still loads as slot 1, its stored bytes unchanged, and the index appears (a v3 save gets one when it is first saved);
  - a missing index is built without touching a life; an index is not made for a browser with no life; building it again changes nothing;
  - an unreadable, truncated or malformed index is copied first (stockholm-life-slots-corrupt-<ts>), then rebuilt from the slot keys;
    when the active slot cannot be told, saving pauses and nothing is overwritten or deleted;
  - the active slot decides which key is loaded and saved; the v3 fallback is for slot 1 only;
  - data is written and read back before the index; an interrupted write leaves the life safe and the index repaired by the next save;
  - a tab whose slot is no longer the active one stops saving (this narrows KNOWN_ISSUES M20, it does not make saving atomic);
  - deportation ends only the active slot and leaves it listed as ended; import prunes only its own old copies, never the -corrupt- evidence.
Faults are injected as in test_save_safety.py. Negative controls: run on a scratch copy with SL_INDEX_HTML=<file> (see tests/README.md)."""
import json
import time
from pathlib import Path
import pytest
import game
from test_save_safety import Tab, game_ctx, tab, seeded, LIFE, V4, V3, ONLY_V4, WRITE  # noqa: F401  (game_ctx is a fixture)

pytestmark = [pytest.mark.browser, pytest.mark.hook]

IDX = 'stockholm-life-slots-v1'
SLOT2 = 'stockholm-life-v4-slot-2'
COPY = 'stockholm-life-slots-corrupt-'
SECOND = {**LIFE, 'name': 'Second', 'day': 5, 'money': 777}
OTHER = {**LIFE, 'name': 'Other', 'day': 9}
VALID = {'v': 1, 'active': 1, 'slots': [{'id': 1, 'name': 'Real', 'day': 3}]}
FX = Path(__file__).resolve().parent / 'fixtures' / 'saves'
MANIFEST = json.loads((FX / 'manifest.json').read_text(encoding='utf-8'))['fixtures']


def index(t):
    r = t.raw(IDX)
    return json.loads(r) if r else None


def copies(t, prefix=COPY):
    return {k: v for k, v in t.store().items() if k.startswith(prefix)}


def mode(t):
    return t.js("() => window.__TS.SV.mode")


# ---------- existing lives ----------
@pytest.mark.parametrize('fx', MANIFEST, ids=[e['id'] for e in MANIFEST])
def test_every_fixture_loads_as_slot_one_unchanged(game_ctx, fx):
    raw = (FX / fx['file']).read_text(encoding='utf-8')
    life = json.loads(raw)
    # writes to the life's own keys fail, so what is stored after the start is exactly what was seeded
    t = tab(game_ctx, {fx['storage_key']: raw}, set=r'^stockholm-life-v[34]$')
    assert not t.intro(), 'the saved life was not loaded'
    assert t.raw(fx['storage_key']) == raw, 'the stored life changed'
    if fx['storage_key'] == V4:
        assert index(t) == {'v': 1, 'active': 1, 'slots': [{'id': 1, 'name': life['name'], 'day': life['day']}]}
    else:
        assert index(t) is None, 'a v3 life has no slot yet; the index appears when it is first saved to slot 1'
        t.faults(set=None)
        t.js("() => window.__TS.save()")
        assert t.raw(V4) and index(t)['active'] == 1 and index(t)['slots'][0]['name'] == life['name']
        assert t.raw(V3) == raw, 'the v3 key is left alone'
    assert t.err.uncaught == []


def test_a_browser_with_no_life_gets_no_index_until_a_life_is_saved(game_ctx):
    t = tab(game_ctx)
    assert t.intro() and index(t) is None
    t.go('Newbie')
    t.js("() => window.__TS.save()")
    assert index(t) == {'v': 1, 'active': 1, 'slots': [{'id': 1, 'name': 'Newbie', 'day': 1}]}


def test_building_the_index_is_repeatable(game_ctx):
    t = tab(game_ctx, seeded())
    first = index(t)
    assert first == VALID
    for _ in range(2):
        t.reload()
        assert index(t) == first and json.loads(t.raw())['name'] == 'Real'
    assert t.backups() == {}, 'a valid index needs no copy'


# ---------- a corrupt index ----------
def truncated():
    return json.dumps(VALID)[:-6]


BAD_INDEXES = {
    'not json': '{not json', 'empty object': '{}', 'array': '[]', 'null': 'null', 'truncated': None,
    'wrong version': json.dumps({**VALID, 'v': 2}),
    'duplicate ids': json.dumps({'v': 1, 'active': 1, 'slots': [{'id': 1}, {'id': 1}]}),
    'slot id out of range': json.dumps({'v': 1, 'active': 1, 'slots': [{'id': 1}, {'id': 9}]}),
    'active slot not listed': json.dumps({'v': 1, 'active': 2, 'slots': [{'id': 1}]}),
    'name of the wrong type': json.dumps({'v': 1, 'active': 1, 'slots': [{'id': 1, 'name': 7}]}),
    'day of the wrong type': json.dumps({'v': 1, 'active': 1, 'slots': [{'id': 1, 'day': 'x'}]}),
}


@pytest.mark.parametrize('why', list(BAD_INDEXES))
def test_corrupt_index_is_copied_then_rebuilt(game_ctx, why):
    bad = BAD_INDEXES[why] or truncated()
    t = tab(game_ctx, {**seeded(), IDX: bad})
    assert not t.intro(), 'the life must still load'
    assert list(copies(t).values()) == [bad], 'the unreadable index must be kept byte for byte before it is replaced'
    assert index(t) == VALID, 'the index is rebuilt from the slot keys'
    assert json.loads(t.raw())['name'] == 'Real'
    assert 'list of your save slots' in t.status()
    # a second start finds a valid index, makes no further copy, and the first copy is still there
    t.reload()
    assert list(copies(t).values()) == [bad] and index(t) == VALID
    assert t.err.uncaught == []


def test_a_corrupt_index_that_names_the_slot_is_trusted(game_ctx):
    bad = '{"v":1,"active":2,"slots":[{"id":1},{"id":2,"name":7}]}'  # well-formed JSON with bad metadata, and it names slot 2
    t = tab(game_ctx, {**seeded(), SLOT2: json.dumps(SECOND), IDX: bad})
    assert list(copies(t).values()) == [bad]
    assert index(t)['active'] == 2 and t.js("() => window.__TS.S.name") == 'Second'
    assert [m['id'] for m in index(t)['slots']] == [1, 2]


def test_active_slot_unknown_pauses_saving_and_changes_nothing(game_ctx):
    bad = '{broken'
    t = tab(game_ctx, {**seeded(), SLOT2: json.dumps(SECOND), IDX: bad})
    assert mode(t) == 'blocked' and 'need attention' in t.status()
    assert t.raw(IDX) == bad and list(copies(t).values()) == [bad]
    before = t.store()
    t.change()
    assert t.store() == before, 'nothing may be written or deleted'
    res = t.js("() => { const S = window.__TS.S; return window.__TS.importApply(JSON.parse(JSON.stringify(S))) }")
    assert 'need attention' in res and t.store() == before, 'import is a destructive action and is refused'
    assert t.err.uncaught == []


def test_missing_index_with_two_lives_does_not_guess(game_ctx):
    t = tab(game_ctx, {**seeded(), SLOT2: json.dumps(SECOND)})
    assert mode(t) == 'blocked' and index(t) is None
    before = t.store()
    t.change()
    assert t.store() == before


def test_full_storage_and_a_corrupt_index_change_nothing(game_ctx):
    t = tab(game_ctx, {**seeded(), IDX: '{broken'}, set='.*')
    assert mode(t) == 'blocked' and 'need attention' in t.status()
    assert t.raw(IDX) == '{broken' and copies(t) == {}, 'no copy could be made, so the index is left alone'
    assert json.loads(t.raw())['name'] == 'Real'


# ---------- the active slot ----------
def two_slots(active):
    idx = {'v': 1, 'active': active, 'slots': [{'id': 1, 'name': 'Real', 'day': 3}, {'id': 2, 'name': 'Second', 'day': 5}]}
    return {**seeded(), SLOT2: json.dumps(SECOND), IDX: json.dumps(idx)}


def test_the_active_slot_is_loaded_saved_and_kept_across_reloads(game_ctx):
    seed = two_slots(2)
    t = tab(game_ctx, seed)
    assert t.js("() => window.__TS.S.name") == 'Second'
    t.change()
    assert json.loads(t.raw(SLOT2))['money'] == 784
    assert t.raw(V4) == seed[V4], 'saving in slot 2 must not touch slot 1'
    t.reload()
    assert t.js("() => window.__TS.S.name") == 'Second' and index(t)['active'] == 2


def test_operations_on_one_slot_leave_the_other_alone(game_ctx):
    seed = two_slots(1)
    t = tab(game_ctx, seed)
    t.change()
    assert t.raw(SLOT2) == seed[SLOT2]
    assert json.loads(t.raw())['money'] == 1207


def test_the_v3_fallback_belongs_to_slot_one(game_ctx):
    idx = {'v': 1, 'active': 2, 'slots': [{'id': 1}, {'id': 2}]}
    t = tab(game_ctx, {V3: json.dumps(LIFE), IDX: json.dumps(idx)})
    assert t.intro(), 'slot 2 is empty: the old v3 life belongs to slot 1 and must not appear here'
    assert t.raw(V3) == json.dumps(LIFE)


# ---------- writes: data first, index second ----------
def test_data_is_written_before_the_index(game_ctx):
    t = tab(game_ctx, {**seeded(), IDX: json.dumps(VALID)})
    t.faults(set=ONLY_V4)
    t.js("() => { window.__TS.S.day = 9; window.__TS.save() }")
    assert WRITE in t.status()
    assert index(t) == VALID, 'the index must not move ahead of data that could not be written'
    assert json.loads(t.raw())['day'] == 3


def test_an_interrupted_index_write_leaves_the_life_safe_and_is_repaired(game_ctx):
    t = tab(game_ctx, {**seeded(), IDX: json.dumps(VALID)})
    t.faults(set=f'^{IDX}$')
    t.js("() => { window.__TS.S.day = 4; window.__TS.save() }")
    assert json.loads(t.raw())['day'] == 4 and index(t)['slots'][0]['day'] == 3, 'the data is stored, the index is one save behind'
    assert t.status() == '', 'a stale index is not a failed save'
    t.reload()
    assert t.js("() => window.__TS.S.day") == 4 and index(t)['active'] == 1
    t.js("() => { window.__TS.S.day = 5; window.__TS.save() }")
    t.faults(set=None)
    t.js("() => { window.__TS.S.day = 6; window.__TS.save() }")
    assert index(t)['slots'][0]['day'] == 6


def test_full_storage_changes_neither_the_life_nor_the_index(game_ctx):
    t = tab(game_ctx, {**seeded(), IDX: json.dumps(VALID)})
    t.faults(set='.*')
    before = t.store()
    t.js("() => { window.__TS.S.day = 8; window.__TS.save() }")
    assert WRITE in t.status() and t.store() == before


# ---------- another tab ----------
def two(game_ctx, seed):
    ctx = game_ctx(seed)
    return Tab(ctx).boot(), Tab(ctx).boot()


def test_a_tab_stops_when_another_slot_becomes_active(game_ctx):
    seed = two_slots(1)
    a, b = two(game_ctx, seed)
    b.js("v => localStorage.setItem('%s', v)" % IDX, json.dumps({'v': 1, 'active': 2, 'slots': index(a)['slots']}))
    t0 = time.time()
    while index(a)['active'] != 2:
        assert time.time() - t0 < 120, 'the write never reached the first tab'
        time.sleep(0.1)
    before = a.raw()
    a.change()
    assert 'another tab' in a.status()
    assert a.raw() == before, 'a stale tab must not write into a slot that is no longer its own'
    assert a.err.uncaught == []


# ---------- deportation and import copies ----------
def test_deportation_ends_only_the_active_slot_and_lists_it(game_ctx):
    seed = {**two_slots(2), V3: json.dumps(LIFE)}
    t = tab(game_ctx, seed)
    t.js("() => window.__TS.deported()")
    assert t.raw(SLOT2) is None and t.raw(V4) == seed[V4] and t.raw(V3) == seed[V3]
    m = {s['id']: s for s in index(t)['slots']}
    assert m[2].get('ended') is True and 'ended' not in m[1]
    assert t.reload().intro()
    t.go('Again')
    t.js("() => window.__TS.save()")
    assert 'ended' not in {s['id']: s for s in index(t)['slots']}[2] and index(t)['slots'][1]['name'] == 'Again'


def test_deportation_of_slot_one_is_listed_as_ended(game_ctx):
    t = tab(game_ctx, {**seeded(), V3: json.dumps(LIFE), IDX: json.dumps(VALID)})
    t.js("() => window.__TS.deported()")
    assert t.raw() is None and t.raw(V3) is None
    assert index(t)['slots'][0].get('ended') is True


IMPORT = "() => { const T = window.__TS; const g = JSON.parse(JSON.stringify(T.S)); g.name = 'Imported'; return T.importApply(g) }"


def test_import_keeps_three_copies_and_never_prunes_corrupt_evidence(game_ctx):
    olds = {f'{V4}-before-import-{n}000': json.dumps({**LIFE, 'name': f'old{n}'}) for n in range(1, 6)}
    evidence = {f'{V4}-corrupt-1': '{a', f'{COPY}1': '{b'}
    t = tab(game_ctx, {**seeded(), IDX: json.dumps(VALID), **olds, **evidence})
    assert t.js(IMPORT) is None
    kept = [k for k in t.store() if '-before-import-' in k]
    assert len(kept) == 3 and f'{V4}-before-import-4000' in kept and f'{V4}-before-import-5000' in kept, kept   # the newest copy is the one just made
    assert {k: t.raw(k) for k in evidence} == evidence, 'the evidence of unreadable data is never pruned'
    assert json.loads(t.raw())['name'] == 'Imported'


def test_a_failed_import_prunes_nothing(game_ctx):
    olds = {f'{V4}-before-import-{n}000': '{"x":%d}' % n for n in range(1, 6)}
    t = tab(game_ctx, {**seeded(), IDX: json.dumps(VALID), **olds}, set=ONLY_V4)
    res = t.js(IMPORT)
    assert res and 'Nothing was changed' in res
    assert len([k for k in t.store() if '-before-import-' in k]) == 6, 'nothing is pruned before the action it protects succeeds'
    assert json.loads(t.raw())['name'] == 'Real'
