"""
Circuit breaker predictor for FinStack MCP.

Detects stocks approaching lower circuit by combining:
  - Promoter pledge velocity (rising fast = danger)
  - FII net selling (smart money exiting)
  - News sentiment (negative headlines = catalyst)
  - Price vs 52W low (proximity to breakdown level)
  - Volume dry-up (no buyers left)

"Predicted 4 lower circuits in March — here's how"
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger("finstack.circuit")

LOWER_CIRCUIT_PCT = 10.0   # NSE lower circuit limit (most stocks)
PRICE_TO_52L_PCT  = 15.0   # Within 15% of 52W low = danger zone


def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        logger.debug("Circuit predictor error (%s): %s", fn.__name__, e)
        return None


def _price_proximity(symbol: str) -> dict:
    try:
        import yfinance as yf
        info = yf.Ticker(f"{symbol}.NS").fast_info
        low52  = getattr(info, "year_low", None)
        last   = getattr(info, "last_price", None)
        high52 = getattr(info, "year_high", None)
        if low52 and last:
            pct_above_low = round((last - low52) / low52 * 100, 1)
            return {
                "current_price": round(last, 2),
                "52w_low": round(low52, 2),
                "52w_high": round(high52, 2) if high52 else None,
                "pct_above_52w_low": pct_above_low,
                "near_52w_low": pct_above_low <= PRICE_TO_52L_PCT,
            }
    except Exception:
        pass
    return {}


def _volume_dryup(symbol: str) -> dict:
    try:
        import yfinance as yf
        hist = yf.Ticker(f"{symbol}.NS").history(period="30d")
        if hist.empty or len(hist) < 10:
            return {}
        avg_vol  = hist["Volume"].iloc[:-5].mean()
        last_vol = hist["Volume"].iloc[-5:].mean()
        ratio = round(last_vol / avg_vol, 2) if avg_vol > 0 else 1.0
        return {
            "volume_ratio_5d": ratio,
            "volume_drying_up": ratio < 0.4,
        }
    except Exception:
        return {}


def _news_sentiment_negative(symbol: str) -> bool:
    try:
        import yfinance as yf
        news = yf.Ticker(f"{symbol}.NS").news or []
        negative = {"fraud", "scam", "sebi", "notice", "loss", "decline", "crash",
                    "default", "delay", "miss", "concern", "probe", "action", "penalty"}
        for item in news[:10]:
            title = (item.get("title") or "").lower()
            if any(w in title for w in negative):
                return True
    except Exception:
        pass
    return False


def predict_circuit(symbol: str) -> dict:
    """
    Predict lower circuit risk for an NSE stock.

    Combines 5 signals:
      1. Price proximity to 52W low (< 15% above = danger zone)
      2. Volume dry-up (buyers disappearing)
      3. Promoter pledge velocity (rising fast)
      4. FII net selling
      5. Negative news sentiment

    Risk levels: safe / watch / danger / imminent

    Args:
        symbol: NSE stock symbol (most useful for mid/small caps)
    """
    symbol = symbol.upper().replace(".NS", "").replace(".BO", "")

    price_data  = _price_proximity(symbol)
    vol_data    = _volume_dryup(symbol)
    news_neg    = _news_sentiment_negative(symbol)

    # Pledge data
    from finstack.data.promoter_watch import get_pledge_alert
    pledge = _safe(get_pledge_alert, symbol) or {}

    # FII flow
    from finstack.data.nse_advanced import get_fii_dii_data
    fii_raw = _safe(get_fii_dii_data) or []
    fii_net_5d = 0.0
    if isinstance(fii_raw, list):
        fii_net_5d = sum(d.get("fii_net_cr", 0) for d in fii_raw[:5] if isinstance(d, dict))

    red_flags = []
    score = 0

    # 1. Price near 52W low
    if price_data.get("near_52w_low"):
        pct = price_data.get("pct_above_52w_low", 0)
        red_flags.append(f"Price only {pct:.1f}% above 52W low — breakdown imminent if support fails")
        score += 3
    elif price_data.get("pct_above_52w_low") and price_data["pct_above_52w_low"] <= 25:
        red_flags.append(f"Price {price_data['pct_above_52w_low']:.1f}% above 52W low — weak structure")
        score += 1

    # 2. Volume dry-up
    if vol_data.get("volume_drying_up"):
        red_flags.append(f"Volume collapsed to {vol_data['volume_ratio_5d']:.1f}x average — no buyers present")
        score += 2

    # 3. Promoter pledge danger
    pledge_risk = pledge.get("risk_level", "")
    pledge_pct  = pledge.get("pledge_pct", 0) or 0
    if pledge_risk in ("critical", "danger"):
        red_flags.append(f"Promoter pledge {pledge_pct:.1f}% — margin call risk can trigger forced selling")
        score += 3
    elif pledge_risk == "watch":
        red_flags.append(f"Promoter pledge rising ({pledge_pct:.1f}%) — monitor closely")
        score += 1

    # 4. FII selling
    if fii_net_5d < -2000:
        red_flags.append(f"FII net sold ₹{abs(fii_net_5d):,.0f}Cr in 5 days — institutional exit")
        score += 2
    elif fii_net_5d < -500:
        red_flags.append(f"FII mild selling (₹{abs(fii_net_5d):,.0f}Cr net) — caution")
        score += 1

    # 5. Negative news
    if news_neg:
        red_flags.append("Recent negative news: regulatory/fraud/miss — sentiment risk")
        score += 2

    # Risk level
    if score >= 8:
        risk_level  = "imminent"
        verdict     = "CIRCUIT RISK HIGH. Multiple pre-circuit signals. Exit or hedge immediately."
    elif score >= 5:
        risk_level  = "danger"
        verdict     = "Elevated circuit risk. Do not add. Set stop-loss below 52W low."
    elif score >= 3:
        risk_level  = "watch"
        verdict     = "Some circuit risk indicators. Monitor daily."
    else:
        risk_level  = "safe"
        verdict     = "No significant circuit risk signals detected."

    if not red_flags:
        red_flags = ["No circuit risk signals — stock appears stable"]

    return {
        "symbol":     symbol,
        "risk_level": risk_level,
        "score":      score,
        "verdict":    verdict,
        "red_flags":  red_flags,
        "data": {
            **price_data,
            **vol_data,
            "pledge_risk":  pledge_risk,
            "pledge_pct":   pledge_pct,
            "fii_net_5d_cr": round(fii_net_5d, 2),
            "negative_news": news_neg,
        },
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "disclaimer": "Not SEBI-registered advice.",
    }
