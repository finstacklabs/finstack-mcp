"""
MCP tools: Phase 4 — circuit predictor, SEBI tracker, GST predictor,
AGM briefing, insider signal, Telegram tracker, budget analyzer.
"""

import json
from mcp.server.fastmcp import FastMCP


def register_phase4_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def predict_circuit(symbol: str) -> str:
        """
        Predict lower circuit risk for an NSE stock.

        Combines 5 signals: price proximity to 52W low, volume dry-up,
        promoter pledge velocity, FII net selling, negative news sentiment.

        Risk levels: safe / watch / danger / imminent

        "Predicted 4 lower circuits in March — here's how"

        Args:
            symbol: NSE symbol (most useful for mid/small caps under stress)
        """
        from finstack.data.circuit import predict_circuit as _get
        return json.dumps(_get(symbol), indent=2, default=str)

    @mcp.tool()
    def get_sebi_alerts(sector: str = "all") -> str:
        """
        SEBI enforcement order tracker — early warning before regulatory crash.

        Fetches recent SEBI orders and classifies by severity and sector.
        High-severity actions (fraud, manipulation, debarment) historically
        precede 15-30% corrections in the affected stock.

        "SEBI filed 3 orders against this sector this week —
         historically precedes 15% correction"

        Args:
            sector: Filter by sector (e.g. "Banking", "SME/Micro", "Broking").
                    Use "all" for full report.
        """
        from finstack.data.sebi_tracker import get_sebi_alerts as _get
        return json.dumps(_get(sector), indent=2, default=str)

    @mcp.tool()
    def correlate_gst_to_stocks(sector: str = "all") -> str:
        """
        GST collection data → sector performance predictor.

        Monthly GST figures (Finance Ministry, public) are a 1-3 month
        leading indicator for demand-sensitive sectors.

        "GST from auto sector up 24% YoY → MSIL/Bajaj Auto historically follow in 2-3 months"

        Sectors covered: Auto, FMCG, Real Estate, Cement, Steel, IT, Banking, Retail.

        Args:
            sector: Sector name (e.g. "Auto", "FMCG", "Cement").
                    Use "all" for full cross-sector report.
        """
        from finstack.data.gst import correlate_gst_to_stocks as _get
        return json.dumps(_get(sector), indent=2, default=str)

    @mcp.tool()
    def get_agm_brief(symbol: str) -> str:
        """
        AI briefing for upcoming AGM/EGM resolutions from NSE filings.

        Flags unusual resolutions:
          - Large debt issuance (₹500Cr+ raise)
          - Management salary hikes
          - Related-party transactions (promoter benefit risk)
          - New subsidiary creation (liability hiding risk)
          - Buyback cancellation (cash crunch signal)
          - Fresh equity (dilution)
          - Auditor resignation (serious red flag)
          - Promoter pledge approval

        "This company is passing a resolution to raise ₹500Cr debt next week —
         should you be worried?"

        Args:
            symbol: NSE symbol (e.g. RELIANCE, ZEEL, ADANIENT)
        """
        from finstack.data.agm import get_agm_brief as _get
        return json.dumps(_get(symbol), indent=2, default=str)

    @mcp.tool()
    def get_insider_signal(symbol: str) -> str:
        """
        Insider trading pattern analysis from SEBI SAST disclosures (public).

        Tracks promoter/director/KMP buy and sell transactions.
        Insiders buying their own stock = strongest possible conviction signal.

        "When this CFO buys his own stock → average return is +23% in 6 months"

        Returns:
          - signal: BUY / SELL / NEUTRAL
          - net_signal: accumulating / distributing / neutral
          - recent buy/sell transactions with person + designation
          - price change since last insider buy

        Args:
            symbol: NSE symbol (e.g. RELIANCE, INFY, ZEEL)
        """
        from finstack.data.insider_pattern import get_insider_signal as _get
        return json.dumps(_get(symbol), indent=2, default=str)

    @mcp.tool()
    def get_telegram_tracker(channel: str = "") -> str:
        """
        Dalal Street Telegram signal tracker.

        Compares 50 public Indian stock tip channels by accuracy %, average
        return %, and pump-and-dump probability.

        "I tracked 50 Indian stock tip channels for 30 days —
         here's which ones are scamming you"

        Works out of the box with curated channel database.
        Enable live tracking with: pip install telethon + TELEGRAM_API_ID/HASH/PHONE

        Args:
            channel: Specific channel handle (e.g. "@NSEBSEtips").
                     Leave empty for full comparison database.
        """
        from finstack.data.telegram_tracker import get_telegram_tracker as _get
        return json.dumps(_get(channel or None), indent=2, default=str)

    @mcp.tool()
    def analyze_budget_live(text: str) -> str:
        """
        Real-time budget speech analyzer — use on Feb 1st as FM speaks.

        Paste the Finance Minister's speech text (any length, even partial).
        Returns instant sector + stock impact mapping.

        "FM just said ₹2L Cr for infrastructure → BUY L&T, NTPC, IRB Infra"

        Detects mentions of: Infrastructure, Defence, Pharma, Renewable Energy,
        Real Estate, Agriculture, Auto, FMCG, IT/Digital, Steel, Telecom, Tax changes.

        Args:
            text: Budget speech transcript text (paste directly from live broadcast)
        """
        from finstack.data.budget import analyze_budget_live as _get
        return json.dumps(_get(text), indent=2, default=str)

    @mcp.tool()
    def get_budget_impact(year: str = "2025") -> str:
        """
        Historical Union Budget impact by year.

        Returns key announcements, sector winners, sector losers,
        and market reaction from past Indian Union Budgets.

        Available years: 2023, 2024, 2025

        Args:
            year: Budget year as string (e.g. "2025", "2024", "2023")
        """
        from finstack.data.budget import get_budget_impact as _get
        return json.dumps(_get(year), indent=2, default=str)

    # ── Signal Outcome Tracking ───────────────────────────────────────────────

    @mcp.tool()
    def get_signal_accuracy(
        source: str = "",
        symbol: str = "",
        days: int = 30,
    ) -> str:
        """
        Show how accurate FinStack signals have been — backed by real outcome data.

        Signals are logged automatically every time get_stock_brief or get_stock_debate
        runs. After 7 days, the actual stock price is checked and outcomes are labelled
        correct / wrong / neutral.

        Use this to:
        - Prove to users/investors that the signals work
        - Find which signal source (brief vs debate) is more accurate
        - Find which stocks the model reads best

        Args:
            source: filter by source — 'brief', 'debate', 'score', or '' for all
            symbol: filter by NSE symbol, or '' for all stocks
            days:   look-back window in days (default 30)

        Returns:
            Accuracy %, avg 7-day return, breakdown by signal type, top symbols.
        """
        from finstack.data.signal_tracker import get_accuracy_stats
        return json.dumps(
            get_accuracy_stats(
                source=source or None,
                symbol=symbol or None,
                days=days,
            ),
            indent=2, default=str,
        )

    @mcp.tool()
    def get_signal_history(symbol: str = "", limit: int = 20) -> str:
        """
        View recent signals logged by FinStack with their actual outcomes.

        Each row shows: symbol, signal (BUY/HOLD/SELL), price at signal time,
        7-day actual return, and outcome label (correct/wrong/neutral).

        Use this to audit the model, build trust with users, or export for analysis.

        Args:
            symbol: NSE symbol to filter (e.g. RELIANCE), or '' for all
            limit:  number of rows to return (default 20, max 100)
        """
        from finstack.data.signal_tracker import get_signal_history as _get
        return json.dumps(
            _get(symbol=symbol or None, limit=min(limit, 100)),
            indent=2, default=str,
        )

    @mcp.tool()
    def check_signal_outcomes() -> str:
        """
        Manually trigger outcome checking for all pending signals.

        Normally runs automatically, but you can call this to force-check any
        signals whose 7-day or 30-day window has elapsed.

        Returns how many signals were updated.
        """
        from finstack.data.signal_tracker import check_pending_outcomes
        result = check_pending_outcomes()
        return json.dumps(
            {"status": "done", "updated": result},
            indent=2,
        )
