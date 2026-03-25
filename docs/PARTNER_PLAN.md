# FinStack Partner Plan

## Decision

We are not deleting `finstack-mcp`.

We are using it as the open-source engine and public distribution layer.

The paid wedge is:

**Indian market daily brief**

## Why This Wedge

This is the best fit for the current constraints:

- the founder is busy and cannot do heavy outbound sales every day
- marketing budget is small, around `INR 1,000-2,000`
- the repo already has enough market-data functionality to support a daily brief product faster than a full advisor platform
- a daily brief has clear repeat value and is easier to explain than a generic finance MCP
- portfolio analyzers are crowded and trust-sensitive
- advisor or research-desk software can make more money, but it needs stronger sales and support effort right now

## Product Stack

### Public Product

Repo: `finstack-mcp`

Role:

- open-source MCP server
- GitHub credibility
- PyPI package
- MCP registry presence
- top-of-funnel acquisition

### Paid Product

Working name options:

- `finstack-brief`
- `finstack-daily`
- `finstack-research`

Recommended choice:

**`finstack-brief`**

Role:

- hosted daily Indian market brief
- email/Telegram/WhatsApp-ready output
- watchlist summaries
- earnings and corporate-action digest
- premium reports for paying users

## Version 1 Scope

The first paid product should generate a daily market brief with:

1. Nifty, Sensex, and Bank Nifty snapshot
2. top gainers and losers
3. FII/DII summary when available
4. important earnings and corporate actions
5. sector strength summary
6. watchlist update for selected stocks
7. AI-written summary in plain English

## Customer Target

Start with:

- serious Indian retail investors
- market-content creators
- Telegram or Discord paid communities
- small research desks

Do not start with enterprise or institutions.

## Revenue Model

Start simple:

- Free: public MCP repo and limited sample briefs
- Pro: `INR 499-999/month` for daily brief and watchlists
- Creator/Desk: `INR 2,999-7,999/month` for branded or multi-watchlist workflow

## 30-Day Priorities

### Week 1

- clean repo and public messaging
- fix README and docs
- publish GitHub repo professionally
- publish PyPI package

### Week 2

- list on MCP registries
- create landing page copy around the daily brief positioning
- add screenshots or GIF demo

### Week 3

- build first hosted daily brief prototype
- generate a brief for one sample watchlist
- create one email-style and one Telegram-style output

### Week 4

- onboard first 5-10 users manually
- collect feedback
- refine pricing and delivery

## Rules For Us

1. do not compete on tool count
2. do not build random features without a distribution path
3. keep `finstack-mcp` public and clean
4. put business progress in `docs/WORKLOG.md`
5. focus on one wedge until it gets real usage

## Immediate Next Build Recommendation

The next software deliverable after repo cleanup should be:

**A daily brief generator**

Input:

- date
- watchlist symbols
- summary style

Output:

- market snapshot
- movers
- key events
- watchlist notes
- short AI summary

That is the shortest path from this repo to a real paid product.
