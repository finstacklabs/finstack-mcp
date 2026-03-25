# Worklog

## 2026-03-25

### Product Direction

- Chosen paid wedge: **Indian market daily brief**
- Decision: keep `finstack-mcp` as the public open-source engine and funnel
- Decision: do not delete this repo
- Decision: treat the future hosted brief product as the revenue layer

### Repo Hygiene

- Fixed `.gitignore` so `docs/` is no longer ignored
- Added `pytest-cache-files-*/` to `.gitignore` to avoid temp-directory noise

### Public Positioning

- Rewrote `README.md` with cleaner positioning
- Corrected the public tool count to `39`
- Linked the README to the partner plan and worklog
- Rewrote `landing-page/index.html` around the OSS engine plus paid daily brief story
- Replaced stale `server.json` copy with current metadata and counts
- Rebuilt the landing page for mobile with a hamburger menu, responsive sections, and stronger cinematic styling
- Corrected public links and contact details on the landing page to use `finstacklabs`
- Expanded the README into a fuller public product document with overview, coverage, setup, and daily-brief direction
- Added more trust and conversion detail to the landing page, including demo link, use-case sections, and pricing CTAs
- Removed the not-yet-live hosted transport claim from `server.json`
- Converted `server.json` to the official MCP Registry schema and published `io.github.finstacklabs/finstack-mcp`

### Product Build

- Added `src/finstack/briefs.py` as the first daily brief generator
- Added CLI entry point: `finstack-brief`
- Added tests for the brief generator
- Updated CI to run the test suite
- Fixed daily brief summary status mapping
- Fixed market-mover loser filtering so positive stocks do not appear as losers
- Fixed quarterly result enrichment bug caused by mutating a dict during iteration
- Cleaned AI-looking banner comments in core server/config files and replaced stale backend project links

### Documentation

- Added `docs/DAILY_BRIEF.md`
- Added `docs/LAUNCH_TODAY.md`
- Rewrote `docs/MASTER_TRACKER.md`
- Rewrote `docs/LAUNCH_GUIDE.md`

### Notes

- A stray root directory named `pytest-cache-files-5ho_lexf` appears to be temporary test noise
- Attempted deletion failed because the path is access-denied on this machine
- It is now ignored so it does not affect future repo hygiene
