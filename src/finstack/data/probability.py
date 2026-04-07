"""
Nifty direction probability score for FinStack MCP.

Inputs:
  RSI(14)              — momentum
  FII net flow 5d      — smart money direction
  Put/Call Ratio (PCR) — market positioning
  India VIX            — fear level
  G-Sec 10Y yield      — risk-free rate pressure
  GIFT Nifty premium   — overnight global signal

Output: single % probability Nifty closes UP tomorrow + bull/bear factors.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger("finstack.probability")


def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        logger.debug("Probability data error: %s", e)
        return None


def _get_nifty_rsi() -> float | None:
    """Nifty 50 RSI(14) from yfinance."""
    try:
        import yfinance as yf
        hist = yf.Ticker("^NSEI").history(period="30d")
        if hist.empty or len(hist) < 15:
            return None
        close = hist["Close"]
        delta = close.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / loss.replace(0, float("nan"))
        rsi   = 100 - (100 / (1 + rs))
        return round(float(rsi.iloc[-1]), 2)
    except Exception as e:
        logger.debug("Nifty RSI error: %s", e)
        return None


def _get_fii_net_5d() -> float | None:
    """FII net flow over last 5 trading days in Cr."""
    from finstack.data.nse_advanced import get_fii_dii_data
    data = _safe(get_fii_dii_data)
    if not data or not isinstance(data, list):
        return None
    nets = [d.get("fii_net_cr", 0) for d in data[:5] if isinstance(d, dict)]
    return round(sum(nets), 2) if nets else None


def _get_pcr() -> float | None:
    """Nifty overall Put/Call ratio from PCR trend tool."""
    from finstack.data.market_intelligence import get_nifty_pcr_trend
    data = _safe(get_nifty_pcr_trend)
    if not data or not isinstance(data, dict):
        return None
    return data.get("overall_pcr") or data.get("pcr")


def _get_vix() -> float | None:
    """India VIX current value."""
    from finstack.data.market_intelligence import get_india_vix
    data = _safe(get_india_vix)
    if not data or not isinstance(data, dict):
        return None
    return data.get("vix") or data.get("current")


def _get_gsec_10y() -> float | None:
    """India 10-year G-Sec yield. Falls back to RBI reference value."""
    try:
        import yfinance as yf
        for sym in ("^INBMK", "INGVT10Y=X"):
            try:
                t = yf.Ticker(sym)
                info = t.info
                price = info.get("regularMarketPrice") or info.get("bid")
                if price:
                    return round(float(price), 3)
                hist = t.history(period="3d")
                if not hist.empty:
                    return round(float(hist["Close"].iloc[-1]), 3)
            except Exception:
                continue
    except Exception:
        pass
    return 6.85  # RBI published 10Y G-Sec reference (Apr 2025)


def _get_gift_nifty_premium() -> float | None:
    """GIFT Nifty premium vs Nifty spot."""
    from finstack.data.market_intelligence import get_gift_nifty
    data = _safe(get_gift_nifty)
    if not data or not isinstance(data, dict):
        return None
    return data.get("premium") or data.get("gift_premium")


# ── Scoring engine ────────────────────────────────────────────────────────────

def _score_input(name: str, value, thresholds: dict) -> tuple[float, str]:
    """
    Score a single input between -1.0 (strong bear) and +1.0 (strong bull).
    thresholds: {bull_strong, bull_mild, bear_mild, bear_strong}
    """
    if value is None:
        return 0.0, f"{name}: data unavailable (neutral)"

    bs = thresholds.get("bull_strong")
    bm = thresholds.get("bull_mild")
    br = thresholds.get("bear_mild")
    be = thresholds.get("bear_strong")

    # RSI-style: low = bullish (oversold), high = bearish
    if thresholds.get("inverted"):
        if bs and value <= bs:
            return 1.0, f"{name} {value} — strongly bullish"
        if bm and value <= bm:
            return 0.5, f"{name} {value} — mildly bullish"
        if br and value >= br:
            return -0.5, f"{name} {value} — mildly bearish"
        if be and value >= be:
            return -1.0, f"{name} {value} — strongly bearish"
        return 0.0, f"{name} {value} — neutral"

    # Normal: high = bullish
    if bs and value >= bs:
        return 1.0, f"{name} {value} — strongly bullish"
    if bm and value >= bm:
        return 0.5, f"{name} {value} — mildly bullish"
    if br and value <= br:
        return -0.5, f"{name} {value} — mildly bearish"
    if be and value <= be:
        return -1.0, f"{name} {value} — strongly bearish"
    return 0.0, f"{name} {value} — neutral"


# ── Main entry point ──────────────────────────────────────────────────────────

def get_nifty_outlook() -> dict:
    """
    Compute Nifty 50 direction probability for the next trading session.

    Aggregates 6 market signals into a single probability score:
      • RSI(14)         — momentum / mean-reversion
      • FII net flow    — institutional direction
      • PCR             — options market sentiment
      • India VIX       — fear vs greed
      • G-Sec 10Y yield — macro interest rate pressure
      • GIFT Nifty      — overnight global pre-market signal

    Returns:
        {
            "probability_up": 67,        # % chance Nifty closes up tomorrow
            "signal": "Cautiously bullish",
            "bull_factors": [...],
            "bear_factors": [...],
            "inputs": { rsi, fii_net_5d, pcr, vix, gsec_10y, gift_premium },
        }
    """
    logger.info("Computing Nifty direction probability")

    # Fetch all inputs in parallel-ish (sequential, but each is cached/fast)
    rsi          = _get_nifty_rsi()
    fii_net_5d   = _get_fii_net_5d()
    pcr          = _get_pcr()
    vix          = _get_vix()
    gsec_10y     = _get_gsec_10y()
    gift_premium = _get_gift_nifty_premium()

    # Score each input
    scores = []
    factors = []

    s, f = _score_input("RSI(14)", rsi, {
        "bull_strong": None, "bull_mild": None,
        "bear_mild": 65, "bear_strong": 72,
        "bull_strong_inv": 30, "bull_mild_inv": 40,
        "inverted": True,
        # Remap: RSI < 35 → bullish, RSI > 65 → bearish
    })
    # Custom RSI scoring (oversold = bullish, overbought = bearish)
    if rsi is not None:
        if rsi < 35:
            s, f = 1.0, f"RSI {rsi} — oversold, mean-reversion likely"
        elif rsi < 45:
            s, f = 0.5, f"RSI {rsi} — leaning oversold"
        elif rsi > 65:
            s, f = -0.5, f"RSI {rsi} — overbought, momentum may fade"
        elif rsi > 72:
            s, f = -1.0, f"RSI {rsi} — strongly overbought"
        else:
            s, f = 0.0, f"RSI {rsi} — neutral momentum"
    scores.append(s)
    factors.append((s, f))

    # FII: net buying > 1000Cr = bullish, net selling < -1000Cr = bearish
    if fii_net_5d is not None:
        if fii_net_5d > 3000:
            s, f = 1.0, f"FII 5d net +₹{fii_net_5d:,.0f}Cr — strong buying"
        elif fii_net_5d > 1000:
            s, f = 0.5, f"FII 5d net +₹{fii_net_5d:,.0f}Cr — mild buying"
        elif fii_net_5d < -3000:
            s, f = -1.0, f"FII 5d net -₹{abs(fii_net_5d):,.0f}Cr — heavy selling"
        elif fii_net_5d < -1000:
            s, f = -0.5, f"FII 5d net -₹{abs(fii_net_5d):,.0f}Cr — mild selling"
        else:
            s, f = 0.0, f"FII 5d net ₹{fii_net_5d:,.0f}Cr — neutral flows"
        scores.append(s)
        factors.append((s, f))

    # PCR: > 1.2 = put heavy = bullish (market has hedges on), < 0.8 = call heavy = bearish
    if pcr is not None:
        if pcr > 1.4:
            s, f = 1.0, f"PCR {pcr:.2f} — put heavy, market over-hedged, contrarian bullish"
        elif pcr > 1.1:
            s, f = 0.5, f"PCR {pcr:.2f} — slightly put heavy, mild bullish lean"
        elif pcr < 0.7:
            s, f = -1.0, f"PCR {pcr:.2f} — call heavy, complacency, bearish signal"
        elif pcr < 0.9:
            s, f = -0.5, f"PCR {pcr:.2f} — mild call bias, slight bearish"
        else:
            s, f = 0.0, f"PCR {pcr:.2f} — balanced"
        scores.append(s)
        factors.append((s, f))

    # VIX: low VIX = risk-on (mild bull), high VIX = fear (potential bear OR oversold bounce)
    if vix is not None:
        if vix < 12:
            s, f = 0.5, f"VIX {vix:.1f} — very low fear, risk-on"
        elif vix < 16:
            s, f = 0.3, f"VIX {vix:.1f} — calm market"
        elif vix > 25:
            s, f = -0.8, f"VIX {vix:.1f} — high fear, volatility spike"
        elif vix > 20:
            s, f = -0.4, f"VIX {vix:.1f} — elevated fear"
        else:
            s, f = 0.0, f"VIX {vix:.1f} — normal range"
        scores.append(s)
        factors.append((s, f))

    # G-Sec: rising yields = bearish for equities
    if gsec_10y is not None:
        if gsec_10y > 7.5:
            s, f = -0.5, f"10Y G-Sec {gsec_10y:.2f}% — high yields, equity headwind"
        elif gsec_10y < 6.8:
            s, f =  0.5, f"10Y G-Sec {gsec_10y:.2f}% — low yields, equity tailwind"
        else:
            s, f =  0.0, f"10Y G-Sec {gsec_10y:.2f}% — neutral"
        scores.append(s)
        factors.append((s, f))

    # GIFT Nifty premium
    if gift_premium is not None:
        if gift_premium > 80:
            s, f = 1.0, f"GIFT Nifty +{gift_premium:.0f}pts premium — strong gap-up signal"
        elif gift_premium > 30:
            s, f = 0.5, f"GIFT Nifty +{gift_premium:.0f}pts — mild gap-up"
        elif gift_premium < -80:
            s, f = -1.0, f"GIFT Nifty {gift_premium:.0f}pts — strong gap-down signal"
        elif gift_premium < -30:
            s, f = -0.5, f"GIFT Nifty {gift_premium:.0f}pts — mild gap-down"
        else:
            s, f =  0.0, f"GIFT Nifty ±{abs(gift_premium):.0f}pts — flat"
        scores.append(s)
        factors.append((s, f))

    # ── Aggregate ──────────────────────────────────────────────────────────
    if not scores:
        return {
            "symbol": "NIFTY50",
            "error": "Unable to fetch market data for probability computation",
        }

    avg_score = sum(scores) / len(scores)  # -1 to +1

    # Convert to probability: map [-1, +1] → [20%, 80%]
    prob_up = round(50 + avg_score * 30)
    prob_up = max(15, min(85, prob_up))  # clamp to reasonable range

    bull_factors = [f for s, f in factors if s > 0]
    bear_factors = [f for s, f in factors if s < 0]

    if prob_up >= 65:
        signal = "Bullish"
    elif prob_up >= 55:
        signal = "Cautiously bullish"
    elif prob_up >= 45:
        signal = "Neutral / wait and watch"
    elif prob_up >= 35:
        signal = "Cautiously bearish"
    else:
        signal = "Bearish"

    return {
        "index": "NIFTY50",
        "probability_up": prob_up,
        "probability_down": 100 - prob_up,
        "signal": signal,
        "bull_factors": bull_factors,
        "bear_factors": bear_factors,
        "inputs": {
            "rsi_14": rsi,
            "fii_net_5d_cr": fii_net_5d,
            "pcr": pcr,
            "india_vix": vix,
            "gsec_10y_pct": gsec_10y,
            "gift_nifty_premium": gift_premium,
        },
        "model": "weighted-heuristic-v1 (6 signals)",
        "computed_at": datetime.now(tz=timezone.utc).isoformat(),
        "disclaimer": "Statistical signal only. Not SEBI-registered advice. Past signals ≠ future performance.",
    }
