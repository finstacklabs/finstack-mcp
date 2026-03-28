"""
FinStack Market Intelligence Data

New data layer covering features that paid platforms charge for:
- Options OI Analytics: PCR trend, Max Pain, IV summary (Sensibull charges ₹1,300/mo)
- Options Greeks: Delta, Gamma, Theta, Vega via Black-Scholes (Sensibull Pro)
- Insider Trading: NSE SAST disclosures (Trendlyne/Screener Pro)
- Promoter Shareholding: ownership pattern (Screener Pro ₹4,999/yr)
- RBI Policy Rates: repo, reverse repo, CRR, SLR (Bloomberg charges $24k/yr)
- India Macro Indicators: CPI, GDP, current account (Bloomberg/Refinitiv paid)
- AMFI Fund Flows: monthly MF industry inflows/outflows (Morningstar $17,500/yr)
- India G-Sec Yields: government bond yield curve (Bloomberg paid)

All data from free public sources: NSE, RBI, AMFI, World Bank API.
No API keys required.
"""

import logging
from datetime import datetime, timedelta
from math import log, sqrt, exp, erf
from typing import Any

import httpx
import yfinance as yf
import pandas as pd

from finstack.utils.cache import cached, quotes_cache, general_cache, fundamentals_cache
from finstack.utils.helpers import validate_symbol, to_nse_symbol, clean_nan

logger = logging.getLogger("finstack.data.market_intelligence")

NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


def _nse_session() -> httpx.Client:
    """Create an NSE session with cookies."""
    client = httpx.Client(headers=NSE_HEADERS, timeout=15, follow_redirects=True)
    try:
        client.get("https://www.nseindia.com/")
    except Exception:
        pass
    return client


# ──────────────────────────────────────────────
# BLACK-SCHOLES GREEKS (pure Python, no scipy)
# ──────────────────────────────────────────────

def _norm_cdf(x: float) -> float:
    return (1.0 + erf(x / sqrt(2.0))) / 2.0


def _norm_pdf(x: float) -> float:
    return exp(-0.5 * x * x) / sqrt(2.0 * 3.141592653589793)


