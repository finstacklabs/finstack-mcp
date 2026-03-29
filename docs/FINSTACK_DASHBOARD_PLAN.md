# FinStack Dashboard — Build Plan
**by Arthex · finstack-mcp data engine**

> A TradingView-inspired web dashboard for Indian markets — NSE/BSE real-time charts, options chain, screener, FII/DII flow, portfolio tracker — all powered by finstack-mcp. Free to use. No Bloomberg required.

---

## What We Are Building

A full-stack web trading dashboard. Think TradingView + Screener.in + Sensibull combined into one product, built on top of our existing 58-tool finstack-mcp data engine.

**The pitch:**
- TradingView: $15/mo (no India-first features)
- Sensibull: ₹1,300/mo (options only)
- Screener Pro: ₹4,999/yr (no live charts)
- **FinStack Dashboard: Free tier + ₹299/mo Pro**

---

## Tech Stack

### Frontend
| Layer | Choice | Why |
|---|---|---|
| Framework | **Next.js 14** (App Router) | SSR + SSG + API routes in one, Vercel deploys free |
| Language | **TypeScript** | Catches bugs before runtime |
| Styling | **Tailwind CSS** | Fast, consistent, no CSS file bloat |
| Charts | **TradingView Lightweight Charts v4** | MIT licensed, by TradingView itself, best candlestick lib |
| State | **Zustand** | Simpler than Redux, perfect for watchlist + chart state |
| Data fetching | **SWR** | Polling + caching for live prices, auto-revalidation |
| Icons | **Lucide React** | Clean, consistent |
| Fonts | **Inter + JetBrains Mono** | Matches our brand |

### Backend (Data API)
| Layer | Choice | Why |
|---|---|---|
| Framework | **FastAPI** (Python) | Wraps finstack-mcp tools as HTTP endpoints |
| Runtime | **Python 3.11** | Same as finstack-mcp |
| Real-time | **Server-Sent Events (SSE)** | Push live prices to frontend without WebSocket complexity |
| Cache | **Redis** (optional) | Cache NSE responses, avoid rate limits |
| Deployment | **Railway or Render** | Free tier, auto-deploy from GitHub |

### Frontend Deployment
- **Vercel** — auto-deploys on git push, free tier, global CDN

### Architecture Diagram
```
Browser (Next.js)
    │
    ├── /api/* (Next.js API routes) → FastAPI (Python)
    │                                      │
    │                                      ├── finstack-mcp tools
    │                                      ├── Angel One SmartAPI (real-time)
    │                                      ├── NSE/BSE direct endpoints
    │                                      └── yfinance (historical)
    │
    └── Lightweight Charts (renders candles/indicators in canvas)
```

---

## What We Will Build — Feature by Feature

### Phase 1 — Core Dashboard (2 weeks)

#### 1.1 Market Overview Bar (top of screen)
- Nifty 50 live price + % change (green/red)
- Bank Nifty live price + % change
- Sensex live price + % change
- India VIX + signal (green = calm, red = fear)
- Market status (OPEN / CLOSED / PRE-MARKET)
- GIFT Nifty (pre-market indicator)
- Auto-refreshes every 5 seconds via SWR polling

#### 1.2 Watchlist Panel (left sidebar)
- Add/remove NSE symbols
- Live LTP, change %, day high/low for each
- Color-coded: green if up, red if down
- Saved to localStorage (no login needed for free tier)
- Click any stock → loads it in the chart

#### 1.3 Candlestick Chart (main area)
- TradingView Lightweight Charts
- Timeframes: 1D, 1W, 1M, 3M, 6M, 1Y, 5Y
- OHLCV data from finstack-mcp `nse_historical` tool
- Real-time LTP line overlay (Angel One)
- Volume histogram below chart
- Crosshair with OHLC tooltip

#### 1.4 Technical Indicators (chart overlay)
- Simple Moving Average (SMA 20, 50, 200)
- EMA 9, 21
- Bollinger Bands
- RSI panel below chart (with 30/70 lines)
- MACD panel
- All from finstack-mcp `technical_indicators` tool

#### 1.5 Stock Info Panel (right sidebar)
- Company name, sector, market cap
- Day range, 52-week range
- Volume vs average volume
- P/E, EPS, dividend yield
- From finstack-mcp `key_ratios` + `company_profile`

