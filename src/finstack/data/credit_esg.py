"""
FinStack Credit Ratings + ESG/BRSR Data

Credit ratings from public NSE/BSE exchange filings.
BRSR-based ESG indicators from SEBI-mandated public disclosures.

Bloomberg and LSEG charge $24,000–$32,000/year for this.
SEBI mandates public disclosure. We surface it free.
"""

import logging
from datetime import datetime

import httpx

from finstack.utils.cache import cached, general_cache, fundamentals_cache
from finstack.utils.helpers import clean_nan, validate_symbol

logger = logging.getLogger("finstack.data.credit_esg")

NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com/",
}


# ──────────────────────────────────────────────
# CREDIT RATINGS
# ──────────────────────────────────────────────

@cached(general_cache, ttl=86400)
def get_credit_ratings(symbol: str) -> dict:
    """
    Credit ratings for an Indian listed company from exchange filings.
    Bloomberg/LSEG charge $24,000+/year. SEBI mandates public disclosure on BSE/NSE.
    """
    symbol = validate_symbol(symbol).replace(".NS", "").replace(".BO", "")

    result: dict = {
        "symbol": symbol,
        "timestamp": datetime.now().isoformat(),
    }

    # Try NSE credit ratings API
    with httpx.Client(headers=NSE_HEADERS, timeout=15, follow_redirects=True) as client:
        try:
            # NSE session cookie
            client.get("https://www.nseindia.com/")

            resp = client.get(
                "https://www.nseindia.com/api/corporates-credit-ratings",
                params={"symbol": symbol, "from_date": "01-01-2023", "to_date": datetime.now().strftime("%d-%m-%Y")},
            )
            if resp.status_code == 200:
                data = resp.json()
                ratings = data if isinstance(data, list) else data.get("data", [])

                if ratings:
                    parsed = []
                    for r in ratings[:20]:
                        parsed.append({
                            "rating_agency": r.get("ratingAgency") or r.get("agency", ""),
                            "instrument_type": r.get("instrumentType") or r.get("instrument", ""),
                            "rating": r.get("currentRating") or r.get("rating", ""),
                            "rating_action": r.get("ratingAction") or r.get("action", ""),
                            "outlook": r.get("outlook", ""),
                            "rated_amount_cr": r.get("ratedAmount") or r.get("amount", ""),
                            "date": r.get("ratingDate") or r.get("date", ""),
                        })

                    result["ratings"] = parsed
                    result["total_entries"] = len(ratings)
                    result["data_source"] = "NSE Corporate Filings (SEBI mandated)"
                    result["agencies_seen"] = list(set(p["rating_agency"] for p in parsed if p["rating_agency"]))
                    return clean_nan(result)

        except Exception as e:
            logger.debug("NSE credit ratings API: %s", e)

    # Fallback: BSE credit ratings search
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(
                "https://api.bseindia.com/BseIndiaAPI/api/CreditRating/w",
                params={"scripcode": "", "companyname": symbol},
                headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bseindia.com/"},
            )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    result["ratings"] = data[:10] if isinstance(data, list) else [data]
                    result["data_source"] = "BSE India"
                    return clean_nan(result)
    except Exception as e:
        logger.debug("BSE credit ratings: %s", e)

    result["ratings"] = []
    result["note"] = (
        f"Credit rating disclosures for {symbol} not found via automated fetch. "
        "Check manually: https://www.nseindia.com/companies-listing/corporate-filings-credit-ratings"
    )
    result["agencies"] = {
        "india": ["CRISIL", "ICRA", "CARE Ratings", "India Ratings (Fitch)"],
        "global": ["Moody's", "S&P", "Fitch"],
        "bloomberg_charges": "$24,000/year for this data — SEBI mandates public disclosure",
    }
    result["data_source"] = "NSE/BSE public filings"
    return result


# ──────────────────────────────────────────────
# BRSR / ESG DATA
# ──────────────────────────────────────────────

