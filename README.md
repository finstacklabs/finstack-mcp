# FinStack MCP

**83 free tools for Indian + global markets. Works inside Claude, Cursor, and any MCP client.**

[![PyPI](https://badge.fury.io/py/finstack-mcp.svg)](https://pypi.org/project/finstack-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

```bash
pip install finstack-mcp
```

Ask Claude things like:

```
"Give me a full stock brief on Reliance"
→ 4 AI agents debate: FII Desk + Algo Trader + Value Investor + Retail Pulse
→ Consensus: BUY/HOLD/SELL with reasoning

"Is someone accumulating HDFC Bank quietly?"
→ Checks OI buildup, block deals, promoter buying, volume spike simultaneously

"What's the social buzz on TCS before results?"
→ StockTwits + Reddit + Economic Times → 67% bullish · Signal: HOLD

"Will Nifty go up tomorrow?"
→ RSI + FII flow + PCR + VIX + G-Sec + GIFT Nifty → 63% probability up

"Scan my portfolio for risk"
→ Sector concentration, pledged promoters, FII exposure, XIRR, diversification score

"Is this Telegram stock tip channel a scam?"
→ Accuracy %, avg return %, pump-and-dump probability scored
```

---

## What this replaces

| Tool | What you pay | finstack-mcp |
|---|---|---|
| Bloomberg Terminal | $31,980 / yr | **FREE** |
| Bloomberg ESG + Credit | $24,000 / yr | **FREE** |
| Sensibull (Options Greeks) | ₹15,600 / yr | **FREE** |
| Morningstar (MF flows) | $17,500 / yr | **FREE** |
| Zerodha real-time data | ₹6,000 / yr | **FREE** via Angel One |
| Screener.in Pro | ₹4,999 / yr | **FREE** |
| Trendlyne Pro | ₹4,950 / yr | **FREE** |

---

## Install + connect (2 minutes)

```bash
pip install finstack-mcp
```

Add to `claude_desktop_config.json`:

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

Restart Claude Desktop. Done.

Works with: **Claude Desktop · Cursor · Windsurf · Cline · Continue.dev · Zed · Jan.ai · LibreChat · any MCP client**

---

## 83 tools across 9 categories

### Indian Markets (live data)
- NSE/BSE real-time quotes, OHLCV history, market status
- Nifty 50, Bank Nifty, Sensex indices
- FII/DII institutional flows (daily + historical)
- Bulk & block deals, circuit breaker scanner, 52W high/low scanner
- Mutual fund NAV, corporate actions, earnings calendar, IPO calendar

### AI Intelligence (unique to finstack-mcp)
- **`get_stock_brief`** — 4 AI agents debate any stock → BUY/HOLD/SELL consensus
- **`get_social_sentiment`** — StockTwits + Reddit + ET RSS → sentiment signal
- **`detect_unusual_activity`** — OI buildup + block deals + promoter change + volume spike
- **`get_nifty_outlook`** — 6-signal probability model for next session direction
- **`predict_earnings`** — beat/miss probability before quarterly results
- **`get_fii_retail_divergence`** — highest-conviction Indian market signal

### Portfolio & Risk
- **`analyze_portfolio`** — P&L, XIRR, sector concentration, risk flags, diversification score
- **`get_mf_overlap`** — fund overlap % from AMFI public disclosures
- **`get_pledge_alert`** — promoter pledge early warning with QoQ velocity
- **`scan_pledge_risks`** — batch pledge scan across your watchlist
- **`predict_circuit`** — lower circuit risk prediction
- **`detect_pump`** — pump-and-dump pattern detector for small/micro caps

### Broker Integrations (zero-delay live data)
- Angel One SmartAPI — live quotes, Level 2 depth, intraday candles
- Fyers API v3 — live quotes + candles
- ICICI Breeze — live quotes + candles
- Dhan SmartAPI — live quotes + candles
- Upstox API v2 — live quotes + candles

### Options & Greeks
- Full NSE options chain with PCR, Open Interest, Max Pain
- Black-Scholes Greeks: Delta, Gamma, Theta, Vega, Rho
- OI analytics, IV summary, top OI strikes

### Market Intelligence
- India VIX + signal, GIFT Nifty pre-market
- NSE insider trading (SAST filings), promoter shareholding + pledge %
- RBI policy rates, India macro (CPI, GDP, CAD)
- AMFI mutual fund flows, India G-Sec yield curve
- **`get_sebi_alerts`** — SEBI enforcement order tracker (early crash warning)
- **`get_morning_brief`** — 8:15 AM pre-market brief

### Never-built-before (India-specific)
- **`correlate_gst_to_stocks`** — GST monthly data as 1-3mo sector leading indicator
- **`get_agm_brief`** — AGM/EGM unusual resolution detector (debt raise, salary hike, pledge approval)
- **`get_insider_signal`** — SEBI SAST insider buy/sell pattern vs forward returns
- **`get_telegram_tracker`** — Dalal Street tip channel accuracy + pump-and-dump scoring
- **`analyze_budget_live`** — paste FM speech → instant sector/stock signals (Feb 1st)
- **`get_budget_impact`** — historical Union Budget winners + losers by year

### Fundamentals
- Income statement, balance sheet, cash flow (Indian + US)
- Key ratios: P/E, ROE, margins, debt/equity, growth
- Company profile, dividend history (10-year), stock comparison

### Global + Crypto + Tax
- US, EU, global equities — quotes + history
- Crypto: BTC, ETH, SOL, 100+ coins (CoinGecko)
- Forex: USD/INR, EUR/INR, 50+ pairs
- SEC filings (10-K, 10-Q, 8-K)
- **LTCG/STCG tax calculator** (post-July 2024 Budget rules — nobody else has this)

---

## Comparison vs Indian market tools

| Feature | finstack-mcp | Screener.in | Tickertape | Sensibull | Trendlyne | TradingView |
|---|---|---|---|---|---|---|
| AI agents debate a stock | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Social sentiment (Reddit + StockTwits) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Nifty direction probability | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Telegram tip channel tracker | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Budget speech live analyzer | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| GST → sector stock predictor | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Pump-and-dump detector | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Promoter pledge early warning | ✅ | ❌ | ✅ paid | ❌ | ✅ paid | ❌ |
| Options Greeks | ✅ free | ❌ | ❌ | ✅ ₹1,300/mo | ❌ | ✅ paid |
| FII/DII flows | ✅ free | ❌ | ✅ | ✅ | ✅ paid | ❌ |
| Fundamentals (P/E, ROE, etc.) | ✅ free | ✅ free | ✅ | ❌ | ✅ | ✅ paid |
| Works inside Claude / Cursor | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Price | **Free** | ₹4,999/yr | ₹2,800/yr | ₹15,600/yr | ₹4,950/yr | $168/yr |

---

## Real-time data (optional)

Without setup: 15-minute delayed data (yfinance — free, no API key).
With Angel One: zero delay, Level 2 order book, intraday candles.

```bash
pip install finstack-mcp[broker]
```

```env
ANGEL_API_KEY=your_key
ANGEL_CLIENT_ID=your_client_id
ANGEL_PASSWORD=your_pin
ANGEL_TOTP_SECRET=your_totp_secret
```

Free account at [smartapi.angelbroking.com](https://smartapi.angelbroking.com/). Your key stays local in `.env` — never leaves your machine.

Other brokers: Fyers, ICICI Breeze, Dhan, Upstox also supported.

---

## Demo

[![FinStack MCP Demo](https://img.youtube.com/vi/PWK89gBbHEM/maxresdefault.jpg)](https://youtu.be/PWK89gBbHEM)

---

## Data sources

| Source | Covers | Key needed |
|---|---|---|
| yfinance | NSE/BSE/US equities, crypto, forex, history | None |
| NSE direct API | FII/DII, options chain, insider trading, corporate actions | None |
| BSE India API | Credit ratings, ESG/BRSR | None |
| SEC EDGAR | US filings (10-K, 10-Q, 8-K) | None |
| CoinGecko | Crypto market data | None |
| World Bank | India macro: CPI, GDP, CAD | None |
| AMFI / mfapi.in | Mutual fund NAV, AUM, SIP flows | None |
| StockTwits | Trader sentiment (pre-tagged bullish/bearish) | None |
| Reddit (praw) | r/IndiaInvestments + r/DalalStreetTalks | Optional free |
| Finance Ministry | Monthly GST collection data | None |
| SEBI public filings | Enforcement orders, insider SAST disclosures | None |
| Angel One SmartAPI | Real-time NSE, Level 2 depth, intraday | Free account |

---

## Troubleshooting

**Claude says "finstack not found" after install**
- Restart Claude Desktop fully (quit from system tray, not just close)
- Config path on Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Verify Python is in PATH: `python --version`

**pip install fails**
```bash
python -m pip install --upgrade pip
pip install finstack-mcp
```

**Angel One TOTP fails**
- TOTP secret ≠ password. Find it in Angel One app → Profile → Enable TOTP → secret key
- Install: `pip install finstack-mcp[broker]`

---

## Development

```bash
git clone https://github.com/finstacklabs/finstack-mcp.git
cd finstack-mcp
pip install -e .[dev]
pytest -q
```

PRs welcome. Adding a new broker: create `src/finstack/data/broker_X.py` and register in `tools/`.

---

## Links

- PyPI: https://pypi.org/project/finstack-mcp/
- Landing page: https://finstacklabs.github.io/
- YouTube: https://youtu.be/PWK89gBbHEM
- X: https://x.com/finstacklabs1

---

MIT License · [finstacklabs.github.io](https://finstacklabs.github.io/)
