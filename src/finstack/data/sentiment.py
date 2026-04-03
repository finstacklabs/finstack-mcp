"""
India social sentiment analyzer for FinStack MCP.

Sources:
  1. StockTwits   — free REST API, no key needed, sentiment pre-tagged (bullish/bearish)
  2. Reddit       — r/IndiaInvestments + r/DalalStreetTalks (needs praw + free app)
  3. Economic Times — news headlines scraped from ET Markets RSS (no key needed)

Setup (Reddit only — StockTwits + ET work with zero setup):
    pip install praw
    REDDIT_CLIENT_ID=your_id
    REDDIT_CLIENT_SECRET=your_secret
    (Create free script app at https://www.reddit.com/prefs/apps)
"""

import os
import re
import logging
from datetime import datetime, timezone

logger = logging.getLogger("finstack.sentiment")

# ── Keyword classifier (fallback when source has no pre-tagged sentiment) ─────

BULLISH_WORDS = {
    "buy", "bullish", "long", "breakout", "strong", "accumulate", "uptrend",
    "bounce", "rally", "momentum", "support", "calls", "target", "hold",
    "all time high", "ath", "buy on dip", "good results", "beat", "outperform",
    "upgraded", "positive", "green", "multibagger", "compounding", "surge",
    "profit", "record", "growth",
}

BEARISH_WORDS = {
    "sell", "bearish", "short", "breakdown", "weak", "exit", "downtrend",
    "fall", "crash", "dump", "puts", "cut", "below", "miss", "missed",
    "downgrade", "negative", "red", "avoid", "warning", "fraud", "scam",
    "pledge", "circuit", "manipulation", "concern", "loss", "risk",
}


def _classify(text: str) -> str:
    lower = text.lower()
    b = sum(1 for w in BULLISH_WORDS if w in lower)
    s = sum(1 for w in BEARISH_WORDS if w in lower)
    return "bullish" if b > s else ("bearish" if s > b else "neutral")


def _extract_themes(texts: list[str]) -> list[str]:
    from collections import Counter
    stop = {
        "the", "a", "an", "is", "are", "was", "for", "in", "on", "at", "to",
        "of", "and", "or", "but", "this", "that", "with", "my", "i", "it",
        "be", "not", "have", "has", "do", "did", "will", "from", "by", "as",
        "so", "if", "its", "up", "down", "just", "me", "we", "they", "he",
        "she", "you", "what", "who", "nse", "bse", "nifty", "stock", "share",
        "market", "india", "get", "got", "can", "cant", "would", "should",
    }
    counts: Counter = Counter()
    for text in texts:
        words = re.findall(r"[a-z]+", text.lower())
        filtered = [w for w in words if w not in stop and len(w) > 2]
        for i in range(len(filtered) - 1):
            counts[f"{filtered[i]} {filtered[i+1]}"] += 1
    return [p for p, c in counts.most_common(5) if c >= 2]


# ── Source 1: StockTwits (free, no API key, sentiment pre-tagged) ─────────────