---

### Phase 2 — Advanced Data (2 weeks)

#### 2.1 Options Chain Viewer
- Full NSE options chain for any symbol
- CE/PE side-by-side table
- OI, change in OI, IV, LTP, bid/ask
- Max Pain highlighted
- PCR (Put-Call Ratio) displayed prominently
- Color intensity based on OI concentration (like Sensibull)
- From finstack-mcp `nse_options_chain` + `options_oi_analytics`

#### 2.2 Options Greeks Panel
- For selected strike: Delta, Gamma, Theta, Vega, Rho
- IV surface visualization (strikes × expiry grid)
- From finstack-mcp `options_greeks`

#### 2.3 FII/DII Flow Dashboard
- Daily FII buy/sell + net, DII buy/sell + net
- 30-day trend chart (area chart)
- "FII sold ₹2,400 Cr today" summary card
- From finstack-mcp `nse_fii_dii_data`

#### 2.4 Stock Screener
- Filter by: sector, market cap, P/E, ROE, 52-week performance
- Results table with click-to-chart
- Save custom screens (localStorage)
- From finstack-mcp `stock_screener`

#### 2.5 Bulk & Block Deals Feed
- Live feed of today's bulk/block deals
- Company, quantity, price, buyer/seller name
- From finstack-mcp `nse_bulk_deals`

---

### Phase 3 — Market Intelligence (1 week)

#### 3.1 Insider Trading Feed
- NSE SAST disclosures
- Promoter, person, % acquired/sold, date
- "Promoter bought ₹12 Cr" — this is the hook
- From finstack-mcp `nse_insider_trading`

#### 3.2 Promoter Shareholding & Pledge Tracker
- Quarterly shareholding pattern chart
- Pledge % with risk signal (red if >20%)
- From finstack-mcp `promoter_shareholding` + `promoter_pledge`

#### 3.3 Macro Dashboard
- RBI repo rate, CRR, SLR, bank rate
- India CPI (inflation), GDP growth, current account
- G-Sec yield curve (T-bill → 30yr bond)
- AMFI SIP flows + MF industry AUM
- From finstack-mcp macro tools

#### 3.4 Credit Ratings Panel
- CRISIL/ICRA/CARE ratings for any listed company
- Rating history chart
- Outlook badge (stable/watch/negative)
- From finstack-mcp `credit_ratings`

#### 3.5 BRSR/ESG Panel
- ESG score breakdown by principle
- BRSR filing links for last 3 years
- From finstack-mcp `brsr_esg`

---

### Phase 4 — Portfolio & Tax (1 week)

#### 4.1 Portfolio Tracker
- Add trades: symbol, quantity, buy price, date
- Live P&L (unrealized gain/loss)
- Sector allocation pie chart
- XIRR calculation
- From finstack-mcp `portfolio_analysis`

#### 4.2 LTCG/STCG Tax Calculator
- Enter your trades → get tax liability breakdown
- LTCG vs STCG breakdown
- Post-July 2024 Budget rules
- From finstack-mcp `calculate_tax_liability`

---

### Phase 5 — Pro Features (paid tier)

#### 5.1 Price Alerts
- Set price alerts: "Alert me when RELIANCE hits ₹2,900"
- Email + Telegram delivery
- Needs: user accounts (NextAuth.js) + background worker

#### 5.2 Daily Brief Delivery
- The existing FinStack Brief product → now integrated into dashboard
- Morning market brief emailed/Telegrapmed at 8:15 AM
- Watchlist-specific + general market overview

#### 5.3 Custom Screener Saves + Alerts
- Save screener presets
- Alert when a stock enters your screener

---

## Folder Structure

