# Report: local test-runner qualification (`local-qualification`)

- **Task:** `local-qualification`: qualify an isolated local test runner, then document the result
- **Agent:** Claude Code, with ChatGPT reviewing through the user
- **Date:** 2026-11-05 to 2026-11-07
- **Commits:** qualified and documented at `main` `6e9ac76ba8f07051fe96b620e0c3e03cec5343cc`; this report is added on the branch `docs/local-qualification`
- **Branch and pull request:** `docs/local-qualification`, not yet pushed; no pull request yet. Nothing merged or deployed by this task
- **Files changed:** `docs/TEST_PLAN.md`, `docs/PROJECT_STATUS.md`, `docs/FEATURE_INVENTORY.md`, `.agent/QUEUE.md`, and this report. No game code, tests, data, tools or workflows

## Summary

An isolated local test runner (a shell runner and a Docker image) was built and qualified so that the whole suite can run against one exact commit on a developer's machine without touching that machine's checkout. The runner and the image are kept outside this repository, so nobody else can reproduce these runs yet. How the runner works, its results and limitations: [TEST_PLAN.md §7](../../docs/TEST_PLAN.md).

The qualification went in stages, each approved separately. Defects found on the way were fixed in the runner or its scripts and tested again before the next stage. Stage D was accepted on its third attempt: the first stopped at its preconditions before running anything, and the second found a runner defect (it could not read the worktree configuration of a checkout with linked worktrees), which was fixed and checked with the harnesses first. Every stage after D passed on its only run.

| Stage | Purpose | Result |
| --- | --- | --- |
| Harnesses | The runner's logic against a simulated Docker, including adversarial cases | 135 of 135 and 74 of 74 |
| D | Controls from GitHub: an injected runtime error and an injected syntax error are detected | Both detected; nothing else changed |
| W | One verification worktree on its own branch at `6e9ac76`, the source for the local stages | Created; nothing else changed |
| E | The same controls, cloning from that local worktree | Both detected; integrity check passed with no findings |
| F | The full suite, cloning from that local worktree | Passed (below); integrity check passed with no findings |

## Results

Full run on `6e9ac76` (stage F, 2026-11-07, 56 minutes): `RESULT=PASS`.

- Syntax stage (host): 3 collected, 3 passed.
- Browser stage (container): 218 collected, which is all of `tests/` (79 for the game, including the 3 syntax tests again, and 139 for `tools/live_check.py`); 217 passed and 1 xpassed: `test_traincam.py::test_place_label_after_getting_off` (KNOWN_ISSUES L10); 0 failed, errors, skips or deselections.
- The copy stayed clean, the protected checkouts were unchanged, and no out-of-memory event was logged (peak 1.8 GB of the 6 GiB limit).
- The CPU set the container actually had (its cgroup's `cpuset.cpus.effective`) was 0–5, as requested.
- The test IDs were the same 218 as an earlier full run of the same commit cloned from GitHub (2026-11-05: 217 passed, 1 xpassed).

No CI ran as part of this task. CI runs on pull requests only and did not run on `main` `6e9ac76` itself.

## Known problems and limitations

- This qualifies the runner. It does not show that the game works beyond what the suite tests, on real devices, or on the live site, which serves `870fe30`, an older commit without the merged work listed in [PROJECT_STATUS.md](../../docs/PROJECT_STATUS.md).
- The L10 `xpass` means the bug did not appear in this run, not that it is fixed.
- The containers' network mode was not recorded; from the runner's code they used Docker's default bridge with outbound internet.
- Results written inside the container, including the effective CPU set, could be falsified by a hostile test.
- Not detected: ignored files in a local source outside `tests/output`; a change to the global Git configuration during a run; a consistent forgery of every result before the checker reads it.
- Every check is a point-in-time observation of one machine. The runner is not in this repository and has run on one machine only.

## Outstanding work

- Decide whether the runner belongs in this repository, after more use shows that it is stable.
- The paused M0 task `m0-desktop-checks` is unchanged and still waits for the owner's approval to resume ([QUEUE.md](../QUEUE.md)).

## Recommended next action

Review this documentation change and, if approved, push the branch and open a pull request; merging is a separate approval. Then return to game development through the queue.
