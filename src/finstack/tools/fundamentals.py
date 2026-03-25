"""
FinStack Fundamentals MCP Tools

Week 2 tools (6):
  15. income_statement   - Annual/quarterly P&L
  16. balance_sheet      - Annual/quarterly balance sheet
  17. cash_flow          - Annual/quarterly cash flow
  18. key_ratios         - P/E, ROE, debt/equity, margins, growth
  19. company_profile    - Company overview, sector, description
  20. dividend_history   - Historical dividend payments
"""

import json
from finstack.data.fundamentals import (
    get_income_statement,
    get_balance_sheet,
    get_cash_flow,
    get_key_ratios,
    get_company_profile,
    get_dividend_history,
)


def register_fundamental_tools(mcp):
    """Register all fundamental analysis tools with the MCP server."""

    @mcp.tool()
    def income_statement(symbol: str, quarterly: bool = False) -> str:
        """Get income statement (Profit & Loss) for a company.

        Returns revenue, COGS, gross profit, operating income, net income,
        EPS, EBITDA, and other P&L line items.

        Works for both Indian (NSE/BSE) and US stocks.

        Args:
            symbol: Stock ticker (e.g., RELIANCE, TCS, AAPL, MSFT)
            quarterly: If True, returns quarterly data. If False (default), annual data.

        Examples:
            income_statement("RELIANCE") → Reliance annual P&L (last 4 years)
            income_statement("TCS", quarterly=True) → TCS quarterly P&L
            income_statement("AAPL") → Apple annual P&L
        """
        result = get_income_statement(symbol, quarterly)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def balance_sheet(symbol: str, quarterly: bool = False) -> str:
        """Get balance sheet for a company.

        Returns total assets, total liabilities, shareholder equity,
        cash, debt, inventory, receivables, and more.

        Args:
            symbol: Stock ticker (e.g., RELIANCE, TCS, AAPL, MSFT)
            quarterly: If True, quarterly data. If False (default), annual.

        Examples:
            balance_sheet("HDFCBANK") → HDFC Bank annual balance sheet
            balance_sheet("AAPL", quarterly=True) → Apple quarterly balance sheet
        """
        result = get_balance_sheet(symbol, quarterly)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def cash_flow(symbol: str, quarterly: bool = False) -> str:
        """Get cash flow statement for a company.

        Returns operating cash flow, investing cash flow, financing cash flow,
        free cash flow, capital expenditure, and more.

        Args:
            symbol: Stock ticker (e.g., INFY, SBIN, GOOGL, AMZN)
            quarterly: If True, quarterly data. If False (default), annual.

        Examples:
            cash_flow("INFY") → Infosys annual cash flow
            cash_flow("GOOGL", quarterly=True) → Google quarterly cash flow
        """
        result = get_cash_flow(symbol, quarterly)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def key_ratios(symbol: str) -> str:
        """Get key financial ratios and valuation metrics for a company.

        Returns comprehensive metrics organized into categories:
        - Valuation: P/E, P/B, EV/EBITDA, PEG ratio, price-to-sales
        - Profitability: ROE, ROA, profit margin, operating margin, gross margin
        - Growth: Revenue growth, earnings growth
        - Financial Health: Debt/equity, current ratio, quick ratio, free cash flow
        - Per Share: EPS, book value, revenue per share
        - Dividend: Yield, payout ratio, ex-dividend date

        Works for both Indian and US stocks.

        Args:
            symbol: Stock ticker (e.g., RELIANCE, TCS, AAPL, MSFT)

        Examples:
            key_ratios("RELIANCE") → Reliance complete ratio analysis
            key_ratios("AAPL") → Apple valuation & financial metrics
            key_ratios("HDFCBANK") → HDFC Bank financial health check
        """
        result = get_key_ratios(symbol)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def company_profile(symbol: str) -> str:
        """Get company overview and profile information.

        Returns company name, sector, industry, country, number of employees,
        website, business description, exchange, and market cap.

        Args:
            symbol: Stock ticker (e.g., RELIANCE, TCS, AAPL, MSFT)

        Examples:
            company_profile("RELIANCE") → What does Reliance Industries do?
            company_profile("TSLA") → Tesla company overview
            company_profile("INFY") → Infosys company details
        """
        result = get_company_profile(symbol)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def dividend_history(symbol: str) -> str:
        """Get historical dividend payments for a stock.

        Returns past dividend dates and amounts, total dividends paid,
        average dividend, and latest dividend info.

        Args:
            symbol: Stock ticker (e.g., ITC, COALINDIA, AAPL, MSFT)

        Examples:
            dividend_history("ITC") → ITC dividend payment history
            dividend_history("COALINDIA") → Coal India dividends
            dividend_history("AAPL") → Apple dividend history
        """
        result = get_dividend_history(symbol)
        return json.dumps(result, indent=2, default=str)
