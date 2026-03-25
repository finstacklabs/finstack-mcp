"""
FinStack Fundamentals Data Fetcher

Financial statements, key ratios, company profiles, dividends.
All via yfinance — works for both Indian and US stocks.
"""

import logging
from datetime import datetime
from typing import Any

import yfinance as yf
import pandas as pd

from finstack.utils.cache import cached, fundamentals_cache
from finstack.utils.helpers import (
    validate_symbol, to_nse_symbol, clean_nan, safe_get, format_market_cap,
)

logger = logging.getLogger("finstack.data.fundamentals")


def _get_ticker(symbol: str) -> tuple[yf.Ticker, str]:
    """Get yfinance Ticker, auto-detecting exchange."""
    symbol = validate_symbol(symbol)
    # Try as-is first, then with .NS suffix
    ticker = yf.Ticker(symbol)
    info = ticker.info
    if info and info.get("regularMarketPrice") is not None:
        return ticker, symbol

    # Try NSE
    nse_sym = to_nse_symbol(symbol)
    if nse_sym != symbol:
        ticker = yf.Ticker(nse_sym)
        info = ticker.info
        if info and info.get("regularMarketPrice") is not None:
            return ticker, nse_sym

    return yf.Ticker(symbol), symbol


# ===== INCOME STATEMENT =====

