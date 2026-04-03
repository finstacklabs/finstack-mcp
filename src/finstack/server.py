"""Main entry point for the FinStack MCP server."""

import logging
import sys

from mcp.server.fastmcp import FastMCP

from finstack.config import config
from finstack.tools.indian import register_indian_tools

config.setup_logging()
logger = logging.getLogger("finstack")

TOOL_CATALOG = [
    {"name": "nse_quote", "description": "Real-time NSE stock quote", "tier": "free"},
    {"name": "bse_quote", "description": "Real-time BSE stock quote", "tier": "free"},
    {"name": "nse_market_status", "description": "Market open/closed status", "tier": "free"},
    {"name": "nifty_index", "description": "Index values (Nifty, Sensex, Bank Nifty)", "tier": "free"},
    {"name": "nse_historical", "description": "Historical OHLCV data", "tier": "free"},
    {"name": "nse_top_movers", "description": "Top gainers, losers, most active", "tier": "free"},
    {"name": "mutual_fund_nav", "description": "Live NAV for any Indian mutual fund", "tier": "free"},
    {"name": "nse_circuit_breakers", "description": "Stocks hitting upper/lower circuit limits", "tier": "free"},
    {"name": "sensex_components", "description": "All stocks in Nifty 50 or Sensex with live prices", "tier": "free"},
    {"name": "nse_52week_scanner", "description": "Stocks near 52-week high or low", "tier": "free"},
    {"name": "stock_quote", "description": "Global stock quote (US, EU, Asia)", "tier": "free"},
    {"name": "stock_historical", "description": "Global historical OHLCV data", "tier": "free"},
    {"name": "crypto_price", "description": "Live crypto prices (BTC, ETH, SOL)", "tier": "free"},
    {"name": "crypto_historical", "description": "Historical crypto data", "tier": "free"},
    {"name": "forex_rate", "description": "Live forex rates (USD/INR, EUR/INR)", "tier": "free"},
    {"name": "market_news", "description": "Market news by ticker or general", "tier": "free"},
    {"name": "sec_filing", "description": "SEC filings (10-K, 10-Q, 8-K)", "tier": "free"},
    {"name": "sec_filing_search", "description": "Search SEC EDGAR for companies", "tier": "free"},
    {"name": "income_statement", "description": "Income statement / P&L", "tier": "free"},
    {"name": "balance_sheet", "description": "Balance sheet data", "tier": "free"},
    {"name": "cash_flow", "description": "Cash flow statement", "tier": "free"},
    {"name": "key_ratios", "description": "P/E, ROE, margins, debt/equity, growth", "tier": "free"},
    {"name": "company_profile", "description": "Company overview and description", "tier": "free"},
    {"name": "dividend_history", "description": "Historical dividend payments", "tier": "free"},
    {"name": "technical_indicators", "description": "RSI, MACD, SMA, Bollinger, ATR, Stochastic, ADX", "tier": "free"},
    {"name": "compare_stocks_tool", "description": "Side-by-side stock comparison (2-5 stocks)", "tier": "free"},
    {"name": "sector_performance", "description": "Nifty sectoral index performance", "tier": "free"},
    {"name": "nse_fii_dii_data", "description": "FII/DII institutional activity", "tier": "free"},
    {"name": "nse_bulk_deals", "description": "Bulk & block deals on NSE", "tier": "free"},
    {"name": "nse_corporate_actions", "description": "Dividends, splits, bonuses", "tier": "free"},
    {"name": "nse_quarterly_results", "description": "Latest quarterly financials with QoQ growth", "tier": "free"},
    {"name": "earnings_calendar", "description": "Upcoming earnings dates", "tier": "free"},
    {"name": "ipo_calendar", "description": "Upcoming & recent IPOs", "tier": "free"},
    {"name": "stock_screener", "description": "Screen stocks by P/E, ROE, market cap, sector", "tier": "pro"},
    {"name": "support_resistance", "description": "Pivot points & key price levels", "tier": "pro"},
    {"name": "nse_options_chain", "description": "Options chain with PCR analysis", "tier": "pro"},
    {"name": "portfolio_analysis", "description": "Portfolio P&L, weights, risk analysis", "tier": "pro"},
    {"name": "backtest_strategy", "description": "SMA crossover strategy backtesting", "tier": "pro"},
    {"name": "calculate_tax_liability", "description": "LTCG/STCG tax calculator for Indian equity and mutual fund trades", "tier": "free"},
    # ── Market Intelligence (Tools 41–48) — features paid platforms charge for ──
    {"name": "options_oi_analytics", "description": "Max Pain, PCR trend, IV summary, top OI strikes [Sensibull Pro ₹1,300/mo → FREE]", "tier": "free"},
    {"name": "options_greeks", "description": "Black-Scholes Greeks: Delta, Gamma, Theta, Vega, Rho [Sensibull Pro → FREE]", "tier": "free"},
    {"name": "nse_insider_trading", "description": "NSE SAST insider trading disclosures [Trendlyne ₹4,950/yr → FREE]", "tier": "free"},
    {"name": "promoter_shareholding", "description": "Promoter/FII/DII/public shareholding pattern [Screener Pro ₹4,999/yr → FREE]", "tier": "free"},
    {"name": "rbi_policy_rates", "description": "RBI repo, CRR, SLR, MSF, bank rate [Bloomberg $31,980/yr → FREE]", "tier": "free"},
    {"name": "india_macro_indicators", "description": "CPI inflation, GDP growth, current account [Bloomberg $31,980/yr → FREE]", "tier": "free"},
    {"name": "amfi_fund_flows", "description": "MF industry AUM, SIP flows, category breakdown [Morningstar $17,500/yr → FREE]", "tier": "free"},
    {"name": "india_gsec_yields", "description": "G-Sec yield curve: T-bill to 30-yr bond [Bloomberg $31,980/yr → FREE]", "tier": "free"},
    {"name": "india_vix", "description": "India VIX fear index + signal + history [Trendlyne paid → FREE]", "tier": "free"},
    {"name": "gift_nifty", "description": "GIFT Nifty pre-market + overnight global indices [Bloomberg paid → FREE]", "tier": "free"},
    {"name": "promoter_pledge", "description": "Promoter pledge % risk signal [Screener Pro ₹4,999/yr → FREE]", "tier": "free"},
    {"name": "dividend_history_deep", "description": "10-year dividend history + trailing yield [Bloomberg/FactSet paid → FREE]", "tier": "free"},
    {"name": "nifty_pcr_trend", "description": "Nifty PCR across all expiries + overall sentiment [Sensibull ₹1,300/mo → FREE]", "tier": "free"},
    # ── Broker + Credit + ESG (Tools 54–58) ──
    {"name": "live_quote", "description": "Real-time NSE quote via Angel One SmartAPI — zero delay [Zerodha ₹500/mo → FREE]", "tier": "free"},
    {"name": "market_depth", "description": "Level 2 order book top 5 bid/ask via Angel One [Zerodha ₹500/mo → FREE]", "tier": "free"},
    {"name": "broker_setup_status", "description": "Check Angel One SmartAPI integration status + setup guide", "tier": "free"},
    {"name": "credit_ratings", "description": "NSE/BSE credit ratings from SEBI filings [Bloomberg $24k/yr → FREE]", "tier": "free"},
    {"name": "brsr_esg", "description": "BRSR sustainability data from SEBI filings [Bloomberg ESG $24k/yr → FREE]", "tier": "free"},
    # ── Broker: Fyers API v3 ──
    {"name": "fyers_live_quote", "description": "Real-time NSE quote via Fyers API v3 (zero delay)", "tier": "free"},
    {"name": "fyers_candles", "description": "Historical OHLCV candles from Fyers API v3", "tier": "free"},
    {"name": "fyers_status", "description": "Fyers API configuration status + setup guide", "tier": "free"},
    # ── Broker: ICICI Breeze ──
    {"name": "icici_live_quote", "description": "Real-time NSE quote via ICICI Breeze (zero delay)", "tier": "free"},
    {"name": "icici_candles", "description": "Historical OHLCV candles from ICICI Breeze", "tier": "free"},
    {"name": "icici_status", "description": "ICICI Breeze configuration status + daily session guide", "tier": "free"},
    # ── Phase 3: Multi-agent + Intelligence ──
    {"name": "get_social_sentiment", "description": "Social sentiment for any NSE stock from Reddit + Twitter (BUY/HOLD/SELL)", "tier": "free"},
    {"name": "get_stock_brief", "description": "Multi-agent AI debate: 4 personas analyse a stock → consensus signal", "tier": "free"},
    {"name": "detect_unusual_activity", "description": "Smart money detector: OI buildup, block deals, promoter buying, volume spike", "tier": "free"},
    {"name": "get_nifty_outlook", "description": "Nifty direction probability % (RSI + FII + PCR + VIX + G-Sec + GIFT Nifty)", "tier": "free"},
    # ── Phase 3: Intelligence tools ──
    {"name": "predict_earnings", "description": "AI earnings preview: beat/miss probability before quarterly results", "tier": "free"},
    {"name": "analyze_portfolio", "description": "Portfolio X-ray: P&L, XIRR, sector concentration, risk flags, diversification score", "tier": "free"},
    {"name": "get_mf_overlap", "description": "Mutual fund overlap: % common holdings between two funds (AMFI data)", "tier": "free"},
    {"name": "get_fii_retail_divergence", "description": "FII vs retail divergence signal — highest-conviction Indian market signal", "tier": "free"},
    {"name": "get_morning_brief", "description": "8:15 AM pre-market brief: GIFT Nifty + FII + top setups + direction probability", "tier": "free"},
    {"name": "get_pledge_alert", "description": "Promoter pledge early warning: pledge % + QoQ change + risk level", "tier": "free"},
    {"name": "scan_pledge_risks", "description": "Scan multiple stocks for promoter pledge risk simultaneously", "tier": "free"},
    {"name": "detect_pump", "description": "Pump-and-dump detector: volume spike + circuit days + price surge", "tier": "free"},
    # ── Phase 4: Never-before-built Indian market tools ──
    {"name": "predict_circuit", "description": "Lower circuit risk predictor: pledge + FII selling + 52W low proximity", "tier": "free"},
    {"name": "get_sebi_alerts", "description": "SEBI enforcement order tracker — early warning before regulatory crash", "tier": "free"},
    {"name": "correlate_gst_to_stocks", "description": "GST collection trend → sector stock predictor (1-3mo leading indicator)", "tier": "free"},
    {"name": "get_agm_brief", "description": "AGM/EGM unusual resolution detector: debt raise, salary hike, pledge approval", "tier": "free"},
    {"name": "get_insider_signal", "description": "SEBI SAST insider trading pattern: who is buying/selling their own stock", "tier": "free"},
    {"name": "get_telegram_tracker", "description": "Dalal Street Telegram tip channel accuracy + pump-and-dump scoring", "tier": "free"},
    {"name": "analyze_budget_live", "description": "Real-time budget speech analyzer: paste FM text → instant sector/stock signals", "tier": "free"},
    {"name": "get_budget_impact", "description": "Historical Union Budget impact by year: winners, losers, key announcements", "tier": "free"},
]

