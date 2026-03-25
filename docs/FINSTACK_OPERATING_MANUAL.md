# FinStack Operating Manual

## 1. Current State

FinStack is now live in its core public form.

Live assets:

- GitHub: `https://github.com/finstacklabs/finstack-mcp`
- PyPI: `https://pypi.org/project/finstack-mcp/`
- Landing page: `https://finstacklabs.github.io/`
- Official MCP Registry name: `io.github.finstacklabs/finstack-mcp`

Current product split:

- `finstack-mcp` = public open-source engine
- `FinStack Brief` = future paid daily-brief product built on top of the engine

Current wedge:

- Indian market daily brief

Current strengths:

- India-first positioning
- live GitHub, PyPI, landing page, and official MCP Registry presence
- 39 tools across Indian markets, global markets, fundamentals, and analytics
- daily brief generator already present

Current limitations:

- no self-serve hosted checkout yet
- no real remote public MCP endpoint yet
- no production delivery workflow yet for email / Telegram / WhatsApp
- no strong customer proof yet

## 2. Founder Account Setup

Recommended structure:

- Use `finstacklabs` as the product-facing GitHub account
- Use your personal LinkedIn/X for founder credibility and distribution
- Do not create separate random accounts for every platform unless your current one is messy or spammy

Best operating setup:

- GitHub: `finstacklabs`
- Email for product contact: `arunodayya32@gmail.com`
- Personal accounts: use for founder story, launch posts, and outreach
- Product pages: use `finstacklabs` branding consistently

Rule:

- product assets should look like one clean brand
- personal social can amplify the brand
- do not split attention across too many new accounts

## 3. Product Direction

Do not position this as:

- another generic finance MCP
- a tool-count competition
- a full SaaS platform already

Position it as:

- India-first MCP engine for market intelligence
- open-source research engine
- foundation for a paid Indian market daily brief

Why this wedge:

- easier to explain
- easier to ship
- easier to sell than advisor software
- fits the current codebase
- does not require heavy enterprise sales immediately

## 4. What The Public Repo Should Contain

Keep:

- `src/`
- `tests/`
- `landing-page/`
- `.github/`
- `docs/FINSTACK_OPERATING_MANUAL.md`
- `README.md`
- `LICENSE`
- `CONTRIBUTING.md`
- `pyproject.toml`
- `server.json`
- `CHANGELOG.md`

Remove or keep local-only:

- `dist/`
- `.tmp/`
- `pytest-cache-files-*`
- `.mcpregistry_*`
- local binaries like `mcp-publisher.exe`

## 5. Revenue Plan

### Short-term revenue path

Start with:

- free OSS distribution
- manual interest capture
- paid brief waitlist
- manual customer onboarding

Initial pricing:

- `FinStack MCP`: free
- `FinStack Brief`: `INR 499-999/month`
- `Creator / Desk`: `INR 2,999+ / month`

### First paying users

Best targets:

- serious retail users
- market-content creators
- paid Telegram / Discord communities
- small research desks

Do not start with:

- enterprise
- large institutions
- custom full-platform builds

## 6. Sales Plan

### First sales approach

Do not sell "AI finance platform".

Sell:

- daily Indian market brief
- watchlist intelligence
- earnings and corporate-action summaries
- branded brief workflow for creators or desks

### Sales message

Use this:

```text
FinStack gives you an India-first daily market brief built on top of a live MCP market-data engine. Instead of manually collecting NSE/BSE moves, earnings dates, corporate actions, sector performance, and watchlist context every day, the brief composes it into one repeatable output you can use for yourself, your paid community, or your desk.
```

### First outreach targets

Start with:

- 10 finance creators
- 10 active retail power users
- 10 small research / advisory operators

### Sales CTA

Use simple asks:

- "Want early access to the daily brief?"
- "Want this in email or Telegram format?"
- "Want a branded version for your watchlist or community?"

## 7. Marketing Plan

### Channels

Focus on:

- GitHub
- MCP Registry discovery
- X
- LinkedIn
- Reddit
- WhatsApp / Telegram sharing to trusted circles

### Content angles

Use these angles:

- India-first finance MCP
- NSE/BSE plus fundamentals and analytics
- daily brief workflow
- open-source engine with real PyPI package
- watchlist-ready market research

### Demo assets

Use:

- GitHub repo
- PyPI link
- demo video
- landing page
- one example daily brief output

### Budget

With `INR 1,000-2,000`, do not spend on broad ads.

Use it only for:

- boosting one strong post
- a simple domain later if needed
- one clean logo / visual asset if necessary

## 8. Launch Copy

### Short launch post

```text
Built and launched FinStack MCP.

It is an India-first MCP server for NSE/BSE, fundamentals, analytics, and market research workflows.

Live now:
GitHub: https://github.com/finstacklabs/finstack-mcp
PyPI: https://pypi.org/project/finstack-mcp/
Site: https://finstacklabs.github.io/

The open-source engine is live now. The paid direction on top is an Indian market daily brief.
```

### Better founder-style post

```text
I launched FinStack MCP, an India-first financial data and research engine for MCP clients.

It gives Claude, Cursor, ChatGPT, and other MCP tools structured access to:
- NSE/BSE quotes and indices
- corporate actions and quarterly results
- FII/DII activity
- fundamentals and analytics
- watchlist-ready research workflows

Live now:
GitHub: https://github.com/finstacklabs/finstack-mcp
PyPI: https://pypi.org/project/finstack-mcp/
Landing page: https://finstacklabs.github.io/

The public repo is the engine.
The next paid layer is an Indian market daily brief.
```

## 9. Public Messaging Rules

Say:

- open-source engine
- India-first
- daily-brief direction
- live GitHub + PyPI + MCP Registry

Do not say:

- billion-dollar platform
- fully automated investing system
- fully live SaaS if it is not
- fake pricing checkout if payments are not live

## 10. What To Do This Week

### Immediate

1. Let MCP directories propagate
2. Check PulseMCP and Glama over the next few days
3. Share launch post
4. Ask 5-10 users to install and test
5. Collect failure points and confusion points

### Do not do immediately

1. do not keep rewriting branding
2. do not add random new features
3. do not change pricing repeatedly
4. do not build enterprise features before user pull

## 11. Technical Production Rules

Before each release:

1. run tests
2. confirm README and package metadata match
3. confirm `server.json` is honest
4. confirm landing page links are current
5. publish new PyPI version only for real package changes

Version rule:

- GitHub docs/site-only changes: no package bump needed
- installable package changes: bump version

## 12. Current Worklog Summary

Completed:

- repo cleaned and launched
- landing page made mobile-friendly
- README rewritten and expanded
- daily brief generator added
- tests added and passing
- PyPI release published
- official MCP Registry listing published

Current package version:

- `0.3.2`

## 13. Next Real Product Build

The next software deliverable should be:

- a better formatted daily brief output

Then:

- email-ready format
- Telegram-ready format
- waitlist capture or manual onboarding

Do not build a full dashboard first.

## 14. Final Decision

Do not delete this project.

Use it as:

- the public engine
- the trust layer
- the acquisition layer

Build revenue on top of it through:

- FinStack Brief
- daily market summaries
- watchlist delivery
- creator / desk workflow
