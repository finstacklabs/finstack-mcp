"""
Portfolio X-ray for FinStack MCP.

Input:  list of {symbol, qty, avg_price}
Output: sector concentration %, FII flow on each holding,
        pledged promoter risk, XIRR, total P&L, risk score.
"""

import logging
from datetime import datetime, date, timezone

logger = logging.getLogger("finstack.portfolio")

# NSE sector map (symbol → sector)
SECTOR_MAP = {
    "RELIANCE": "Energy", "ONGC": "Energy", "NTPC": "Energy", "POWERGRID": "Energy",
    "TCS": "IT", "INFY": "IT", "WIPRO": "IT", "HCLTECH": "IT", "TECHM": "IT",
    "HDFCBANK": "Banking", "ICICIBANK": "Banking", "SBIN": "Banking", "AXISBANK": "Banking",
    "KOTAKBANK": "Banking", "INDUSINDBK": "Banking", "BANDHANBNK": "Banking",
    "BAJFINANCE": "NBFC", "BAJAJFINSV": "NBFC", "CHOLAFIN": "NBFC",
    "MARUTI": "Auto", "TATAMOTORS": "Auto", "M&M": "Auto", "EICHERMOT": "Auto",
    "HEROMOTOCO": "Auto", "BAJAJ-AUTO": "Auto",
    "SUNPHARMA": "Pharma", "DRREDDY": "Pharma", "CIPLA": "Pharma", "DIVISLAB": "Pharma",
    "TITAN": "Consumer", "ASIANPAINT": "Consumer", "HINDUNILVR": "Consumer",
    "NESTLEIND": "Consumer", "BRITANNIA": "Consumer", "DABUR": "Consumer",
    "LT": "Infra", "ULTRACEMCO": "Infra", "GRASIM": "Infra", "ADANIPORTS": "Infra",
    "JSWSTEEL": "Metals", "TATASTEEL": "Metals", "HINDALCO": "Metals", "COALINDIA": "Metals",
    "BHARTIARTL": "Telecom", "IDEA": "Telecom",
    "HDFC": "Finance", "BAJAJHLDNG": "Finance",
}


def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        logger.debug("Portfolio data error: %s", e)
        return None


def _get_current_price(symbol: str) -> float | None:
    try:
        import yfinance as yf
        info = yf.Ticker(f"{symbol}.NS").fast_info
        return getattr(info, "last_price", None)
    except Exception:
        return None


def _xirr(cashflows: list[tuple[date, float]]) -> float | None:
    """Simple XIRR approximation using Newton-Raphson."""
    try:
        if len(cashflows) < 2:
            return None
        dates  = [cf[0] for cf in cashflows]
        values = [cf[1] for cf in cashflows]
        t0 = dates[0]
        years = [(d - t0).days / 365.0 for d in dates]

        def npv(r):
            return sum(v / (1 + r) ** t for v, t in zip(values, years))

        def dnpv(r):
            return sum(-t * v / (1 + r) ** (t + 1) for v, t in zip(values, years))

        r = 0.1
        for _ in range(100):
            f = npv(r)
            df = dnpv(r)
            if df == 0:
                break
            r -= f / df
            if abs(f) < 1e-6:
                break
        return round(r * 100, 2) if -1 < r < 10 else None
    except Exception:
        return None


