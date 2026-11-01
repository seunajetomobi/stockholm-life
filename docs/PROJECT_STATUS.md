# Project status

The single authoritative status of Stockholm Life. Other documents link here instead of keeping their own status summaries. The current task and the tasks after it are in [`.agent/QUEUE.md`](../.agent/QUEUE.md).

**Verified 2026-11-01 at `main` `d9b8882`** (GitHub API, `git ls-remote`, the live `version.txt`). Refreshed with the next meaningful project or documentation update, not after every merge, so check the date and SHA before relying on it.

## Code and release

| | Commit | Notes |
| --- | --- | --- |
| `main` | `d9b8882dbb9d77aa99c0ea08edca9c568563e656` | Merge of PR #6, 2026-11-01 09:37 Z |
| Live site | `870fe309543c6eb375e6e150423002a09763a3db` | `version.txt` on GitHub Pages; last successful deployment `7465401024` (run `41249126992`), 2026-10-31 22:58:50 Z |
| Merged, **not deployed** | | PR #3 pendeltåg camera and phone message strip (`40d913e`); PR #4 strip clear of every control (`3d04635`); PR #6 strip follows layout changes (`d9b8882`). PR #5 (documentation, `b0ad590`) does not change the published files |
| Open pull requests | | None at verification, apart from the one that adds this file (`chore/agent-workspace`) |

Publishing happens only through the manual "Deploy to GitHub Pages" workflow with the `github-pages` approval; merging into `main` does not change the live site ([TECHNICAL_ARCHITECTURE.md §4](TECHNICAL_ARCHITECTURE.md)).

## Milestone

**M0 — Stabilise: in progress.** No milestone is complete. Scope and acceptance: [MASTER_ROADMAP.md](MASTER_ROADMAP.md#m0--stabilise).

| M0 item | Status | Evidence |
| --- | --- | --- |
| Automated tests in CI as required checks; approval-gated manual deployment; Pages published by GitHub Actions; `main` protected by a ruleset; Actions hardened | Done | PR #1, PR #2; ruleset "Protect main" (`tests-syntax`, `tests-browser`, strict up-to-date) |
| Pendeltåg camera and M14 merged | Done | PR #3 (`40d913e`) |
| Message strip clear of every control | Done | PR #4 (`3d04635`); timing fix PR #6 (`d9b8882`), KNOWN_ISSUES M16, M17 |
| Project documentation in the repository | Done | PR #5 (`b0ad590`) |
| Real-device check of the camera and the message strip | **Not done** | Checklist in [TEST_PLAN.md §4](TEST_PLAN.md); KNOWN_ISSUES M15 |
| Deploy `main` and verify it live | **Not done** | Live is `870fe30` (above) |
| Flights relay redeployed with `/waittime` | **Not done** | Probed 2026-11-01: `/waittime` answers with the old help text listing only `/flights` and `/news`; needs a redeploy and the `SWEDAVIA_KEY` secret (KNOWN_ISSUES M1) |

## Current task and next steps

- **Current:** the agent workspace (this file, `AGENTS.md`, `.agent/QUEUE.md`) on `chore/agent-workspace`, in review.
- **Next:** see [`.agent/QUEUE.md`](../.agent/QUEUE.md). In short: finish M0 (real-device checks, deploying `main`, the relay), each with the user's approval, then M1 (save and state).

## Latest verification results

| What | Result |
| --- | --- |
| PR #6 CI on `9ac0dcf` (run `41291235894`) | `tests-syntax` 3 passed; `tests-browser` 32 passed, 1 xpassed (L10); GitGuardian passed. `main` `d9b8882` has the same tree as `9ac0dcf` |
| PR #6 regression test `test_strip_follows_layout_changes` | Fails on `3d04635` (negative control); passed 5 of 5 repeats with the fix |
| PR #5 CI on `c9575c7` (run `41273927661`) | Attempt 1: one browser test failed (the M17 timing defect); attempt 2: 31 passed, 1 xpassed |
| Known flaky result | `test_place_label_after_getting_off` is an `xfail` for L10 that passes in some runs |
| Not verified | Real devices; frame rate; a full pendeltåg ride between stations (TEST_PLAN.md §3) |

## Where merged work came from

| Branch | Commit | Merged as |
| --- | --- | --- |
| `fix-m14-phone-message-strip`, `pendeltag-camera` | `742403b`, `df54793` | Original M14 and camera commits, integrated by cherry-pick in PR #3 (`40d913e`) |
| `fix/m14-short-screen` | `081682f` | PR #4, `3d04635` |
| `docs/project-baseline` | `c9575c7` | PR #5, `b0ad590` |
| `fix/m14-layout-recalculation` | `9ac0dcf` | PR #6, `d9b8882` |
