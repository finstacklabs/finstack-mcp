"""MCP tools: Fyers + ICICI Breeze broker integrations."""

import json
from mcp.server.fastmcp import FastMCP


def register_broker_tools(mcp: FastMCP) -> None:

    # ── Fyers API v3 ──────────────────────────────────────────────────────────

    @mcp.tool()
    def fyers_live_quote(symbol: str) -> str:
        """
        Real-time NSE stock quote via Fyers API v3 (zero delay when configured).

        Returns LTP, O/H/L/C, volume, change%, 52W high/low.

        Setup:
            pip install fyers-apiv3
            FYERS_APP_ID=...  FYERS_ACCESS_TOKEN=...  FYERS_CLIENT_ID=...
            Get credentials at https://myapi.fyers.in/

        Args:
            symbol: NSE symbol (e.g. RELIANCE, TCS, INFY)
        """
        from finstack.data.broker_fyers import get_live_quote_fyers
        return json.dumps(get_live_quote_fyers(symbol), indent=2)

    @mcp.tool()
    def fyers_candles(symbol: str, interval: str = "1d", days: int = 30) -> str:
        """
        Historical OHLCV candles from Fyers API v3.

        interval options: 1m, 3m, 5m, 10m, 15m, 30m, 1h, 2h, 4h, 1d, 1w, 1mo

        Args:
            symbol:   NSE symbol (e.g. RELIANCE)
            interval: Candle interval (default: 1d)
            days:     Number of days of history (default: 30)
        """
        from finstack.data.broker_fyers import get_candle_data_fyers
        return json.dumps(get_candle_data_fyers(symbol, interval, days), indent=2)

    @mcp.tool()
    def fyers_status() -> str:
        """Check Fyers API v3 configuration status and setup instructions."""
        from finstack.data.broker_fyers import broker_status_fyers
        return json.dumps(broker_status_fyers(), indent=2)

    # ── ICICI Breeze ──────────────────────────────────────────────────────────

    @mcp.tool()
    def icici_live_quote(symbol: str) -> str:
        """
        Real-time NSE quote via ICICI Breeze API (zero delay when configured).

        Returns LTP, O/H/L, previous close, volume, change%.

        Setup:
            pip install breeze-connect
            ICICI_API_KEY=...  ICICI_API_SECRET=...  ICICI_SESSION_TOKEN=...
            Session token refreshed daily: ICICIdirect app → My Account → Generate API Session

        Args:
            symbol: NSE symbol (e.g. RELIANCE, TCS, HDFCBANK)
        """
        from finstack.data.broker_icici import get_live_quote_icici
        return json.dumps(get_live_quote_icici(symbol), indent=2)

    @mcp.tool()
    def icici_candles(symbol: str, interval: str = "1day", days: int = 30) -> str:
        """
        Historical OHLCV candles from ICICI Breeze API.

        interval options: 1m, 5m, 30m, 1h, 1d

        Args:
            symbol:   NSE symbol (e.g. RELIANCE)
            interval: Candle interval (default: 1day)
            days:     Number of days of history (default: 30)
        """
        from finstack.data.broker_icici import get_candle_data_icici
        return json.dumps(get_candle_data_icici(symbol, interval, days), indent=2)

    @mcp.tool()
    def icici_status() -> str:
        """Check ICICI Breeze API configuration status and daily session token instructions."""
        from finstack.data.broker_icici import broker_status_icici
        return json.dumps(broker_status_icici(), indent=2)
