"""
FinStack Analytics + Advanced Indian MCP Tools

Week 3 tools (15):
  21. stock_screener         - Screen stocks by financial criteria (PRO)
  22. compare_stocks         - Side-by-side comparison
  23. technical_indicators   - RSI, MACD, SMA, Bollinger, etc.
  24. support_resistance     - Key support & resistance levels (PRO)
  25. sector_performance     - Sector-wise performance
  26. portfolio_analysis     - Portfolio risk & return (PRO)
  27. backtest_strategy      - SMA crossover backtest (PRO)
  28. earnings_calendar      - Upcoming earnings dates
  29. ipo_calendar           - Upcoming IPOs
  30. nse_options_chain      - Options chain + PCR (PRO)
  31. nse_fii_dii_data       - FII/DII activity
  32. nse_bulk_deals         - Bulk & block deals
  33. nse_corporate_actions  - Dividends, splits, bonuses
  34. nse_quarterly_results  - Latest quarterly financials
"""

import json
from finstack.config import config, UserTier
from finstack.utils.helpers import tier_locked_error

from finstack.data.analytics import (
    compute_technical_indicators,
    compute_support_resistance,
    screen_stocks,
    compare_stocks,
    get_sector_performance,
    analyze_portfolio,
    backtest_sma_crossover,
)

from finstack.data.nse_advanced import (
    get_options_chain,
    get_fii_dii_data,
    get_bulk_deals,
    get_corporate_actions,
    get_quarterly_results,
    get_earnings_calendar,
    get_ipo_calendar,
)


