# finstack-mcp · by Arthex

<!-- mcp-name: io.github.finstacklabs/finstack-mcp -->

[![PyPI version](https://badge.fury.io/py/finstack-mcp.svg)](https://pypi.org/project/finstack-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)

**They charge $97,000+/year. We made it free.**

finstack-mcp is an open-source MCP server that gives Claude, Cursor, ChatGPT, and any MCP client structured access to Indian and global financial data — 58 tools, zero subscriptions, zero API keys.

Built by **Arunodayya B S** ([@SpawnAgent](https://x.com/finstacklabs1)) · [Arthex](https://finstacklabs.github.io/) · MIT licensed.

---

## What they charge. What you pay.

| Feature | They charge | finstack-mcp |
|---|---|---|
| Real-time NSE data | Zerodha ₹6,000/yr | **FREE** (Angel One) |
| Options Greeks (Black-Scholes) | Sensibull ₹15,600/yr | **FREE** |
| Options Max Pain + PCR | Sensibull ₹15,600/yr | **FREE** |
| MF flows + AMFI AUM | Morningstar $17,500/yr | **FREE** |
| NSE Insider trading (SAST) | Trendlyne ₹4,950/yr | **FREE** |
| Promoter/FII/DII shareholding | Screener ₹4,999/yr | **FREE** |
| RBI rates + India macro | Bloomberg $31,980/yr | **FREE** |
| Credit ratings (CRISIL/ICRA/CARE) | Bloomberg $24,000/yr | **FREE** |
| BRSR/ESG data (SEBI-mandated) | Bloomberg ESG $24,000/yr | **FREE** |
| Fundamentals (P&L, balance sheet) | FactSet $12,000/yr | **FREE** |
| LTCG/STCG tax calculator | Nobody has this | **ONLY US** |

---

## Products

| Product | What it is | Price |
|---|---|---|
| **finstack-mcp** | 58-tool MCP server for Claude/Cursor/ChatGPT | Free forever (MIT) |
| **Dashboard** | TradingView-style web chart + options + screener | ₹299/mo (7-day free trial) |
| **Ideas** | Social trading community — post/like/comment analysis | Free |
| **Creator Desk** | Managed AI workspace + research reports + multi-portfolio | ₹2,999/mo |

**Dashboard** → [landing-page/dashboard.html](landing-page/dashboard.html) · Real candlestick charts, options chain with Max Pain, FII/DII flows, screener, portfolio tracker. Connects to real NSE data via Angel One.

**Ideas feed** → [landing-page/ideas.html](landing-page/ideas.html) · Post your market analysis, like/comment on others, browse by symbol, direction, or trending.

---

## Demo

[![FinStack MCP Demo](https://img.youtube.com/vi/PWK89gBbHEM/maxresdefault.jpg)](https://youtu.be/PWK89gBbHEM?si=MqYuCRRJ0EUP10fm)

---

## Quick Start

```bash
pip install finstack-mcp
```

For real-time NSE data via Angel One SmartAPI (optional):

```bash
pip install finstack-mcp[broker]
```

Add to your `.env` (stays local, never on GitHub):

```
ANGEL_API_KEY=your_api_key
ANGEL_CLIENT_ID=your_client_id
ANGEL_PASSWORD=your_pin
ANGEL_TOTP_SECRET=your_totp_secret
```

## Claude Desktop Setup

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

Restart Claude Desktop and try:

- *"What's the credit rating for Reliance? Show CRISIL/ICRA ratings."*
- *"Get real-time live price for TCS via Angel One."*
- *"Show BRSR ESG data for HDFC Bank."*
- *"What are the Options Greeks for NIFTY 24000 CE expiring next week?"*
- *"Compare TCS, Infosys, and Wipro on margins and valuation."*
- *"Show insider trading activity for ADANIENT."*
- *"What's the India VIX and what does it signal?"*
- *"Calculate my LTCG tax on 500 shares of Reliance bought at ₹2,200, sold at ₹2,900."*

---

## Tool Coverage — 58 Tools

### Indian Markets (16 tools)
- NSE/BSE live quotes · market status · Nifty/Sensex/Bank Nifty indices
- Historical OHLCV · top movers · mutual fund NAV
- Circuit breaker scanner · 52-week scanner · Sensex components
- FII/DII institutional activity · bulk & block deals
- Corporate actions · quarterly results · earnings calendar · IPO calendar

### Global Markets (8 tools)
- Global stock quotes + historical data
- Crypto prices + history (BTC, ETH, SOL, 100+)
- Forex rates (USD/INR, EUR/INR, 50+ pairs)
- Market news by ticker · SEC filings (10-K, 10-Q, 8-K) · SEC search

### Fundamentals (7 tools)
- Income statement · balance sheet · cash flow
- Key ratios (P/E, ROE, margins, debt/equity, growth)
- Company profile · dividend history · stock comparison

### Analytics (5 tools)
- Technical indicators (RSI, MACD, SMA, Bollinger, ATR, Stochastic, ADX)
- Sector performance · stock screener · support/resistance · backtesting

### Options & Greeks (3 tools)
- Options chain with PCR analysis
- Black-Scholes Greeks: Delta, Gamma, Theta, Vega, Rho
- Options OI analytics: Max Pain, IV summary, top OI strikes

### Market Intelligence (10 tools)
- India VIX fear index + signal · GIFT Nifty pre-market
- NSE insider trading (SAST) · promoter shareholding · promoter pledge
- RBI policy rates (repo, CRR, SLR, MSF) · India macro (CPI, GDP, CAD)
- AMFI fund flows + SIP data · India G-Sec yield curve · Nifty PCR trend
- Dividend history deep (10yr) · portfolio analysis

### Real-time Broker Data — NEW (3 tools)
- `live_quote` — real-time NSE LTP via Angel One SmartAPI (zero delay)
- `market_depth` — Level 2 order book top 5 bid/ask (Zerodha charges ₹500/mo → FREE)
- `broker_setup_status` — check Angel One connection + setup guide

### Credit & ESG — NEW (2 tools)
- `credit_ratings` — CRISIL/ICRA/CARE/India Ratings from SEBI-mandated NSE/BSE filings (Bloomberg $24k/yr → FREE)
- `brsr_esg` — BRSR sustainability report data from SEBI-mandated filings (Bloomberg ESG $24k/yr → FREE)

### Tax (1 tool)
- LTCG/STCG tax calculator (Indian equity + mutual fund trades, post-July 2024 Budget rules)

---

## Data Sources

| Source | Coverage | API key required |
|---|---|---|
| yfinance | NSE, BSE, US equities, crypto, forex | No |
| NSE direct endpoints | FII/DII, bulk deals, options chain, insider trading, credit ratings, BRSR | No |
| BSE India API | Supplemental quotes, credit ratings | No |
| SEC EDGAR | US filings (10-K, 10-Q, 8-K) | No |
| CoinGecko | Crypto market data | No |
| World Bank API | India macro: CPI, GDP, current account | No |
| AMFI / mfapi.in | Mutual fund NAV, industry AUM, SIP flows | No |
| Angel One SmartAPI | Real-time NSE quotes, Level 2 depth | Your own broker key (free for account holders) |

---

## Security — Your API Key is Safe

When you configure Angel One SmartAPI, your credentials live in your local `.env` file which is in `.gitignore`. The open-source code only reads `os.environ` — it never stores, logs, or transmits your key. Every user sets their own credentials.

---

## Development

```bash
git clone https://github.com/finstacklabs/finstack-mcp.git
cd finstack-mcp
pip install -e .[dev]
pytest -q
```

---

## Run the Dashboard Locally (with real NSE data)

```bash
# 1. Start the data API
cd dashboard-api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 2. Open dashboard.html in your browser
# The dashboard auto-detects the API and shows a green ⬤ LIVE badge
# Without the API it runs in demo mode with realistic fake data
```

> **⚠ Data delay warning:** Without Angel One configured, chart data is 15-min delayed (yfinance). Do not use for intraday trading without real-time data. Configure Angel One SmartAPI for zero-delay quotes.

---

## Current Status

- GitHub: https://github.com/finstacklabs/finstack-mcp
- PyPI: https://pypi.org/project/finstack-mcp/
- Landing page: https://finstacklabs.github.io/
- Dashboard: [landing-page/dashboard.html](landing-page/dashboard.html)
- Ideas feed: [landing-page/ideas.html](landing-page/ideas.html)
- YouTube demo: https://youtu.be/PWK89gBbHEM
- X / Twitter: https://x.com/finstacklabs1

---

## Contributing

PRs welcome. Keep changes focused, test what you touch, document new tools clearly.

## License

MIT · Arthex · finstack-mcp v0.6.1
