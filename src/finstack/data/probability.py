"""
Nifty direction probability score for FinStack MCP.

Inputs:
  RSI(14)              - momentum
  FII net flow 5d      - smart money direction
  Put/Call Ratio (PCR) - market positioning
  India VIX            - fear level
  G-Sec 10Y yield      - risk-free rate pressure
  GIFT Nifty premium   - overnight global signal

Output: single % probability Nifty closes UP tomorrow + bull/bear factors.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger("finstack.probability")

INDEX_MAP = {
    "NIFTY": {"ticker": "^NSEI", "step": 50},
    "BANKNIFTY": {"ticker": "^NSEBANK", "step": 100},
}


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
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, float("nan"))
        rsi = 100 - (100 / (1 + rs))
        return round(float(rsi.iloc[-1]), 2)
    except Exception as e:
        logger.debug("Nifty RSI error: %s", e)
        return None


def _get_index_snapshot(index_name: str) -> dict | None:
    """Fetch basic index technical state for NIFTY / BANKNIFTY."""
    try:
        import yfinance as yf

        meta = INDEX_MAP[index_name]
        hist = yf.Ticker(meta["ticker"]).history(period="3mo", interval="1d")
        if hist.empty or len(hist) < 35:
            return None

        close = hist["Close"]
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, float("nan"))
        rsi = 100 - (100 / (1 + rs))

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        sma20 = close.rolling(window=20).mean()

        spot = float(close.iloc[-1])
        return {
            "spot": round(spot, 2),
            "rsi": round(float(rsi.iloc[-1]), 2) if rsi.notna().iloc[-1] else None,
            "macd": round(float(macd.iloc[-1]), 2) if macd.notna().iloc[-1] else None,
            "macd_signal": round(float(macd_signal.iloc[-1]), 2) if macd_signal.notna().iloc[-1] else None,
            "sma20": round(float(sma20.iloc[-1]), 2) if sma20.notna().iloc[-1] else None,
        }
    except Exception as e:
        logger.debug("Index snapshot error for %s: %s", index_name, e)
        return None


def _get_vix_regime(vix: float | None) -> tuple[str, int]:
    if vix is None:
        return "unknown", 6
    if vix < 20:
        return "sweet", 5
    if vix < 28:
        return "elevated", 6
    if vix < 40:
        return "fear", 7
    return "panic", 8


def _atm(spot: float, step: int) -> int:
    return int(round(spot / step) * step)


def _get_fii_net_5d() -> float | None:
    """FII net flow over last 5 trading days in Cr."""
    from finstack.data.nse_advanced import get_fii_dii_data

    data = _safe(get_fii_dii_data)
    if not data:
        return None

    if isinstance(data, dict) and isinstance(data.get("data"), list):
        rows = data["data"]
    elif isinstance(data, list):
        rows = data
    else:
        rows = []

    nets = []
    for row in rows[:5]:
        if not isinstance(row, dict):
            continue
        value = row.get("fii_net_cr")
        if value is None:
            value = row.get("fii_net")
        if value is not None:
            try:
                nets.append(float(value))
            except Exception:
                continue
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
    return 6.85


def _get_gift_nifty_premium() -> float | None:
    """GIFT Nifty premium vs Nifty spot."""
    from finstack.data.market_intelligence import get_gift_nifty

    data = _safe(get_gift_nifty)
    if not data or not isinstance(data, dict):
        return None
    return data.get("premium") or data.get("gift_premium")


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

    if thresholds.get("inverted"):
        if bs and value <= bs:
            return 1.0, f"{name} {value} - strongly bullish"
        if bm and value <= bm:
            return 0.5, f"{name} {value} - mildly bullish"
        if br and value >= br:
            return -0.5, f"{name} {value} - mildly bearish"
        if be and value >= be:
            return -1.0, f"{name} {value} - strongly bearish"
        return 0.0, f"{name} {value} - neutral"

    if bs and value >= bs:
        return 1.0, f"{name} {value} - strongly bullish"
    if bm and value >= bm:
        return 0.5, f"{name} {value} - mildly bullish"
    if br and value <= br:
        return -0.5, f"{name} {value} - mildly bearish"
    if be and value <= be:
        return -1.0, f"{name} {value} - strongly bearish"
    return 0.0, f"{name} {value} - neutral"


def get_nifty_outlook() -> dict:
    """
    Compute Nifty 50 direction probability for the next trading session.
    """
    logger.info("Computing Nifty direction probability")

    rsi = _get_nifty_rsi()
    fii_net_5d = _get_fii_net_5d()
    pcr = _get_pcr()
    vix = _get_vix()
    gsec_10y = _get_gsec_10y()
    gift_premium = _get_gift_nifty_premium()

    scores = []
    factors = []

    s, f = _score_input(
        "RSI(14)",
        rsi,
        {
            "bull_strong": None,
            "bull_mild": None,
            "bear_mild": 65,
            "bear_strong": 72,
            "bull_strong_inv": 30,
            "bull_mild_inv": 40,
            "inverted": True,
        },
    )
    if rsi is not None:
        if rsi < 35:
            s, f = 1.0, f"RSI {rsi} - oversold, mean-reversion likely"
        elif rsi < 45:
            s, f = 0.5, f"RSI {rsi} - leaning oversold"
        elif rsi > 72:
            s, f = -1.0, f"RSI {rsi} - strongly overbought"
        elif rsi > 65:
            s, f = -0.5, f"RSI {rsi} - overbought, momentum may fade"
        else:
            s, f = 0.0, f"RSI {rsi} - neutral momentum"
    scores.append(s)
    factors.append((s, f))

    if fii_net_5d is not None:
        if fii_net_5d > 3000:
            s, f = 1.0, f"FII 5d net +Rs{fii_net_5d:,.0f}Cr - strong buying"
        elif fii_net_5d > 1000:
            s, f = 0.5, f"FII 5d net +Rs{fii_net_5d:,.0f}Cr - mild buying"
        elif fii_net_5d < -3000:
            s, f = -1.0, f"FII 5d net -Rs{abs(fii_net_5d):,.0f}Cr - heavy selling"
        elif fii_net_5d < -1000:
            s, f = -0.5, f"FII 5d net -Rs{abs(fii_net_5d):,.0f}Cr - mild selling"
        else:
            s, f = 0.0, f"FII 5d net Rs{fii_net_5d:,.0f}Cr - neutral flows"
        scores.append(s)
        factors.append((s, f))

    if pcr is not None:
        if pcr > 1.4:
            s, f = 1.0, f"PCR {pcr:.2f} - put heavy, contrarian bullish"
        elif pcr > 1.1:
            s, f = 0.5, f"PCR {pcr:.2f} - slightly put heavy, mild bullish lean"
        elif pcr < 0.7:
            s, f = -1.0, f"PCR {pcr:.2f} - call heavy, complacency, bearish signal"
        elif pcr < 0.9:
            s, f = -0.5, f"PCR {pcr:.2f} - mild call bias, slight bearish"
        else:
            s, f = 0.0, f"PCR {pcr:.2f} - balanced"
        scores.append(s)
        factors.append((s, f))

    if vix is not None:
        if vix < 12:
            s, f = 0.5, f"VIX {vix:.1f} - very low fear, risk-on"
        elif vix < 16:
            s, f = 0.3, f"VIX {vix:.1f} - calm market"
        elif vix > 25:
            s, f = -0.8, f"VIX {vix:.1f} - high fear, volatility spike"
        elif vix > 20:
            s, f = -0.4, f"VIX {vix:.1f} - elevated fear"
        else:
            s, f = 0.0, f"VIX {vix:.1f} - normal range"
        scores.append(s)
        factors.append((s, f))

    if gsec_10y is not None:
        if gsec_10y > 7.5:
            s, f = -0.5, f"10Y G-Sec {gsec_10y:.2f}% - high yields, equity headwind"
        elif gsec_10y < 6.8:
            s, f = 0.5, f"10Y G-Sec {gsec_10y:.2f}% - low yields, equity tailwind"
        else:
            s, f = 0.0, f"10Y G-Sec {gsec_10y:.2f}% - neutral"
        scores.append(s)
        factors.append((s, f))

    if gift_premium is not None:
        if gift_premium > 80:
            s, f = 1.0, f"GIFT Nifty +{gift_premium:.0f}pts premium - strong gap-up signal"
        elif gift_premium > 30:
            s, f = 0.5, f"GIFT Nifty +{gift_premium:.0f}pts - mild gap-up"
        elif gift_premium < -80:
            s, f = -1.0, f"GIFT Nifty {gift_premium:.0f}pts - strong gap-down signal"
        elif gift_premium < -30:
            s, f = -0.5, f"GIFT Nifty {gift_premium:.0f}pts - mild gap-down"
        else:
            s, f = 0.0, f"GIFT Nifty flat near {gift_premium:.0f}pts"
        scores.append(s)
        factors.append((s, f))

    if not scores:
        return {
            "symbol": "NIFTY50",
            "error": "Unable to fetch market data for probability computation",
        }

    avg_score = sum(scores) / len(scores)
    prob_up = round(50 + avg_score * 30)
    prob_up = max(15, min(85, prob_up))

    bull_factors = [factor for score, factor in factors if score > 0]
    bear_factors = [factor for score, factor in factors if score < 0]

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
        "disclaimer": "Statistical signal only. Not SEBI-registered advice. Past signals are not future performance.",
    }


def get_fno_trade_setup(symbol: str = "NIFTY") -> dict:
    """
    Build a high-signal intraday F&O setup for NIFTY / BANKNIFTY.

    This packages the original nifty-agent hook into one MCP-native
    response: watch the index, options positioning, VIX regime, FII flow,
    and overnight context, then return one clear action.
    """
    index_name = (symbol or "NIFTY").upper().replace(" ", "")
    if index_name not in INDEX_MAP:
        return {
            "error": f"Unsupported index '{symbol}'. Use NIFTY or BANKNIFTY.",
            "supported_indices": list(INDEX_MAP.keys()),
        }

    snapshot = _get_index_snapshot(index_name)
    vix = _get_vix()
    pcr = _get_pcr()
    fii_net_5d = _get_fii_net_5d()
    gift_premium = _get_gift_nifty_premium() if index_name == "NIFTY" else None

    if not snapshot:
        return {
            "index": index_name,
            "error": "Could not fetch enough index data to build an F&O setup.",
        }

    bull_score = 0.0
    bear_score = 0.0
    bull_reasons: list[str] = []
    bear_reasons: list[str] = []

    spot = snapshot["spot"]
    sma20 = snapshot.get("sma20")
    rsi = snapshot.get("rsi")
    macd = snapshot.get("macd")
    macd_signal = snapshot.get("macd_signal")
    atm = _atm(spot, INDEX_MAP[index_name]["step"])
    vix_regime, min_score = _get_vix_regime(vix)

    if sma20 is not None:
        if spot > sma20:
            bull_score += 1.0
            bull_reasons.append(f"Spot {spot:,.0f} is above 20DMA {sma20:,.0f}")
        else:
            bear_score += 1.0
            bear_reasons.append(f"Spot {spot:,.0f} is below 20DMA {sma20:,.0f}")

    if macd is not None and macd_signal is not None:
        if macd > macd_signal:
            bull_score += 0.8
            bull_reasons.append(f"MACD {macd:.2f} is above signal {macd_signal:.2f}")
        else:
            bear_score += 0.8
            bear_reasons.append(f"MACD {macd:.2f} is below signal {macd_signal:.2f}")

    if rsi is not None:
        if rsi < 35:
            bull_score += 0.7
            bull_reasons.append(f"RSI {rsi:.1f} is oversold, bounce setup possible")
        elif rsi < 48:
            bull_score += 0.3
            bull_reasons.append(f"RSI {rsi:.1f} leaves room for upside")
        elif rsi > 70:
            bear_score += 0.8
            bear_reasons.append(f"RSI {rsi:.1f} is overbought, fade risk rising")
        elif rsi > 60:
            bear_score += 0.3
            bear_reasons.append(f"RSI {rsi:.1f} is stretched near the upper band")

    if fii_net_5d is not None:
        if fii_net_5d > 3000:
            bull_score += 1.0
            bull_reasons.append(f"FII 5d flow is strongly positive at Rs {fii_net_5d:,.0f}Cr")
        elif fii_net_5d > 1000:
            bull_score += 0.5
            bull_reasons.append(f"FII 5d flow is supportive at Rs {fii_net_5d:,.0f}Cr")
        elif fii_net_5d < -3000:
            bear_score += 1.0
            bear_reasons.append(f"FII 5d flow is heavily negative at Rs {abs(fii_net_5d):,.0f}Cr")
        elif fii_net_5d < -1000:
            bear_score += 0.5
            bear_reasons.append(f"FII 5d flow is weak at Rs {abs(fii_net_5d):,.0f}Cr sold")

    if pcr is not None:
        if pcr > 1.25:
            bull_score += 0.7
            bull_reasons.append(f"PCR {pcr:.2f} shows put-heavy hedging, contrarian bullish")
        elif pcr > 1.05:
            bull_score += 0.3
            bull_reasons.append(f"PCR {pcr:.2f} mildly supports bulls")
        elif pcr < 0.75:
            bear_score += 0.7
            bear_reasons.append(f"PCR {pcr:.2f} is call-heavy, downside trap risk")
        elif pcr < 0.9:
            bear_score += 0.3
            bear_reasons.append(f"PCR {pcr:.2f} mildly favors bears")

    if gift_premium is not None:
        if gift_premium > 40:
            bull_score += 0.8
            bull_reasons.append(f"GIFT Nifty premium is +{gift_premium:.0f} points")
        elif gift_premium > 15:
            bull_score += 0.4
            bull_reasons.append(f"GIFT Nifty is mildly positive at +{gift_premium:.0f} points")
        elif gift_premium < -40:
            bear_score += 0.8
            bear_reasons.append(f"GIFT Nifty discount is {gift_premium:.0f} points")
        elif gift_premium < -15:
            bear_score += 0.4
            bear_reasons.append(f"GIFT Nifty is mildly negative at {gift_premium:.0f} points")

    volatility_penalty = 0.0
    if vix_regime == "panic":
        volatility_penalty = 1.2
    elif vix_regime == "fear":
        volatility_penalty = 0.6

    edge = bull_score - bear_score
    confidence = round(min(92, max(18, 50 + edge * 12 - volatility_penalty * 8)))

    signal = "NO_TRADE"
    option_side = "WAIT"
    conviction = "LOW"
    final_reasons: list[str] = []

    if edge >= 1.4 and bull_score >= min_score / 4:
        signal = "BUY_CE"
        option_side = "CALL"
        conviction = "HIGH" if edge >= 2.4 else "MODERATE"
        final_reasons = bull_reasons[:4]
    elif edge <= -1.4 and bear_score >= min_score / 4:
        signal = "BUY_PE"
        option_side = "PUT"
        conviction = "HIGH" if edge <= -2.4 else "MODERATE"
        final_reasons = bear_reasons[:4]
    else:
        final_reasons = [
            "Signals are mixed, so the cleaner trade is to wait",
            *([bull_reasons[0]] if bull_reasons else []),
            *([bear_reasons[0]] if bear_reasons else []),
        ][:4]

    setup_name = {
        "BUY_CE": f"{index_name} momentum continuation",
        "BUY_PE": f"{index_name} downside pressure setup",
        "NO_TRADE": f"{index_name} mixed tape / no clean edge",
    }[signal]

    approve_message = {
        "BUY_CE": f"{index_name} bullish setup active. Prefer {atm} CE zone on dip confirmation.",
        "BUY_PE": f"{index_name} bearish setup active. Prefer {atm} PE zone on failed bounce.",
        "NO_TRADE": f"{index_name} has no clean edge right now. Skip fresh option buys.",
    }[signal]

    return {
        "index": index_name,
        "signal": signal,
        "setup_name": setup_name,
        "option_side": option_side,
        "conviction": conviction,
        "confidence_pct": confidence,
        "execution_hint": {
            "style": "intraday options",
            "preferred_strike_zone": atm,
            "contract_hint": f"{index_name} {atm} {'CE' if signal == 'BUY_CE' else 'PE' if signal == 'BUY_PE' else 'ATM straddle/watch'}",
        },
        "approve_message": approve_message,
        "bull_score": round(bull_score, 2),
        "bear_score": round(bear_score, 2),
        "market_context": {
            "spot": spot,
            "rsi_14": rsi,
            "macd": macd,
            "macd_signal": macd_signal,
            "sma20": sma20,
            "fii_net_5d_cr": fii_net_5d,
            "pcr": pcr,
            "india_vix": vix,
            "vix_regime": vix_regime,
            "gift_nifty_premium": gift_premium,
        },
        "supporting_factors": final_reasons,
        "bull_factors": bull_reasons,
        "bear_factors": bear_reasons,
        "risk_flags": [
            *([f"VIX regime is {vix_regime}; option premium can stay expensive"] if vix_regime in {"fear", "panic"} else []),
            *(["Confidence is below 58%, so position size should stay small"] if confidence < 58 else []),
        ],
        "computed_at": datetime.now(tz=timezone.utc).isoformat(),
        "disclaimer": "Signal aid only. For educational use. Not broker-linked auto execution or SEBI-registered advice.",
    }