def register_analytics_tools(mcp):
    """Register all analytics + advanced Indian tools with the MCP server."""

    # ===== FREE TOOLS =====

    @mcp.tool()
    def technical_indicators(
        symbol: str,
        period: str = "6mo",
        indicators: str = "",
    ) -> str:
        """Compute technical indicators for a stock with buy/sell signals.

        Calculates RSI, MACD, SMA (20/50/200), EMA, Bollinger Bands, ATR,
        Stochastic, ADX, OBV — all computed locally, no API cost.

        Works for Indian (NSE/BSE) and US stocks.

        Args:
            symbol: Stock ticker (e.g., RELIANCE, TCS, AAPL, TSLA)
            period: Data period for calculation: 3mo, 6mo, 1y, 2y (default: 6mo)
            indicators: Comma-separated list of specific indicators.
                        Options: RSI, MACD, SMA, EMA, BBANDS, ATR, STOCH, ADX, OBV
                        Leave empty for ALL indicators.

        Examples:
            technical_indicators("RELIANCE") → All indicators for Reliance
            technical_indicators("AAPL", "1y") → Apple with 1 year data
            technical_indicators("TCS", "6mo", "RSI,MACD,SMA") → Only RSI, MACD, SMA
        """
        ind_list = [i.strip() for i in indicators.split(",") if i.strip()] or None
        result = compute_technical_indicators(symbol, period, ind_list)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def compare_stocks_tool(symbols: str) -> str:
        """Compare 2-5 stocks side by side.

        Shows price, P/E, P/B, ROE, profit margin, revenue growth,
        debt/equity, dividend yield, beta, sector, and 52-week range
        for each stock in a comparison table format.

        Args:
            symbols: Comma-separated stock symbols (2-5 stocks).
                     e.g., "RELIANCE,TCS,INFY" or "AAPL,MSFT,GOOGL"

        Examples:
            compare_stocks_tool("RELIANCE,TCS,INFY") → Compare 3 Indian IT giants
            compare_stocks_tool("AAPL,MSFT,GOOGL,AMZN") → Compare US tech
            compare_stocks_tool("HDFCBANK,ICICIBANK,SBIN,KOTAKBANK") → Compare banks
        """
        sym_list = [s.strip() for s in symbols.split(",") if s.strip()]
        result = compare_stocks(sym_list)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def sector_performance() -> str:
        """Get performance of Nifty sectoral indices.

        Shows how different sectors (Banking, IT, Pharma, FMCG, Auto, Metal,
        Realty, Energy) performed today, with best and worst performers highlighted.

        No arguments needed.

        Examples:
            sector_performance() → Which sectors are up/down today?
        """
        result = get_sector_performance()
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def nse_fii_dii_data() -> str:
        """Get FII (Foreign Institutional Investor) and DII (Domestic Institutional Investor)
        activity data.

        Shows how much foreign and domestic institutions bought/sold today.
        FII net buy = bullish signal. DII net buy = domestic accumulation.

        No arguments needed.

        Examples:
            nse_fii_dii_data() → Today's FII/DII activity
        """
        result = get_fii_dii_data()
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def nse_bulk_deals() -> str:
        """Get recent bulk and block deals on NSE.

        Shows large transactions where quantity traded exceeds 0.5% of total
        shares. Useful for tracking institutional activity.

        No arguments needed.

        Examples:
            nse_bulk_deals() → Recent bulk/block deals
        """
        result = get_bulk_deals()
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def nse_corporate_actions(symbol: str) -> str:
        """Get corporate actions for an NSE stock — dividends, stock splits, bonuses.

        Shows recent and historical corporate actions with dates and values.

        Args:
            symbol: NSE stock symbol (e.g., ITC, RELIANCE, TCS, COALINDIA)

        Examples:
            nse_corporate_actions("ITC") → ITC dividends and splits
            nse_corporate_actions("RELIANCE") → Reliance corporate actions
        """
        result = get_corporate_actions(symbol)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def nse_quarterly_results(symbol: str) -> str:
        """Get latest quarterly financial results for an NSE stock.

        Shows revenue, profit, EPS, EBITDA for last 4 quarters with
        quarter-over-quarter growth rates.

        Args:
            symbol: NSE stock symbol (e.g., RELIANCE, TCS, INFY, HDFCBANK)

        Examples:
            nse_quarterly_results("RELIANCE") → Reliance Q results
            nse_quarterly_results("TCS") → TCS quarterly financials
        """
        result = get_quarterly_results(symbol)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def earnings_calendar(symbol: str = "") -> str:
        """Get upcoming earnings dates for a stock.

        Shows when a company is expected to report earnings, along with
        analyst estimates (EPS and revenue).

        Args:
            symbol: Stock ticker (e.g., RELIANCE, AAPL). Required.

        Examples:
            earnings_calendar("RELIANCE") → When does Reliance report next?
            earnings_calendar("AAPL") → Apple earnings date
        """
        result = get_earnings_calendar(symbol)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def ipo_calendar() -> str:
        """Get upcoming and recent IPOs on NSE.

        Shows company name, price band, dates, issue size, and status.

        No arguments needed.

        Examples:
            ipo_calendar() → What IPOs are coming up?
        """
        result = get_ipo_calendar()
        return json.dumps(result, indent=2, default=str)

    # ===== PRO TOOLS (locked for free users) =====

    @mcp.tool()
    def stock_screener(
        exchange: str = "NSE",
        pe_max: float = 0,
        pe_min: float = 0,
        roe_min: float = 0,
        market_cap_min: float = 0,
        dividend_yield_min: float = 0,
        debt_equity_max: float = 0,
        sector: str = "",
        limit: int = 15,
    ) -> str:
        """Screen stocks by multiple financial criteria. [PRO]

        Filter Nifty 50 or S&P 500 stocks by P/E ratio, ROE, market cap,
        dividend yield, debt/equity ratio, and sector.

        Args:
            exchange: "NSE" for Indian stocks, "US" for US stocks (default: NSE)
            pe_max: Maximum P/E ratio (e.g., 15 for value stocks). 0 = no filter.
            pe_min: Minimum P/E ratio. 0 = no filter.
            roe_min: Minimum Return on Equity in % (e.g., 20). 0 = no filter.
            market_cap_min: Minimum market cap in USD (e.g., 1000000000 for $1B). 0 = no filter.
            dividend_yield_min: Minimum dividend yield in % (e.g., 2). 0 = no filter.
            debt_equity_max: Maximum debt-to-equity ratio (e.g., 50). 0 = no filter.
            sector: Filter by sector name (e.g., "Technology", "Financial"). Empty = all.
            limit: Max number of results (default: 15)

        Examples:
            stock_screener("NSE", pe_max=15, roe_min=20) → Value stocks with high ROE
            stock_screener("NSE", dividend_yield_min=3) → High dividend yield stocks
            stock_screener("US", pe_max=20, sector="Technology") → Cheap US tech stocks
        """
        if not config.is_tool_allowed("stock_screener"):
            return json.dumps(tier_locked_error("stock_screener"), indent=2)

        result = screen_stocks(
            exchange=exchange,
            pe_max=pe_max if pe_max > 0 else None,
            pe_min=pe_min if pe_min > 0 else None,
            roe_min=roe_min if roe_min > 0 else None,
            market_cap_min=market_cap_min if market_cap_min > 0 else None,
            dividend_yield_min=dividend_yield_min if dividend_yield_min > 0 else None,
            debt_equity_max=debt_equity_max if debt_equity_max > 0 else None,
            sector=sector if sector else None,
            limit=min(limit, 25),
        )
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def support_resistance(symbol: str, period: str = "6mo") -> str:
        """Compute support and resistance levels for a stock. [PRO]

        Calculates pivot points (R1, R2, R3, S1, S2, S3) and identifies
        key price levels from historical price action.

        Args:
            symbol: Stock ticker (e.g., RELIANCE, AAPL, TCS)
            period: Data period: 3mo, 6mo, 1y, 2y (default: 6mo)

        Examples:
            support_resistance("RELIANCE") → Key levels for Reliance
            support_resistance("AAPL", "1y") → Apple support/resistance with 1yr data
        """
        if not config.is_tool_allowed("support_resistance"):
            return json.dumps(tier_locked_error("support_resistance"), indent=2)

        result = compute_support_resistance(symbol, period)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def nse_options_chain(symbol: str) -> str:
        """Get options chain data for an NSE stock or index. [PRO]

        Returns call and put options with strike price, premium, volume,
        open interest, implied volatility, and Put-Call Ratio (PCR).

        Args:
            symbol: NSE stock or index symbol (e.g., RELIANCE, NIFTY, BANKNIFTY, TCS)

        Examples:
            nse_options_chain("RELIANCE") → Reliance options chain
            nse_options_chain("NIFTY") → Nifty 50 options chain
            nse_options_chain("BANKNIFTY") → Bank Nifty options
        """
        if not config.is_tool_allowed("nse_options_chain"):
            return json.dumps(tier_locked_error("nse_options_chain"), indent=2)

        result = get_options_chain(symbol)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def portfolio_analysis(holdings: str) -> str:
        """Analyze a stock portfolio — P&L, weights, risk. [PRO]

        Provide your holdings and get total P&L, individual stock performance,
        portfolio weights, concentration risk, winners and losers.

        Args:
            holdings: JSON string of holdings array. Each holding needs:
                      symbol, quantity, buy_price.
                      Example: '[{"symbol":"RELIANCE","quantity":10,"buy_price":2500},
                                 {"symbol":"TCS","quantity":5,"buy_price":3800}]'

        Examples:
            portfolio_analysis('[{"symbol":"RELIANCE","quantity":10,"buy_price":2500}]')
            portfolio_analysis('[{"symbol":"AAPL","quantity":5,"buy_price":150},
                                {"symbol":"MSFT","quantity":3,"buy_price":380}]')
        """
        if not config.is_tool_allowed("portfolio_analysis"):
            return json.dumps(tier_locked_error("portfolio_analysis"), indent=2)

        try:
            holdings_list = json.loads(holdings)
            if not isinstance(holdings_list, list):
                return json.dumps({
                    "error": True,
                    "message": "Holdings must be a JSON array.",
                    "example": '[{"symbol":"RELIANCE","quantity":10,"buy_price":2500}]'
                }, indent=2)
        except json.JSONDecodeError as e:
            return json.dumps({
                "error": True,
                "message": f"Invalid JSON: {str(e)}",
                "example": '[{"symbol":"RELIANCE","quantity":10,"buy_price":2500}]'
            }, indent=2)

        result = analyze_portfolio(holdings_list)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def backtest_strategy(
        symbol: str,
        short_window: int = 20,
        long_window: int = 50,
        period: str = "2y",
        initial_capital: float = 100000,
    ) -> str:
        """Backtest a Simple Moving Average (SMA) crossover strategy. [PRO]

        Tests: Buy when short SMA crosses above long SMA, sell when it crosses below.
        Compares strategy return vs buy-and-hold.

        Args:
            symbol: Stock ticker (e.g., RELIANCE, AAPL, TCS)
            short_window: Short SMA period in days (default: 20)
            long_window: Long SMA period in days (default: 50)
            period: Backtest period: 1y, 2y, 5y (default: 2y)
            initial_capital: Starting capital (default: 100000)

        Examples:
            backtest_strategy("RELIANCE") → Default 20/50 SMA backtest
            backtest_strategy("AAPL", 10, 30, "5y") → Custom 10/30 SMA, 5 years
            backtest_strategy("TCS", 50, 200, "5y", 500000) → Golden cross, 5L capital
        """
        if not config.is_tool_allowed("backtest_strategy"):
            return json.dumps(tier_locked_error("backtest_strategy"), indent=2)

        result = backtest_sma_crossover(symbol, short_window, long_window, period, initial_capital)
        return json.dumps(result, indent=2, default=str)
