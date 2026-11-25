"""tests/shard.py, which splits the test files over the parallel CI browser jobs: every file runs in exactly one shard,
the split is the same every time, a new file still runs, and the completeness check catches a file left out."""
import subprocess, sys
import pytest
import shard

NAMES = shard.test_files()


def flat(shards):
    return sorted(f for s in shards for f in s)


@pytest.mark.parametrize('n', range(1, 9))
def test_every_file_is_in_exactly_one_shard(n):
    assert flat(shard.split(n, NAMES)) == NAMES
    assert shard.problems(n, NAMES, set(NAMES)) == []


def test_the_split_does_not_depend_on_the_order():
    assert shard.split(6, list(reversed(NAMES))) == shard.split(6, NAMES)


def test_a_file_without_a_time_still_runs():
    names = NAMES + ['test_not_timed_yet.py']
    shards = shard.split(6, names)
    assert flat(shards) == sorted(names)
    assert sum(s.count('test_not_timed_yet.py') for s in shards) == 1


def test_the_shards_are_balanced():
    """With the times in shard.py, no shard is more than a third over the least any split could do: the average, or the
    longest file if that is more (on 2026-11-25 the slowest of 6 shards was within 1 % of it)."""
    for n in (2, 4, 6, 8):
        loads = [sum(map(shard.seconds, s)) for s in shard.split(n, NAMES)]
        best = max(sum(loads) / n, max(map(shard.seconds, NAMES)))
        assert max(loads) <= best * 4 / 3, (n, loads)


def test_the_check_catches_a_file_in_no_shard():
    assert shard.problems(6, NAMES, set(NAMES) | {'test_elsewhere.py'}) == ['test_elsewhere.py has tests but is in no shard']


def test_the_check_catches_an_empty_shard_and_an_empty_collection():
    assert shard.problems(3, ['test_a.py', 'test_b.py'], {'test_a.py', 'test_b.py'}) == ['shard 3 of 3 has no files']
    assert shard.problems(6, NAMES, set()) == ['pytest collected no tests']


def test_collected_files_reads_pytest_node_ids():
    out = ['tests/test_m14.py::test_layout[390]', 'test_smoke.py::test_boot', '', '2 tests collected in 0.5s']
    assert shard.collected_files(out) == {'test_m14.py', 'test_smoke.py'}


def run(*args, stdin=''):
    return subprocess.run([sys.executable, str(shard.HERE / 'shard.py'), *args], input=stdin, capture_output=True,
                          text=True, cwd=shard.HERE.parent, timeout=60)


def test_the_command_line():
    """What tests.yml runs: the shards' paths together are every test file once; --check fails on a missing file."""
    paths = [l for k in range(1, 7) for l in run(str(k), '6').stdout.split()]
    assert sorted(paths) == [f'tests/{f}' for f in NAMES]
    ok = run('--check', '6', stdin='\n'.join(f'tests/{f}::test_x' for f in NAMES))
    assert ok.returncode == 0, ok.stdout + ok.stderr
    bad = run('--check', '6', stdin='tests/test_elsewhere.py::test_x\n')
    assert bad.returncode == 1 and '::error::test_elsewhere.py has tests but is in no shard' in bad.stdout, bad.stdout
    assert run('7', '6').returncode != 0
