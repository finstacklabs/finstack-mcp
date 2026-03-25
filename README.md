# FinStack MCP

<!-- mcp-name: io.github.finstacklabs/finstack-mcp -->

[![PyPI version](https://badge.fury.io/py/finstack-mcp.svg)](https://pypi.org/project/finstack-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)

FinStack MCP is an India-first financial data and research engine for MCP clients. It gives Claude, Cursor, ChatGPT, and other MCP-compatible tools a structured interface for NSE/BSE market data, global market coverage, fundamentals, analytics, and watchlist-ready research workflows.

The repo is public on purpose. It is the open-source engine, trust layer, and distribution channel for the broader FinStack product line.

Demo video: https://drive.google.com/file/d/1sWKAB2K62oUG14YtS5YqEo72Unr9xfq3/view?usp=sharing

## Overview

FinStack MCP is designed around a simple product split:

- `finstack-mcp` is the open-source MCP engine
- `FinStack Brief` is the paid delivery layer built on top of it

That means this repo focuses on the part that should be public and reusable:

- financial data access for Indian and global markets
- structured tools that work inside MCP clients
- reusable analytics for research workflows
- a base layer for future brief, alert, and dashboard products

## Why This Exists

Most finance MCP servers are either too generic, too thin, or too dependent on API-key-heavy setups. FinStack MCP is meant to be more practical:

- India-first coverage instead of treating NSE/BSE as an afterthought
- broad enough to be useful on day one
- simple enough to install with one package
- compatible with local MCP workflows before any hosted product exists

## What You Get

Current package scope:

- 39 tools in total
- 33 tools available in the free flow
- Indian market support for NSE/BSE quotes, indices, corporate actions, quarterly results, FII/DII activity, bulk deals, IPOs, and market status
- global market support for equities, crypto, forex, news, and SEC filings
- fundamentals support for income statement, balance sheet, cash flow, key ratios, company profiles, and dividend history
- analytics support for technical indicators, sector performance, stock comparison, screening, portfolio analysis, support/resistance, options chain, and backtesting

## Quick Start

Install from PyPI:

```bash
pip install finstack-mcp
```

Run locally:

```bash
python -m finstack.server
```

Or use the installed entry point:

```bash
finstack-mcp
```

Generate a daily brief from the CLI:

```bash
finstack-brief --watchlist RELIANCE,TCS,HDFCBANK
```

## Claude Desktop Setup

Add this to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "finstack": {
      "command": "python",
      "args": ["-m", "finstack.server"]
    }
  }
}
```

Restart Claude Desktop and try prompts like:

- "What's the latest price and day range for Reliance?"
- "Compare TCS, Infosys, and Wipro on margins and valuation."
- "Show me upcoming earnings and corporate actions for HDFCBANK."
- "Generate a quick Indian market brief for my watchlist."

## Tool Coverage

### Indian Markets

- NSE quotes
- BSE quotes
- market status
- Nifty, Sensex, and Bank Nifty indices
- historical OHLCV data
- top movers
- mutual fund NAV
- circuit-breaker scanner
- Sensex component snapshot
- 52-week scanner
- FII/DII activity
- bulk deals
- corporate actions
- quarterly results
- earnings calendar
- IPO calendar

### Global Markets

- global stock quotes
- historical stock data
- crypto quotes
- crypto history
- forex rates
- market news
- SEC filings
- SEC search

### Fundamentals And Analytics

- income statement
- balance sheet
- cash flow
- key ratios
- company profile
- dividend history
- technical indicators
- stock comparison
- sector performance
- stock screener
- support and resistance
- options chain
- portfolio analysis
- strategy backtesting

## Product Role

This repo is not meant to be the whole business by itself.

Its role is:

- public GitHub presence
- PyPI distribution
- MCP ecosystem discovery
- technical credibility
- reusable engine for future products

The paid wedge currently being built on top of this engine is the Indian market daily brief.

Reference doc:

- Operating manual: [docs/FINSTACK_OPERATING_MANUAL.md](docs/FINSTACK_OPERATING_MANUAL.md)

## Data Sources

| Source | Coverage | API key required |
|---|---|---|
| yfinance | NSE, BSE, US equities, crypto, forex, earnings | No |
| NSE Direct endpoints | FII/DII, bulk deals, market data, IPO context | No |
| SEC EDGAR | US filings and company submission data | No |
| CoinGecko | Crypto market data | No for current free flow |

## Daily Brief Direction

The first commercial layer on top of FinStack MCP is not "generic pro access." It is a repeatable workflow:

1. pull Indian market state
2. enrich it with watchlist context
3. compose a structured brief
4. deliver it through email, Telegram, WhatsApp, or a hosted dashboard

That is the bridge from open-source distribution to paid recurring value.

## Development

Clone the repo:

```bash
git clone https://github.com/finstacklabs/finstack-mcp.git
cd finstack-mcp
```

Install development dependencies:

```bash
pip install -e .[dev]
```

Run tests:

```bash
pytest -q
```

Build the package:

```bash
python -m build
```

## Current Status

This package is live on:

- GitHub: https://github.com/finstacklabs/finstack-mcp
- PyPI: https://pypi.org/project/finstack-mcp/
- Landing page: https://finstacklabs.github.io/

The hosted commercial layer is not public checkout yet. Public pricing should currently be treated as interest capture and positioning, not as a fully self-serve SaaS checkout.

## Contributing

PRs are welcome. Keep changes focused, test what you touch, and document new tools or changed behavior clearly.

## License

MIT
