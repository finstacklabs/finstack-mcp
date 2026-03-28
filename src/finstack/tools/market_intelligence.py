"""
FinStack Market Intelligence MCP Tools

Tool 41: options_oi_analytics    — Max Pain, PCR, IV heatmap  [Sensibull Pro ₹1,300/mo → FREE]
Tool 42: options_greeks          — Delta, Gamma, Theta, Vega  [Sensibull Pro ₹1,300/mo → FREE]
Tool 43: nse_insider_trading     — SAST insider disclosures   [Trendlyne ₹4,950/yr → FREE]
Tool 44: promoter_shareholding   — Promoter/FII/DII pattern   [Screener Pro ₹4,999/yr → FREE]
Tool 45: rbi_policy_rates        — Repo, CRR, SLR, MSF        [Bloomberg $24,000/yr → FREE]
Tool 46: india_macro_indicators  — CPI, GDP, current account  [Bloomberg $24,000/yr → FREE]
Tool 47: amfi_fund_flows         — MF industry AUM & flows    [Morningstar $17,500/yr → FREE]
Tool 48: india_gsec_yields       — G-Sec yield curve          [Bloomberg $24,000/yr → FREE]
Tool 49: india_vix               — Fear index + history       [Trendlyne paid → FREE]
Tool 50: gift_nifty              — Pre-market + global indices [Bloomberg paid → FREE]
Tool 51: promoter_pledge         — Pledge % risk signal       [Screener Pro ₹4,999/yr → FREE]
Tool 52: dividend_history_deep   — 10-year dividends + yield  [Bloomberg/FactSet paid → FREE]
Tool 53: nifty_pcr_trend         — PCR across all expiries    [Sensibull ₹1,300/mo → FREE]
"""

from finstack.data.market_intelligence import (
    get_options_oi_analytics,
    get_options_greeks,
    get_insider_trading,
    get_promoter_shareholding,
    get_rbi_policy_rates,
    get_india_macro_indicators,
    get_amfi_fund_flows,
    get_india_gsec_yields,
    get_india_vix,
    get_gift_nifty,
    get_promoter_pledge,
    get_dividend_history_deep,
    get_nifty_pcr_trend,
)


