"""MCP tool: Multi-agent stock brief."""

import json

from mcp.server.fastmcp import FastMCP


def register_agent_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def get_stock_brief(symbol: str) -> str:
        """
        Multi-agent AI stock brief: 6 personas debate whether to BUY, HOLD, or SELL.

        Like a Rs500Cr fund meeting, 6 different experts analyse the same stock
        from their angle and reach a consensus using real Indian market data:

          - FII Desk: institutional flows, promoter holding, FII %
          - Algo Trader: RSI, MACD, VWAP, volume anomaly
          - Value Investor: P/E, ROE, debt ratio, credit rating
          - Retail Pulse: news tone, 52W position, India VIX
          - Macro Analyst: RBI rates, CPI inflation, G-Sec yields
          - Options Flow: PCR, max pain, OI skew

        Args:
            symbol: NSE stock symbol (e.g. RELIANCE, TCS, HDFCBANK)

        Returns JSON with:
            - consensus: {signal, strength, votes, disagreement}
            - debate: [{agent, verdict, argument, one_liner}] - the 6-way debate
            - agents_detail: full data + reasoning per agent
        """
        from finstack.data.agents import get_stock_brief as _get

        result = _get(symbol=symbol)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def get_stock_debate(symbol: str) -> str:
        """
        3-round sequential debate: AI agents read each other's arguments and rebut.

        Unlike get_stock_brief (parallel analysis), this runs a live debate:
          Round 1 - Each agent analyses independently
          Round 2 - Each agent reads all other Round 1 verdicts and can change mind
          Round 3 - Final lock-in with closing statement

        Watch for "minds_changed" - when agents flip verdict mid-debate,
        it signals a complex setup worth closer attention.

        Also returns "debate_edges" - who influenced whom - consumable by
        the AgentBattle canvas visualisation.

        Args:
            symbol: NSE stock symbol (e.g. RELIANCE, TCS, HDFCBANK)

        Returns JSON with:
            - rounds: {round1, round2, round3} - full transcript
            - debate_edges: [{from, to, type, text}] - influence graph
            - minds_changed: how many agents revised their verdict
            - final_consensus: {signal, strength, votes, note}
        """
        from finstack.data.agents import get_stock_debate as _get

        result = _get(symbol=symbol)
        return json.dumps(result, indent=2, default=str)
