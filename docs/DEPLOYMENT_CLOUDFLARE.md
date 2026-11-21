# Hosting on Cloudflare Pages at stockholmsliv.app (proposed)

**Status: proposed on 2026-11-21. Nothing is set up or deployed.** Today's hosting is still GitHub Pages with the manual, approval-gated workflow ([TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md) §4). This page becomes the record of a decision in §5 only after the owner has created the project and the first release is verified.

## Design
- **Static site, no build.** Cloudflare Pages publishes the repository root of one branch as it is. Build command: none. Output directory: `/`.
- **Production branch: `live`**, not `main`. Merging into `main` never publishes. A commit reaches `live` only through the promotion step below, so unfinished work on `main` does not go live by accident, yet every promotion is automatic and takes about a minute.
- **Other branches** get private preview URLs from Cloudflare and never touch the live site.
- **Domain:** `stockholmsliv.app` (main) and `www.stockholmsliv.app`, both added as custom domains on the Pages project (DNS is on Cloudflare, so the records and the certificate are created automatically).

## Promoting a release
Only a commit that is already on `main` and whose three required checks passed (`tests-syntax`, `tests-browser`, GitGuardian):

```
git fetch origin
git merge-base --is-ancestor <sha> origin/main        # must succeed
git push origin <sha>:refs/heads/live                 # fast-forward only; never force
python3 tools/live_check.py --url https://stockholmsliv.app/   # after Cloudflare has published
```

## Rollback
Either promote an earlier verified commit (a fast-forward is not possible going backwards, so use the Cloudflare dashboard: Pages project > Deployments > an earlier deployment > "Rollback to this deployment"), or revert on `main` and promote the revert.

## Things to check after the first release
- The game boots, three.js loads and `data/*.json` and `src/*.js` are served with correct types.
- Flights, news and Arlanda queue times work through the relay (its CORS list must include the new domain and the Worker must be redeployed; see KNOWN_ISSUES M13).
- `version.txt` matches the promoted commit.
- Saves do not move between addresses (browser storage is per origin): before leaving the old address use Save slots > Export, then Import on the new one.

## Owner-only steps
Create the Pages project and connect the repository, set the production branch to `live`, add the custom domains, redeploy the relay Worker, and decide when the old GitHub Pages site is retired (a destructive step). The deploy workflow and `tools/live_check.py`'s default address change only after the new site is verified.
