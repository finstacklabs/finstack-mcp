# Founder Playbook

## Purpose

This document is for internal founder use.

It is not the public README.
It is not the public landing-page copy.
It is the working reference for running FinStack as a business and product.

If you are confused about what to do next, read this file first.

## 1. What We Have Right Now

Live:

- GitHub repo
- PyPI package
- landing page
- official MCP Registry listing

Product identity:

- `finstack-mcp` = public OSS engine
- `FinStack Brief` = future paid product on top

Current wedge:

- Indian market daily brief

## 2. Folder Reference

Use this as the practical meaning of each main folder:

- `src/`
  The actual product code
- `tests/`
  Safety net before releases
- `landing-page/`
  Public marketing site content
- `docs/`
  Business, launch, and founder reference material
- `.github/`
  CI and GitHub automation

Core root files:

- `README.md`
  Public technical overview
- `server.json`
  MCP Registry metadata
- `pyproject.toml`
  Python package metadata and dependencies
- `CHANGELOG.md`
  Release history
- `CONTRIBUTING.md`
  Public contribution guide

## 3. Founder Role

Your job is not to keep changing everything.

Your real job now is:

- keep product direction clear
- get first users
- collect failures and confusion
- convert useful feedback into focused improvements
- move toward paid daily brief delivery

Do not spend most of your time on:

- random redesigns
- endless branding changes
- vanity features
- speculative enterprise planning

## 4. CEO Guide

As founder/CEO, focus on:

- positioning
- distribution
- pricing
- user feedback
- decision-making

Weekly founder priorities:

1. check installs, stars, traffic, messages
2. talk to at least 3 real users
3. identify the top 3 friction points
4. decide one product improvement and one distribution action
5. keep the paid wedge message consistent

Core business message:

- public OSS engine for trust and discovery
- paid brief for recurring value

## 5. Developer Guide

Before changing code:

1. ask whether the change helps distribution, trust, or paid workflow
2. avoid broad rewrites without user evidence
3. keep metadata and docs aligned with reality

Developer rules:

- keep comments minimal and human
- keep public claims honest
- write tests for meaningful behavior changes
- bump PyPI version only for package changes
- do not fake hosted features that are not live

Next best code work:

1. improve brief formatting
2. make email-style output
3. make Telegram-style output
4. improve example/demo outputs

## 6. Tester Guide

Before every release:

1. install in clean env if possible
2. run:
   - `pytest -q`
   - `python -m finstack.server`
   - `python -m finstack.briefs --watchlist RELIANCE,TCS,HDFCBANK`
3. verify README links
4. verify landing-page links
5. verify `server.json` is honest

Smoke-test questions:

- does package install from PyPI?
- does local MCP start?
- does daily brief run?
- do public links open?
- does landing page look correct on desktop and mobile?

## 7. Product Guide

What we are building:

- India-first market intelligence engine
- daily brief workflow
- watchlist-driven repeatable output

What we are not building first:

- full portfolio SaaS
- advisor CRM
- enterprise dashboard platform
- trade execution platform

## 8. Marketing Guide

Best channels:

- GitHub
- MCP Registry visibility
- X
- LinkedIn
- Reddit
- WhatsApp / Telegram sharing

Best messages:

- India-first MCP for NSE/BSE
- open-source engine with real PyPI package
- daily market brief direction
- watchlist-ready research workflow

Best assets:

- GitHub repo
- landing page
- demo video
- PyPI link
- one sample brief screenshot or text block

What not to do:

- broad paid ads
- fake hype
- overclaiming scale
- promising unsupported features

## 9. Sales Guide

First customer types:

- serious retail users
- market-content creators
- paid communities
- small research desks

First sales message:

```text
FinStack gives you an India-first daily market brief built on top of a live MCP market-data engine. Instead of manually checking NSE/BSE moves, watchlist names, earnings, and corporate actions every day, the system composes that into one repeatable output.
```

First CTA options:

- join waitlist
- request access
- ask for a custom watchlist brief
- ask for creator/desk version

## 10. Revenue Guide

Current realistic monetization path:

- free OSS for reach
- manual onboarding for early paid users
- paid brief subscriptions
- creator/desk plan later

Simple revenue ladder:

- Free: OSS engine
- Pro Brief: `INR 499-999/month`
- Creator/Desk: `INR 2,999+ / month`

Revenue goal right now:

- not "huge scale immediately"
- first paying users
- proof of repeat usage

## 11. Weekly Execution Template

### Monday

- check all live links
- check product feedback
- decide weekly focus

### Tuesday

- code/product improvement

### Wednesday

- demo content or launch content

### Thursday

- user outreach

### Friday

- review traction
- document what worked
- plan next week

## 12. Launch Post Templates

### X / LinkedIn

```text
I launched FinStack MCP, an India-first financial data and research engine for MCP clients.

It gives Claude, Cursor, ChatGPT, and other MCP tools access to:
- NSE/BSE quotes and indices
- corporate actions and quarterly results
- FII/DII activity
- fundamentals and analytics
- watchlist-ready research workflows

Live now:
GitHub: https://github.com/finstacklabs/finstack-mcp
PyPI: https://pypi.org/project/finstack-mcp/
Site: https://finstacklabs.github.io/

The OSS engine is live now.
The paid direction on top is an Indian market daily brief.
```

### WhatsApp / Direct share

```text
Launched FinStack MCP today.
It is an India-first MCP server for NSE/BSE, fundamentals, analytics, and market research workflows.

GitHub: https://github.com/finstacklabs/finstack-mcp
PyPI: https://pypi.org/project/finstack-mcp/
Site: https://finstacklabs.github.io/

Would love your feedback after trying it.
```

## 13. GitHub Release Template

Tag:

- `v0.3.2`

Release title:

- `FinStack MCP v0.3.2`

Release notes:

```md
## FinStack MCP v0.3.2

This release prepares FinStack MCP for public discovery and registry distribution.

### Highlights
- Published official MCP Registry metadata
- Expanded README and public product documentation
- Improved landing page content and mobile responsiveness
- Cleaned project metadata and public links
- Daily brief workflow positioning clarified

### Live Links
- GitHub: https://github.com/finstacklabs/finstack-mcp
- PyPI: https://pypi.org/project/finstack-mcp/
- Website: https://finstacklabs.github.io/
- MCP Registry name: `io.github.finstacklabs/finstack-mcp`

### Notes
This repo is the open-source engine for FinStack.
The paid direction on top is the Indian market daily brief.
```

## 14. Local Cleanup Notes

About `__pycache__`, `.tmp`, `dist`, and `pytest-cache-files-*`:

- they are local junk, not product files
- they are already ignored in `.gitignore`
- they can be deleted safely
- if Windows keeps them locked, leave them for now
- they do not affect GitHub or PyPI if ignored

If they stay stuck:

- close terminals and Python processes
- restart VS Code if needed
- then delete them later

## 15. Next Real Priorities

Now focus on:

1. first real user feedback
2. launch posts and sharing
3. better brief formatting
4. waitlist / paid-interest collection

Do not focus on:

1. more cleanup
2. more random features
3. more branding changes
4. new accounts for no reason
