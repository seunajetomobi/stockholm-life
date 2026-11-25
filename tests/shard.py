"""Splits the test files into shards of about equal running time, so CI runs the browser suite in parallel jobs.

    python3 tests/shard.py 2 6           the files of shard 2 of 6, one path per line
    python3 tests/shard.py --check 6     reads `pytest --collect-only -q` output on stdin and fails unless every
                                         file that has a test is in exactly one of the 6 shards and no shard is empty

Run one shard locally the way CI does: python3 -m pytest $(python3 tests/shard.py 2 6)

Longest file first, each file goes to the shard with the least time so far (ties to the lower shard), so the split is
the same on every machine. The times below only affect the balance, never which tests run: a file that is not in the
table counts as DEFAULT seconds and still goes to exactly one shard.
"""
import argparse, os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Seconds per file in CI, from run 45521784213 attempt 2 (PR #56, 2026-11-25: 1 h 51 min for the whole suite in one
# job); test_arrival_hall.py from run 45536626373 (PR #57), scaled to that runner. Files of open pull requests are
# listed so the split stays even when they merge; a name without a file is ignored. Update when a file gets much
# slower or faster (the per-file times are the gaps between the progress lines of a CI log).
SECONDS = {
    'test_save_fixtures.py': 1128, 'test_save_slot_ui.py': 1070, 'test_save_safety.py': 957, 'test_m14.py': 782,
    'test_title_page.py': 565, 'test_save_slots.py': 540, 'test_arrival_hall.py': 516, 'test_save_place.py': 330,
    'test_prompt_mouse.py': 239, 'test_menu_extras.py': 201, 'test_traincam.py': 174, 'test_live_check.py': 111,
    'test_smoke.py': 105, 'test_prompt_keyboard.py': 82, 'test_layout.py': 58, 'test_boat_rides.py': 47,
    'test_realtime_start.py': 40, 'test_save.py': 40, 'test_vehicle_lanes.py': 34, 'test_transit_rides.py': 27,
    'test_time_rules.py': 20, 'test_red_day_hours.py': 18, 'test_namnsdag_ui.py': 18, 'test_sun.py': 14,
    'test_geography.py': 13, 'test_tables.py': 13, 'test_format.py': 11, 'test_city_data.py': 11,
    'test_loading_flash.py': 9, 'test_life_start.py': 1, 'test_stockholm_time.py': 1, 'test_realtime.py': 1,
    'test_world.py': 1, 'test_namnsdag.py': 1, 'test_holidays.py': 1, 'test_syntax.py': 1, 'test_clock.py': 1,
    'test_harness.py': 1, 'test_name.py': 1, 'test_shard.py': 1,
}
DEFAULT = 60


def test_files(folder=HERE):
    """The test files pytest collects from this folder (pytest.ini: python_files = test_*.py)."""
    return sorted(p.name for p in Path(folder).glob('test_*.py'))


def seconds(name):
    return SECONDS.get(name, DEFAULT)


def split(n, names):
    """n lists of file names, each sorted; every name in exactly one."""
    if n < 1:
        raise ValueError(f'need at least one shard, not {n}')
    load, out = [0] * n, [[] for _ in range(n)]
    for name in sorted(set(names), key=lambda f: (-seconds(f), f)):
        i = min(range(n), key=lambda k: (load[k], k))
        load[i] += seconds(name)
        out[i].append(name)
    return [sorted(s) for s in out]


def collected_files(lines):
    """The file names in `pytest --collect-only -q` output (node ids such as tests/test_x.py::test_y[390])."""
    return {Path(m.group(1)).name for m in (re.match(r'(\S+?\.py)::', l.strip()) for l in lines) if m}


def problems(n, names, collected):
    """Why the split of `names` into n shards would not run exactly the `collected` files once each ([] if it would)."""
    shards = split(n, names)
    where = {}
    for i, s in enumerate(shards, 1):
        for f in s:
            where.setdefault(f, []).append(i)
    out = [] if collected else ['pytest collected no tests']
    out += [f'{f} has tests but is in no shard' for f in sorted(collected) if f not in where]
    out += [f'{f} is in shards {w}' for f, w in sorted(where.items()) if len(w) != 1]
    out += [f'shard {i} of {n} has no files' for i, s in enumerate(shards, 1) if not s]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--tests', type=Path, default=HERE, help='the tests folder (default: the one this file is in)')
    ap.add_argument('--check', action='store_true', help='check the split against pytest --collect-only -q on stdin')
    ap.add_argument('numbers', type=int, nargs='+', help='K N (shard K of N, from 1) or, with --check, N')
    a = ap.parse_args(argv)
    names = test_files(a.tests)
    if a.check:
        if len(a.numbers) != 1:
            ap.error('--check takes one number: the number of shards')
        bad = problems(a.numbers[0], names, collected_files(sys.stdin))
        for p in bad:
            print(f'::error::{p}')
        if not bad:
            print(f'{len(names)} test files, each in exactly one of {a.numbers[0]} shards')
        return 1 if bad else 0
    if len(a.numbers) != 2 or not 1 <= a.numbers[0] <= a.numbers[1]:
        ap.error('give K N with 1 <= K <= N')
    k, n = a.numbers
    mine = split(n, names)[k - 1]
    if not mine:
        print(f'shard {k} of {n} has no files', file=sys.stderr)
        return 1
    for f in mine:
        print(Path(os.path.relpath(a.tests / f)).as_posix())
    print(f'shard {k} of {n}: {len(mine)} file{"s" * (len(mine) != 1)}, about {round(sum(map(seconds, mine)) / 60)} min in CI', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
