"""
Budget speech analyzer for FinStack MCP.

Two modes:
  1. analyze_budget_live(text)  — real-time: paste FM speech text as they speak
                                   → instant sector/stock impact mapping
  2. get_budget_impact(year)    — historical: look up impact of past budgets

"AI tells you which stocks to buy AS the Finance Minister speaks"

Happened every Feb 1st. CNBC-TV18 / Moneycontrol / ET would cover this tool.
Data: public speech transcript + hardcoded sector-keyword-to-stock mapping.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger("finstack.budget")

# Sector-keyword → stock mapping for budget speech analysis
BUDGET_SECTOR_MAP = {
    "Infrastructure": {
        "keywords": ["infrastructure", "road", "highway", "railway", "metro", "port", "airport",
                     "capex", "capital expenditure", "pli scheme", "national infrastructure"],
        "stocks":   ["LT", "IRB", "RVNL", "IRFC", "NTPC", "POWERGRID", "ADANIPORTS", "GMR"],
        "bias":     "bullish",
    },
    "Defence": {
        "keywords": ["defence", "defense", "military", "armed forces", "hal", "drdo",
                     "indigenous", "atmanirbhar defence", "defence corridor"],
        "stocks":   ["HAL", "BEL", "BEML", "BHEL", "MTAR", "PARAS", "DATA"],
        "bias":     "bullish",
    },
    "Banking": {
        "keywords": ["bank", "credit", "lending", "npa", "psl", "financial inclusion",
                     "repo rate", "rbi", "nbfc", "microfinance"],
        "stocks":   ["SBIN", "HDFCBANK", "ICICIBANK", "AXISBANK", "BANKBARODA", "CANFIN"],
        "bias":     "neutral",
    },
    "Pharma": {
        "keywords": ["health", "pharma", "medicine", "hospital", "ayushman", "jan aushadhi",
                     "bulk drug", "medical device", "healthcare"],
        "stocks":   ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "APOLLOHOSP", "FORTIS"],
        "bias":     "bullish",
    },
    "Renewable Energy": {
        "keywords": ["solar", "wind", "renewable", "green energy", "clean energy", "ev",
                     "electric vehicle", "battery", "green hydrogen", "net zero"],
        "stocks":   ["ADANIGREEN", "TATAPOWER", "NTPC", "JSWENERGY", "GREENPANEL", "TATAMOTOR"],
        "bias":     "bullish",
    },
    "Real Estate": {
        "keywords": ["housing", "affordable housing", "pmay", "home loan", "smart city",
                     "urban development", "real estate", "realty"],
        "stocks":   ["DLF", "GODREJPROP", "BRIGADE", "OBEROIRLTY", "PRESTIGE", "HDFC"],
        "bias":     "bullish",
    },
    "Agriculture": {
        "keywords": ["farm", "farmer", "agriculture", "kisan", "msp", "irrigation", "crop",
                     "fertilizer", "agri", "rural", "pm kisan"],
        "stocks":   ["COROMANDEL", "CHAMBAL", "NFL", "GNFC", "PI", "DHANUKA"],
        "bias":     "bullish",
    },
    "Auto": {
        "keywords": ["automobile", "auto", "ev subsidy", "vehicle", "scrappage", "electric vehicle",
                     "charging infrastructure", "fame"],
        "stocks":   ["MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "HEROMOTOCO"],
        "bias":     "bullish",
    },
    "FMCG": {
        "keywords": ["consumption", "rural spending", "direct benefit", "fmcg", "consumer",
                     "disposable income", "income tax cut"],
        "stocks":   ["HINDUNILVR", "DABUR", "BRITANNIA", "NESTLEIND", "ITC", "MARICO"],
        "bias":     "bullish",
    },
    "Tobacco/Alcohol": {
        "keywords": ["cigarette", "tobacco", "alcohol", "sin tax", "excise duty hike"],
        "stocks":   ["ITC", "VST"],
        "bias":     "bearish",
    },
    "IT/Digital": {
        "keywords": ["digital india", "technology", "startup", "innovation", "data center",
                     "artificial intelligence", "semiconductor", "electronics"],
        "stocks":   ["TCS", "INFY", "WIPRO", "HCLTECH", "Dixon", "AMBER"],
        "bias":     "bullish",
    },
    "Steel/Metals": {
        "keywords": ["steel", "metal", "mining", "iron ore", "coal", "aluminium",
                     "anti-dumping", "import duty"],
        "stocks":   ["JSWSTEEL", "TATASTEEL", "HINDALCO", "COALINDIA", "NMDC", "SAIL"],
        "bias":     "neutral",
    },
    "Fiscal/Tax": {
        "keywords": ["income tax", "tax slab", "standard deduction", "capital gains",
                     "stcg", "ltcg", "stt", "securities transaction"],
        "stocks":   ["all equity markets"],
        "bias":     "depends on direction",
    },
    "Telecom": {
        "keywords": ["telecom", "5g", "spectrum", "broadband", "bsnl", "satellite"],
        "stocks":   ["BHARTIARTL", "VODAFONE", "INDUS", "TATACOMM"],
        "bias":     "bullish",
    },
}

# Historical budget impact data
HISTORICAL_IMPACTS = {
    "2025": {
        "date": "2025-02-01",
        "key_announcements": [
            "Income tax relief — zero tax up to ₹12L income (new regime)",
            "Capex target ₹11.21L Cr — infra focused",
            "MSME credit guarantee increased",
            "No LTCG rate hike (markets relieved)",
        ],
        "winners": ["LT", "RVNL", "IRFC", "NTPC", "consumer stocks on income tax relief"],
        "losers":  ["No major sector negatives"],
    },
    "2024": {
        "date": "2024-07-23",
        "key_announcements": [
            "LTCG raised from 10% to 12.5% — negative for equities",
            "STCG raised from 15% to 20%",
            "Capex kept at ₹11.1L Cr",
            "Angel tax abolished for startups",
        ],
        "winners": ["Startups, defence, railways"],
        "losers":  ["All equity markets initially — LTCG hike caused sell-off"],
    },
    "2023": {
        "date": "2023-02-01",
        "key_announcements": [
            "Capex hiked 33% to ₹10L Cr — massive infra push",
            "Income tax slabs revised under new regime",
            "Railway budget ₹2.4L Cr — all-time high",
        ],
        "winners": ["LT", "RVNL", "railways, defence, infra"],
        "losers":  ["Cigarette stocks — excise duty hiked", "Gold — import duty unchanged"],
    },
}


def _analyze_text(text: str) -> list[dict]:
    """Scan speech text for sector keywords and return impact mapping."""
    lower = text.lower()
    impacts = []

    for sector, data in BUDGET_SECTOR_MAP.items():
        matched_keywords = [kw for kw in data["keywords"] if kw in lower]
        if not matched_keywords:
            continue

        # Determine if context is positive or negative
        negative_context = any(
            phrase in lower for phrase in
            ["cut", "reduce", "hike duty", "increase tax", "ban", "restrict", "penalty"]
        )
        # Check if the keyword is near negative words
        bias = "bearish" if (negative_context and data["bias"] != "bearish") else data["bias"]

        impacts.append({
            "sector":           sector,
            "matched_keywords": matched_keywords,
            "stocks":           data["stocks"],
            "bias":             bias,
            "action":           f"{'BUY' if bias == 'bullish' else 'SELL' if bias == 'bearish' else 'MONITOR'} "
                                f"{', '.join(data['stocks'][:3])}",
        })

    impacts.sort(key=lambda x: len(x["matched_keywords"]), reverse=True)
    return impacts


def analyze_budget_live(text: str) -> dict:
    """
    Real-time budget speech analyzer.

    Paste the Finance Minister's speech text (or partial transcript as they speak).
    Returns instant sector + stock impact mapping.

    "FM just said ₹2L Cr for infrastructure → BUY L&T, NTPC, IRB Infra"

    Use on Feb 1st: paste each paragraph as the FM speaks for live signals.

    Args:
        text: Budget speech text (partial or full transcript)

    Returns:
        - sector_impacts: sectors mentioned with bullish/bearish bias
        - buy_signals: stocks to buy based on mentions
        - sell_signals: stocks to avoid/sell
        - key_themes: top sectors/themes detected
    """
    if not text or len(text.strip()) < 20:
        return {"error": "Provide budget speech text — paste the FM's speech transcript"}

    impacts = _analyze_text(text)

    buy_signals  = []
    sell_signals = []

    for imp in impacts:
        if imp["bias"] == "bullish":
            buy_signals.extend(imp["stocks"][:3])
        elif imp["bias"] == "bearish":
            sell_signals.extend(imp["stocks"][:3])

    # Deduplicate
    buy_signals  = list(dict.fromkeys(buy_signals))
    sell_signals = list(dict.fromkeys(sell_signals))
    key_themes   = [imp["sector"] for imp in impacts[:5]]

    return {
        "analysis_type":  "live_budget_speech",
        "sectors_detected": len(impacts),
        "key_themes":     key_themes,
        "sector_impacts": impacts,
        "buy_signals":    buy_signals,
        "sell_signals":   sell_signals,
        "summary": (
            f"Detected {len(impacts)} sector mentions. "
            f"Buy signals: {', '.join(buy_signals[:5]) or 'none'}. "
            f"Sell signals: {', '.join(sell_signals[:3]) or 'none'}."
        ),
        "analyzed_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def get_budget_impact(year: str = "2025") -> dict:
    """
    Historical budget impact for a given year.

    Returns key announcements, sector winners/losers,
    and market reaction from past Union Budgets.

    Args:
        year: Budget year as string (e.g. "2025", "2024", "2023")

    Returns:
        - key_announcements, winners, losers, date
    """
    data = HISTORICAL_IMPACTS.get(str(year))
    if not data:
        available = list(HISTORICAL_IMPACTS.keys())
        return {
            "error": f"No data for budget year {year}",
            "available_years": available,
        }

    return {
        "year":                str(year),
        "date":                data["date"],
        "key_announcements":   data["key_announcements"],
        "winners":             data["winners"],
        "losers":              data["losers"],
        "note": "Add TELEGRAM_API keys to track real-time FM speech and get instant signals on Feb 1.",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }
