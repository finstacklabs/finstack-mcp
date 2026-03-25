# Daily Brief

## Purpose

`finstack-mcp` remains the public open-source engine.

The first commercial bridge built on top of it is the **Indian market daily brief** workflow.

This repo now includes a first generator module for that workflow.

## CLI Usage

```bash
python -m finstack.briefs --watchlist RELIANCE,TCS,HDFCBANK
```

Or after install:

```bash
finstack-brief --watchlist RELIANCE,TCS,HDFCBANK
```

## Output

The generator returns structured JSON with:

- market status
- Nifty, Sensex, Bank Nifty snapshot
- gainers, losers, most active
- sector performance
- FII/DII summary
- bulk deals
- watchlist earnings, results, and corporate actions
- short narrative summary

## Intended Product Path

This generator should be reused later in:

- email briefs
- Telegram or WhatsApp formatted briefs
- premium watchlist products
- the future hosted `finstack-brief` product

## Current Status

This is version 1 of the brief engine.

It is suitable for:

- demos
- early user feedback
- launch positioning

It is not yet a full hosted product.