TOTAL_TOOLS = len(TOOL_CATALOG) + 1

mcp = FastMCP("FinStack")

register_indian_tools(mcp)

from finstack.tools.analytics import register_analytics_tools
from finstack.tools.fundamentals import register_fundamental_tools
from finstack.tools.global_ import register_global_tools
from finstack.tools.tax import register_tax_tools
from finstack.tools.market_intelligence import register_market_intelligence_tools
from finstack.tools.broker_credit_esg import register_broker_credit_esg_tools
from finstack.tools.brokers import register_broker_tools
from finstack.tools.sentiment import register_sentiment_tools
from finstack.tools.agents import register_agent_tools
from finstack.tools.smart_money import register_smart_money_tools
from finstack.tools.probability import register_probability_tools
from finstack.tools.intelligence import register_intelligence_tools
from finstack.tools.phase4 import register_phase4_tools

register_global_tools(mcp)
register_fundamental_tools(mcp)
register_analytics_tools(mcp)
register_tax_tools(mcp)
register_market_intelligence_tools(mcp)
register_broker_credit_esg_tools(mcp)
register_broker_tools(mcp)
register_sentiment_tools(mcp)
register_agent_tools(mcp)
register_smart_money_tools(mcp)
register_probability_tools(mcp)
register_intelligence_tools(mcp)
register_phase4_tools(mcp)


