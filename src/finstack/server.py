"""
FinStack MCP Server

The main entry point for the FinStack MCP server.
Registers all tools and starts the server in stdio or HTTP mode.

Usage:
    # Local stdio mode (Claude Desktop, Cursor)
    python -m finstack.server

    # Or via the console script
    finstack-mcp

    # HTTP mode (hosted, remote access)
    FINSTACK_MODE=pro python -m finstack.server --transport http
"""

import sys
import logging
from mcp.server.fastmcp import FastMCP

from finstack.config import config
from finstack.tools.indian import register_indian_tools

# Setup logging
config.setup_logging()
logger = logging.getLogger("finstack")

TOOL_CATALOG = [
    # Indian market tools
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
    # Global market tools
    {"name": "stock_quote", "description": "Global stock quote (US, EU, Asia)", "tier": "free"},
    {"name": "stock_historical", "description": "Global historical OHLCV data", "tier": "free"},
    {"name": "crypto_price", "description": "Live crypto prices (BTC, ETH, SOL)", "tier": "free"},
    {"name": "crypto_historical", "description": "Historical crypto data", "tier": "free"},
    {"name": "forex_rate", "description": "Live forex rates (USD/INR, EUR/INR)", "tier": "free"},
    {"name": "market_news", "description": "Market news by ticker or general", "tier": "free"},
    {"name": "sec_filing", "description": "SEC filings (10-K, 10-Q, 8-K)", "tier": "free"},
    {"name": "sec_filing_search", "description": "Search SEC EDGAR for companies", "tier": "free"},
    # Fundamental tools
    {"name": "income_statement", "description": "Income statement / P&L", "tier": "free"},
    {"name": "balance_sheet", "description": "Balance sheet data", "tier": "free"},
    {"name": "cash_flow", "description": "Cash flow statement", "tier": "free"},
    {"name": "key_ratios", "description": "P/E, ROE, margins, debt/equity, growth", "tier": "free"},
    {"name": "company_profile", "description": "Company overview and description", "tier": "free"},
    {"name": "dividend_history", "description": "Historical dividend payments", "tier": "free"},
    # Analytics tools
    {"name": "technical_indicators", "description": "RSI, MACD, SMA, Bollinger, ATR, Stochastic, ADX", "tier": "free"},
    {"name": "compare_stocks_tool", "description": "Side-by-side stock comparison (2-5 stocks)", "tier": "free"},
    {"name": "sector_performance", "description": "Nifty sectoral index performance", "tier": "free"},
    {"name": "nse_fii_dii_data", "description": "FII/DII institutional activity", "tier": "free"},
    {"name": "nse_bulk_deals", "description": "Bulk & block deals on NSE", "tier": "free"},
    {"name": "nse_corporate_actions", "description": "Dividends, splits, bonuses", "tier": "free"},
    {"name": "nse_quarterly_results", "description": "Latest quarterly financials with QoQ growth", "tier": "free"},
    {"name": "earnings_calendar", "description": "Upcoming earnings dates", "tier": "free"},
    {"name": "ipo_calendar", "description": "Upcoming & recent IPOs", "tier": "free"},
    # Pro tools
    {"name": "stock_screener", "description": "Screen stocks by P/E, ROE, market cap, sector", "tier": "pro"},
    {"name": "support_resistance", "description": "Pivot points & key price levels", "tier": "pro"},
    {"name": "nse_options_chain", "description": "Options chain with PCR analysis", "tier": "pro"},
    {"name": "portfolio_analysis", "description": "Portfolio P&L, weights, risk analysis", "tier": "pro"},
    {"name": "backtest_strategy", "description": "SMA crossover strategy backtesting", "tier": "pro"},
]

TOTAL_TOOLS = len(TOOL_CATALOG) + 1

# ===== Create the MCP Server =====
mcp = FastMCP("FinStack")

# ===== Register Tool Modules =====
# Week 1: Indian market tools (6 tools)
register_indian_tools(mcp)

# Week 2: Global market tools (8 tools)
from finstack.tools.global_ import register_global_tools
register_global_tools(mcp)

# Week 2: Fundamental analysis tools (6 tools)
from finstack.tools.fundamentals import register_fundamental_tools
register_fundamental_tools(mcp)

# Week 3: AI analytics + advanced Indian tools (15 tools)
from finstack.tools.analytics import register_analytics_tools
register_analytics_tools(mcp)


# ===== Server Info Tool =====
@mcp.tool()
def finstack_info() -> str:
    """Get information about the FinStack MCP server.

    Returns version, available tools, tier status, and usage stats.
    Call this to see what FinStack can do.
    """
    import json
    from finstack import __version__

    return json.dumps({
        "name": "FinStack MCP",
        "version": __version__,
        "description": "Open-source financial data for AI assistants",
        "tier": config.mode.value,
        "tools_available": len(TOOL_CATALOG),
        "tools": TOOL_CATALOG,
        "links": {
            "github": "https://github.com/SpawnAgent/finstack-mcp",
            "website": "https://finstack.dev",
            "pricing": "https://finstack.dev/pricing",
            "docs": "https://github.com/SpawnAgent/finstack-mcp#readme",
        },
        "data_sources": [
            "yfinance (NSE, BSE, US, Crypto — free, no API key)",
            "SEC EDGAR (US filings — free, no API key)",
            "CoinGecko (Crypto — free tier, 30 calls/min)",
        ],
    }, indent=2)


# ===== Entry Point =====
def main():
    """Main entry point for the FinStack MCP server."""
    transport = "stdio"

    # Check for --transport flag
    if "--transport" in sys.argv:
        idx = sys.argv.index("--transport")
        if idx + 1 < len(sys.argv):
            transport = sys.argv[idx + 1]

    # Also support environment variable
    import os
    transport = os.getenv("FINSTACK_TRANSPORT", transport)

    logger.info(f"Starting FinStack MCP server v{__import__('finstack').__version__}")
    logger.info(f"Transport: {transport}")
    logger.info(f"Mode: {config.mode.value}")

    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport in ("http", "streamable-http"):
        mcp.run(
            transport="streamable-http",
            host=config.host,
            port=config.port,
        )
    else:
        logger.error(f"Unknown transport: {transport}")
        sys.exit(1)


def health_check() -> dict:
    """Return server health status — used by Railway/Docker/UptimeRobot."""
    from finstack import __version__
    return {
        "status": "ok",
        "version": __version__,
        "mode": config.mode.value,
        "tools": TOTAL_TOOLS,
    }


if __name__ == "__main__":
    main()