```
finstack-dashboard/
├── apps/
│   ├── web/                          ← Next.js frontend
│   │   ├── app/
│   │   │   ├── page.tsx              ← Dashboard home
│   │   │   ├── chart/[symbol]/       ← Chart page per stock
│   │   │   ├── options/[symbol]/     ← Options chain
│   │   │   ├── screener/             ← Stock screener
│   │   │   ├── macro/                ← RBI/CPI/G-Sec
│   │   │   └── portfolio/            ← Portfolio tracker
│   │   ├── components/
│   │   │   ├── chart/
│   │   │   │   ├── CandlestickChart.tsx
│   │   │   │   ├── IndicatorPanel.tsx
│   │   │   │   └── VolumeChart.tsx
│   │   │   ├── watchlist/
│   │   │   │   ├── WatchlistPanel.tsx
│   │   │   │   └── WatchlistItem.tsx
│   │   │   ├── options/
│   │   │   │   ├── OptionsChain.tsx
│   │   │   │   └── GreeksPanel.tsx
│   │   │   ├── market/
│   │   │   │   ├── MarketBar.tsx     ← top Nifty/BN/VIX bar
│   │   │   │   ├── FIIDIIChart.tsx
│   │   │   │   └── MacroDashboard.tsx
│   │   │   └── ui/                   ← shared components
│   │   └── lib/
│   │       ├── api.ts                ← fetcher functions
│   │       └── store.ts              ← Zustand state
│   │
│   └── api/                          ← FastAPI backend
│       ├── main.py                   ← FastAPI app
│       ├── routes/
│       │   ├── quotes.py             ← /quote/{symbol}
│       │   ├── historical.py         ← /historical/{symbol}
│       │   ├── options.py            ← /options/{symbol}
│       │   ├── fundamentals.py       ← /fundamentals/{symbol}
│       │   ├── macro.py              ← /macro/*
│       │   └── sse.py                ← /sse/prices (Server-Sent Events)
│       └── services/
│           └── finstack.py           ← wraps finstack-mcp tools
│
└── packages/
    └── finstack-mcp/                 ← symlink or submodule to existing repo
```

---

## Timeline

| Phase | What ships | Time |
|---|---|---|
| Phase 1 | Market bar, watchlist, candlestick chart, indicators, stock info | 2 weeks |
| Phase 2 | Options chain, Greeks, FII/DII, screener, bulk deals | 2 weeks |
| Phase 3 | Insider trading, macro, credit ratings, ESG | 1 week |
| Phase 4 | Portfolio tracker, tax calculator | 1 week |
| Phase 5 | Alerts, brief delivery, auth, payments | 2 weeks |
| **Total MVP** | Phases 1–3 | **~5 weeks** |

---

## What We Cannot Build (Yet)

| Feature | Why Not |
|---|---|
| Tick-by-tick real-time chart (true streaming) | Angel One gives REST polling, not WebSocket tick feed. Can fake it with 1s polling — looks real-time |
| 500+ indicators | TradingView has a team of 200 engineers. We cover the top 10 used by 90% of traders |
| Pine Script execution | Custom scripting language = years of work. Skip for now |
| Order placement | Need SEBI broker license or direct Zerodha/Angel One integration. Possible via Angel One SmartOrder API later |
| Social features (copy trading, ideas feed) | Separate product. Phase 6 if we get traction |

---

## First Screen to Build

The very first screen will be:

```
┌─────────────────────────────────────────────────────────────────┐
│ Arthex · finstack-mcp  [Nifty 24,812 +0.88%] [BankNifty +1.2%] │
├──────────┬──────────────────────────────────┬───────────────────┤
│Watchlist │        RELIANCE — 1D Chart        │   Stock Info      │
│          │                                  │                   │
│RELIANCE  │   [Candlestick chart here]        │ P/E: 22.4         │
│TCS       │   [Volume below]                 │ Mkt Cap: ₹18.2L Cr│
│HDFCBANK  │   [RSI panel]                    │ 52W: 2188–3217    │
│INFY      │                                  │ Div Yield: 0.4%   │
│SBIN      │  Indicators: MA20 MA50 BB RSI    │                   │
│+ Add     │                                  │ [Options] [ESG]   │
└──────────┴──────────────────────────────────┴───────────────────┘
```

---

## Decision for You to Make

**New repo or monorepo?**
- Option A: `finstack-dashboard` — new separate GitHub repo, calls finstack-mcp as a PyPI package
- Option B: Add `dashboard/` folder inside this repo (monorepo)

**Recommended: Option A** — keeps the open-source MCP engine clean and separate from the dashboard app. Dashboard can be a private or public repo as you choose.

Once you confirm the plan, I'll start with Phase 1: FastAPI wrapper + Next.js shell + candlestick chart with real RELIANCE data.
