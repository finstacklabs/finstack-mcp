"""
FinStack Telegram Bot
---------------------
Free WhatsApp-style alerts via Telegram Bot API.

Features:
  - /start → captures chat_id, stores in Supabase
  - Morning brief at 9:00 AM IST (NIFTY, movers, VIX, FII)
  - Price alert delivery when Arthex alert fires
  - Agent Battle verdict delivery

Setup:
  1. Message @BotFather on Telegram → /newbot → copy token
  2. Set env var TELEGRAM_BOT_TOKEN=your_token
  3. Start bot: python telegram_bot.py  (runs alongside uvicorn)

Environment vars needed:
  TELEGRAM_BOT_TOKEN   — from @BotFather
  SUPABASE_URL         — your Supabase project URL
  SUPABASE_SERVICE_KEY — service role key (not anon key) for server-side writes
"""

import os
import asyncio
import httpx
from datetime import datetime, timezone, timedelta

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")  # service role key
API_BASE = os.getenv("SELF_API_BASE", "http://localhost:8000")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
IST = timezone(timedelta(hours=5, minutes=30))


# ─── Telegram HTTP helpers ────────────────────────────────────────────────────

async def tg_get(method: str, params: dict = {}) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{TG_API}/{method}", params=params)
        return r.json()


async def tg_post(method: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{TG_API}/{method}", json=payload)
        return r.json()


async def send_message(chat_id: int | str, text: str, parse_mode: str = "HTML") -> dict:
    return await tg_post("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    })


# ─── Supabase helpers ─────────────────────────────────────────────────────────

def _sb_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


async def save_subscriber(chat_id: int, username: str, first_name: str):
    """Upsert subscriber into telegram_subscribers table."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print(f"[telegram] Supabase not configured — skipping save for {chat_id}")
        return
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"{SUPABASE_URL}/rest/v1/telegram_subscribers",
            headers={**_sb_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"},
            json={
                "chat_id": str(chat_id),
                "username": username or "",
                "first_name": first_name or "",
                "active": True,
            },
        )


async def get_all_subscribers() -> list[dict]:
    """Fetch all active subscribers."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{SUPABASE_URL}/rest/v1/telegram_subscribers",
            headers=_sb_headers(),
            params={"active": "eq.true", "select": "chat_id,first_name"},
        )
        return r.json() if r.status_code == 200 else []


async def mark_unsubscribed(chat_id: int):
    async with httpx.AsyncClient(timeout=10) as client:
        await client.patch(
            f"{SUPABASE_URL}/rest/v1/telegram_subscribers",
            headers=_sb_headers(),
            params={"chat_id": f"eq.{chat_id}"},
            json={"active": False},
        )


# ─── Message formatters ───────────────────────────────────────────────────────

def fmt_num(v, decimals=2):
    if v is None:
        return "—"
    try:
        return f"{float(v):,.{decimals}f}"
    except Exception:
        return str(v)


def fmt_chg(v):
    if v is None:
        return "—"
    try:
        f = float(v)
        arrow = "▲" if f >= 0 else "▼"
        return f"{arrow} {abs(f):.2f}%"
    except Exception:
        return str(v)


async def build_morning_brief() -> str:
    """Fetch live data and compose morning brief message."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            nifty_r = await client.get(f"{API_BASE}/api/nifty")
            vix_r   = await client.get(f"{API_BASE}/api/vix")
            fii_r   = await client.get(f"{API_BASE}/api/fii-dii")
            screen_r = await client.get(f"{API_BASE}/api/screener?filter=gainers")

        nifty = nifty_r.json() if nifty_r.status_code == 200 else {}
        vix_data = vix_r.json() if vix_r.status_code == 200 else {}
        fii = fii_r.json() if fii_r.status_code == 200 else {}
        screen = screen_r.json() if screen_r.status_code == 200 else {}

        n50  = nifty.get("NIFTY50", {})
        bnk  = nifty.get("BANKNIFTY", {})

        # VIX — actual field is current_vix
        vix_val = fmt_num(vix_data.get("current_vix"), 1) if isinstance(vix_data, dict) else "—"

        # FII net — data is list with category field
        fii_net = "—"
        fii_rows = fii.get("data", []) if isinstance(fii, dict) else []
        for row in fii_rows:
            if "FII" in str(row.get("category", "")):
                fii_net = fmt_num(row.get("netValue"), 0)
                break

        # Top gainers
        gainers = screen.get("results", [])[:3]
        gainer_lines = ""
        for g in gainers:
            sym = g.get("symbol", "")
            chg = g.get("change_pct") or g.get("change_percent") or g.get("change") or 0
            gainer_lines += f"\n  • <b>{sym}</b> {fmt_chg(chg)}"

        now_ist = datetime.now(IST).strftime("%d %b %Y, %I:%M %p IST")

        msg = (
            f"🌅 <b>FinStack Morning Brief</b>\n"
            f"<i>{now_ist}</i>\n\n"
            f"📊 <b>Indices</b>\n"
            f"  NIFTY 50   <b>{fmt_num(n50.get('value'))}</b>  {fmt_chg(n50.get('change_pct'))}\n"
            f"  BANKNIFTY  <b>{fmt_num(bnk.get('value'))}</b>  {fmt_chg(bnk.get('change_pct'))}\n\n"
            f"🌡️ <b>India VIX</b>  {vix_val}\n\n"
            f"🏦 <b>FII Net (₹ Cr)</b>  {fii_net}\n\n"
        )

        if gainer_lines:
            msg += f"🚀 <b>Top Movers</b>{gainer_lines}\n\n"

        msg += "📱 <i>Powered by FinStack MCP · arthex.vercel.app</i>"
        return msg

    except Exception as e:
        return f"⚠️ Morning brief unavailable: {e}"


def build_alert_message(symbol: str, condition: str, price: float, current: float) -> str:
    arrow = "🔴" if "below" in condition.lower() or "sell" in condition.lower() else "🟢"
    return (
        f"{arrow} <b>Price Alert — {symbol}</b>\n\n"
        f"Condition: <b>{condition}</b>\n"
        f"Target: ₹{fmt_num(price)}\n"
        f"Current: ₹{fmt_num(current)}\n\n"
        f"<i>View chart → arthex.vercel.app/?symbol={symbol}</i>"
    )


def build_battle_message(symbol: str, signal: str, strength: str, avg_score: float, note: str) -> str:
    emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}.get(signal.upper(), "⚡")
    return (
        f"⚔️ <b>Agent Battle — {symbol}</b>\n\n"
        f"{emoji} Verdict: <b>{signal.upper()}</b>  ({strength})\n"
        f"Avg Score: {avg_score:.2f}\n\n"
        f"{note or ''}\n\n"
        f"<i>Full debate → arthex.vercel.app/battle?symbol={symbol}</i>"
    )


# ─── Update handler ───────────────────────────────────────────────────────────

WELCOME = (
    "👋 Welcome to <b>FinStack Alerts</b>!\n\n"
    "You'll receive:\n"
    "  🌅 Morning brief at 9:00 AM IST\n"
    "  🔔 Price alerts from your Arthex watchlist\n"
    "  ⚔️ Agent Battle verdicts\n\n"
    "Commands:\n"
    "  /brief — get morning brief now\n"
    "  /stop — unsubscribe\n\n"
    "<i>Powered by FinStack MCP</i>"
)


async def handle_update(update: dict) -> dict | None:
    """
    Handle a Telegram update.
    Returns an inline reply dict when called from webhook (Railway can't make outbound calls).
    Returns None when called from polling (reply is sent via send_message instead).
    """
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return None

    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()
    user = msg.get("from", {})
    username = user.get("username", "")
    first_name = user.get("first_name", "")

    def _inline(text: str) -> dict:
        """Build inline webhook reply — no outbound HTTP needed."""
        return {
            "method": "sendMessage",
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

    if text.startswith("/start"):
        try:
            await save_subscriber(chat_id, username, first_name)
        except Exception as e:
            print(f"[telegram] save_subscriber error: {e}")
        return _inline(WELCOME)

    elif text.startswith("/brief"):
        # Can't do async fetch + inline reply simultaneously — send inline "fetching" first
        # then fire-and-forget the actual brief via background task
        asyncio.create_task(_send_brief_delayed(chat_id))
        return _inline("⏳ Fetching morning brief… will arrive in a few seconds.")

    elif text.startswith("/stop"):
        try:
            await mark_unsubscribed(chat_id)
        except Exception:
            pass
        return _inline("✅ Unsubscribed. Send /start to resubscribe.")

    elif text.startswith("/help"):
        return _inline(WELCOME)

    return None


async def _send_brief_delayed(chat_id: int):
    """Fetch brief and send via outbound call (best-effort, may fail on Railway)."""
    try:
        brief = await build_morning_brief()
        await send_message(chat_id, brief)
    except Exception as e:
        print(f"[telegram] Brief send error: {e}")


# ─── Polling loop (runs when script executed directly) ────────────────────────

async def poll_forever():
    """Long-poll Telegram for updates. Run alongside uvicorn in a thread."""
    offset = None
    print(f"[telegram] Polling started. Bot token: ...{BOT_TOKEN[-8:] if BOT_TOKEN else 'NOT SET'}")
    while True:
        try:
            params = {"timeout": 30, "allowed_updates": ["message"]}
            if offset:
                params["offset"] = offset
            resp = await tg_get("getUpdates", params)
            updates = resp.get("result", [])
            for upd in updates:
                await handle_update(upd)
                offset = upd["update_id"] + 1
        except Exception as e:
            print(f"[telegram] Poll error: {e}")
            await asyncio.sleep(5)


# ─── Broadcast helpers (called from main.py endpoints) ───────────────────────

async def broadcast_morning_brief():
    """Send morning brief to all active subscribers. Called by scheduler."""
    brief = await build_morning_brief()
    subs = await get_all_subscribers()
    print(f"[telegram] Broadcasting morning brief to {len(subs)} subscribers")
    for sub in subs:
        try:
            await send_message(sub["chat_id"], brief)
        except Exception as e:
            print(f"[telegram] Failed to send to {sub['chat_id']}: {e}")


async def send_alert_to_subscribers(symbol: str, condition: str, price: float, current: float, chat_ids: list[str] = None):
    """Send price alert. chat_ids=None → broadcast to all."""
    msg = build_alert_message(symbol, condition, price, current)
    targets = chat_ids or [s["chat_id"] for s in await get_all_subscribers()]
    for cid in targets:
        try:
            await send_message(cid, msg)
        except Exception as e:
            print(f"[telegram] Alert send failed for {cid}: {e}")


async def send_battle_to_chat(chat_id: str, symbol: str, signal: str, strength: str, avg_score: float, note: str):
    msg = build_battle_message(symbol, signal, strength, avg_score, note)
    await send_message(chat_id, msg)


# ─── Run standalone ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(poll_forever())
