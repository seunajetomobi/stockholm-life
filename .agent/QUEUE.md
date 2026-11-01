# Task queue

The single source of the current task and the tasks after it. Project status (commits, live site, milestone) is in [`docs/PROJECT_STATUS.md`](../docs/PROJECT_STATUS.md); rules, roles and the report format in [`AGENTS.md`](../AGENTS.md).

How to use it: one task is **Current**. The coordinator (ChatGPT, through the user) adds and orders tasks; the user approves them. An agent starts only the current task, moves it to **Done** with a link to its pull request or report when the user has accepted it, and does not start the next one without approval. A task that needs more than a few lines gets a spec in `.agent/tasks/<task-id>.md`.

Updated 2026-11-01.

## Current

| ID | Task | Owner | Status | Needs approval for |
| --- | --- | --- | --- | --- |
| agent-workspace | Shared agent instructions (`AGENTS.md`, with the code map), `CLAUDE.md` importing them, `docs/PROJECT_STATUS.md`, this queue; KNOWN_ISSUES and MASTER_ROADMAP link to the status | Claude Code | In review (branch `chore/agent-workspace`) | Merging |

## Up next

In order. None of these has started.

| ID | Task | Owner | Notes | Needs approval for |
| --- | --- | --- | --- | --- |
| local-cleanup | Bring the user's local checkout up to date after the workspace pull request: move the untracked copies of files now on `main` aside (they are kept in the user's private backup), switch to `main`, fast-forward; remove the scratch worktrees whose branches are merged | Claude Code | Keep the local branches `fix-m14-phone-message-strip` and `pendeltag-camera`; push neither | Every step |
| m0-devices | Real-device checks of the pendeltåg camera and the message strip ([TEST_PLAN.md §4](../docs/TEST_PLAN.md)), results recorded | User, with Claude Code recording | Needs a real phone, tablet and desktop GPU | — |
| m0-deploy | Deploy `main` with the "Deploy to GitHub Pages" workflow and verify it live | User approves; Claude Code verifies | Live is still `870fe30` | Deploying |
| m0-relay | Redeploy the flights relay (`tools/flights-worker.js`) with `/waittime` and the `SWEDAVIA_KEY` secret | User | Needs Cloudflare access; KNOWN_ISSUES M1 | Deploying the Worker |
| m1-save | M1 save and state foundation ([MASTER_ROADMAP.md](../docs/MASTER_ROADMAP.md#m1--save-and-state-foundation)) | Claude Code | Spec to be written in `.agent/tasks/` when M0 is closed | Starting, then merging |

## Done

| ID | Result |
| --- | --- |
| m14-layout-timing | PR #6, merged as `d9b8882` (not deployed) |
| project-docs | PR #5, merged as `b0ad590` |
