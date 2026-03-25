"""
FinStack Global Market MCP Tools

Week 2 tools (8):
  7. stock_quote       - Global stock quote (US, EU, Asia)
  8. stock_historical  - Global historical OHLCV
  9. crypto_price      - Live crypto prices
  10. crypto_historical - Historical crypto data
  11. forex_rate        - Live forex exchange rates
  12. sec_filing        - SEC filings for US companies
  13. market_news       - Market news by ticker or general
  14. sec_filing_search - Search SEC by company
"""

import json
from finstack.data.global_markets import (
    get_global_quote,
    get_global_historical,
    get_crypto_price,
    get_crypto_historical,
    get_forex_rate,
    get_market_news,
    get_sec_filings,
)


def register_global_tools(mcp):
    """Register all global market tools with the MCP server."""

    @mcp.tool()
    def stock_quote(symbol: str) -> str:
        """Get real-time stock quote for any global stock.

        Works for US, UK, European, Asian, and Indian stocks.
        Returns price, change, volume, market cap, P/E, sector, country, and more.

        Args:
            symbol: Stock ticker symbol. Formats:
                - US stocks: AAPL, MSFT, GOOGL, TSLA, AMZN
                - UK stocks: HSBA.L, BP.L, VOD.L
                - Japan: 7203.T (Toyota), 6758.T (Sony)
                - Hong Kong: 0700.HK (Tencent)
                - India: RELIANCE.NS, TCS.NS (use nse_quote for Indian stocks)

        Examples:
            stock_quote("AAPL") → Apple live price
            stock_quote("MSFT") → Microsoft live price
            stock_quote("TSLA") → Tesla live price
        """
        result = get_global_quote(symbol)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def stock_historical(
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> str:
        """Get historical price data for any global stock.

        Returns OHLCV data with summary stats.

        Args:
            symbol: Stock ticker (e.g., AAPL, MSFT, TSLA)
            period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
            interval: 1m, 5m, 15m, 30m, 1h, 1d, 5d, 1wk, 1mo

        Examples:
            stock_historical("AAPL", "1y", "1d") → Apple 1 year daily
            stock_historical("TSLA", "3mo", "1wk") → Tesla 3 month weekly
        """
        result = get_global_historical(symbol, period, interval)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def crypto_price(symbol: str) -> str:
        """Get live cryptocurrency price in USD.

        Returns current price, 24h change, market cap, volume, and all-time high.

        Args:
            symbol: Crypto ticker (e.g., BTC, ETH, SOL, XRP, DOGE, ADA, MATIC, DOT)

        Examples:
            crypto_price("BTC") → Bitcoin live price
            crypto_price("ETH") → Ethereum live price
            crypto_price("SOL") → Solana live price
        """
        result = get_crypto_price(symbol)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def crypto_historical(
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> str:
        """Get historical cryptocurrency price data.

        Args:
            symbol: Crypto ticker (e.g., BTC, ETH, SOL)
            period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max
            interval: 1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo

        Examples:
            crypto_historical("BTC", "1y", "1d") → Bitcoin 1 year daily
            crypto_historical("ETH", "3mo", "1wk") → Ethereum 3 month weekly
        """
        result = get_crypto_historical(symbol, period, interval)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def forex_rate(from_currency: str, to_currency: str = "INR") -> str:
        """Get live forex exchange rate between two currencies.

        Returns current rate, day's change, high/low, and 52-week range.

        Args:
            from_currency: Source currency code (e.g., USD, EUR, GBP, AED, JPY)
            to_currency: Target currency code (default: INR)

        Examples:
            forex_rate("USD", "INR") → US Dollar to Indian Rupee
            forex_rate("EUR", "INR") → Euro to Indian Rupee
            forex_rate("AED", "INR") → UAE Dirham to Indian Rupee
            forex_rate("USD", "EUR") → US Dollar to Euro
            forex_rate("GBP", "USD") → British Pound to US Dollar
        """
        result = get_forex_rate(from_currency, to_currency)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def market_news(symbol: str = "") -> str:
        """Get latest market news for a stock or general market.

        Returns up to 10 recent news articles with title, publisher, and link.

        Args:
            symbol: Stock ticker for company-specific news (optional).
                    Leave empty for general market news.

        Examples:
            market_news("AAPL") → Apple-related news
            market_news("RELIANCE.NS") → Reliance Industries news
            market_news() → General market news
        """
        result = get_market_news(symbol)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def sec_filing(
        symbol: str,
        filing_type: str = "10-K",
        count: int = 5,
    ) -> str:
        """Get SEC filings for a US-listed company.

        Returns links to actual filing documents on SEC EDGAR.

        Args:
            symbol: US stock ticker (e.g., AAPL, MSFT, GOOGL)
            filing_type: Type of filing. Options:
                - 10-K: Annual report
                - 10-Q: Quarterly report
                - 8-K: Current events report
                - ALL: All filing types
            count: Number of filings to return (default: 5, max: 20)

        Examples:
            sec_filing("AAPL", "10-K") → Apple annual reports
            sec_filing("TSLA", "10-Q", 3) → Tesla last 3 quarterly reports
            sec_filing("MSFT", "ALL", 10) → Microsoft all recent filings
        """
        count = min(max(1, count), 20)
        result = get_sec_filings(symbol, filing_type, count)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def sec_filing_search(symbol: str) -> str:
        """Search SEC EDGAR for a company and get their filing page.

        Returns company info (CIK number) and link to their SEC filings page.
        Use sec_filing() to get specific filing documents.

        Args:
            symbol: US stock ticker (e.g., AAPL, MSFT, GOOGL)

        Examples:
            sec_filing_search("AAPL") → Find Apple on SEC EDGAR
            sec_filing_search("NVDA") → Find NVIDIA on SEC EDGAR
        """
        # Just get 1 filing to confirm company exists and return CIK
        result = get_sec_filings(symbol, "10-K", 1)
        if result.get("error"):
            return json.dumps(result, indent=2, default=str)

        return json.dumps({
            "symbol": result.get("symbol"),
            "company": result.get("company"),
            "cik": result.get("cik"),
            "sec_page": result.get("sec_page"),
            "message": f"Found {result.get('company')} on SEC EDGAR. Use sec_filing() to get specific filings.",
        }, indent=2, default=str)