@cached(fundamentals_cache, ttl=3600)
def get_income_statement(symbol: str, quarterly: bool = False) -> dict:
    """
    Get income statement data.

    Returns: revenue, cost of revenue, gross profit, operating income,
    net income, EPS, EBITDA, and more.
    """
    try:
        ticker, resolved = _get_ticker(symbol)

        if quarterly:
            stmt = ticker.quarterly_income_stmt
            period_type = "quarterly"
        else:
            stmt = ticker.income_stmt
            period_type = "annual"

        if stmt is None or stmt.empty:
            return {
                "error": True,
                "message": f"No income statement data for '{symbol}'.",
                "suggestion": "Financial statements may not be available for all stocks.",
            }

        # Convert DataFrame: rows=line items, columns=dates
        records = []
        for col in stmt.columns[:4]:  # Last 4 periods max
            period_data = {"period": col.strftime("%Y-%m-%d")}
            for row_name in stmt.index:
                # Clean the key name
                key = str(row_name).replace(" ", "_").lower()
                val = stmt.loc[row_name, col]
                period_data[key] = round(float(val), 2) if pd.notna(val) else None
            records.append(period_data)

        return clean_nan({
            "symbol": symbol.replace(".NS", "").replace(".BO", ""),
            "type": period_type,
            "periods": len(records),
            "currency": safe_get(ticker.info, "currency", default="INR"),
            "data": records,
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        logger.error(f"Error fetching income statement for {symbol}: {e}")
        return {"error": True, "message": str(e)}


# ===== BALANCE SHEET =====

@cached(fundamentals_cache, ttl=3600)
def get_balance_sheet(symbol: str, quarterly: bool = False) -> dict:
    """
    Get balance sheet data.

    Returns: total assets, total liabilities, equity, cash, debt, etc.
    """
    try:
        ticker, resolved = _get_ticker(symbol)

        if quarterly:
            stmt = ticker.quarterly_balance_sheet
            period_type = "quarterly"
        else:
            stmt = ticker.balance_sheet
            period_type = "annual"

        if stmt is None or stmt.empty:
            return {"error": True, "message": f"No balance sheet for '{symbol}'."}

        records = []
        for col in stmt.columns[:4]:
            period_data = {"period": col.strftime("%Y-%m-%d")}
            for row_name in stmt.index:
                key = str(row_name).replace(" ", "_").lower()
                val = stmt.loc[row_name, col]
                period_data[key] = round(float(val), 2) if pd.notna(val) else None
            records.append(period_data)

        return clean_nan({
            "symbol": symbol.replace(".NS", "").replace(".BO", ""),
            "type": period_type,
            "periods": len(records),
            "currency": safe_get(ticker.info, "currency", default="INR"),
            "data": records,
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        logger.error(f"Error fetching balance sheet for {symbol}: {e}")
        return {"error": True, "message": str(e)}


# ===== CASH FLOW =====

@cached(fundamentals_cache, ttl=3600)
def get_cash_flow(symbol: str, quarterly: bool = False) -> dict:
    """
    Get cash flow statement.

    Returns: operating, investing, financing cash flows, free cash flow, capex.
    """
    try:
        ticker, resolved = _get_ticker(symbol)

        if quarterly:
            stmt = ticker.quarterly_cashflow
            period_type = "quarterly"
        else:
            stmt = ticker.cashflow
            period_type = "annual"

        if stmt is None or stmt.empty:
            return {"error": True, "message": f"No cash flow data for '{symbol}'."}

        records = []
        for col in stmt.columns[:4]:
            period_data = {"period": col.strftime("%Y-%m-%d")}
            for row_name in stmt.index:
                key = str(row_name).replace(" ", "_").lower()
                val = stmt.loc[row_name, col]
                period_data[key] = round(float(val), 2) if pd.notna(val) else None
            records.append(period_data)

        return clean_nan({
            "symbol": symbol.replace(".NS", "").replace(".BO", ""),
            "type": period_type,
            "periods": len(records),
            "currency": safe_get(ticker.info, "currency", default="INR"),
            "data": records,
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        logger.error(f"Error fetching cash flow for {symbol}: {e}")
        return {"error": True, "message": str(e)}


# ===== KEY RATIOS =====

@cached(fundamentals_cache, ttl=1800)
def get_key_ratios(symbol: str) -> dict:
    """
    Get key financial ratios and valuation metrics.

    Returns P/E, P/B, EV/EBITDA, ROE, ROA, debt/equity, current ratio,
    profit margins, revenue growth, etc.
    """
    try:
        ticker, resolved = _get_ticker(symbol)
        info = ticker.info

        if not info or info.get("regularMarketPrice") is None:
            return {"error": True, "message": f"No data for '{symbol}'."}

        result = {
            "symbol": symbol.replace(".NS", "").replace(".BO", ""),
            "name": safe_get(info, "longName", default=symbol),
            "currency": safe_get(info, "currency", default="INR"),

            # Valuation
            "valuation": {
                "pe_trailing": safe_get(info, "trailingPE"),
                "pe_forward": safe_get(info, "forwardPE"),
                "peg_ratio": safe_get(info, "pegRatio"),
                "price_to_book": safe_get(info, "priceToBook"),
                "price_to_sales": safe_get(info, "priceToSalesTrailing12Months"),
                "ev_to_ebitda": safe_get(info, "enterpriseToEbitda"),
                "ev_to_revenue": safe_get(info, "enterpriseToRevenue"),
                "enterprise_value": safe_get(info, "enterpriseValue"),
                "market_cap": safe_get(info, "marketCap"),
            },

            # Profitability
            "profitability": {
                "profit_margin": safe_get(info, "profitMargins"),
                "operating_margin": safe_get(info, "operatingMargins"),
                "gross_margin": safe_get(info, "grossMargins"),
                "ebitda_margin": safe_get(info, "ebitdaMargins"),
                "roe": safe_get(info, "returnOnEquity"),
                "roa": safe_get(info, "returnOnAssets"),
            },

            # Growth
            "growth": {
                "revenue_growth": safe_get(info, "revenueGrowth"),
                "earnings_growth": safe_get(info, "earningsGrowth"),
                "earnings_quarterly_growth": safe_get(info, "earningsQuarterlyGrowth"),
            },

            # Financial health
            "financial_health": {
                "debt_to_equity": safe_get(info, "debtToEquity"),
                "current_ratio": safe_get(info, "currentRatio"),
                "quick_ratio": safe_get(info, "quickRatio"),
                "total_debt": safe_get(info, "totalDebt"),
                "total_cash": safe_get(info, "totalCash"),
                "free_cash_flow": safe_get(info, "freeCashflow"),
            },

            # Per share
            "per_share": {
                "eps_trailing": safe_get(info, "trailingEps"),
                "eps_forward": safe_get(info, "forwardEps"),
                "book_value": safe_get(info, "bookValue"),
                "revenue_per_share": safe_get(info, "revenuePerShare"),
            },

            # Dividend
            "dividend": {
                "dividend_rate": safe_get(info, "dividendRate"),
                "dividend_yield": safe_get(info, "dividendYield"),
                "payout_ratio": safe_get(info, "payoutRatio"),
                "ex_dividend_date": safe_get(info, "exDividendDate"),
            },

            "timestamp": datetime.now().isoformat(),
        }

        return clean_nan(result)

    except Exception as e:
        logger.error(f"Error fetching ratios for {symbol}: {e}")
        return {"error": True, "message": str(e)}


# ===== COMPANY PROFILE =====

@cached(fundamentals_cache, ttl=86400)
def get_company_profile(symbol: str) -> dict:
    """Get company overview — sector, industry, employees, description, officers."""
    try:
        ticker, resolved = _get_ticker(symbol)
        info = ticker.info

        if not info or info.get("regularMarketPrice") is None:
            return {"error": True, "message": f"No data for '{symbol}'."}

        result = {
            "symbol": symbol.replace(".NS", "").replace(".BO", ""),
            "name": safe_get(info, "longName", default=symbol),
            "sector": safe_get(info, "sector"),
            "industry": safe_get(info, "industry"),
            "country": safe_get(info, "country"),
            "city": safe_get(info, "city"),
            "state": safe_get(info, "state"),
            "website": safe_get(info, "website"),
            "employees": safe_get(info, "fullTimeEmployees"),
            "description": safe_get(info, "longBusinessSummary"),
            "exchange": safe_get(info, "exchange"),
            "currency": safe_get(info, "currency"),
            "market_cap": safe_get(info, "marketCap"),
            "market_cap_formatted": format_market_cap(safe_get(info, "marketCap")),
            "timestamp": datetime.now().isoformat(),
        }

        return clean_nan(result)

    except Exception as e:
        logger.error(f"Error fetching profile for {symbol}: {e}")
        return {"error": True, "message": str(e)}


# ===== DIVIDEND HISTORY =====

@cached(fundamentals_cache, ttl=86400)
def get_dividend_history(symbol: str) -> dict:
    """Get historical dividend payments."""
    try:
        ticker, resolved = _get_ticker(symbol)
        dividends = ticker.dividends

        if dividends is None or dividends.empty:
            return {
                "symbol": symbol.replace(".NS", "").replace(".BO", ""),
                "dividends": [],
                "message": "No dividend history found. Company may not pay dividends.",
            }

        records = []
        for date, amount in dividends.items():
            records.append({
                "date": date.strftime("%Y-%m-%d"),
                "amount": round(float(amount), 4),
            })

        # Sort newest first
        records.reverse()

        # Summary
        total = sum(r["amount"] for r in records)
        avg = total / len(records) if records else 0

        return clean_nan({
            "symbol": symbol.replace(".NS", "").replace(".BO", ""),
            "total_dividends_paid": len(records),
            "total_amount": round(total, 2),
            "average_dividend": round(avg, 4),
            "latest": records[0] if records else None,
            "currency": safe_get(ticker.info, "currency", default="INR"),
            "history": records[:20],  # Last 20 dividends
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        logger.error(f"Error fetching dividends for {symbol}: {e}")
        return {"error": True, "message": str(e)}
