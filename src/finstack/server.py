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
]

TOTAL_TOOLS = len(TOOL_CATALOG) + 1

mcp = FastMCP("FinStack")

register_indian_tools(mcp)

from finstack.tools.analytics import register_analytics_tools
from finstack.tools.fundamentals import register_fundamental_tools
from finstack.tools.global_ import register_global_tools
from finstack.tools.tax import register_tax_tools

register_global_tools(mcp)
register_fundamental_tools(mcp)
register_analytics_tools(mcp)
register_tax_tools(mcp)


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
