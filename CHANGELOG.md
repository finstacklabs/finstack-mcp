# Changelog

All notable changes to FinStack MCP are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.3.0] — 2025-03-25

### Added
- **37 total MCP tools** across Indian markets, global markets, fundamentals, and analytics
- `mutual_fund_nav` — live NAV for any Indian mutual fund via AMFI (free, no key)
- `nse_circuit_breakers` — scan stocks hitting upper/lower circuit limits today
- `sensex_components` — full constituent list of Nifty 50 or Sensex with live prices, top gainers/losers within the index
- `nse_52week_scanner` — scan Nifty 50 for stocks near 52-week high or low with configurable threshold
- `stock_screener` (Pro) — filter stocks by P/E, ROE, market cap, sector, momentum
- `nse_options_chain` (Pro) — full options chain with PCR, max pain, IV skew
- `backtest_strategy` (Pro) — SMA crossover backtesting with CAGR, win rate, trade log
- `portfolio_analysis` (Pro) — P&L, weights, correlation, risk for a basket of stocks
- `support_resistance` (Pro) — pivot points and key price levels
- `nse_fii_dii_data` — FII/DII institutional activity
- `nse_bulk_deals` — bulk and block deals
- `nse_corporate_actions` — dividends, splits, bonuses
- `nse_quarterly_results` — latest quarterly financials with QoQ growth
- `earnings_calendar` — upcoming earnings dates
- `ipo_calendar` — upcoming and recent IPOs
- `sector_performance` — Nifty sectoral index performance
- Landing page (`landing-page/index.html`) with interactive mesh background
- Dockerfile and Railway deployment config
- Health check function for hosted deployments
- GitHub Actions CI (Python 3.10 / 3.11 / 3.12)

### Changed
- SEC filing fetcher now uses context manager — eliminates resource leak on error paths
- Removed unused `pandas-ta` and `cachetools` dependencies
- Added `numpy` as explicit dependency
- Version classifier upgraded Alpha → Beta

---

## [0.2.0] — 2025-03-18

### Added
- **20 total MCP tools**
- `stock_quote`, `stock_historical` — global equities (US, EU, Asia)
- `crypto_price`, `crypto_historical` — Bitcoin, Ethereum, any coin
- `forex_rate` — any currency pair live
- `market_news` — news by ticker or general market
- `sec_filing`, `sec_filing_search` — SEC EDGAR 10-K / 10-Q / 8-K
- `income_statement`, `balance_sheet`, `cash_flow` — annual & quarterly
- `key_ratios`, `company_profile`, `dividend_history`
- TTL cache system (5 min quotes / 1 hr fundamentals / 24 hr history)
- Per-tier rate limiter

---

## [0.1.0] — 2025-03-11

### Added
- Initial release — 6 Indian market tools
- `nse_quote` — real-time NSE price, P/E, market cap
- `bse_quote` — real-time BSE price
- `nse_market_status` — open / closed / pre-open check
- `nifty_index` — Nifty 50, Sensex, Bank Nifty, IT index
- `nse_historical` — OHLCV for any period and interval
- `nse_top_movers` — top gainers, losers, most active
- FastMCP-based server with stdio and HTTP transport
- MIT license
