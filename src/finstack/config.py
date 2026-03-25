"""
FinStack Configuration & Tier Management

Handles all settings, API keys, caching config, and user tier logic.
Tiers: free (default), pro ($19/mo), api ($49/mo), enterprise ($199/mo)
"""

import os
import logging
from enum import Enum
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("finstack")


class UserTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    API = "api"
    ENTERPRISE = "enterprise"


# Rate limits per tier (requests per day)
TIER_RATE_LIMITS = {
    UserTier.FREE: 100,
    UserTier.PRO: 5000,
    UserTier.API: 50000,
    UserTier.ENTERPRISE: 500000,
}

# Which tools are available per tier
# "all" means all tools are available
# Otherwise, list specific tool name prefixes that are LOCKED for free users
FREE_TIER_LOCKED_TOOLS = {
    "nse_options_chain",      # Pro+
    "backtest_strategy",      # Pro+
    "portfolio_analysis",     # Pro+
    "stock_screener",         # Pro+ (basic version free, advanced locked)
    "support_resistance",     # Pro+
}

PRO_TIER_LOCKED_TOOLS = set()  # Pro users get everything except enterprise features

ENTERPRISE_ONLY_TOOLS = {
    "custom_screener",        # Enterprise
    "bulk_export",            # Enterprise
    "webhook_alerts",         # Enterprise
}


@dataclass
class FinStackConfig:
    """Central configuration for the FinStack MCP server."""

    # Server
    host: str = field(default_factory=lambda: os.getenv("FINSTACK_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("FINSTACK_PORT", "8000")))
    log_level: str = field(default_factory=lambda: os.getenv("FINSTACK_LOG_LEVEL", "INFO"))
    mode: UserTier = field(
        default_factory=lambda: UserTier(os.getenv("FINSTACK_MODE", "free"))
    )

    # Cache TTLs (seconds)
    cache_ttl_quotes: int = field(
        default_factory=lambda: int(os.getenv("FINSTACK_CACHE_TTL_QUOTES", "300"))
    )
    cache_ttl_fundamentals: int = field(
        default_factory=lambda: int(os.getenv("FINSTACK_CACHE_TTL_FUNDAMENTALS", "3600"))
    )
    cache_ttl_historical: int = field(
        default_factory=lambda: int(os.getenv("FINSTACK_CACHE_TTL_HISTORICAL", "86400"))
    )

    # API Keys (all optional — core works without them)
    alpha_vantage_key: str = field(
        default_factory=lambda: os.getenv("ALPHA_VANTAGE_API_KEY", "")
    )
    coingecko_key: str = field(
        default_factory=lambda: os.getenv("COINGECKO_API_KEY", "")
    )
    sec_user_agent: str = field(
        default_factory=lambda: os.getenv(
            "SEC_EDGAR_USER_AGENT", "FinStack/0.1.0 finstack@spawnagent.com"
        )
    )

    # Payment (Phase 2+)
    stripe_secret_key: str = field(
        default_factory=lambda: os.getenv("STRIPE_SECRET_KEY", "")
    )
    stripe_webhook_secret: str = field(
        default_factory=lambda: os.getenv("STRIPE_WEBHOOK_SECRET", "")
    )
    razorpay_key_id: str = field(
        default_factory=lambda: os.getenv("RAZORPAY_KEY_ID", "")
    )
    razorpay_key_secret: str = field(
        default_factory=lambda: os.getenv("RAZORPAY_KEY_SECRET", "")
    )

    def is_tool_allowed(self, tool_name: str, user_tier: UserTier | None = None) -> bool:
        """Check if a tool is allowed for the given tier."""
        tier = user_tier or self.mode

        if tier == UserTier.ENTERPRISE:
            return True

        if tier == UserTier.FREE:
            if tool_name in FREE_TIER_LOCKED_TOOLS:
                return False
            if tool_name in ENTERPRISE_ONLY_TOOLS:
                return False
            return True

        if tier in (UserTier.PRO, UserTier.API):
            if tool_name in ENTERPRISE_ONLY_TOOLS:
                return False
            return True

        return True

    def get_rate_limit(self, user_tier: UserTier | None = None) -> int:
        """Get daily request limit for the tier."""
        tier = user_tier or self.mode
        return TIER_RATE_LIMITS.get(tier, 100)

    def setup_logging(self) -> None:
        """Configure logging for the server."""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper(), logging.INFO),
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


# Singleton config instance
config = FinStackConfig()
