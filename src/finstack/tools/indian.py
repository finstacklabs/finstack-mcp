"""
FinStack Indian Market MCP Tools

These are the actual MCP-exposed tools for Indian stock market data.
Each function is decorated with @mcp.tool and has clear docstrings
that Claude/Cursor/ChatGPT use to understand what the tool does.

Week 1 tools (6):
  1. nse_quote        - Real-time NSE stock quote
  2. bse_quote        - Real-time BSE stock quote
  3. nse_market_status - Market open/closed status
  4. nifty_index      - Index values (Nifty, Sensex, Bank Nifty)
  5. nse_historical   - Historical OHLCV data
  6. nse_top_movers   - Top gainers, losers, most active
"""

import json
from finstack.data.nse import (
    get_nse_quote,
    get_bse_quote,
    get_index_data,
    get_historical_data,
    get_market_movers,
    get_market_status,
)
from finstack.data.nse_advanced import (
    get_mutual_fund_nav,
    get_circuit_breakers,
    get_index_components,
    get_52week_scanner,
)


def register_indian_tools(mcp):
    """Register all Indian market tools with the MCP server."""

    @mcp.tool()
    def nse_quote(symbol: str) -> str:
        """Get real-time NSE (National Stock Exchange) quote for an Indian stock.

        Returns current price, change, volume, market cap, P/E ratio, 52-week range,
        sector, and more.

        Args:
            symbol: NSE stock symbol (e.g., RELIANCE, TCS, INFY, HDFCBANK, SBIN, ITC)

        Examples:
            nse_quote("RELIANCE") → Reliance Industries live price & stats
            nse_quote("TCS") → TCS live price & stats
            nse_quote("HDFCBANK") → HDFC Bank live price & stats
        """
        result = get_nse_quote(symbol)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def bse_quote(symbol: str) -> str:
        """Get real-time BSE (Bombay Stock Exchange) quote for an Indian stock.

        Returns current price, change, volume, market cap, and key ratios.

        Args:
            symbol: BSE stock symbol (e.g., RELIANCE, TCS, INFY)

        Examples:
            bse_quote("RELIANCE") → Reliance Industries BSE price
            bse_quote("TCS") → TCS BSE price
        """
        result = get_bse_quote(symbol)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def nse_market_status() -> str:
        """Check if the Indian stock market (NSE/BSE) is currently open or closed.

        Returns market status (OPEN, CLOSED, PRE_OPEN, POST_CLOSE),
        trading hours, and current IST time.

        No arguments needed.

        Examples:
            nse_market_status() → Shows if market is open right now
        """
        result = get_market_status()
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def nifty_index(index_name: str = "NIFTY50") -> str:
        """Get current value of Indian market indices.

        Returns the current value, change, change %, day's high/low,
        and 52-week range for the specified index.

        Args:
            index_name: Index name. Options:
                - NIFTY50 (or NIFTY) - Nifty 50 index
                - SENSEX - BSE Sensex
                - BANKNIFTY - Nifty Bank index
                - NIFTYIT - Nifty IT index
                - NIFTYPHARMA - Nifty Pharma index
                - ALL - Get all major indices at once

        Examples:
            nifty_index("NIFTY50") → Current Nifty 50 value
            nifty_index("SENSEX") → Current Sensex value
            nifty_index("ALL") → All major indices
        """
        result = get_index_data(index_name)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def nse_historical(
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> str:
        """Get historical price data (OHLCV) for an NSE stock.

        Returns open, high, low, close, volume data for the specified period.
        Also includes summary stats: period return %, high, low, avg volume.

        Args:
            symbol: NSE stock symbol (e.g., RELIANCE, TCS, INFY)
            period: Time period. Options: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
            interval: Data interval. Options: 1m, 5m, 15m, 30m, 1h, 1d, 5d, 1wk, 1mo
                      Note: 1m data only available for last 7 days

        Examples:
            nse_historical("RELIANCE", "1mo", "1d") → 1 month daily data
            nse_historical("TCS", "1y", "1wk") → 1 year weekly data
            nse_historical("INFY", "5y", "1mo") → 5 year monthly data
            nse_historical("SBIN", "5d", "15m") → 5 day intraday (15min candles)
        """
        result = get_historical_data(symbol, period, interval)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def nse_top_movers(mover_type: str = "gainers") -> str:
        """Get today's top performing stocks on NSE.

        Returns the top 10 stocks by the specified criteria from Nifty 50 components.

        Args:
            mover_type: Type of movers to fetch. Options:
                - gainers: Top 10 stocks with highest % gain today
                - losers: Top 10 stocks with highest % loss today
                - active: Top 10 stocks by trading volume

        Examples:
            nse_top_movers("gainers") → Today's top gainers
            nse_top_movers("losers") → Today's top losers
            nse_top_movers("active") → Most actively traded stocks
        """
        result = get_market_movers(mover_type)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def mutual_fund_nav(query: str) -> str:
        """Get the latest NAV and details for any Indian mutual fund.

        Searches the AMFI database — no API key required.

        Args:
            query: Fund name (e.g. "SBI Bluechip", "HDFC Flexi Cap") or
                   numeric scheme code (e.g. "119598")

        Examples:
            mutual_fund_nav("SBI Bluechip") → NAV, change, 7-day history
            mutual_fund_nav("Axis Long Term") → ELSS fund NAV
            mutual_fund_nav("119598") → Fetch by scheme code directly
        """
        result = get_mutual_fund_nav(query)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def nse_circuit_breakers(circuit_type: str = "both") -> str:
        """Scan NSE stocks currently hitting upper or lower circuit limits.

        Checks Nifty 500 stocks where the current price is frozen at
        the intraday high (upper circuit) or intraday low (lower circuit).

        Args:
            circuit_type: "upper" (locked at high), "lower" (locked at low),
                          or "both" (default)

        Examples:
            nse_circuit_breakers("upper") → Stocks hitting upper circuit today
            nse_circuit_breakers("lower") → Stocks hitting lower circuit today
            nse_circuit_breakers("both")  → All circuit-locked stocks
        """
        result = get_circuit_breakers(circuit_type)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def sensex_components(index_name: str = "nifty50") -> str:
        """Get the list of stocks in Nifty 50 or Sensex with live prices.

        Returns all constituent stocks with current price, % change today,
        market cap, plus top 5 gainers and losers within the index.

        Args:
            index_name: "nifty50" (default) or "sensex"

        Examples:
            sensex_components("nifty50")  → All 50 Nifty stocks with live prices
            sensex_components("sensex")   → All 30 Sensex stocks with live prices
        """
        result = get_index_components(index_name)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def nse_52week_scanner(scan_type: str = "near_high", threshold_pct: float = 5.0) -> str:
        """Scan Nifty 50 stocks near their 52-week high or low.

        This is the most popular scan on Screener.in — stocks breaking out
        near 52-week highs are momentum candidates; those near 52-week lows
        may be value opportunities or falling knives.

        Args:
            scan_type:     "near_high" — stocks within threshold% of 52w high (default)
                           "near_low"  — stocks within threshold% of 52w low
                           "both"      — return both lists
            threshold_pct: Closeness threshold in % (default 5.0 = within 5% of extreme)

        Examples:
            nse_52week_scanner("near_high", 5)  → Stocks near all-time high area
            nse_52week_scanner("near_low", 10)  → Stocks near 52-week low
            nse_52week_scanner("both", 3)        → Very tight near both extremes
        """
        result = get_52week_scanner(scan_type, threshold_pct)
        return json.dumps(result, indent=2, default=str)
