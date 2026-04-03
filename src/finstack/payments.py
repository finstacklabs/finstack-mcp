"""
FinStack Payment & User Management

Handles:
1. API key generation (fsk_pro_xxxx format)
2. Razorpay webhook → tier activation
3. Stripe webhook → tier activation
4. User database (SQLite - zero cost)
5. Key validation on every request

This module is only needed for the hosted version (Week 5+).
Local stdio mode doesn't use this.
"""

import os
import json
import hmac
import hashlib
import secrets
import sqlite3
import logging
from datetime import datetime, timedelta

from finstack.config import UserTier

logger = logging.getLogger("finstack.payments")

DB_PATH = os.getenv("FINSTACK_DB_PATH", "finstack_users.db")


# ===== DATABASE =====

def _get_db() -> sqlite3.Connection:
    """Get SQLite connection with auto-create tables."""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            tier TEXT NOT NULL DEFAULT 'free',
            created_at TEXT NOT NULL,
            expires_at TEXT,
            payment_id TEXT,
            payment_provider TEXT,
            subscription_id TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            requests_today INTEGER NOT NULL DEFAULT 0,
            last_request_date TEXT
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS payment_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event_type TEXT NOT NULL,
            payment_id TEXT,
            amount REAL,
            currency TEXT,
            provider TEXT NOT NULL,
            raw_data TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    db.commit()
    return db


# ===== API KEY GENERATION =====

def generate_api_key(tier: UserTier = UserTier.FREE) -> str:
    """
    Generate a unique API key.

    Format: fsk_{tier}_{random_24_chars}
    Examples:
        fsk_free_a1b2c3d4e5f6g7h8i9j0k1l2
        fsk_pro_x9y8z7w6v5u4t3s2r1q0p9o8
    """
    random_part = secrets.token_hex(12)  # 24 hex chars
    return f"fsk_{tier.value}_{random_part}"


# ===== USER MANAGEMENT =====

