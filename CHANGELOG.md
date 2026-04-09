# Changelog

All notable changes to FinStack MCP are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.10.0] - 2026-04-09

### Added
- 95-tool release across Indian market data, debate, research, ranking, and F&O workflows
- `get_fno_trade_setup` for NIFTY / BANKNIFTY options calls with `BUY_CE`, `BUY_PE`, or `NO_TRADE`
- `get_morning_fno_brief` for 8:15 AM pre-market F&O summaries
- research and ranking layer: `scan_watchlist`, `get_stock_timeline`, `get_stock_signal_score`, `get_sector_peer_context`
- signal proof layer: `evaluate_signal_quality`
- demo asset coverage in the README for stock brief and agent battle workflows

### Changed
- README repositioned around daily-use hooks, MCP-native workflows, and launch-ready product copy
- probability module refactored into a cleaner reusable signal surface for Nifty/F&O workflows
- BottomTabs and InfoPanel live wiring in the Arthex companion app were aligned to real backend shapes

### Fixed
- local yfinance cache setup hardened through the FinStack package init path
- morning F&O brief now degrades gracefully when live upstream market feeds are unavailable

---

## [0.3.1] - 2026-03-25

### Fixed
- Daily brief summary now reads market status from the correct NSE field
- Losers list now excludes positive movers
- Quarterly-results enrichment no longer mutates a dictionary while iterating it
- Earnings calendar values are formatted into cleaner JSON-friendly output
- Replaced a noisy invalid mover symbol in the default market-mover basket

---

## [0.3.0] - 2025-03-25

### Added
- 37 total MCP tools across Indian markets, global markets, fundamentals, and analytics
- `mutual_fund_nav` for live NAV data via AMFI
- `nse_circuit_breakers`
- `sensex_components`
- `nse_52week_scanner`
- `stock_screener` (Pro)
- `nse_options_chain` (Pro)
- `backtest_strategy` (Pro)
- `portfolio_analysis` (Pro)
- `support_resistance` (Pro)
- `nse_fii_dii_data`
- `nse_bulk_deals`
- `nse_corporate_actions`
- `nse_quarterly_results`
- `earnings_calendar`
- `ipo_calendar`
- `sector_performance`
- landing page, Dockerfile, Railway config, health check, and CI

### Changed
- Improved SEC filing fetcher resource handling
- Removed unused dependencies
- Added `numpy` as an explicit dependency

---

## [0.2.0] - 2025-03-18

### Added
- 20 total MCP tools
- global equities, crypto, forex, news, SEC filings
- income statement, balance sheet, cash flow, key ratios, company profile, dividend history
- TTL caching and per-tier rate limiting

---

## [0.1.0] - 2025-03-11

### Added
- Initial release with 6 Indian market tools
- `nse_quote`
- `bse_quote`
- `nse_market_status`
- `nifty_index`
- `nse_historical`
- `nse_top_movers`