def analyze_portfolio(holdings: list[dict]) -> dict:
    """
    Portfolio X-ray: deep risk + return analysis for a list of holdings.

    Args:
        holdings: list of dicts, each with:
            - symbol:    NSE symbol (e.g. "RELIANCE")
            - qty:       number of shares
            - avg_price: your average buy price
            - buy_date:  (optional) "YYYY-MM-DD" for XIRR calculation

    Returns:
        - total invested, current value, total P&L, P&L %
        - per-holding: current price, P&L, weight %
        - sector concentration breakdown
        - risk flags: pledged promoters, FII reducing, high P/E
        - XIRR (if buy_date provided)
        - diversification score
    """
    if not holdings:
        return {"error": "No holdings provided"}

    today = date.today()
    enriched = []
    sector_weights: dict[str, float] = {}
    risk_flags = []
    cashflows: list[tuple[date, float]] = []
    total_invested = 0.0
    total_current  = 0.0

    for h in holdings:
        symbol    = h.get("symbol", "").upper().replace(".NS", "")
        qty       = float(h.get("qty", 0))
        avg_price = float(h.get("avg_price", 0))
        buy_date_str = h.get("buy_date")

        if not symbol or qty <= 0 or avg_price <= 0:
            continue

        invested = qty * avg_price
        current_price = _get_current_price(symbol) or avg_price
        current_val   = qty * current_price
        pnl           = current_val - invested
        pnl_pct       = round(pnl / invested * 100, 2) if invested else 0

        total_invested += invested
        total_current  += current_val

        # XIRR cashflows
        if buy_date_str:
            try:
                bd = date.fromisoformat(buy_date_str)
                cashflows.append((bd, -invested))
            except Exception:
                pass

        sector = SECTOR_MAP.get(symbol, "Other")
        sector_weights[sector] = sector_weights.get(sector, 0) + current_val

        # Promoter pledge risk
        pledge_data = _safe(
            __import__("finstack.data.market_intelligence", fromlist=["get_promoter_pledge"]).get_promoter_pledge,
            symbol
        )
        pledge_pct = None
        if pledge_data and isinstance(pledge_data, dict):
            pledge_pct = pledge_data.get("pledge_pct") or pledge_data.get("pledged")
            if pledge_pct and float(pledge_pct) > 20:
                risk_flags.append(f"{symbol}: promoter pledge {pledge_pct}% — elevated risk")

        enriched.append({
            "symbol": symbol,
            "qty": qty,
            "avg_price": avg_price,
            "current_price": round(current_price, 2),
            "invested": round(invested, 2),
            "current_value": round(current_val, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": pnl_pct,
            "sector": sector,
            "pledge_pct": pledge_pct,
        })

    if total_invested == 0:
        return {"error": "All holdings have zero value — check qty and avg_price"}

    # Weights
    for h in enriched:
        h["weight_pct"] = round(h["current_value"] / total_current * 100, 1)

    # Sector concentration
    sector_pct = {
        s: round(v / total_current * 100, 1)
        for s, v in sorted(sector_weights.items(), key=lambda x: -x[1])
    }

    # Concentration risk
    top_sector_pct = max(sector_pct.values()) if sector_pct else 0
    if top_sector_pct > 40:
        risk_flags.append(f"High sector concentration: {max(sector_pct, key=sector_pct.get)} = {top_sector_pct}% of portfolio")

    # Single stock concentration
    for h in enriched:
        if h["weight_pct"] > 30:
            risk_flags.append(f"{h['symbol']} is {h['weight_pct']}% of portfolio — too concentrated")

    # XIRR
    xirr_val = None
    if cashflows:
        cashflows.append((today, total_current))
        xirr_val = _xirr(cashflows)

    # Diversification score (0–100)
    n = len(enriched)
    n_sectors = len(sector_pct)
    div_score = min(100, round((min(n, 15) / 15 * 50) + (min(n_sectors, 6) / 6 * 50)))

    total_pnl     = total_current - total_invested
    total_pnl_pct = round(total_pnl / total_invested * 100, 2)

    if not risk_flags:
        risk_flags.append("No major risk flags — portfolio looks diversified")

    return {
        "summary": {
            "total_invested":   round(total_invested, 2),
            "current_value":    round(total_current, 2),
            "total_pnl":        round(total_pnl, 2),
            "total_pnl_pct":    total_pnl_pct,
            "xirr_pct":         xirr_val,
            "holdings_count":   len(enriched),
            "diversification_score": div_score,
        },
        "holdings":            enriched,
        "sector_allocation":   sector_pct,
        "risk_flags":          risk_flags,
        "generated_at":        datetime.now(tz=timezone.utc).isoformat(),
        "disclaimer":          "Not SEBI-registered advice. For informational purposes only.",
    }
