"""MCP tool: Multi-agent stock brief."""

import json
from mcp.server.fastmcp import FastMCP


def register_agent_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_stock_brief(symbol: str) -> str:
        """
        Multi-agent AI stock brief: 4 personas debate whether to BUY, HOLD, or SELL.

        Like a ₹500Cr fund meeting — 4 different experts analyse the same stock
        from their angle and reach a consensus using real Indian market data:

          • FII Desk       — institutional flows, promoter holding, FII %
          • Algo Trader    — RSI, MACD, VWAP, volume anomaly
          • Value Investor — P/E, ROE, debt ratio, credit rating
          • Retail Pulse   — news tone, 52W position, India VIX

        Args:
            symbol: NSE stock symbol (e.g. RELIANCE, TCS, HDFCBANK)

        Returns JSON with:
            - consensus: {signal, strength, votes, disagreement}
            - debate: [{agent, verdict, argument, one_liner}] — the 4-way debate
            - agents_detail: full data + reasoning per agent
        """
        from finstack.data.agents import get_stock_brief as _get
        result = _get(symbol=symbol)
        return json.dumps(result, indent=2, default=str)
