"""
FinStack Rate Limiter

Per-user (or per-API-key) rate limiting.
- Free: 100 requests/day
- Pro: 5,000/day
- API: 50,000/day
- Enterprise: 500,000/day

In local stdio mode, rate limiting is disabled (you're the only user).
In hosted HTTP mode, rate limits are enforced per API key.
"""

import time
import logging
from collections import defaultdict
from finstack.config import UserTier, TIER_RATE_LIMITS

logger = logging.getLogger("finstack.ratelimit")


class RateLimiter:
    """Simple sliding-window rate limiter."""

    def __init__(self):
        # key -> list of timestamps
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._window = 86400  # 24 hours in seconds

    def check(self, key: str, tier: UserTier = UserTier.FREE) -> tuple[bool, dict]:
        """
        Check if a request is allowed.

        Returns:
            (allowed: bool, info: dict) where info contains:
                - remaining: requests left in window
                - limit: total limit
                - reset_at: timestamp when window resets
        """
        now = time.time()
        limit = TIER_RATE_LIMITS.get(tier, 100)

        # Clean old requests outside the window
        self._requests[key] = [
            ts for ts in self._requests[key] if now - ts < self._window
        ]

        current_count = len(self._requests[key])
        remaining = max(0, limit - current_count)

        if current_count >= limit:
            # Find when the oldest request in window expires
            oldest = min(self._requests[key]) if self._requests[key] else now
            reset_at = oldest + self._window

            logger.warning(
                f"Rate limit exceeded for {key[:16]}... "
                f"({current_count}/{limit}, tier={tier.value})"
            )
            return False, {
                "remaining": 0,
                "limit": limit,
                "reset_at": reset_at,
                "tier": tier.value,
                "error": f"Rate limit exceeded. {limit} requests/day for {tier.value} tier. "
                         f"Upgrade to Pro for 5,000/day: https://finstack.dev/pricing"
            }

        # Record this request
        self._requests[key].append(now)

        return True, {
            "remaining": remaining - 1,
            "limit": limit,
            "tier": tier.value,
        }

    def get_usage(self, key: str, tier: UserTier = UserTier.FREE) -> dict:
        """Get current usage stats without consuming a request."""
        now = time.time()
        limit = TIER_RATE_LIMITS.get(tier, 100)

        self._requests[key] = [
            ts for ts in self._requests[key] if now - ts < self._window
        ]

        used = len(self._requests[key])
        return {
            "used": used,
            "remaining": max(0, limit - used),
            "limit": limit,
            "tier": tier.value,
        }

    def cleanup(self) -> None:
        """Remove expired entries to free memory."""
        now = time.time()
        empty_keys = []
        for key in self._requests:
            self._requests[key] = [
                ts for ts in self._requests[key] if now - ts < self._window
            ]
            if not self._requests[key]:
                empty_keys.append(key)
        for key in empty_keys:
            del self._requests[key]


# Global rate limiter instance
rate_limiter = RateLimiter()