@cached(fundamentals_cache, ttl=86400)
def get_brsr_esg(symbol: str) -> dict:
    """
    BRSR (Business Responsibility & Sustainability Report) data for Indian listed companies.
    SEBI mandates BRSR from top 1000 listed companies since FY2022-23.
    Bloomberg/LSEG charge $24,000+/year for ESG data. SEBI makes this public. We surface it free.
    """
    symbol = validate_symbol(symbol).replace(".NS", "").replace(".BO", "")

    result: dict = {
        "symbol": symbol,
        "timestamp": datetime.now().isoformat(),
    }

    # Try NSE BRSR filings
    with httpx.Client(headers=NSE_HEADERS, timeout=15, follow_redirects=True) as client:
        try:
            client.get("https://www.nseindia.com/")

            resp = client.get(
                "https://www.nseindia.com/api/corporates-financial-results",
                params={"symbol": symbol, "type": "brsr"},
            )
            if resp.status_code == 200:
                data = resp.json()
                filings = data if isinstance(data, list) else data.get("data", [])

                if filings:
                    result["brsr_filings"] = [
                        {
                            "year": f.get("fromDate", "")[:4],
                            "filing_date": f.get("xbrlLink") or f.get("date", ""),
                            "period": f.get("period", ""),
                            "pdf_link": f.get("pdfLink") or f.get("link", ""),
                        }
                        for f in filings[:5]
                    ]
                    result["data_source"] = "NSE BRSR Filings"
                    result["note"] = "Full BRSR PDF available at links above"
        except Exception as e:
            logger.debug("NSE BRSR: %s", e)

    # Try BSE BRSR/sustainability filings
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(
                "https://api.bseindia.com/BseIndiaAPI/api/AnnualReport/w",
                params={"scripcode": "", "companyname": symbol, "type": "BRSR"},
                headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bseindia.com/"},
            )
            if resp.status_code == 200 and resp.json():
                result["bse_brsr_filings"] = resp.json()[:5] if isinstance(resp.json(), list) else []
                result["data_source"] = result.get("data_source", "") + " + BSE"
    except Exception as e:
        logger.debug("BSE BRSR: %s", e)

    # Always add the SEBI BRSR framework context (public knowledge)
    result["brsr_framework"] = {
        "what_is_brsr": (
            "BRSR = Business Responsibility & Sustainability Report. "
            "SEBI mandates this from India's top 1000 listed companies since FY2022-23."
        ),
        "key_sections": [
            "Section A: General disclosures (employees, turnover, CSR spending)",
            "Section B: Management & process disclosures",
            "Section C: Principle-wise performance (9 principles covering ESG topics)",
        ],
        "principles_covered": [
            "P1: Ethics & Transparency",
            "P2: Sustainable products & services",
            "P3: Employee wellbeing",
            "P4: Stakeholder engagement",
            "P5: Human rights",
            "P6: Environment (GHG emissions, energy, water, waste)",
            "P7: Policy advocacy",
            "P8: Inclusive growth & CSR",
            "P9: Customer responsibility",
        ],
        "bloomberg_esg_charge": "$24,000+/year — SEBI BRSR is free",
        "source": "https://www.sebi.gov.in/legal/circulars/may-2021/business-responsibility-and-sustainability-reporting-by-listed-entities_50096.html",
        "nse_brsr_portal": f"https://www.nseindia.com/companies-listing/corporate-filings-others?type=brsr&symbol={symbol}",
        "bse_brsr_portal": f"https://www.bseindia.com/stock-share-price/{symbol}/",
    }

    if "brsr_filings" not in result and "bse_brsr_filings" not in result:
        result["note"] = (
            f"Automated fetch returned no structured data for {symbol}. "
            "BRSR PDFs are available at the portal links above."
        )
        result["data_source"] = "NSE/BSE SEBI-mandated public filings"

    return clean_nan(result)
