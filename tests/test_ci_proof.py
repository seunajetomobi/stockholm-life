"""TEMPORARY, on the branch ci/browser-shards-proof only (a draft pull request that must not be merged): a deliberate
failure, to show on GitHub that one failing shard fails the required check tests-browser, and that a test file with no
time in tests/shard.py still runs in exactly one shard."""


def test_a_failing_shard_fails_tests_browser():
    assert False, 'deliberate failure (proof for PR #59): this shard must fail, and tests-browser with it'
