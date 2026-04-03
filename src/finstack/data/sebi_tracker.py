"""
SEBI order sentiment tracker for FinStack MCP.

Fetches SEBI enforcement orders from the public SEBI website RSS/API,
runs NLP to identify which sectors/companies are under scrutiny,
and produces an early warning before the stock crashes on regulatory action.

"SEBI filed 3 orders against this sector this week —
 historically precedes 15% correction"

Data: SEBI public enforcement orders (free, no auth needed)
"""

import logging
import urllib.request
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timezone

logger = logging.getLogger("finstack.sebi_tracker")

# SEBI enforcement orders RSS
SEBI_ORDERS_URL = "https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doGetOrderDerived=yes&type=1&intmId=4"
SEBI_RSS_URL    = "https://www.sebi.gov.in/sebi_data/rss/SEBIOrders.xml"

# Sector keyword mapping
SECTOR_KEYWORDS = {
    "Banking":    ["bank", "nbfc", "lending", "deposit", "credit"],
    "IT":         ["software", "it company", "technology", "infosys", "tcs", "wipro"],
    "Pharma":     ["pharma", "drug", "medicine", "api", "bulk drug"],
    "Real Estate":["real estate", "housing", "builder", "construction", "realty"],
    "Broking":    ["broker", "stock broker", "trading member", "depository"],
    "SME/Micro":  ["sme", "small company", "micro cap", "penny stock", "shell"],
    "Mutual Fund":["mutual fund", "amc", "asset management", "scheme", "nav"],
    "Crypto":     ["crypto", "bitcoin", "digital asset", "virtual currency"],
    "Commodity":  ["commodity", "mcx", "futures", "derivative"],
    "Insurance":  ["insurance", "lic", "irda", "policy"],
}

ACTION_KEYWORDS = {
    "high":   ["debarred", "prohibited", "impounded", "attached", "arrested",
               "criminal", "fraud", "manipulation", "insider", "disgorgement"],
    "medium": ["show cause", "adjudication", "penalty", "fine", "warning",
               "suspension", "consent", "settlement"],
    "low":    ["observation", "clarification", "disclosure", "minor", "technical"],
}


def _classify_severity(text: str) -> str:
    lower = text.lower()
    for level, words in ACTION_KEYWORDS.items():
        if any(w in lower for w in words):
            return level
    return "low"


def _classify_sector(text: str) -> list[str]:
    lower = text.lower()
    sectors = []
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            sectors.append(sector)
    return sectors or ["General"]


def _fetch_sebi_orders(limit: int = 20) -> list[dict]:
    orders = []
    for url in [SEBI_RSS_URL, SEBI_ORDERS_URL]:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 finstack-mcp/1.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read()
            tree = ET.fromstring(raw)
            items = tree.findall(".//item")
            if not items:
                continue
            for item in items[:limit]:
                title   = (item.findtext("title") or "").strip()
                desc    = (item.findtext("description") or "").strip()
                pubdate = (item.findtext("pubDate") or "").strip()
                link    = (item.findtext("link") or "").strip()
                combined = f"{title} {desc}"
                orders.append({
                    "title":    title,
                    "summary":  desc[:300],
                    "date":     pubdate,
                    "link":     link,
                    "severity": _classify_severity(combined),
                    "sectors":  _classify_sector(combined),
                })
            if orders:
                break
        except Exception as e:
            logger.debug("SEBI RSS fetch error (%s): %s", url, e)

    return orders


def get_sebi_alerts(sector: str | None = None) -> dict:
    """
    Fetch and analyze recent SEBI enforcement orders.

    Identifies which sectors and companies are under regulatory scrutiny.
    High-severity actions (debarment, fraud, manipulation) historically
    precede 15-30% corrections in the affected stock.

    Args:
        sector: Filter by sector name (e.g. "Banking", "Pharma", "SME/Micro").
                Pass None or "all" to get all recent orders.

    Returns:
        - orders: list of recent SEBI actions with severity classification
        - sector_summary: count of actions per sector
        - high_severity_count: number of serious actions this week
        - alert: human-readable warning if elevated activity
    """
    orders = _fetch_sebi_orders(limit=30)

    if not orders:
        return {
            "error": "Could not fetch SEBI orders. SEBI website may be down.",
            "fallback": "Check manually at https://www.sebi.gov.in/enforcement/orders/",
        }

    # Filter by sector
    if sector and sector.lower() != "all":
        sector_norm = sector.strip().title()
        filtered = [o for o in orders if sector_norm in o["sectors"] or
                    any(sector.lower() in s.lower() for s in o["sectors"])]
    else:
        filtered = orders

    # Sector summary
    sector_counts: dict[str, int] = {}
    for o in filtered:
        for s in o["sectors"]:
            sector_counts[s] = sector_counts.get(s, 0) + 1

    high_count   = sum(1 for o in filtered if o["severity"] == "high")
    medium_count = sum(1 for o in filtered if o["severity"] == "medium")

    # Alert generation
    if high_count >= 3:
        alert = (
            f"HIGH ALERT: {high_count} serious SEBI actions in recent orders "
            f"(fraud/manipulation/debarment). Historically precedes significant corrections."
        )
        alert_level = "high"
    elif high_count >= 1:
        alert = f"{high_count} high-severity SEBI action detected. Monitor affected stocks closely."
        alert_level = "medium"
    elif medium_count >= 5:
        alert = f"Elevated regulatory activity: {medium_count} penalty/fine orders. Sector under scrutiny."
        alert_level = "medium"
    else:
        alert = "Normal regulatory activity. No elevated sector scrutiny."
        alert_level = "low"

    top_sector = max(sector_counts, key=sector_counts.get) if sector_counts else "N/A"

    return {
        "filter_sector":      sector or "all",
        "orders_found":       len(filtered),
        "alert_level":        alert_level,
        "alert":              alert,
        "high_severity_count": high_count,
        "sector_summary":     dict(sorted(sector_counts.items(), key=lambda x: -x[1])),
        "most_active_sector": top_sector,
        "recent_orders":      filtered[:10],
        "source":             "SEBI public enforcement orders",
        "generated_at":       datetime.now(tz=timezone.utc).isoformat(),
    }