def _fetch_stocktwits(symbol: str, limit: int = 50) -> list[dict]:
    """
    StockTwits free REST API — no key needed.
    Returns up to 30 most recent messages with bull/bear sentiment.
    Symbol format: just the ticker (RELIANCE, TCS etc.)
    StockTwits uses US format internally but works for many NSE names.
    """
    posts = []
    try:
        import urllib.request
        import json as _json

        url = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
        req = urllib.request.Request(url, headers={"User-Agent": "finstack-mcp/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = _json.loads(resp.read().decode())

        messages = data.get("messages") or []
        for msg in messages[:limit]:
            sentiment_tag = (msg.get("entities") or {}).get("sentiment") or {}
            sentiment = sentiment_tag.get("basic", "").lower() or None  # "Bullish"/"Bearish"/None
            if sentiment:
                sentiment = sentiment.lower()
            else:
                sentiment = _classify(msg.get("body", ""))

            posts.append({
                "source": "stocktwits",
                "text": (msg.get("body") or "")[:400],
                "score": msg.get("likes", {}).get("total", 0) if isinstance(msg.get("likes"), dict) else 0,
                "created": msg.get("created_at", ""),
                "sentiment": sentiment,
            })
    except Exception as e:
        logger.debug("StockTwits fetch error (%s): %s", symbol, e)
    return posts


# ── Source 2: Reddit praw (free, needs client_id + secret) ───────────────────

def _fetch_reddit(symbol: str, limit: int = 40) -> list[dict]:
    """r/IndiaInvestments + r/DalalStreetTalks via praw (read-only)."""
    posts = []
    if not os.getenv("REDDIT_CLIENT_ID") or not os.getenv("REDDIT_CLIENT_SECRET"):
        logger.debug("REDDIT_CLIENT_ID/SECRET not set — skipping Reddit")
        return posts
    try:
        import praw  # type: ignore
        reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent="finstack-mcp:v1.0",
        )
        for sub in ("IndiaInvestments", "DalalStreetTalks"):
            for post in reddit.subreddit(sub).search(symbol, limit=limit // 2, sort="new"):
                text = f"{post.title} {post.selftext}"
                posts.append({
                    "source": f"reddit/r/{sub}",
                    "text": text[:500],
                    "score": post.score,
                    "created": datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat(),
                    "sentiment": _classify(text),
                })
    except ImportError:
        logger.debug("praw not installed — pip install praw")
    except Exception as e:
        logger.warning("Reddit error: %s", e)
    return posts


# ── Source 3: Economic Times Markets RSS (free, no key, scrape) ──────────────

def _fetch_et_news(symbol: str) -> list[dict]:
    """
    Economic Times Markets RSS feed.
    Filters headlines mentioning the symbol.
    ET RSS is public and doesn't need any auth.
    """
    posts = []
    try:
        import urllib.request
        import xml.etree.ElementTree as ET

        feeds = [
            "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",  # stocks news
            "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",       # markets
        ]
        sym_lower = symbol.lower()

        for feed_url in feeds:
            req = urllib.request.Request(
                feed_url,
                headers={"User-Agent": "Mozilla/5.0 finstack-mcp/1.0"},
            )
            try:
                with urllib.request.urlopen(req, timeout=8) as resp:
                    tree = ET.parse(resp)
            except Exception:
                continue

            for item in tree.findall(".//item"):
                title = (item.findtext("title") or "").strip()
                desc  = (item.findtext("description") or "").strip()
                combined = f"{title} {desc}"

                # Only include if the symbol or company name appears
                if sym_lower not in combined.lower():
                    continue

                pub_date = item.findtext("pubDate") or ""
                posts.append({
                    "source": "economic_times",
                    "text": combined[:400],
                    "score": 0,
                    "created": pub_date,
                    "sentiment": _classify(combined),
                })

            if len(posts) >= 20:
                break

    except Exception as e:
        logger.debug("ET news error: %s", e)
    return posts


# ── Main function ─────────────────────────────────────────────────────────────

def get_social_sentiment(symbol: str, limit: int = 100) -> dict:
    """
    Aggregate social + news sentiment for an NSE stock.

    Sources (all free, zero external cost):
      1. StockTwits     — no API key needed, pre-tagged bullish/bearish
      2. Reddit         — r/IndiaInvestments + r/DalalStreetTalks (needs praw + free app)
      3. Economic Times — ET Markets RSS headlines, no key needed

    Returns BUY/HOLD/SELL signal + confidence + key themes + breakdown.
    """
    symbol = symbol.upper().replace(".NS", "").replace(".BO", "")

    # Gather from all 3 sources
    all_posts: list[dict] = []
    all_posts.extend(_fetch_stocktwits(symbol, limit=limit // 3))
    all_posts.extend(_fetch_reddit(symbol, limit=limit // 3))
    all_posts.extend(_fetch_et_news(symbol))

    if not all_posts:
        return {
            "symbol": symbol,
            "error": "No data returned from any source.",
            "sources_tried": ["stocktwits", "reddit", "economic_times"],
            "setup": {
                "stocktwits": "Works with zero setup — no API key needed.",
                "reddit": "pip install praw  |  REDDIT_CLIENT_ID=...  REDDIT_CLIENT_SECRET=...  (free at reddit.com/prefs/apps)",
                "economic_times": "Works with zero setup — public RSS feed.",
            }
        }

    total = len(all_posts)
    bullish = sum(1 for p in all_posts if p["sentiment"] == "bullish")
    bearish = sum(1 for p in all_posts if p["sentiment"] == "bearish")
    neutral = total - bullish - bearish

    bullish_pct = round(bullish / total * 100)
    bearish_pct = round(bearish / total * 100)
    neutral_pct = 100 - bullish_pct - bearish_pct

    if bullish_pct >= 60:
        signal = "BUY"
    elif bearish_pct >= 55:
        signal = "SELL"
    else:
        signal = "HOLD"

    confidence = "high" if total >= 50 else ("medium" if total >= 20 else "low")
    themes = _extract_themes([p["text"] for p in all_posts])

    top_posts = sorted(all_posts, key=lambda p: p.get("score", 0), reverse=True)[:5]
    sample = [
        {"source": p["source"], "text": p["text"][:120], "sentiment": p["sentiment"]}
        for p in top_posts
    ]

    # Per-source breakdown
    sources_used = list({p["source"] for p in all_posts})
    source_breakdown = {}
    for src in sources_used:
        src_posts = [p for p in all_posts if p["source"] == src]
        src_bull = sum(1 for p in src_posts if p["sentiment"] == "bullish")
        src_bear = sum(1 for p in src_posts if p["sentiment"] == "bearish")
        source_breakdown[src] = {
            "count": len(src_posts),
            "bullish": src_bull,
            "bearish": src_bear,
            "neutral": len(src_posts) - src_bull - src_bear,
        }

    theme_str = " · ".join(themes[:3]) if themes else "no strong themes"
    summary = (
        f"{bullish_pct}% bullish · {bearish_pct}% bearish · {neutral_pct}% neutral "
        f"| Key themes: {theme_str} | Signal: {signal}"
    )

    return {
        "symbol": symbol,
        "posts_analyzed": total,
        "bullish_pct": bullish_pct,
        "bearish_pct": bearish_pct,
        "neutral_pct": neutral_pct,
        "signal": signal,
        "confidence": confidence,
        "key_themes": themes,
        "sources": sources_used,
        "source_breakdown": source_breakdown,
        "summary": summary,
        "sample_posts": sample,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }
