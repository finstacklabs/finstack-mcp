"""
Smart money / unusual activity detector for FinStack MCP.

Detects:
  • Options OI buildup > 2x average across strikes
  • Block deal and bulk deal spikes
  • Promoter buying from shareholding changes
  • Volume anomaly (current vs 20-day average)

The "someone knows something" signal for Indian markets.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger("finstack.smart_money")


def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        logger.debug("Smart money data error: %s", e)
        return None


def _check_volume_anomaly(symbol: str) -> dict | None:
    """Volume vs 20-day average."""
    try:
        import yfinance as yf
        hist = yf.Ticker(f"{symbol}.NS").history(period="22d")
        if hist.empty or len(hist) < 5:
            return None
        avg_vol = hist["Volume"].iloc[:-1].mean()
        cur_vol = hist["Volume"].iloc[-1]
        ratio = cur_vol / avg_vol if avg_vol > 0 else 0
        return {
            "current_volume": int(cur_vol),
            "avg_volume_20d": int(avg_vol),
            "ratio": round(ratio, 2),
            "anomaly": ratio >= 2.0,
            "signal": f"Volume {ratio:.1f}x average — {'unusual activity detected' if ratio >= 2 else 'normal'}",
        }
    except Exception as e:
        logger.debug("Volume anomaly error: %s", e)
        return None


def _check_oi_buildup(symbol: str) -> dict | None:
    """Options OI buildup — check if any strike has 2x average OI."""
    from finstack.data.market_intelligence import get_options_oi_analytics

    oi_data = _safe(get_options_oi_analytics, symbol)
    if not oi_data or not isinstance(oi_data, dict):
        return None

    chain = oi_data.get("chain") or oi_data.get("options_chain") or []
    if not chain:
        return None

    # Compute total OI per strike (call + put)
    strike_oi = {}
    for row in chain:
        strike = row.get("strike_price") or row.get("strike")
        if not strike:
            continue
        call_oi = row.get("call_oi", 0) or 0
        put_oi  = row.get("put_oi", 0) or 0
        strike_oi[strike] = (call_oi or 0) + (put_oi or 0)

    if not strike_oi:
        return None

    oi_values = list(strike_oi.values())
    avg_oi = sum(oi_values) / len(oi_values) if oi_values else 0

    # Find strikes with >= 2x average
    unusual = [
        {"strike": k, "total_oi": v, "ratio": round(v / avg_oi, 1)}
        for k, v in strike_oi.items()
        if avg_oi > 0 and v >= avg_oi * 2
    ]
    unusual.sort(key=lambda x: x["ratio"], reverse=True)

    if unusual:
        top = unusual[0]
        return {
            "unusual_strikes": unusual[:5],
            "avg_oi_per_strike": int(avg_oi),
            "anomaly": True,
            "signal": (
                f"Unusual OI at {top['strike']} strike ({top['ratio']}x average) — "
                "someone is positioning for a big move"
            ),
        }
    return {
        "unusual_strikes": [],
        "avg_oi_per_strike": int(avg_oi),
        "anomaly": False,
        "signal": "OI distribution normal — no unusual positioning",
    }


def _check_block_bulk_deals(symbol: str) -> dict | None:
    """Check recent block/bulk deals."""
    from finstack.data.nse_advanced import get_nse_bulk_deals

    deals_data = _safe(get_nse_bulk_deals)
    if not deals_data:
        return None

    # Filter for this symbol
    deals = []
    raw = deals_data if isinstance(deals_data, list) else deals_data.get("data", [])
    for d in raw:
        sym = (d.get("symbol") or d.get("SYMBOL") or "").upper()
        if sym == symbol.upper():
            deals.append({
                "date":     d.get("date") or d.get("BD_DT_DATE", ""),
                "client":   d.get("clientName") or d.get("BD_CLIENT_NAME", ""),
                "buy_sell": d.get("buySell") or d.get("BD_BUY_SELL", ""),
                "qty":      d.get("tradedQty") or d.get("BD_QTY_TRD", 0),
                "price":    d.get("tradePrice") or d.get("BD_TP_WATP", 0),
            })

    if not deals:
        return {"deals": [], "anomaly": False, "signal": "No recent block/bulk deals"}

    buy_deals  = [d for d in deals if "B" in str(d["buy_sell"]).upper()]
    sell_deals = [d for d in deals if "S" in str(d["buy_sell"]).upper()]

    signal_parts = []
    if buy_deals:
        signal_parts.append(f"{len(buy_deals)} bulk buy deal(s) — institutions accumulating")
    if sell_deals:
        signal_parts.append(f"{len(sell_deals)} bulk sell deal(s) — institutional distribution")

    return {
        "deals": deals[:10],
        "buy_count":  len(buy_deals),
        "sell_count": len(sell_deals),
        "anomaly": len(deals) > 0,
        "signal": " · ".join(signal_parts) if signal_parts else "Block/bulk activity detected",
    }


def _check_promoter_buying(symbol: str) -> dict | None:
    """Detect recent promoter shareholding increase."""
    from finstack.data.market_intelligence import get_promoter_shareholding

    data = _safe(get_promoter_shareholding, symbol)
    if not data or not isinstance(data, dict):
        return None

    history = data.get("history") or data.get("quarterly_history") or []
    if len(history) < 2:
        sh = data.get("shareholding", {})
        pct = sh.get("promoter_pct")
        if pct:
            return {
                "current_promoter_pct": pct,
                "change": None,
                "anomaly": False,
                "signal": f"Promoter holding {pct:.1f}% — no historical change data",
            }
        return None

    # Compare latest 2 quarters
    latest = history[0].get("promoter_pct") or history[0].get("promoter")
    prev   = history[1].get("promoter_pct") or history[1].get("promoter")

    if latest is None or prev is None:
        return None

    change = round(latest - prev, 2)
    anomaly = abs(change) >= 1.0  # 1% or more is notable

    if change > 0:
        signal = f"Promoter increased holding by {change:.1f}% QoQ — insider buying signal"
    elif change < 0:
        signal = f"Promoter reduced holding by {abs(change):.1f}% QoQ — insider selling"
    else:
        signal = "Promoter holding unchanged QoQ"

    return {
        "current_promoter_pct": latest,
        "previous_promoter_pct": prev,
        "change": change,
        "anomaly": anomaly,
        "signal": signal,
    }


# ── Main entry point ──────────────────────────────────────────────────────────

def detect_unusual_activity(symbol: str) -> dict:
    """
    Detect smart money / unusual activity for an NSE stock.

    Checks:
      1. Volume anomaly (2x+ average)
      2. Options OI buildup at specific strikes
      3. Block/bulk deals
      4. Promoter shareholding change

    Args:
        symbol: NSE stock symbol (e.g. RELIANCE, INFY, SBIN)

    Returns:
        Structured report with per-category findings + overall verdict.
    """
    symbol = symbol.upper().replace(".NS", "").replace(".BO", "")
    logger.info("Smart money scan for %s", symbol)

    findings = {}
    alerts = []

    # 1. Volume
    vol = _check_volume_anomaly(symbol)
    findings["volume"] = vol
    if vol and vol.get("anomaly"):
        alerts.append(vol["signal"])

    # 2. OI buildup
    oi = _check_oi_buildup(symbol)
    findings["options_oi"] = oi
    if oi and oi.get("anomaly"):
        alerts.append(oi["signal"])

    # 3. Block/bulk deals
    deals = _check_block_bulk_deals(symbol)
    findings["block_deals"] = deals
    if deals and deals.get("anomaly"):
        alerts.append(deals["signal"])

    # 4. Promoter buying
    promoter = _check_promoter_buying(symbol)
    findings["promoter"] = promoter
    if promoter and promoter.get("anomaly"):
        alerts.append(promoter["signal"])

    # Overall verdict
    alert_count = len(alerts)
    if alert_count >= 3:
        verdict = "HIGH ALERT — multiple smart money signals firing simultaneously"
        level = "high"
    elif alert_count >= 2:
        verdict = "MODERATE ALERT — some unusual activity detected"
        level = "moderate"
    elif alert_count == 1:
        verdict = "LOW ALERT — one unusual signal detected"
        level = "low"
    else:
        verdict = "No unusual activity — nothing to act on right now"
        level = "none"

    return {
        "symbol": symbol,
        "alert_level": level,
        "verdict": verdict,
        "alerts": alerts,
        "findings": findings,
        "scanned_at": datetime.now(tz=timezone.utc).isoformat(),
        "disclaimer": "Smart money signals are indicative only. Not SEBI-registered advice.",
    }