def register_market_intelligence_tools(mcp):
    """Register all Market Intelligence tools with the MCP server."""

    @mcp.tool()
    def options_oi_analytics(symbol: str) -> str:
        """Advanced options OI analytics: Max Pain, PCR trend, IV summary, top OI strikes.

        Covers features Sensibull Pro charges ₹1,300/month for — free here.

        Provides:
        - Put-Call Ratio (OI and Volume) with sentiment signal
        - Max Pain calculation (price gravity at expiry)
        - Top call OI strikes (resistance levels from options market)
        - Top put OI strikes (support levels from options market)
        - Average IV across expiry
        - Analysis for 3 nearest expiries

        Args:
            symbol: NSE stock or index symbol (e.g., NIFTY, BANKNIFTY, RELIANCE, TCS)

        Examples:
            options_oi_analytics("NIFTY") → Nifty OI analytics, Max Pain, PCR
            options_oi_analytics("RELIANCE") → Reliance OI analysis
            options_oi_analytics("BANKNIFTY") → Bank Nifty options sentiment
        """
        import json
        return json.dumps(get_options_oi_analytics(symbol), indent=2)

    @mcp.tool()
    def options_greeks(symbol: str, expiry: str = None) -> str:
        """Calculate Black-Scholes Greeks (Delta, Gamma, Theta, Vega, Rho) for all option strikes.

        Covers features Sensibull Pro charges ₹1,300/month for — free here.

        Provides:
        - Delta: price sensitivity to underlying move
        - Gamma: rate of change of delta (acceleration)
        - Theta: daily time decay (what options lose per day)
        - Vega: sensitivity to 1% change in implied volatility
        - Rho: sensitivity to 1% change in interest rate
        - Full chain with Greeks for both calls and puts

        Args:
            symbol: NSE stock or index symbol (e.g., NIFTY, RELIANCE, INFY)
            expiry: Optional expiry date string YYYY-MM-DD (uses nearest if not provided)

        Examples:
            options_greeks("NIFTY") → Full Greeks for nearest Nifty expiry
            options_greeks("RELIANCE", "2025-04-24") → Greeks for specific expiry
        """
        import json
        return json.dumps(get_options_greeks(symbol, expiry), indent=2)

    @mcp.tool()
    def nse_insider_trading(symbol: str, days: int = 90) -> str:
        """NSE insider trading and SAST (substantial acquisition) disclosures for a stock.

        Covers features Trendlyne (₹4,950/yr) and Screener Pro (₹4,999/yr) charge for — free here.

        Shows:
        - All SEBI-mandated insider trading disclosures from NSE
        - Buy vs sell transaction count
        - Insider sentiment summary
        - Acquirer/seller name, shares traded, dates

        Args:
            symbol: NSE stock symbol (e.g., RELIANCE, TCS, INFY, HDFCBANK)
            days: Lookback period in days (default 90, max ~365)

        Examples:
            nse_insider_trading("RELIANCE") → Last 90 days insider activity for Reliance
            nse_insider_trading("TCS", 180) → Last 6 months insider trades for TCS
        """
        import json
        return json.dumps(get_insider_trading(symbol, days), indent=2)

    @mcp.tool()
    def promoter_shareholding(symbol: str) -> str:
        """Shareholding pattern for an NSE stock: promoter, FII, DII, public breakdown.

        Covers features Screener.in Pro (₹4,999/yr) and Trendlyne charge for — free here.

        Shows:
        - Promoter holding percentage
        - FII (Foreign Institutional Investor) holding
        - DII (Domestic Institutional Investor) holding
        - Public / retail holding
        - Top institutional and mutual fund holders

        Args:
            symbol: NSE stock symbol (e.g., RELIANCE, TCS, INFY, HDFCBANK)

        Examples:
            promoter_shareholding("RELIANCE") → Who owns Reliance and how much
            promoter_shareholding("HDFCBANK") → HDFC Bank ownership breakdown
        """
        import json
        return json.dumps(get_promoter_shareholding(symbol), indent=2)

    @mcp.tool()
    def rbi_policy_rates() -> str:
        """Current RBI monetary policy rates: Repo, Reverse Repo, CRR, SLR, MSF, Bank Rate.

        Bloomberg Terminal charges $31,980/year for central bank data access.
        RBI publishes all policy rates free on rbi.org.in — we surface them here.

        Provides:
        - Repo rate (current RBI lending rate to banks)
        - Reverse repo rate
        - Marginal Standing Facility (MSF) rate
        - Cash Reserve Ratio (CRR)
        - Statutory Liquidity Ratio (SLR)
        - Bank Rate
        - Monetary policy stance
        - Last policy action summary

        Examples:
            rbi_policy_rates() → All current RBI policy rates and stance
        """
        import json
        return json.dumps(get_rbi_policy_rates(), indent=2)

    @mcp.tool()
    def india_macro_indicators() -> str:
        """India macroeconomic indicators: CPI inflation, GDP growth, current account, unemployment.

        Bloomberg and Refinitiv charge $24,000–$32,000/year for macro data access.
        World Bank publishes India macro data free — we surface it here.

        Provides:
        - CPI inflation (latest and previous year)
        - GDP growth rate
        - Current account balance as % of GDP
        - Unemployment rate
        - Gross capital formation
        - RBI inflation target and tolerance band

        Examples:
            india_macro_indicators() → Latest India macro data from World Bank
        """
        import json
        return json.dumps(get_india_macro_indicators(), indent=2)

    @mcp.tool()
    def amfi_fund_flows() -> str:
        """AMFI mutual fund industry data: total AUM, SIP flows, scheme count by category.

        Morningstar Direct charges $17,500/year for mutual fund flow data.
        AMFI (Association of Mutual Funds in India) publishes all data free.

        Provides:
        - Total industry AUM (approximate)
        - Monthly SIP inflow figures
        - Total folios and investor count
        - Scheme breakdown by category (Equity, Debt, Hybrid, ETF, ELSS, etc.)
        - Links to detailed AMFI data portal

        Examples:
            amfi_fund_flows() → India mutual fund industry overview and flows
        """
        import json
        return json.dumps(get_amfi_fund_flows(), indent=2)

    @mcp.tool()
    def india_gsec_yields() -> str:
        """India Government Securities (G-Sec) yield curve: 91-day T-bill to 30-year bond.

        Bloomberg Terminal charges $31,980/year for government bond data.
        RBI and CCIL publish India G-Sec yields free.

        Provides:
        - 91-day, 182-day, 364-day T-bill yields
        - 5-year, 10-year, 30-year G-Sec yields
        - Real interest rate (World Bank)
        - Live data source links (CCIL, RBI)

        Examples:
            india_gsec_yields() → Current India government bond yield curve
        """
        import json
        return json.dumps(get_india_gsec_yields(), indent=2)

    @mcp.tool()
    def india_vix(days: int = 30) -> str:
        """India VIX — the NSE fear/volatility index with history and signal.

        Trendlyne charges for historical India VIX data. NSE publishes it free via ^INDIAVIX.

        Provides:
        - Current VIX level and daily change
        - Signal: low fear / elevated / panic zone
        - 30-day high, low, average
        - Full daily history for the requested period
        - Interpretation guide (what VIX levels mean for markets)

        Args:
            days: Lookback period in days (default 30)

        Examples:
            india_vix() → Current India VIX with signal and 30-day history
            india_vix(90) → 90-day VIX history for trend analysis
        """
        import json
        return json.dumps(get_india_vix(days), indent=2)

    @mcp.tool()
    def gift_nifty() -> str:
        """GIFT Nifty pre-market data + overnight global indices for Indian market preview.

        Bloomberg charges for global futures data. This is free.

        Provides:
        - Nifty 50 last close and change
        - Global indices overnight performance (S&P 500, Dow, NASDAQ, Hang Seng)
        - Market status from NSE
        - Links to live GIFT Nifty sources

        Examples:
            gift_nifty() → Pre-market global sentiment + Nifty reference
        """
        import json
        return json.dumps(get_gift_nifty(), indent=2)

    @mcp.tool()
    def promoter_pledge(symbol: str) -> str:
        """Promoter pledge percentage — how much of promoter holding is pledged as loan collateral.

        Screener.in Pro (₹4,999/yr) charges for this data. NSE publishes it free.

        High pledge = risk signal: if the stock falls, lenders can force-sell pledged shares,
        causing further decline. A key red flag before investing.

        Provides:
        - Promoter pledge % of total shares
        - Pledge % of promoter holding
        - Risk signal (clean / low / moderate / HIGH RISK)
        - Quarter-wise breakdown

        Args:
            symbol: NSE stock symbol (e.g., RELIANCE, TCS, ADANIENT)

        Examples:
            promoter_pledge("ADANIENT") → Adani pledge levels and risk signal
            promoter_pledge("RELIANCE") → Reliance promoter pledge status
        """
        import json
        return json.dumps(get_promoter_pledge(symbol), indent=2)

    @mcp.tool()
    def dividend_history_deep(symbol: str) -> str:
        """10-year dividend history with yield calculation and annual summary.

        Bloomberg and FactSet charge for deep dividend history. yfinance has it free.

        Provides:
        - Full dividend payment history (up to 60 entries)
        - Annual dividend totals per year (last 10 years)
        - Trailing 12-month dividend yield %
        - Total dividends on record

        Args:
            symbol: NSE or global stock symbol (e.g., RELIANCE, TCS, INFY, AAPL)

        Examples:
            dividend_history_deep("TCS") → TCS 10-year dividend history + yield
            dividend_history_deep("HDFCBANK") → HDFC Bank dividend track record
        """
        import json
        return json.dumps(get_dividend_history_deep(symbol), indent=2)

    @mcp.tool()
    def nifty_pcr_trend(num_expiries: int = 5) -> str:
        """Nifty PCR (Put-Call Ratio) trend across multiple expiries — market sentiment gauge.

        Sensibull Pro charges ₹1,300/month for PCR trend data. We calculate it free.

        Provides:
        - PCR (OI-based and Volume-based) per expiry
        - Overall averaged PCR with sentiment signal
        - Bullish / Bearish / Neutral interpretation per expiry
        - Total call and put OI per expiry

        Args:
            num_expiries: Number of expiries to analyze (default 5)

        Examples:
            nifty_pcr_trend() → Nifty PCR across 5 expiries with overall sentiment
            nifty_pcr_trend(3) → Quick 3-expiry PCR snapshot
        """
        import json
        return json.dumps(get_nifty_pcr_trend(num_expiries), indent=2)