def create_user(email: str, tier: UserTier = UserTier.FREE, payment_id: str = "", provider: str = "") -> dict:
    """Create a new user with an API key."""
    db = _get_db()

    # Check if user exists
    existing = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        # Upgrade existing user
        api_key = existing["api_key"]
        expires_at = (datetime.now() + timedelta(days=30)).isoformat() if tier != UserTier.FREE else None

        db.execute("""
            UPDATE users SET tier = ?, expires_at = ?, payment_id = ?,
            payment_provider = ?, is_active = 1 WHERE email = ?
        """, (tier.value, expires_at, payment_id, provider, email))
        db.commit()
        db.close()

        return {
            "email": email,
            "api_key": api_key,
            "tier": tier.value,
            "expires_at": expires_at,
            "status": "upgraded",
        }

    # Create new user
    api_key = generate_api_key(tier)
    now = datetime.now().isoformat()
    expires_at = (datetime.now() + timedelta(days=30)).isoformat() if tier != UserTier.FREE else None

    db.execute("""
        INSERT INTO users (email, api_key, tier, created_at, expires_at, payment_id, payment_provider)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (email, api_key, tier.value, now, expires_at, payment_id, provider))
    db.commit()
    db.close()

    logger.info(f"New user created: {email} (tier={tier.value})")

    return {
        "email": email,
        "api_key": api_key,
        "tier": tier.value,
        "expires_at": expires_at,
        "status": "created",
    }


def validate_api_key(api_key: str) -> dict | None:
    """
    Validate an API key and return user info.
    Returns None if key is invalid or expired.
    """
    if not api_key or not api_key.startswith("fsk_"):
        return None

    db = _get_db()
    user = db.execute("SELECT * FROM users WHERE api_key = ? AND is_active = 1", (api_key,)).fetchone()

    if not user:
        db.close()
        return None

    # Check expiry
    if user["expires_at"]:
        expires = datetime.fromisoformat(user["expires_at"])
        if datetime.now() > expires:
            # Grace period: 3 days
            if datetime.now() > expires + timedelta(days=3):
                db.execute("UPDATE users SET tier = 'free' WHERE api_key = ?", (api_key,))
                db.commit()
                db.close()
                return {
                    "email": user["email"],
                    "tier": UserTier.FREE,
                    "expired": True,
                    "message": "Subscription expired. Downgraded to free tier.",
                }

    # Track daily requests
    today = datetime.now().strftime("%Y-%m-%d")
    if user["last_request_date"] != today:
        db.execute(
            "UPDATE users SET requests_today = 1, last_request_date = ? WHERE api_key = ?",
            (today, api_key)
        )
        requests_today = 1
    else:
        db.execute(
            "UPDATE users SET requests_today = requests_today + 1 WHERE api_key = ?",
            (api_key,)
        )
        requests_today = int(user["requests_today"]) + 1
    db.commit()

    result = {
        "email": user["email"],
        "tier": UserTier(user["tier"]),
        "requests_today": requests_today,
        "expires_at": user["expires_at"],
        "expired": False,
    }
    db.close()
    return result


# ===== RAZORPAY WEBHOOK =====

def handle_razorpay_webhook(payload: bytes, signature: str, secret: str) -> dict:
    """
    Handle Razorpay payment webhook.

    Razorpay sends: payment.captured, subscription.activated, subscription.charged, etc.

    Setup in Razorpay Dashboard:
    1. Go to Settings → Webhooks
    2. Add URL: https://api.finstack.dev/webhook/razorpay
    3. Select events: payment.captured, subscription.activated
    4. Copy webhook secret
    """
    # Verify signature
    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        logger.warning("Razorpay webhook signature mismatch!")
        return {"error": True, "message": "Invalid signature"}

    data = json.loads(payload)
    event = data.get("event", "")

    logger.info(f"Razorpay webhook: {event}")

    if event == "payment.captured":
        payment = data.get("payload", {}).get("payment", {}).get("entity", {})
        email = payment.get("email", "")
        payment_id = payment.get("id", "")
        amount = payment.get("amount", 0) / 100  # Paise to Rupees

        if not email:
            return {"error": True, "message": "No email in payment"}

        # Determine tier from amount
        tier = UserTier.PRO  # Default
        if amount >= 15000:  # ~enterprise ticket in INR
            tier = UserTier.ENTERPRISE
        elif amount >= 4000:  # ~$49 equivalent
            tier = UserTier.API

        result = create_user(email, tier, payment_id, "razorpay")

        # Log payment
        db = _get_db()
        db.execute("""
            INSERT INTO payment_logs (event_type, payment_id, amount, currency, provider, raw_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (event, payment_id, amount, "INR", "razorpay", json.dumps(data), datetime.now().isoformat()))
        db.commit()
        db.close()

        return result

    elif event in ("subscription.activated", "subscription.charged"):
        # Handle subscription renewal
        logger.info(f"Subscription event: {event}")
        return {"status": "processed", "event": event}

    return {"status": "ignored", "event": event}


# ===== STRIPE WEBHOOK =====

def handle_stripe_webhook(payload: bytes, signature: str, secret: str) -> dict:
    """
    Handle Stripe payment webhook.

    Stripe sends: checkout.session.completed, invoice.paid, customer.subscription.deleted, etc.

    Setup in Stripe Dashboard:
    1. Go to Developers → Webhooks
    2. Add endpoint: https://api.finstack.dev/webhook/stripe
    3. Select events: checkout.session.completed, invoice.paid, customer.subscription.deleted
    4. Copy signing secret (whsec_...)
    """
    # Verify signature (Stripe uses timestamp + payload)
    try:
        # Parse Stripe signature header
        sig_parts = dict(part.split("=", 1) for part in signature.split(","))
        timestamp = sig_parts.get("t", "")
        v1_sig = sig_parts.get("v1", "")

        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        expected = hmac.new(
            secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected, v1_sig):
            logger.warning("Stripe webhook signature mismatch!")
            return {"error": True, "message": "Invalid signature"}

    except Exception as e:
        logger.error(f"Stripe signature verification failed: {e}")
        return {"error": True, "message": "Signature verification failed"}

    data = json.loads(payload)
    event_type = data.get("type", "")

    logger.info(f"Stripe webhook: {event_type}")

    if event_type == "checkout.session.completed":
        session = data.get("data", {}).get("object", {})
        email = session.get("customer_email", "")
        payment_id = session.get("payment_intent", "")
        amount = (session.get("amount_total", 0) or 0) / 100  # Cents to dollars

        if not email:
            return {"error": True, "message": "No email in session"}

        tier = UserTier.PRO
        if amount >= 199:
            tier = UserTier.ENTERPRISE
        elif amount >= 49:
            tier = UserTier.API

        result = create_user(email, tier, payment_id, "stripe")

        # Log
        db = _get_db()
        db.execute("""
            INSERT INTO payment_logs (event_type, payment_id, amount, currency, provider, raw_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (event_type, payment_id, amount, "USD", "stripe", json.dumps(data), datetime.now().isoformat()))
        db.commit()
        db.close()

        return result

    elif event_type == "invoice.paid":
        invoice = data.get("data", {}).get("object", {})
        email = invoice.get("customer_email", "")
        if email:
            # Extend subscription by 30 days
            db = _get_db()
            db.execute("""
                UPDATE users SET expires_at = ? WHERE email = ? AND is_active = 1
            """, ((datetime.now() + timedelta(days=30)).isoformat(), email))
            db.commit()
            db.close()
            logger.info(f"Subscription renewed for {email}")
        return {"status": "renewed", "email": email}

    elif event_type == "customer.subscription.deleted":
        sub = data.get("data", {}).get("object", {})
        # Will auto-downgrade when expires_at passes
        logger.info(f"Subscription cancelled: {sub.get('id')}")
        return {"status": "cancelled"}

    return {"status": "ignored", "event": event_type}


# ===== UTILITY =====

def get_user_stats() -> dict:
    """Get overall user statistics (for admin dashboard)."""
    db = _get_db()

    total = db.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    free = db.execute("SELECT COUNT(*) as c FROM users WHERE tier = 'free'").fetchone()["c"]
    pro = db.execute("SELECT COUNT(*) as c FROM users WHERE tier = 'pro'").fetchone()["c"]
    api = db.execute("SELECT COUNT(*) as c FROM users WHERE tier = 'api'").fetchone()["c"]
    enterprise = db.execute("SELECT COUNT(*) as c FROM users WHERE tier = 'enterprise'").fetchone()["c"]

    db.close()

    mrr = (pro * 19) + (api * 49) + (enterprise * 199)

    return {
        "total_users": total,
        "free": free,
        "pro": pro,
        "api": api,
        "enterprise": enterprise,
        "mrr_usd": mrr,
        "mrr_inr": mrr * 84,  # Approximate
        "arr_usd": mrr * 12,
    }
