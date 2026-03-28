"""
FinStack Broker + Credit + ESG MCP Tools

Tool 54: live_quote          — Real-time quote via Angel One SmartAPI (zero delay)
Tool 55: market_depth        — Level 2 order book via Angel One (Zerodha charges ₹500/mo → FREE)
Tool 56: broker_setup_status — Check Angel One integration status + setup guide
Tool 57: credit_ratings      — NSE/BSE credit ratings from SEBI filings (Bloomberg $24k/yr → FREE)
Tool 58: brsr_esg            — BRSR sustainability data from SEBI filings (Bloomberg ESG $24k/yr → FREE)
"""

from finstack.data.broker import get_live_quote_angel, get_market_depth_angel, broker_status
from finstack.data.credit_esg import get_credit_ratings, get_brsr_esg


def register_broker_credit_esg_tools(mcp):
    """Register broker integration + credit + ESG tools."""

    @mcp.tool()
    def live_quote(symbol: str) -> str:
        """Real-time NSE quote via Angel One SmartAPI — zero delay, no yfinance lag.

        Requires Angel One API credentials in your .env file (stays local, never on GitHub).
        Falls back gracefully if not configured, with setup instructions.

        Zerodha Kite Connect charges ₹500/month for real-time data API.
        Angel One SmartAPI is free for account holders.

        Provides (when configured):
        - Live Last Traded Price (LTP) — real-time, zero delay
        - OHLC for the day
        - Volume, average price
        - Upper/lower circuit limits
        - Buy/sell quantity
        - 52-week high/low

        Setup (one-time):
            Add to .env: ANGEL_API_KEY, ANGEL_CLIENT_ID, ANGEL_PASSWORD, ANGEL_TOTP_SECRET
            pip install finstack-mcp[broker]

        Args:
            symbol: NSE symbol (e.g., RELIANCE, TCS, NIFTY, BANKNIFTY)

        Examples:
            live_quote("RELIANCE") → Real-time Reliance price (if Angel One configured)
            live_quote("NIFTY") → Live Nifty index price
        """
        import json
        return json.dumps(get_live_quote_angel(symbol), indent=2)

    @mcp.tool()
    def market_depth(symbol: str) -> str:
        """Level 2 order book depth — top 5 bid/ask prices and quantities.

        This is exchange-licensed real-time data. Zerodha Kite Connect charges
        ₹500/month for this. Angel One SmartAPI provides it free to account holders.

        Requires Angel One API credentials in .env (stays local, never on GitHub).

        Provides (when configured):
        - Top 5 buy orders (bid price + quantity)
        - Top 5 sell orders (ask price + quantity)
        - Total buy and sell queue size

        Args:
            symbol: NSE symbol (e.g., RELIANCE, TCS, HDFCBANK)

        Examples:
            market_depth("RELIANCE") → Live order book for Reliance
        """
        import json
        return json.dumps(get_market_depth_angel(symbol), indent=2)

    @mcp.tool()
    def broker_setup_status() -> str:
        """Check Angel One SmartAPI integration status and get setup instructions.

        Shows whether your Angel One credentials are configured and working.
        Also explains how to set up if not configured yet.

        Your API key stays in your local .env file — never committed to GitHub.
        The open-source code only reads environment variables, never stores keys.

        Examples:
            broker_setup_status() → Check if Angel One is connected + setup guide
        """
        import json
        return json.dumps(broker_status(), indent=2)

    @mcp.tool()
    def credit_ratings(symbol: str) -> str:
        """Credit ratings for an Indian listed company from SEBI-mandated exchange filings.

        SEBI requires all rated instruments to disclose credit rating changes on NSE/BSE.
        Bloomberg charges $24,000/year to access this. SEBI makes it public. We surface it free.

        Provides:
        - Rating agency (CRISIL, ICRA, CARE, India Ratings)
        - Current rating and rating action (upgraded/downgraded/reaffirmed)
        - Instrument type and rated amount
        - Outlook (stable/positive/negative/watch)
        - Filing date

        Args:
            symbol: NSE stock symbol (e.g., RELIANCE, TATAMOTORS, ADANIENT)

        Examples:
            credit_ratings("RELIANCE") → Reliance credit ratings from CRISIL/ICRA
            credit_ratings("ADANIENT") → Adani credit rating history and current outlook
        """
        import json
        return json.dumps(get_credit_ratings(symbol), indent=2)

    @mcp.tool()
    def brsr_esg(symbol: str) -> str:
        """BRSR (Business Responsibility & Sustainability Report) ESG data for listed companies.

        SEBI mandates BRSR from India's top 1000 listed companies since FY2022-23.
        Bloomberg and LSEG charge $24,000+/year for ESG scores.
        SEBI makes BRSR filings publicly available. We surface them free.

        Provides:
        - BRSR filing links (PDF) for last 3-5 years
        - BRSR framework: 9 principles covering ESG topics
        - Environment disclosures (GHG, energy, water, waste)
        - Social disclosures (employees, safety, CSR)
        - Governance disclosures (ethics, stakeholder engagement)
        - Direct links to NSE/BSE BRSR portals

        Args:
            symbol: NSE stock symbol (e.g., RELIANCE, TCS, INFY, HDFCBANK)

        Examples:
            brsr_esg("TCS") → TCS BRSR filings and ESG framework coverage
            brsr_esg("RELIANCE") → Reliance sustainability disclosures
        """
        import json
        return json.dumps(get_brsr_esg(symbol), indent=2)
