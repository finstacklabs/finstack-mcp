"""MCP tool: India social sentiment analyzer."""

import json
from mcp.server.fastmcp import FastMCP


def register_sentiment_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_social_sentiment(symbol: str, limit: int = 100) -> str:
        """
        Analyze social media sentiment for any NSE stock using Reddit + Twitter.

        Scrapes up to `limit` posts from r/IndiaInvestments, r/DalalStreetTalks,
        and Twitter/X, classifies each as bullish/bearish/neutral, extracts key
        themes, and returns a BUY/HOLD/SELL signal with confidence level.

        Falls back to yFinance news headlines if social APIs are not configured.

        Args:
            symbol: NSE stock symbol (e.g. RELIANCE, TCS, INFY)
            limit:  Max posts to analyze (default 100, max 200)

        Returns JSON with:
            - bullish_pct / bearish_pct / neutral_pct
            - signal (BUY / HOLD / SELL)
            - confidence (low / medium / high)
            - key_themes: top recurring topics in the posts
            - summary: single-line readable summary
            - sample_posts: top 5 posts with sentiment tag

        Setup (optional, for real social data):
            pip install praw tweepy
            REDDIT_CLIENT_ID=... REDDIT_CLIENT_SECRET=...
            TWITTER_BEARER_TOKEN=...
        """
        from finstack.data.sentiment import get_social_sentiment as _get
        result = _get(symbol=symbol, limit=min(limit, 200))
        return json.dumps(result, indent=2)
