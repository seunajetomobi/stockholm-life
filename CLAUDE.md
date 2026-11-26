# Notes for Claude Code

@AGENTS.md

The shared rules, roles, approval boundaries, report format and the code map are in `AGENTS.md`, imported above. Status is in `docs/PROJECT_STATUS.md` and the current task in `.agent/QUEUE.md`; read both before starting.

Claude Code only:

- The browser tests use the Chromium build pinned by Playwright and need `SL_PORT` set to a free port other than 8000 (the harness refuses otherwise; port 8000 stays for the owner's `./start.sh`).
- Do not save project facts that the repository already records (status, decisions, the code map) to Claude Code's memory; update the repository files instead.
