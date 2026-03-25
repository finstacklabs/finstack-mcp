# FinStack MCP

[![PyPI version](https://badge.fury.io/py/finstack-mcp.svg)](https://pypi.org/project/finstack-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)

India-first MCP server for market data, fundamentals, and research workflows.

39 tools. Zero API keys. Works with Claude, Cursor, ChatGPT, and MCP clients.

## Install

```bash
pip install finstack-mcp
```

Add to Claude Desktop config:

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

Restart Claude and ask:

- "What's Reliance's stock price?"
- "Compare TCS, Infosys, and Wipro."
- "Show me technical indicators for HDFCBANK."

## Coverage

- Indian markets: NSE/BSE quotes, indices, historical data, corporate actions, quarterly results, FII/DII, bulk deals, IPOs
- Global markets: stocks, crypto, forex, market news, SEC filings
- Fundamentals: income statement, balance sheet, cash flow, key ratios, company profile, dividend history
- Analytics: indicators, stock comparison, sector performance, screeners, options chain, backtesting

## Product Role

This repo is the open-source engine and public distribution layer for FinStack.

The paid wedge we are building on top of this is the hosted **Indian market daily brief** product.

- Strategy: [docs/PARTNER_PLAN.md](docs/PARTNER_PLAN.md)
- Running updates: [docs/WORKLOG.md](docs/WORKLOG.md)

## Data Sources

| Source | Covers | API Key |
|---|---|---|
| yfinance | NSE, BSE, US, Crypto, Forex | Not needed |
| SEC EDGAR | US company filings | Not needed |
| NSE Direct | FII/DII, bulk deals, IPOs | Not needed |

## Contributing

PRs are welcome. Keep changes focused, test what you touch, and document any new tool clearly.

## License

MIT
