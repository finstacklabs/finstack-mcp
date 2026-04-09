"""MCP tool: Nifty direction probability score."""

import json
from mcp.server.fastmcp import FastMCP


def register_probability_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_nifty_outlook() -> str:
        """
        Compute the probability that Nifty 50 closes UP in the next trading session.

        Aggregates 6 market signals into a single % score:
          • RSI(14)           — overbought/oversold momentum
          • FII net flow (5d) — institutional buy/sell pressure
          • Put/Call Ratio    — options market positioning (contrarian signal)
          • India VIX         — fear index (low=risk-on, high=fear)
          • G-Sec 10Y yield   — interest rate pressure on equities
          • GIFT Nifty        — overnight global pre-market signal

        Returns JSON with:
            - probability_up: e.g. 67  (% chance Nifty goes up)
            - signal: "Bullish" / "Cautiously bullish" / "Neutral" / "Bearish"
            - bull_factors: list of signals supporting upside
            - bear_factors: list of signals supporting downside
            - inputs: raw values for all 6 signals

        Example: "67% probability Nifty up tomorrow — FII buying + low VIX but overbought RSI"
        """
        from finstack.data.probability import get_nifty_outlook as _get
        result = _get()
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def get_fno_trade_setup(symbol: str = "NIFTY") -> str:
        """
        Build a clean NIFTY / BANKNIFTY options setup for intraday decisions.

        This packages the strongest nifty-agent behavior into one MCP call:
        read trend, RSI, MACD, FII flows, PCR, VIX regime, and overnight
        context, then return one clear action:

        - BUY_CE
        - BUY_PE
        - NO_TRADE

        Also returns:
        - confidence_pct
        - preferred ATM strike zone
        - approve_message
        - bull and bear factors
        - risk flags
        """
        from finstack.data.probability import get_fno_trade_setup as _get

        result = _get(symbol)
        return json.dumps(result, indent=2, default=str)
