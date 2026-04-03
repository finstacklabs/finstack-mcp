"""
FinStack Helpers

Common utilities: symbol validation, response formatting, error handling.
"""

import re
import logging
from typing import Any

logger = logging.getLogger("finstack.helpers")

# ----- Symbol Validation -----

# Common NSE stock symbols (top 100 by market cap)
# This is used for fuzzy matching, not as a hard whitelist
POPULAR_NSE_SYMBOLS = {
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR",
    "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK", "LT", "AXISBANK",
    "BAJFINANCE", "ASIANPAINT", "MARUTI", "TITAN", "SUNPHARMA",
    "TATAMOTORS", "ULTRACEMCO", "WIPRO", "NESTLEIND", "HCLTECH",
    "ONGC", "NTPC", "POWERGRID", "M&M", "TATASTEEL", "JSWSTEEL",
    "ADANIENT", "ADANIPORTS", "BAJAJFINSV", "TECHM", "HDFCLIFE",
    "DIVISLAB", "DRREDDY", "CIPLA", "EICHERMOT", "GRASIM",
    "BRITANNIA", "APOLLOHOSP", "INDUSINDBK", "COALINDIA",
    "BPCL", "TATACONSUM", "SBILIFE", "HEROMOTOCO", "HINDALCO",
    "UPL", "SHREECEM",
}


def validate_symbol(symbol: str) -> str:
    """
    Validate and normalize a stock symbol.
    Handles: RELIANCE, RELIANCE.NS, RELIANCE.BO, AAPL, AAPL.US
    Returns cleaned uppercase symbol.

    Raises ValueError if symbol is clearly invalid.
    """
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Symbol cannot be empty")

    symbol = symbol.strip().upper()

    # Remove common suffixes for validation
    base = re.sub(r'\.(NS|BO|US|L|TO|AX|HK|SS|SZ)$', '', symbol)

    # Basic format check: 1-20 alphanumeric chars, allow & and -
    if not re.match(r'^[A-Z0-9&\-]{1,20}$', base):
        raise ValueError(
            f"Invalid symbol format: '{symbol}'. "
            f"Use formats like RELIANCE, TCS, AAPL, RELIANCE.NS"
        )

    return symbol


def to_nse_symbol(symbol: str) -> str:
    """Convert a symbol to NSE format (append .NS if needed)."""
    symbol = symbol.strip().upper()
    if symbol.endswith(".NS"):
        return symbol
    if symbol.endswith(".BO"):
        return symbol  # BSE symbol, don't change
    # If it's a known NSE symbol or looks Indian, add .NS
    base = re.sub(r'\.\w+$', '', symbol)
    if base in POPULAR_NSE_SYMBOLS or not re.search(r'[a-z]', symbol.lower()):
        return f"{base}.NS"
    return symbol


def to_bse_symbol(symbol: str) -> str:
    """Convert a symbol to BSE format (append .BO if needed)."""
    symbol = symbol.strip().upper()
    if symbol.endswith(".BO"):
        return symbol
    base = re.sub(r'\.\w+$', '', symbol)
    return f"{base}.BO"


# ----- Period Validation -----

VALID_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}
VALID_INTERVALS = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"}


def validate_period(period: str) -> str:
    """Validate a yfinance-compatible period string."""
    period = period.strip().lower()
    if period not in VALID_PERIODS:
        raise ValueError(
            f"Invalid period '{period}'. Valid: {', '.join(sorted(VALID_PERIODS))}"
        )
    return period


def validate_interval(interval: str) -> str:
    """Validate a yfinance-compatible interval string."""
    interval = interval.strip().lower()
    if interval not in VALID_INTERVALS:
        raise ValueError(
            f"Invalid interval '{interval}'. Valid: {', '.join(sorted(VALID_INTERVALS))}"
        )
    return interval


# ----- Response Formatting -----

def format_number(value: Any, decimals: int = 2) -> str | None:
    """Format a number for display. Returns None if value is invalid."""
    if value is None:
        return None
    try:
        num = float(value)
        if abs(num) >= 1_00_00_000:  # 1 crore (Indian numbering)
            return f"₹{num / 1_00_00_000:.2f} Cr"
        elif abs(num) >= 1_00_000:  # 1 lakh
            return f"₹{num / 1_00_000:.2f} L"
        elif abs(num) >= 1000:
            return f"₹{num:,.{decimals}f}"
        else:
            return f"{num:.{decimals}f}"
    except (ValueError, TypeError):
        return None


def format_market_cap(value: Any) -> str | None:
    """Format market cap in a readable way (supports both INR and USD)."""
    if value is None:
        return None
    try:
        num = float(value)
        if abs(num) >= 1e12:
            return f"${num / 1e12:.2f}T"
        elif abs(num) >= 1e9:
            return f"${num / 1e9:.2f}B"
        elif abs(num) >= 1e6:
            return f"${num / 1e6:.2f}M"
        elif abs(num) >= 1e3:
            return f"${num / 1e3:.2f}K"
        else:
            return f"${num:.2f}"
    except (ValueError, TypeError):
        return None


def format_percentage(value: Any, decimals: int = 2) -> str | None:
    """Format a percentage value."""
    if value is None:
        return None
    try:
        return f"{float(value):.{decimals}f}%"
    except (ValueError, TypeError):
        return None


def clean_nan(data: dict | list) -> dict | list:
    """
    Recursively replace NaN/None/inf values with None for JSON serialization.
    yfinance often returns NaN which breaks JSON.
    """
    import math

    if isinstance(data, dict):
        return {
            k: clean_nan(v) for k, v in data.items()
        }
    elif isinstance(data, list):
        return [clean_nan(item) for item in data]
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
        return data
    return data


def safe_get(obj: Any, *keys, default=None) -> Any:
    """Safely traverse nested dicts/objects."""
    current = obj
    for key in keys:
        try:
            if isinstance(current, dict):
                current = current.get(key, default)
            else:
                current = getattr(current, key, default)
        except (AttributeError, TypeError, KeyError):
            return default
        if current is None:
            return default
    return current


# ----- Error Formatting -----

def tool_error(message: str, suggestion: str = "") -> dict:
    """Create a standardized error response for MCP tools."""
    response = {"error": True, "message": message}
    if suggestion:
        response["suggestion"] = suggestion
    return response


def tier_locked_error(tool_name: str) -> dict:
    """Error response when a free user tries a Pro-only tool."""
    return tool_error(
        f"'{tool_name}' requires a Pro subscription ($19/month).",
        suggestion=(
            "Upgrade at https://finstack.dev/pricing to unlock:\n"
            "• Options chain analysis\n"
            "• Portfolio analytics\n"
            "• Backtesting\n"
            "• Advanced stock screening\n"
            "• Support & resistance levels"
        )
    )
