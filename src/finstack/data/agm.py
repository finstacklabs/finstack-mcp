"""
AGM/EGM AI briefing for FinStack MCP.

Summarizes upcoming shareholder meeting agendas from NSE/BSE disclosures.
Flags unusual resolutions: large salary hikes, debt issuance, subsidiary creation,
related-party transactions, buyback cancellations.

"This company is passing a resolution to raise ₹500Cr debt next week — should you be worried?"

Data: NSE corporate announcements (public, free)
"""

import logging
import urllib.request
import json
from datetime import datetime, timezone

logger = logging.getLogger("finstack.agm")

NSE_ANNOUNCE_URL = "https://www.nseindia.com/api/corporate-announcements?index=equities&symbol={symbol}"

# Unusual resolution patterns to flag
UNUSUAL_PATTERNS = [
    ("large_debt",          ["issue of debentures", "raise debt", "borrow", "ncd", "ecb",
                              "line of credit", "term loan", "bonds"],
                            "Large debt issuance — check debt/equity ratio post-issuance"),
    ("salary_hike",         ["revision of remuneration", "increase in salary", "managerial remuneration",
                              "commission to directors", "sitting fees"],
                            "Significant management pay hike — check if performance justifies it"),
    ("related_party",       ["related party transaction", "rpt", "inter-corporate loan",
                              "transaction with promoter", "subsidiary loan"],
                            "Related party transaction — check terms vs market rate (promoter benefit risk)"),
    ("subsidiary_creation", ["incorporate subsidiary", "new subsidiary", "joint venture",
                              "wholly owned subsidiary", "step-down subsidiary"],
                            "New subsidiary creation — could dilute focus or hide liabilities"),
    ("buyback_cancel",      ["withdrawal of buyback", "cancel buyback", "revoke buyback"],
                            "Buyback cancellation — company signaling cash crunch or reversal"),
    ("rights_issue",        ["rights issue", "preferential allotment", "qip", "fpo",
                              "fresh equity issue"],
                            "Fresh equity issuance — dilution for existing shareholders"),
    ("change_auditor",      ["change of auditor", "resignation of auditor", "new auditor"],
                            "Auditor change — investigate reason (resignation is a red flag)"),
    ("pledge_approval",     ["pledge of shares", "creation of pledge", "encumber shares"],
                            "Promoter pledging more shares — financial stress signal"),
]


def _fetch_nse_announcements(symbol: str) -> list[dict]:
    try:
        url = NSE_ANNOUNCE_URL.format(symbol=symbol.upper())
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "Referer": "https://www.nseindia.com",
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if isinstance(data, list):
            return data[:20]
        return data.get("data", [])[:20]
    except Exception as e:
        logger.debug("NSE announcements fetch error: %s", e)
        return []


def _flag_unusual(text: str) -> list[dict]:
    flags = []
    lower = text.lower()
    for flag_type, keywords, implication in UNUSUAL_PATTERNS:
        if any(kw in lower for kw in keywords):
            flags.append({
                "type":        flag_type,
                "implication": implication,
            })
    return flags


def get_agm_brief(symbol: str) -> dict:
    """
    AI briefing for upcoming AGM/EGM resolutions of an NSE stock.

    Flags unusual resolutions:
      - Large debt issuance (₹500Cr+ debt raise)
      - Management salary hikes
      - Related-party transactions
      - New subsidiary creation
      - Buyback cancellation
      - Fresh equity issuance (dilution)
      - Auditor resignation/change
      - Promoter pledge approval

    "This company is passing a resolution to raise ₹500Cr debt next week —
     should you be worried?"

    Args:
        symbol: NSE stock symbol (e.g. RELIANCE, ZEEL, ADANIENT)

    Returns:
        - upcoming_meetings: AGM/EGM dates and agendas
        - unusual_flags: list of flagged resolutions with implications
        - risk_level: safe / watch / concern
        - verdict: human-readable assessment
    """
    symbol = symbol.upper().replace(".NS", "").replace(".BO", "")

    announcements = _fetch_nse_announcements(symbol)

    # Filter for AGM/EGM related announcements
    meeting_keywords = {"agm", "egm", "postal ballot", "shareholder meeting",
                        "notice of meeting", "annual general", "extraordinary general"}

    meetings = []
    all_flags = []

    for ann in announcements:
        desc = (
            ann.get("description") or
            ann.get("subject") or
            ann.get("desc") or
            ann.get("headline") or ""
        ).lower()

        is_meeting = any(kw in desc for kw in meeting_keywords)

        flags = _flag_unusual(desc)
        if flags:
            all_flags.extend(flags)

        if is_meeting or flags:
            meetings.append({
                "date":    ann.get("date") or ann.get("exchdisstime", ""),
                "subject": ann.get("subject") or ann.get("description", "")[:200],
                "flags":   flags,
            })

    # If no live data, return a helpful response
    if not announcements:
        return {
            "symbol": symbol,
            "error": "NSE announcements not available (may need browser session). "
                     "Check manually at https://www.nseindia.com/companies-listing/corporate-filings-announcements",
            "fallback_tip": "Search for AGM notices in BSE filings at https://www.bseindia.com/corporates/ann.html",
        }

    # Deduplicate flags
    seen_types = set()
    unique_flags = []
    for f in all_flags:
        if f["type"] not in seen_types:
            unique_flags.append(f)
            seen_types.add(f["type"])

    # Risk level
    high_risk_types = {"large_debt", "related_party", "pledge_approval", "change_auditor"}
    has_high = any(f["type"] in high_risk_types for f in unique_flags)

    if has_high and len(unique_flags) >= 2:
        risk_level = "concern"
        verdict = (
            f"{len(unique_flags)} unusual resolution(s) flagged including high-risk items. "
            "Read the full notice before the meeting date."
        )
    elif unique_flags:
        risk_level = "watch"
        verdict = f"{len(unique_flags)} item(s) worth monitoring. Not immediately alarming."
    else:
        risk_level = "safe"
        verdict = "No unusual resolutions flagged in recent announcements."

    return {
        "symbol":          symbol,
        "risk_level":      risk_level,
        "verdict":         verdict,
        "unusual_flags":   unique_flags,
        "meetings":        meetings[:5],
        "total_announcements_scanned": len(announcements),
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "disclaimer": "Based on NSE public filings. Not SEBI-registered advice.",
    }
