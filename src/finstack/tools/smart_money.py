"""MCP tool: Smart money / unusual activity detector."""

import json
from mcp.server.fastmcp import FastMCP


def register_smart_money_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def detect_unusual_activity(symbol: str) -> str:
        """
        Detect smart money and unusual activity for any NSE stock.

        Scans 4 signals simultaneously:
          • Volume anomaly  — current volume vs 20-day average (flags 2x+)
          • Options OI      — strikes with 2x+ average open interest buildup
          • Block/bulk deals — institutional buy/sell transactions on NSE
          • Promoter change — QoQ shareholding increase (insider buying signal)

        Returns an alert level (high/moderate/low/none) with specific findings.

        Example output:
            "Unusual call OI at 3000 strike — someone is positioning for a breakout"
            "Promoter increased holding by 2.3% QoQ — insider buying signal"

        Args:
            symbol: NSE stock symbol (e.g. RELIANCE, HDFC, TATAMOTORS)

        Returns JSON with:
            - alert_level: high / moderate / low / none
            - verdict: human-readable summary
            - alerts: list of specific signals fired
            - findings: per-category details (volume, OI, deals, promoter)
        """
        from finstack.data.smart_money import detect_unusual_activity as _detect
        result = _detect(symbol=symbol)
        return json.dumps(result, indent=2, default=str)
