"""
MCP tools: earnings preview, portfolio X-ray, MF overlap,
FII/retail divergence, morning brief, promoter pledge, pump detector.
"""

import json
from mcp.server.fastmcp import FastMCP


def register_intelligence_tools(mcp: FastMCP) -> None:

    # ── Earnings preview ──────────────────────────────────────────────────────

    @mcp.tool()
    def predict_earnings(symbol: str) -> str:
        """
        AI earnings preview before quarterly results.

        Combines 4 signals to estimate beat/miss probability:
          - Last 4 quarters EPS trend (improving / declining / mixed)
          - Analyst consensus recommendation + target price upside
          - FII QoQ shareholding change (building before results = positive)
          - Stock alpha vs Nifty last 30 days (momentum into results)

        Returns:
          - beat_probability_pct: e.g. 72
          - signal: BEAT LIKELY / SLIGHT BEAT / IN-LINE OR MISS / MISS LIKELY
          - key_risks: list of red flags
          - what_to_watch: what to monitor on results day
          - next_earnings_date: from yFinance calendar

        Viral use: post prediction before TCS/Infy results. Screenshot if correct.

        Args:
            symbol: NSE symbol (e.g. TCS, INFY, HDFCBANK, RELIANCE)
        """
        from finstack.data.earnings import predict_earnings as _get
        return json.dumps(_get(symbol), indent=2, default=str)

    # ── Portfolio X-ray ───────────────────────────────────────────────────────

    @mcp.tool()
    def analyze_portfolio(holdings: list[dict]) -> str:
        """
        Portfolio X-ray: deep risk + return analysis for your holdings.

        Input format — list of holdings:
          [
            {"symbol": "RELIANCE", "qty": 10, "avg_price": 2400, "buy_date": "2024-01-15"},
            {"symbol": "TCS",      "qty": 5,  "avg_price": 3800}
          ]

        Returns:
          - total invested, current value, P&L, P&L %
          - XIRR (if buy_date provided)
          - per-holding breakdown with sector
          - sector concentration % (flags if > 40% in one sector)
          - risk flags: pledged promoters, single stock > 30%, FII reducing
          - diversification score (0–100)

        Args:
            holdings: list of {symbol, qty, avg_price, buy_date (optional)}
        """
        from finstack.data.portfolio import analyze_portfolio as _get
        return json.dumps(_get(holdings), indent=2, default=str)

    # ── MF overlap analyzer ───────────────────────────────────────────────────

    @mcp.tool()
    def get_mf_overlap(fund1: str, fund2: str) -> str:
        """
        Mutual fund overlap analyzer using public AMFI portfolio disclosures.

        "Your HDFC Flexi Cap + Mirae Asset Large Cap have 68% overlap —
         you're not diversified, you're holding the same stocks twice."

        Supported funds include: HDFC Flexi Cap, Mirae Asset Large Cap,
        Parag Parikh Flexi Cap, Axis Bluechip, SBI Bluechip, Nippon Large Cap,
        Kotak Emerging Equity, Quant Small Cap, DSP Small Cap, Nifty 50 Index.

        Returns:
          - overlap_pct: % of stocks common between both funds
          - common_stocks: list of shared holdings
          - unique_to_fund1, unique_to_fund2
          - verdict + risk level (low / medium / high)

        Args:
            fund1: Fund name (e.g. "HDFC Flexi Cap")
            fund2: Fund name (e.g. "Mirae Asset Large Cap")
        """
        from finstack.data.mf_overlap import get_mf_overlap as _get
        return json.dumps(_get(fund1, fund2), indent=2, default=str)

    # ── FII vs Retail divergence ──────────────────────────────────────────────

    @mcp.tool()
    def get_fii_retail_divergence(symbol: str) -> str:
        """
        Detect FII vs retail divergence — the highest-conviction signal in Indian markets.

        When FII and retail move in OPPOSITE directions on the same stock:
          - FII buying + retail selling = institutional accumulation (BUY signal)
          - FII selling + retail buying = institutional distribution (SELL signal)

        "FIIs bought ₹800Cr of HDFC Bank while retail was panic selling —
         historically this means +18% in 3 months"

        Based on public NSE shareholding disclosures (quarterly).

        Args:
            symbol: NSE symbol (e.g. HDFCBANK, RELIANCE, TATAMOTORS)

        Returns:
          - divergence_type, signal, confidence
          - interpretation + historical_implication
          - raw shareholding change data (FII, DII, retail QoQ)
        """
        from finstack.data.divergence import get_fii_retail_divergence as _get
        return json.dumps(_get(symbol), indent=2, default=str)

    # ── Morning brief ─────────────────────────────────────────────────────────

    @mcp.tool()
    def get_morning_brief() -> str:
        """
        8:15 AM pre-market brief for Indian traders.

        Compiles in one call:
          - GIFT Nifty pre-market signal
          - India VIX fear index
          - Nifty direction probability (6-signal model)
          - FII net flow from yesterday
          - Top gainers / losers
          - Sector performance
          - Upcoming earnings today
          - Watchlist signals for top 5 Nifty stocks

        Returns structured JSON + morning_text (ready to copy-paste or send via WhatsApp/email).
        """
        from finstack.briefs import get_morning_brief as _get
        return json.dumps(_get(), indent=2, default=str)

    # ── Promoter pledge alert ─────────────────────────────────────────────────

    @mcp.tool()
    def get_pledge_alert(symbol: str) -> str:
        """
        Promoter pledge early warning for an NSE stock.

        Checks current pledge % and QoQ change velocity.
        Risk levels: safe (< 10%) / watch (rising) / danger (> 30%) / critical (> 50%)

        "Caught 3 stocks before they fell 40% — promoter was pledging shares"

        Risk: When promoters pledge shares as collateral for loans, a falling
        stock price can trigger margin calls → forced selling → crash.

        Args:
            symbol: NSE symbol (e.g. ADANIENT, ZEEL, any stock)

        Returns:
          - pledge_pct, pledge_change_qoq
          - risk_level: safe / watch / danger / critical
          - alert: specific warning message
          - historical: last 4 quarters of pledge data
        """
        from finstack.data.promoter_watch import get_pledge_alert as _get
        return json.dumps(_get(symbol), indent=2, default=str)

    @mcp.tool()
    def scan_pledge_risks(symbols: list[str]) -> str:
        """
        Scan multiple NSE stocks for promoter pledge risk simultaneously.

        Returns results sorted by risk level (critical first).
        Useful for screening your watchlist or Nifty 500 for pledge dangers.

        Args:
            symbols: list of NSE symbols (e.g. ["ADANIENT", "ZEEL", "RELIANCE", "TCS"])
        """
        from finstack.data.promoter_watch import scan_pledge_risks as _get
        return json.dumps(_get(symbols), indent=2, default=str)

    # ── Pump / operator detector ──────────────────────────────────────────────

    @mcp.tool()
    def detect_pump(symbol: str) -> str:
        """
        Detect pump-and-dump operator activity in an NSE stock.

        Scans for coordinated pump patterns:
          - Volume spike > 3x 20-day average
          - Price surge > 20% in 5 days without news
          - Multiple upper circuit days in last week
          - Micro/small cap (highest vulnerability)

        "This microcap hit 3 upper circuits in a week —
         9 out of 10 times this reverses violently"

        Returns:
          - pump_probability: low / medium / high / critical
          - red_flags: specific signals that fired
          - verdict + recommendation (exit / avoid / cautious)

        Args:
            symbol: NSE symbol (most useful for small/micro caps)
        """
        from finstack.data.pump_detector import detect_pump as _get
        return json.dumps(_get(symbol), indent=2, default=str)