def _bs_greeks(S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> dict:
    """
    Black-Scholes Greeks for a European option.
    S = underlying price, K = strike, T = years to expiry,
    r = risk-free rate (decimal), sigma = IV (decimal).
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}

    d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)

    if option_type.lower() == "call":
        delta = _norm_cdf(d1)
        theta = (
            -(S * _norm_pdf(d1) * sigma) / (2.0 * sqrt(T))
            - r * K * exp(-r * T) * _norm_cdf(d2)
        ) / 365.0
        rho = K * T * exp(-r * T) * _norm_cdf(d2) / 100.0
    else:
        delta = _norm_cdf(d1) - 1.0
        theta = (
            -(S * _norm_pdf(d1) * sigma) / (2.0 * sqrt(T))
            + r * K * exp(-r * T) * _norm_cdf(-d2)
        ) / 365.0
        rho = -K * T * exp(-r * T) * _norm_cdf(-d2) / 100.0

    gamma = _norm_pdf(d1) / (S * sigma * sqrt(T))
    vega = S * _norm_pdf(d1) * sqrt(T) / 100.0  # per 1% IV change

    return {
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta, 4),
        "vega": round(vega, 4),
        "rho": round(rho, 4),
    }


def _compute_max_pain(calls: list[dict], puts: list[dict]) -> float:
    """Max Pain = strike where aggregate option writer payout is minimized."""
    all_strikes = sorted(set([c["strike"] for c in calls] + [p["strike"] for p in puts]))
    if not all_strikes:
        return 0.0

    call_oi = {c["strike"]: c["open_interest"] for c in calls}
    put_oi = {p["strike"]: p["open_interest"] for p in puts}

    min_pain = float("inf")
    max_pain_strike = all_strikes[len(all_strikes) // 2]

    for P in all_strikes:
        call_pain = sum((P - K) * call_oi.get(K, 0) for K in all_strikes if K <= P)
        put_pain = sum((K - P) * put_oi.get(K, 0) for K in all_strikes if K >= P)
        total = call_pain + put_pain
        if total < min_pain:
            min_pain = total
            max_pain_strike = P

    return float(max_pain_strike)


# ──────────────────────────────────────────────
# OPTIONS OI ANALYTICS
# ──────────────────────────────────────────────

@cached(quotes_cache, ttl=300)
def get_options_oi_analytics(symbol: str) -> dict:
    """
    Advanced options OI analytics: Max Pain, PCR, IV summary, OI heatmap.
    Covers what Sensibull Pro charges ₹1,300/month for.
    """
    symbol = validate_symbol(symbol)

    for yf_sym in [to_nse_symbol(symbol), symbol]:
        try:
            ticker = yf.Ticker(yf_sym)
            expiry_dates = ticker.options
            if not expiry_dates:
                continue

            underlying = ticker.info.get("regularMarketPrice") or ticker.info.get("currentPrice", 0)

            results = []
            for expiry in list(expiry_dates)[:3]:  # Analyze 3 nearest expiries
                chain = ticker.option_chain(expiry)
                calls = chain.calls
                puts = chain.puts

                def _parse_chain(df: Any, opt_type: str) -> list[dict]:
                    rows = []
                    for _, row in df.iterrows():
                        oi = int(row.get("openInterest", 0)) if pd.notna(row.get("openInterest")) else 0
                        vol = int(row.get("volume", 0)) if pd.notna(row.get("volume")) else 0
                        iv = float(row.get("impliedVolatility", 0)) if pd.notna(row.get("impliedVolatility")) else 0
                        rows.append({
                            "strike": float(row.get("strike", 0)),
                            "last_price": float(row.get("lastPrice", 0)),
                            "open_interest": oi,
                            "volume": vol,
                            "implied_volatility_pct": round(iv * 100, 2),
                            "in_the_money": bool(row.get("inTheMoney", False)),
                            "type": opt_type,
                        })
                    return rows

                calls_data = _parse_chain(calls, "call")
                puts_data = _parse_chain(puts, "put")

                total_call_oi = sum(c["open_interest"] for c in calls_data)
                total_put_oi = sum(p["open_interest"] for p in puts_data)
                total_call_vol = sum(c["volume"] for c in calls_data)
                total_put_vol = sum(p["volume"] for p in puts_data)

                pcr_oi = round(total_put_oi / total_call_oi, 3) if total_call_oi > 0 else None
                pcr_vol = round(total_put_vol / total_call_vol, 3) if total_call_vol > 0 else None

                pcr_signal = "Neutral"
                if pcr_oi:
                    if pcr_oi > 1.3:
                        pcr_signal = "Oversold / Bullish reversal likely"
                    elif pcr_oi > 1.0:
                        pcr_signal = "Bearish bias (heavy put buying)"
                    elif pcr_oi < 0.7:
                        pcr_signal = "Overbought / Bearish reversal likely"
                    elif pcr_oi < 1.0:
                        pcr_signal = "Bullish bias (heavy call buying)"

                max_pain = _compute_max_pain(calls_data, puts_data)

                # Top OI strikes (support/resistance from options market)
                top_call_strikes = sorted(calls_data, key=lambda x: x["open_interest"], reverse=True)[:5]
                top_put_strikes = sorted(puts_data, key=lambda x: x["open_interest"], reverse=True)[:5]

                # IV summary
                call_ivs = [c["implied_volatility_pct"] for c in calls_data if c["implied_volatility_pct"] > 0]
                put_ivs = [p["implied_volatility_pct"] for p in puts_data if p["implied_volatility_pct"] > 0]
                avg_iv = round((sum(call_ivs + put_ivs) / len(call_ivs + put_ivs)), 2) if (call_ivs or put_ivs) else None

                results.append({
                    "expiry": expiry,
                    "total_call_oi": total_call_oi,
                    "total_put_oi": total_put_oi,
                    "total_call_volume": total_call_vol,
                    "total_put_volume": total_put_vol,
                    "pcr_oi": pcr_oi,
                    "pcr_volume": pcr_vol,
                    "pcr_signal": pcr_signal,
                    "max_pain": max_pain,
                    "max_pain_vs_spot": round(max_pain - float(underlying), 2) if underlying else None,
                    "avg_iv_pct": avg_iv,
                    "top_call_oi_strikes": [{"strike": c["strike"], "oi": c["open_interest"]} for c in top_call_strikes],
                    "top_put_oi_strikes": [{"strike": p["strike"], "oi": p["open_interest"]} for p in top_put_strikes],
                })

            return clean_nan({
                "symbol": symbol,
                "underlying_price": float(underlying) if underlying else None,
                "expiries_analyzed": len(results),
                "analysis": results,
                "interpretation": {
                    "max_pain": "Price gravitates toward max pain at expiry (option writer hedging effect)",
                    "pcr_oi": "PCR > 1.2 = bearish sentiment, PCR < 0.8 = bullish sentiment",
                    "top_call_oi": "High call OI at strike = resistance level",
                    "top_put_oi": "High put OI at strike = support level",
                },
                "data_source": "yfinance (NSE options)",
                "timestamp": datetime.now().isoformat(),
            })

        except Exception as e:
            logger.warning("Options OI analytics failed for %s: %s", yf_sym, e)

    return {"error": f"Could not fetch options data for {symbol}"}


# ──────────────────────────────────────────────
# OPTIONS GREEKS (Black-Scholes)
# ──────────────────────────────────────────────

@cached(quotes_cache, ttl=300)
def get_options_greeks(symbol: str, expiry: str = None) -> dict:
    """
    Calculate Black-Scholes Greeks for all strikes in an options chain.
    Delta, Gamma, Theta, Vega, Rho — what Sensibull Pro charges for.
    """
    symbol = validate_symbol(symbol)
    RISK_FREE_RATE = 0.065  # RBI repo rate proxy

    for yf_sym in [to_nse_symbol(symbol), symbol]:
        try:
            ticker = yf.Ticker(yf_sym)
            expiry_dates = ticker.options
            if not expiry_dates:
                continue

            target_expiry = expiry if expiry and expiry in expiry_dates else expiry_dates[0]
            chain = ticker.option_chain(target_expiry)

            info = ticker.info
            S = float(info.get("regularMarketPrice") or info.get("currentPrice", 0))

            # Days to expiry
            expiry_dt = datetime.strptime(target_expiry, "%Y-%m-%d")
            T = max((expiry_dt - datetime.now()).days / 365.0, 1 / 365.0)

            def _enrich(df: Any, opt_type: str) -> list[dict]:
                rows = []
                for _, row in df.iterrows():
                    K = float(row.get("strike", 0))
                    iv = float(row.get("impliedVolatility", 0)) if pd.notna(row.get("impliedVolatility")) else 0
                    if K <= 0 or iv <= 0 or S <= 0:
                        continue
                    greeks = _bs_greeks(S, K, T, RISK_FREE_RATE, iv, opt_type)
                    oi = int(row.get("openInterest", 0)) if pd.notna(row.get("openInterest")) else 0
                    rows.append({
                        "strike": K,
                        "type": opt_type,
                        "last_price": float(row.get("lastPrice", 0)),
                        "implied_volatility_pct": round(iv * 100, 2),
                        "open_interest": oi,
                        "volume": int(row.get("volume", 0)) if pd.notna(row.get("volume")) else 0,
                        "greeks": greeks,
                        "in_the_money": bool(row.get("inTheMoney", False)),
                    })
                return rows

            calls_with_greeks = _enrich(chain.calls, "call")
            puts_with_greeks = _enrich(chain.puts, "put")

            return clean_nan({
                "symbol": symbol,
                "expiry": target_expiry,
                "all_expiries": list(expiry_dates[:6]),
                "underlying_price": S,
                "time_to_expiry_days": round(T * 365),
                "risk_free_rate_used": RISK_FREE_RATE,
                "calls": calls_with_greeks[:25],
                "puts": puts_with_greeks[:25],
                "greeks_legend": {
                    "delta": "Rate of change of option price per ₹1 move in underlying",
                    "gamma": "Rate of change of delta per ₹1 move (acceleration)",
                    "theta": "Daily time decay in option price (per day)",
                    "vega": "Change in option price per 1% change in IV",
                    "rho": "Change in option price per 1% change in interest rate",
                },
                "data_source": "yfinance + Black-Scholes model",
                "timestamp": datetime.now().isoformat(),
            })

        except Exception as e:
            logger.warning("Options Greeks failed for %s: %s", yf_sym, e)

    return {"error": f"Could not compute Greeks for {symbol}"}


# ──────────────────────────────────────────────
# NSE INSIDER TRADING (SAST Disclosures)
# ──────────────────────────────────────────────

@cached(general_cache, ttl=3600)
def get_insider_trading(symbol: str, days: int = 90) -> dict:
    """
    NSE insider trading (SAST) disclosures for a stock.
    Covers what Trendlyne and Screener.in Pro charge for.
    """
    symbol = validate_symbol(symbol).replace(".NS", "").replace(".BO", "")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    to_date = end_date.strftime("%d-%m-%Y")
    from_date = start_date.strftime("%d-%m-%Y")

    with _nse_session() as client:
        try:
            resp = client.get(
                "https://www.nseindia.com/api/corporates-insider-trading",
                params={"symbol": symbol, "from_date": from_date, "to_date": to_date},
            )
            resp.raise_for_status()
            raw = resp.json()

            data = raw if isinstance(raw, list) else raw.get("data", [])
            trades = []
            for item in data[:50]:
                trades.append({
                    "acquirer_name": item.get("acqName") or item.get("personName", ""),
                    "transaction_type": item.get("transactionType", ""),
                    "shares_traded": item.get("secAcq") or item.get("noOfShares", ""),
                    "shares_after": item.get("secHeld") or item.get("sharesAfter", ""),
                    "trade_date": item.get("tdpTransactionDate") or item.get("date", ""),
                    "trading_mode": item.get("tmTradeDate", ""),
                    "disclosure_date": item.get("xDDate", ""),
                    "remarks": item.get("remarks", ""),
                })

            buys = [t for t in trades if "acq" in (t["transaction_type"] or "").lower()
                    or "buy" in (t["transaction_type"] or "").lower()
                    or "purchase" in (t["transaction_type"] or "").lower()]
            sells = [t for t in trades if "disp" in (t["transaction_type"] or "").lower()
                     or "sell" in (t["transaction_type"] or "").lower()
                     or "sale" in (t["transaction_type"] or "").lower()]

            return clean_nan({
                "symbol": symbol,
                "period_days": days,
                "from_date": from_date,
                "to_date": to_date,
                "total_disclosures": len(trades),
                "buy_transactions": len(buys),
                "sell_transactions": len(sells),
                "insider_sentiment": "Buying" if len(buys) > len(sells) else ("Selling" if len(sells) > len(buys) else "Neutral"),
                "trades": trades,
                "data_source": "NSE SAST disclosures (public)",
                "timestamp": datetime.now().isoformat(),
            })

        except Exception as e:
            logger.warning("Insider trading fetch failed for %s: %s", symbol, e)

    # Fallback: yfinance institutional holders
    try:
        ticker = yf.Ticker(to_nse_symbol(symbol))
        holders = ticker.institutional_holders
        major = ticker.major_holders
        return clean_nan({
            "symbol": symbol,
            "note": "Using yfinance holder data (NSE SAST endpoint not available)",
            "major_holders": major.to_dict() if major is not None else {},
            "institutional_holders": holders.head(10).to_dict("records") if holders is not None else [],
            "data_source": "yfinance",
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e2:
        return {"error": f"Could not fetch insider data for {symbol}: {e2}"}


# ──────────────────────────────────────────────
# PROMOTER SHAREHOLDING PATTERN
# ──────────────────────────────────────────────

@cached(fundamentals_cache, ttl=86400)
def get_promoter_shareholding(symbol: str) -> dict:
    """
    Shareholding pattern: promoter, FII, DII, public.
    Covers what Screener.in Pro (₹4,999/yr) and Trendlyne charge for.
    """
    symbol = validate_symbol(symbol).replace(".NS", "").replace(".BO", "")

    with _nse_session() as client:
        try:
            resp = client.get(
                "https://www.nseindia.com/api/corporate-share-holding-category",
                params={"symbol": symbol},
            )
            resp.raise_for_status()
            raw = resp.json()

            categories = raw if isinstance(raw, list) else raw.get("data", [])
            holding = []
            for item in categories:
                holding.append({
                    "category": item.get("category", ""),
                    "shares_held": item.get("noOfSharesHeld", ""),
                    "pct_total": item.get("percentageSharesHeld", ""),
                    "quarter": item.get("quarter", ""),
                })

            promoter_pct = next(
                (h["pct_total"] for h in holding if "promoter" in (h["category"] or "").lower()), None
            )

            return clean_nan({
                "symbol": symbol,
                "promoter_holding_pct": promoter_pct,
                "shareholding_pattern": holding,
                "data_source": "NSE Corporate Filings",
                "timestamp": datetime.now().isoformat(),
            })

        except Exception as e:
            logger.warning("Shareholding pattern failed for %s (NSE): %s", symbol, e)

    # Fallback: yfinance major holders
    try:
        ticker = yf.Ticker(to_nse_symbol(symbol))
        mh = ticker.major_holders
        ih = ticker.institutional_holders
        mf = ticker.mutualfund_holders

        result: dict[str, Any] = {
            "symbol": symbol,
            "note": "NSE shareholding endpoint not available — showing yfinance holder data",
            "data_source": "yfinance",
            "timestamp": datetime.now().isoformat(),
        }
        if mh is not None:
            result["major_holders"] = mh.to_dict()
        if ih is not None:
            result["top_institutional_holders"] = clean_nan(ih.head(10).to_dict("records"))
        if mf is not None:
            result["top_mutual_fund_holders"] = clean_nan(mf.head(10).to_dict("records"))
        return result

    except Exception as e2:
        return {"error": f"Could not fetch shareholding for {symbol}: {e2}"}


# ──────────────────────────────────────────────
# RBI POLICY RATES
# ──────────────────────────────────────────────

@cached(general_cache, ttl=86400)
def get_rbi_policy_rates() -> dict:
    """
    Current RBI monetary policy rates.
    Bloomberg charges $24,000/year to access central bank data.
    We pull from free public sources.
    """
    # Try RBI website for current rates
    rates = {}
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            # World Bank API - India lending rate (annual, latest)
            resp = client.get(
                "https://api.worldbank.org/v2/country/IN/indicator/FR.INR.LEND",
                params={"format": "json", "mrv": 2, "per_page": 5},
            )
            data = resp.json()
            if isinstance(data, list) and len(data) > 1:
                entries = [e for e in data[1] if e.get("value") is not None]
                if entries:
                    rates["lending_rate_pct"] = entries[0]["value"]
                    rates["lending_rate_year"] = entries[0].get("date")

    except Exception as e:
        logger.warning("World Bank lending rate fetch failed: %s", e)

    # Known RBI rates (updated Feb 2025 — last policy action)
    # These are publicly announced rates from RBI press releases
    known_rates = {
        "repo_rate_pct": 6.25,
        "reverse_repo_rate_pct": 3.35,
        "marginal_standing_facility_pct": 6.50,
        "cash_reserve_ratio_pct": 4.0,
        "statutory_liquidity_ratio_pct": 18.0,
        "bank_rate_pct": 6.50,
        "last_policy_action": "Feb 2025 — RBI cut repo rate by 25 bps",
        "monetary_policy_stance": "Neutral",
        "note": "Current RBI rates as of Feb 2025 MPC meeting. Check rbi.org.in for latest.",
    }

    known_rates.update(rates)

    return {
        **known_rates,
        "data_source": "RBI Monetary Policy Committee (public) + World Bank API",
        "rbi_source": "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
        "timestamp": datetime.now().isoformat(),
    }


# ──────────────────────────────────────────────
# INDIA MACRO INDICATORS
# ──────────────────────────────────────────────

@cached(general_cache, ttl=86400)
def get_india_macro_indicators() -> dict:
    """
    India macroeconomic indicators: CPI inflation, GDP growth, current account.
    Bloomberg/Refinitiv charge $24,000+/year for macro data access.
    We use the World Bank free API (no key needed).
    """
    indicators = {
        "FP.CPI.TOTL.ZG": "cpi_inflation_pct",
        "NY.GDP.MKTP.KD.ZG": "gdp_growth_pct",
        "BN.CAB.XOKA.GD.ZS": "current_account_pct_gdp",
        "SL.UEM.TOTL.ZS": "unemployment_rate_pct",
        "NE.GDI.TOTL.ZS": "gross_capital_formation_pct_gdp",
        "FP.CPI.TOTL": "cpi_index",
    }

    result: dict = {
        "country": "India",
        "data_source": "World Bank Open Data API (free, no key required)",
        "timestamp": datetime.now().isoformat(),
    }

    try:
        with httpx.Client(timeout=15) as client:
            for indicator_code, field_name in indicators.items():
                try:
                    resp = client.get(
                        f"https://api.worldbank.org/v2/country/IN/indicator/{indicator_code}",
                        params={"format": "json", "mrv": 3, "per_page": 5},
                    )
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 1:
                        entries = [e for e in data[1] if e.get("value") is not None]
                        if entries:
                            result[field_name] = {
                                "latest_value": round(entries[0]["value"], 2),
                                "year": entries[0].get("date"),
                                "previous_value": round(entries[1]["value"], 2) if len(entries) > 1 else None,
                                "previous_year": entries[1].get("date") if len(entries) > 1 else None,
                            }
                except Exception as e:
                    logger.debug("World Bank indicator %s failed: %s", indicator_code, e)

    except Exception as e:
        logger.warning("India macro indicators fetch failed: %s", e)

    # Add RBI-published headline numbers (publicly available)
    result["rbi_headline_data"] = {
        "note": "For real-time CPI and WPI, see mospi.gov.in and rbi.org.in",
        "latest_cpi_source": "https://mospi.gov.in/",
        "rbi_inflation_target_pct": 4.0,
        "rbi_tolerance_band": "2% to 6%",
    }

    return result


# ──────────────────────────────────────────────
# AMFI MUTUAL FUND FLOWS
# ──────────────────────────────────────────────

@cached(general_cache, ttl=86400)
def get_amfi_fund_flows() -> dict:
    """
    AMFI mutual fund industry data: AUM, flows, category-wise performance.
    Morningstar Direct charges $17,500/year for fund flow data.
    AMFI publishes this free.
    """
    result: dict = {
        "data_source": "AMFI India (Association of Mutual Funds in India)",
        "timestamp": datetime.now().isoformat(),
    }

    # Try AMFI API for industry AUM data
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            # AMFI publishes monthly AUM data
            resp = client.get(
                "https://www.amfiindia.com/modules/AumReport",
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Referer": "https://www.amfiindia.com/",
                },
            )
            if resp.status_code == 200:
                result["amfi_data_available"] = True
                result["amfi_url"] = "https://www.amfiindia.com/research-information/industry-trends"

    except Exception:
        pass

    # Use mfapi.in for category level data (free, no key)
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get("https://api.mfapi.in/mf")
            if resp.status_code == 200:
                all_funds = resp.json()
                result["total_mf_schemes"] = len(all_funds)

                # Categorize funds
                categories: dict = {}
                for fund in all_funds:
                    name = fund.get("schemeName", "")
                    for cat in ["Equity", "Debt", "Hybrid", "ETF", "Index", "ELSS", "Liquid", "Gilt"]:
                        if cat.lower() in name.lower():
                            categories[cat] = categories.get(cat, 0) + 1
                            break
                result["schemes_by_category"] = categories

    except Exception as e:
        logger.debug("mfapi.in fetch failed: %s", e)

    # Known AMFI headline data (publicly published)
    result["industry_snapshot"] = {
        "total_aum_inr_cr_approx": 67_00_000,  # ~₹67 lakh crore as of early 2025
        "sip_monthly_inflows_inr_cr_approx": 26_000,  # SIP inflows ~₹26,000 cr/month
        "total_folios_approx": "22 crore+",
        "note": "Approximate figures. For latest: https://www.amfiindia.com/research-information/industry-trends",
        "monthly_detailed_data": "https://portal.amfiindia.com/DownloadData.aspx",
    }

    return result


# ──────────────────────────────────────────────
# INDIA G-SEC YIELDS
# ──────────────────────────────────────────────

@cached(general_cache, ttl=3600)
def get_india_gsec_yields() -> dict:
    """
    India Government Securities (G-Sec) yield curve.
    Bloomberg charges $24,000/year. RBI and CCIL publish this free.
    """
    yields: dict = {
        "country": "India",
        "currency": "INR",
        "data_source": "yfinance + World Bank",
        "timestamp": datetime.now().isoformat(),
    }

    # yfinance tickers for Indian government bonds/proxies
    gsec_tickers = {
        "10yr_gsec": "^INBMK",      # India benchmark 10-yr
        "india_10yr_alt": "INGVT10Y=X",
    }

    for name, ticker_sym in gsec_tickers.items():
        try:
            t = yf.Ticker(ticker_sym)
            info = t.info
            price = info.get("regularMarketPrice") or info.get("bid")
            if price:
                yields[name] = {
                    "yield_pct": price,
                    "ticker": ticker_sym,
                }
                break
        except Exception:
            pass

    # Try World Bank for India interest rates
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                "https://api.worldbank.org/v2/country/IN/indicator/FR.INR.RINR",
                params={"format": "json", "mrv": 3, "per_page": 5},
            )
            data = resp.json()
            if isinstance(data, list) and len(data) > 1:
                entries = [e for e in data[1] if e.get("value") is not None]
                if entries:
                    yields["real_interest_rate_pct"] = {
                        "value": round(entries[0]["value"], 2),
                        "year": entries[0].get("date"),
                        "source": "World Bank",
                    }
    except Exception as e:
        logger.debug("World Bank interest rate fetch: %s", e)

    # Known G-Sec yield reference points (RBI published)
    yields["reference_yields"] = {
        "note": "Indicative yields — check CCIL or RBI for live data",
        "91_day_tbill_approx_pct": 6.55,
        "182_day_tbill_approx_pct": 6.60,
        "364_day_tbill_approx_pct": 6.65,
        "5yr_gsec_approx_pct": 6.75,
        "10yr_gsec_approx_pct": 6.85,
        "30yr_gsec_approx_pct": 7.00,
        "last_updated_basis": "RBI H.1 release Q1 2025",
        "live_data_source": "https://www.ccilindia.com/",
        "rbi_source": "https://rbi.org.in/Scripts/BS_NSDPDisplay.aspx?param=4",
    }

    return yields


# ──────────────────────────────────────────────
# INDIA VIX (FEAR INDEX)
# ──────────────────────────────────────────────

@cached(quotes_cache, ttl=300)
def get_india_vix(days: int = 30) -> dict:
    """
    India VIX — the NSE volatility / fear index.
    Trendlyne charges for historical VIX data. NSE publishes it free.
    """
    try:
        ticker = yf.Ticker("^INDIAVIX")
        hist = ticker.history(period=f"{days}d")

        if hist.empty:
            return {"error": "India VIX data not available"}

        current = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
        high_30d = float(hist["High"].max())
        low_30d = float(hist["Low"].min())
        avg_30d = round(float(hist["Close"].mean()), 2)

        signal = "Low fear (market complacent)"
        if current > 25:
            signal = "High fear (panic zone — potential buying opportunity)"
        elif current > 18:
            signal = "Elevated fear (caution advised)"
        elif current > 13:
            signal = "Moderate (normal range)"

        history = []
        for date, row in hist.tail(30).iterrows():
            history.append({
                "date": str(date.date()),
                "close": round(float(row["Close"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
            })

        return clean_nan({
            "current_vix": round(current, 2),
            "change": round(current - prev, 2),
            "change_pct": round((current - prev) / prev * 100, 2) if prev else 0,
            "high_period": round(high_30d, 2),
            "low_period": round(low_30d, 2),
            "avg_period": avg_30d,
            "signal": signal,
            "interpretation": {
                "below_13": "Very low fear — market overconfident, watch for correction",
                "13_to_18": "Normal range — healthy market sentiment",
                "18_to_25": "Elevated — traders hedging, expect volatility",
                "above_25": "Fear zone — historically a good time to buy blue chips",
            },
            "history_days": days,
            "history": history,
            "data_source": "NSE India VIX via yfinance (^INDIAVIX)",
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        return {"error": f"India VIX fetch failed: {e}"}


# ──────────────────────────────────────────────
# GIFT NIFTY (SGX NIFTY SUCCESSOR)
# ──────────────────────────────────────────────

@cached(quotes_cache, ttl=60)
def get_gift_nifty() -> dict:
    """
    GIFT Nifty (formerly SGX Nifty) — pre-market indicator for Indian markets.
    Bloomberg charges for global futures data. This is free via yfinance.
    """
    result: dict = {
        "note": "GIFT Nifty direct feed — use NSE pre-open data or GIFT City exchange for live GIFT Nifty",
        "timestamp": datetime.now().isoformat(),
    }

    # Try yfinance for Nifty spot as reference
    try:
        nifty = yf.Ticker("^NSEI")
        hist = nifty.history(period="2d")

        if not hist.empty:
            prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else None
            current = float(hist["Close"].iloc[-1])
            result["nifty_spot"] = {
                "last_close": round(current, 2),
                "prev_close": round(prev_close, 2) if prev_close else None,
                "change": round(current - prev_close, 2) if prev_close else None,
                "change_pct": round((current - prev_close) / prev_close * 100, 2) if prev_close else None,
            }
    except Exception:
        pass

    # NSE pre-open session data as GIFT Nifty proxy
    with _nse_session() as client:
        try:
            resp = client.get("https://www.nseindia.com/api/market-status")
            if resp.status_code == 200:
                data = resp.json()
                result["market_status"] = data
        except Exception:
            pass

    result["gift_nifty_live"] = {
        "source": "https://www.nseindia.com/market-data/live-market-indices",
        "note": "For live GIFT Nifty: check NSE website pre-open (9:00–9:15 AM IST) or GIFT City exchange",
        "ticker_for_futures": "NIFTY futures contracts on NSE",
    }

    # Global indices as overnight sentiment
    global_sentiment = {}
    for sym, name in [("^GSPC", "S&P 500"), ("^DJI", "Dow Jones"), ("^IXIC", "NASDAQ"), ("^HSI", "Hang Seng")]:
        try:
            t = yf.Ticker(sym)
            h = t.history(period="2d")
            if not h.empty and len(h) > 1:
                c = float(h["Close"].iloc[-1])
                p = float(h["Close"].iloc[-2])
                global_sentiment[name] = {
                    "last": round(c, 2),
                    "change_pct": round((c - p) / p * 100, 2),
                }
        except Exception:
            pass

    result["global_indices_overnight"] = global_sentiment
    result["data_source"] = "yfinance + NSE"

    return clean_nan(result)


# ──────────────────────────────────────────────
# PROMOTER PLEDGE DATA
# ──────────────────────────────────────────────

@cached(fundamentals_cache, ttl=86400)
def get_promoter_pledge(symbol: str) -> dict:
    """
    Promoter pledge percentage — how much promoter holding is pledged as collateral.
    Screener Pro (₹4,999/yr) charges for this. NSE publishes it free.
    High pledge = risk signal (forced selling if stock falls).
    """
    symbol = validate_symbol(symbol).replace(".NS", "").replace(".BO", "")

    with _nse_session() as client:
        try:
            resp = client.get(
                "https://www.nseindia.com/api/corporate-share-holding-category",
                params={"symbol": symbol},
            )
            resp.raise_for_status()
            raw = resp.json()
            categories = raw if isinstance(raw, list) else raw.get("data", [])

            promoter_data = []
            for item in categories:
                cat = (item.get("category") or "").lower()
                if "promoter" in cat:
                    promoter_data.append({
                        "category": item.get("category"),
                        "shares_held": item.get("noOfSharesHeld"),
                        "pct_held": item.get("percentageSharesHeld"),
                        "pledged_shares": item.get("noOfSharesPledged"),
                        "pct_pledged_of_total": item.get("percentageSharesPledgedToTotal"),
                        "pct_pledged_of_promoter": item.get("percentageSharesPledgedToPromoter"),
                        "quarter": item.get("quarter"),
                    })

            total_pledged_pct = None
            for p in promoter_data:
                if p.get("pct_pledged_of_total"):
                    try:
                        total_pledged_pct = float(p["pct_pledged_of_total"])
                    except Exception:
                        pass

            risk = "Unknown"
            if total_pledged_pct is not None:
                if total_pledged_pct > 50:
                    risk = "HIGH RISK — more than half of promoter holding pledged"
                elif total_pledged_pct > 20:
                    risk = "Moderate risk — significant pledge, monitor closely"
                elif total_pledged_pct > 0:
                    risk = "Low risk — minor pledge"
                else:
                    risk = "Clean — no promoter pledge"

            return clean_nan({
                "symbol": symbol,
                "promoter_pledge_data": promoter_data,
                "total_pledged_pct": total_pledged_pct,
                "risk_signal": risk,
                "interpretation": "High promoter pledge = forced selling risk if stock price falls (margin call)",
                "data_source": "NSE Corporate Shareholding",
                "timestamp": datetime.now().isoformat(),
            })

        except Exception as e:
            logger.warning("Promoter pledge fetch failed for %s: %s", symbol, e)

    return {
        "symbol": symbol,
        "error": "NSE pledge data not available",
        "note": "Check NSE website: https://www.nseindia.com/companies-listing/corporate-filings-shareholding-pattern",
        "timestamp": datetime.now().isoformat(),
    }


# ──────────────────────────────────────────────
# DIVIDEND HISTORY (DEEP 10-YEAR)
# ──────────────────────────────────────────────

@cached(fundamentals_cache, ttl=86400)
def get_dividend_history_deep(symbol: str) -> dict:
    """
    10-year dividend history with yield calculation.
    Bloomberg/FactSet charge for deep dividend history. yfinance has it free.
    """
    symbol = validate_symbol(symbol)

    for yf_sym in [to_nse_symbol(symbol), symbol]:
        try:
            ticker = yf.Ticker(yf_sym)
            divs = ticker.dividends
            info = ticker.info

            if divs is None or len(divs) == 0:
                continue

            current_price = info.get("regularMarketPrice") or info.get("currentPrice", 0)

            history = []
            for date, amount in divs.items():
                history.append({
                    "date": str(date.date()),
                    "dividend": round(float(amount), 4),
                })
            history = sorted(history, key=lambda x: x["date"], reverse=True)

            # Annual dividend aggregation
            annual: dict = {}
            for item in history:
                year = item["date"][:4]
                annual[year] = annual.get(year, 0) + item["dividend"]
            annual_list = [{"year": y, "total_dividend": round(v, 4)} for y, v in sorted(annual.items(), reverse=True)]

            trailing_12m = sum(
                item["dividend"] for item in history
                if (datetime.now() - datetime.strptime(item["date"], "%Y-%m-%d")).days <= 365
            )
            div_yield = round(trailing_12m / current_price * 100, 2) if current_price else None

            return clean_nan({
                "symbol": symbol.replace(".NS", "").replace(".BO", ""),
                "current_price": current_price,
                "trailing_12m_dividend": round(trailing_12m, 4),
                "dividend_yield_pct": div_yield,
                "total_dividends_on_record": len(history),
                "annual_summary": annual_list[:10],
                "full_history": history[:60],
                "data_source": "yfinance",
                "timestamp": datetime.now().isoformat(),
            })

        except Exception as e:
            logger.warning("Dividend history failed for %s: %s", yf_sym, e)

    return {"error": f"Dividend history not available for {symbol}"}


# ──────────────────────────────────────────────
# INDIA VIX PCR HISTORICAL (NIFTY OPTIONS)
# ──────────────────────────────────────────────

@cached(quotes_cache, ttl=300)
def get_nifty_pcr_trend(num_expiries: int = 5) -> dict:
    """
    Nifty PCR (Put-Call Ratio) trend across multiple expiries.
    Sensibull charges ₹1,300/month for PCR trend data. We calculate it free.
    """
    try:
        ticker = yf.Ticker("^NSEI")
        expiry_dates = ticker.options

        if not expiry_dates:
            return {"error": "NIFTY options data not available"}

        pcr_trend = []
        for expiry in list(expiry_dates)[:num_expiries]:
            try:
                chain = ticker.option_chain(expiry)
                calls = chain.calls
                puts = chain.puts

                call_oi = int(calls["openInterest"].fillna(0).sum())
                put_oi = int(puts["openInterest"].fillna(0).sum())
                call_vol = int(calls["volume"].fillna(0).sum())
                put_vol = int(puts["volume"].fillna(0).sum())

                pcr_oi = round(put_oi / call_oi, 3) if call_oi > 0 else None
                pcr_vol = round(put_vol / call_vol, 3) if call_vol > 0 else None

                signal = "Neutral"
                if pcr_oi:
                    if pcr_oi > 1.3:
                        signal = "Bullish reversal (oversold)"
                    elif pcr_oi > 1.0:
                        signal = "Bearish bias"
                    elif pcr_oi < 0.7:
                        signal = "Bearish reversal (overbought)"
                    else:
                        signal = "Bullish bias"

                pcr_trend.append({
                    "expiry": expiry,
                    "pcr_oi": pcr_oi,
                    "pcr_volume": pcr_vol,
                    "total_call_oi": call_oi,
                    "total_put_oi": put_oi,
                    "signal": signal,
                })
            except Exception:
                continue

        overall_pcr = None
        if pcr_trend:
            vals = [p["pcr_oi"] for p in pcr_trend if p["pcr_oi"]]
            overall_pcr = round(sum(vals) / len(vals), 3) if vals else None

        return clean_nan({
            "index": "NIFTY 50",
            "overall_pcr": overall_pcr,
            "overall_signal": (
                "Bearish sentiment" if overall_pcr and overall_pcr > 1.1
                else "Bullish sentiment" if overall_pcr and overall_pcr < 0.9
                else "Neutral"
            ) if overall_pcr else "Insufficient data",
            "expiry_breakdown": pcr_trend,
            "data_source": "NSE options via yfinance",
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        return {"error": f"Nifty PCR trend failed: {e}"}
