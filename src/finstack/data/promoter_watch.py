"""
Promoter pledge early warning system for FinStack MCP.

Tracks pledge % change velocity across Nifty 500.
Alerts when promoter pledge increases > 5% in one quarter.

"Caught 3 stocks before they fell 40% — promoter was pledging shares"
Data: NSE shareholding disclosures (public, quarterly)
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger("finstack.promoter_watch")

# High-risk pledge thresholds
PLEDGE_HIGH    = 30.0   # > 30% pledged = high risk
PLEDGE_RISING  =  5.0   # > 5% QoQ increase = early warning
PLEDGE_CRITICAL = 50.0  # > 50% = critical, avoid


def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        logger.debug("Promoter watch error: %s", e)
        return None


def get_pledge_alert(symbol: str) -> dict:
    """
    Promoter pledge early warning for an NSE stock.

    Checks:
      - Current pledge % vs previous quarter
      - Rate of change (velocity)
      - Risk classification: safe / watch / danger / critical

    Args:
        symbol: NSE stock symbol (e.g. ADANIENT, ZEEL, RCOM)

    Returns:
        - pledge_pct: current pledged %
        - pledge_change_qoq: change vs previous quarter
        - risk_level: safe / watch / danger / critical
        - alert: human-readable warning if triggered
        - historical: last 4 quarters of pledge data
    """
    symbol = symbol.upper().replace(".NS", "").replace(".BO", "")

    from finstack.data.market_intelligence import get_promoter_pledge, get_promoter_shareholding

    pledge_data = _safe(get_promoter_pledge, symbol)
    sh_data     = _safe(get_promoter_shareholding, symbol)

    current_pledge = None
    prev_pledge    = None
    pledge_history = []
    promoter_pct   = None

    if pledge_data and isinstance(pledge_data, dict):
        current_pledge = pledge_data.get("pledge_pct") or pledge_data.get("pledged")
        if current_pledge:
            current_pledge = float(current_pledge)

    if sh_data and isinstance(sh_data, dict):
        sh = sh_data.get("shareholding", {})
        promoter_pct = sh.get("promoter_pct")

        history = sh_data.get("history") or []
        for q in history[:4]:
            pledge_val = q.get("pledge_pct") or q.get("pledge") or q.get("pledged")
            if pledge_val is not None:
                pledge_history.append({
                    "quarter": q.get("quarter") or q.get("date", ""),
                    "pledge_pct": round(float(pledge_val), 2),
                })

        if len(pledge_history) >= 2 and current_pledge is None:
            current_pledge = pledge_history[0]["pledge_pct"]
        if len(pledge_history) >= 2:
            prev_pledge = pledge_history[1]["pledge_pct"]

    if current_pledge is None:
        return {
            "symbol": symbol,
            "error": "Pledge data unavailable for this stock",
            "note": "Data sourced from NSE shareholding disclosures (quarterly)",
        }

    change_qoq = round(current_pledge - prev_pledge, 2) if prev_pledge is not None else None

    # Risk classification
    if current_pledge >= PLEDGE_CRITICAL:
        risk_level = "critical"
        alert = (
            f"CRITICAL: {current_pledge:.1f}% of promoter shares pledged. "
            "Above 50% — any margin call can trigger forced selling and stock collapse."
        )
    elif current_pledge >= PLEDGE_HIGH:
        risk_level = "danger"
        alert = (
            f"DANGER: {current_pledge:.1f}% pledged. "
            "High pledge ratio — stock vulnerable to margin call cascades."
        )
    elif change_qoq and change_qoq >= PLEDGE_RISING:
        risk_level = "watch"
        alert = (
            f"WATCH: Pledge increased by {change_qoq:.1f}% this quarter (now {current_pledge:.1f}%). "
            "Rising pledge = promoter under financial stress. Monitor next quarter."
        )
    elif current_pledge > 10:
        risk_level = "watch"
        alert = f"Pledge at {current_pledge:.1f}% — elevated but not alarming. Watch for further increase."
    else:
        risk_level = "safe"
        alert = f"Pledge at {current_pledge:.1f}% — low, no concern."

    return {
        "symbol":            symbol,
        "promoter_pct":      promoter_pct,
        "pledge_pct":        current_pledge,
        "pledge_change_qoq": change_qoq,
        "risk_level":        risk_level,
        "alert":             alert,
        "historical":        pledge_history,
        "thresholds": {
            "safe":     "< 10%",
            "watch":    "10–30% or rising > 5% QoQ",
            "danger":   "30–50%",
            "critical": "> 50%",
        },
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "disclaimer": "Based on public NSE shareholding disclosures. Not SEBI-registered advice.",
    }


def scan_pledge_risks(symbols: list[str]) -> dict:
    """
    Scan multiple stocks for pledge risk simultaneously.
    Returns sorted by risk level (critical first).

    Args:
        symbols: list of NSE symbols (e.g. ["ADANIENT", "ZEEL", "RELIANCE"])
    """
    results = []
    risk_order = {"critical": 0, "danger": 1, "watch": 2, "safe": 3}

    for sym in symbols:
        result = get_pledge_alert(sym)
        if "error" not in result:
            results.append(result)

    results.sort(key=lambda r: risk_order.get(r.get("risk_level", "safe"), 3))

    alerts = [r for r in results if r.get("risk_level") in ("critical", "danger", "watch")]

    return {
        "scanned": len(symbols),
        "alerts_count": len(alerts),
        "alerts": alerts,
        "all_results": results,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }
