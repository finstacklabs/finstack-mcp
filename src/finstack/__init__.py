"""FinStack MCP - Open-source financial data MCP server for Indian + Global markets."""

from finstack.utils.yfinance_setup import configure_yfinance_cache

configure_yfinance_cache()

__version__ = "0.10.0"