@mcp.tool()
def finstack_info() -> str:
    """Return basic server metadata and useful links."""
    import json

    from finstack import __version__

    return json.dumps(
        {
            "name": "FinStack MCP",
            "version": __version__,
            "description": "Open-source financial data for AI assistants",
            "tier": config.mode.value,
            "tools_available": len(TOOL_CATALOG),
            "tools": TOOL_CATALOG,
            "links": {
                "github": "https://github.com/finstacklabs/finstack-mcp",
                "website": "https://finstacklabs.github.io/",
                "pricing": "https://finstacklabs.github.io/#pricing",
                "docs": "https://github.com/finstacklabs/finstack-mcp#readme",
            },
            "data_sources": [
                "yfinance (NSE, BSE, US, Crypto - free, no API key)",
                "SEC EDGAR (US filings - free, no API key)",
                "CoinGecko (Crypto - free tier, 30 calls/min)",
            ],
        },
        indent=2,
    )


def main() -> None:
    """Start the MCP server using stdio or streamable HTTP transport."""
    transport = "stdio"

    if "--transport" in sys.argv:
        idx = sys.argv.index("--transport")
        if idx + 1 < len(sys.argv):
            transport = sys.argv[idx + 1]

    import os

    transport = os.getenv("FINSTACK_TRANSPORT", transport)

    logger.info("Starting FinStack MCP server v%s", __import__("finstack").__version__)
    logger.info("Transport: %s", transport)
    logger.info("Mode: %s", config.mode.value)

    if transport == "stdio":
        mcp.run(transport="stdio")
        return

    if transport in ("http", "streamable-http"):
        mcp.run(
            transport="streamable-http",
            host=config.host,
            port=config.port,
        )
        return

    logger.error("Unknown transport: %s", transport)
    sys.exit(1)


def health_check() -> dict:
    """Return a simple health payload for uptime checks."""
    from finstack import __version__

    return {
        "status": "ok",
        "version": __version__,
        "mode": config.mode.value,
        "tools": TOTAL_TOOLS,
    }


if __name__ == "__main__":
    main()
