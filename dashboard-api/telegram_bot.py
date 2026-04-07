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
    """Upsert subscriber into telegram_subscribers table. Silent fail — never blocks reply."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    try:
        async with httpx.AsyncClient(timeout=5) as client:
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
    except Exception:
        pass  # Supabase save is best-effort — welcome message still sends


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
    "<b>Commands:</b>\n"
    "  /brief — full morning market brief\n"
    "  /nifty — live NIFTY &amp; BANKNIFTY prices\n"
    "  /vix — India VIX + regime\n"
    "  /fii — today's FII/DII flow\n"
    "  /signal — latest F&amp;O signal\n"
    "  /pcr — Put-Call Ratio\n"
    "  /q SYMBOL — quick quote (e.g. /q RELIANCE)\n"
    "  /stop — unsubscribe\n\n"
    "<i>Powered by FinStack MCP · arthex.vercel.app</i>"
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
        asyncio.create_task(_send_brief_delayed(chat_id))
        return _inline("⏳ Fetching morning brief… will arrive in a few seconds.")

    elif text.startswith("/nifty"):
        asyncio.create_task(_send_nifty(chat_id))
        return _inline("⏳ Fetching live prices…")

    elif text.startswith("/vix"):
        asyncio.create_task(_send_vix(chat_id))
        return _inline("⏳ Fetching VIX…")

    elif text.startswith("/fii"):
        asyncio.create_task(_send_fii(chat_id))
        return _inline("⏳ Fetching FII/DII data…")

    elif text.startswith("/signal"):
        asyncio.create_task(_send_signal(chat_id))
        return _inline("⏳ Running F&O signal scan…")

    elif text.startswith("/pcr"):
        asyncio.create_task(_send_pcr(chat_id))
        return _inline("⏳ Fetching PCR…")

    elif text.startswith("/q ") or text.startswith("/quote "):
        parts = text.split(None, 1)
        sym = parts[1].strip().upper() if len(parts) > 1 else ""
        if not sym:
            return _inline("Usage: /q RELIANCE")
        asyncio.create_task(_send_quote(chat_id, sym))
        return _inline(f"⏳ Fetching {sym}…")

    elif text.startswith("/stop"):
        try:
            await mark_unsubscribed(chat_id)
        except Exception:
            pass
        return _inline("✅ Unsubscribed. Send /start to resubscribe.")

    elif text.startswith("/help"):
        return _inline(WELCOME)

    return None


# ─── Command helpers (background tasks) ──────────────────────────────────────

async def _send_brief_delayed(chat_id: int):
    try:
        brief = await build_morning_brief()
        await send_message(chat_id, brief)
    except Exception as e:
        print(f"[telegram] Brief send error: {e}")


async def _send_nifty(chat_id: int):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{API_BASE}/api/nifty")
        data = r.json() if r.status_code == 200 else {}
        n50  = data.get("NIFTY50", {})
        bnk  = data.get("BANKNIFTY", {})

        def _fmt(d: dict) -> str:
            val = fmt_num(d.get("value"))
            chg = fmt_chg(d.get("change_pct"))
            return f"<b>{val}</b>  {chg}"

        msg = (
            "📊 <b>Live Indices</b>\n\n"
            f"  NIFTY 50    {_fmt(n50)}\n"
            f"  BANKNIFTY   {_fmt(bnk)}\n\n"
            f"<i>{datetime.now(IST).strftime('%d %b %Y, %I:%M %p IST')}</i>"
        )
        await send_message(chat_id, msg)
    except Exception as e:
        await send_message(chat_id, f"⚠️ Could not fetch prices: {e}")


async def _send_vix(chat_id: int):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{API_BASE}/api/vix")
        data = r.json() if r.status_code == 200 else {}
        vix  = data.get("current_vix") or data.get("vix")
        vix_val = f"{float(vix):.2f}" if vix else "—"

        # Regime label
        try:
            v = float(vix)
            if v < 11:   regime = "💀 Dead (premiums flat)"
            elif v <= 20: regime = "🟢 Sweet spot (best to buy options)"
            elif v <= 28: regime = "🟡 Elevated (buy with caution)"
            elif v <= 40: regime = "🔴 Fear zone (only strong signals)"
            else:          regime = "🚨 Panic (avoid buying)"
        except Exception:
            regime = "—"

        msg = (
            f"🌡️ <b>India VIX</b>\n\n"
            f"  Current: <b>{vix_val}</b>\n"
            f"  Regime:  {regime}\n\n"
            f"<i>VIX measures market fear. Low = calm, High = volatile.</i>"
        )
        await send_message(chat_id, msg)
    except Exception as e:
        await send_message(chat_id, f"⚠️ Could not fetch VIX: {e}")


async def _send_fii(chat_id: int):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{API_BASE}/api/fii-dii")
        data = r.json() if r.status_code == 200 else {}
        rows = data.get("data", []) if isinstance(data, dict) else []

        lines = ""
        for row in rows[:4]:
            cat = row.get("category", "")
            net = row.get("netValue") or row.get("net_value") or 0
            arrow = "🟢" if float(net) >= 0 else "🔴"
            lines += f"  {arrow} <b>{cat}</b>  {fmt_num(net, 0)} Cr\n"

        msg = (
            f"🏦 <b>FII / DII Flow — Today</b>\n\n"
            f"{lines or '  No data available'}\n"
            f"<i>{datetime.now(IST).strftime('%d %b %Y')}</i>"
        )
        await send_message(chat_id, msg)
    except Exception as e:
        await send_message(chat_id, f"⚠️ Could not fetch FII data: {e}")


async def _send_signal(chat_id: int):
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(f"{API_BASE}/api/fno-signals")
        data = r.json() if r.status_code == 200 else {}
        signals = data.get("signals", [])
        vix     = data.get("vix", 0)
        regime  = data.get("regime", "unknown")

        active = [s for s in signals if s.get("direction") not in (None, "NO_SIGNAL")]

        if not active:
            scores = [f"{s['symbol']} {s.get('score',0)}/{s.get('min_score','?')}" for s in signals]
            msg = (
                f"⚡ <b>F&amp;O Signals</b>\n\n"
                f"No signal right now.\n"
                f"VIX <b>{vix:.1f}</b> · regime <b>{regime}</b>\n\n"
                f"Scores: {' | '.join(scores) or '—'}\n\n"
                f"<i>Open Arthex for live updates → arthex.vercel.app</i>"
            )
        else:
            lines = ""
            for s in active:
                dir_icon = "🟢 BUY CALL ↑" if s["direction"] == "BUY_CE" else "🔴 BUY PUT ↓"
                lines += (
                    f"\n<b>{s['symbol']}</b> — {dir_icon}\n"
                    f"  Strike: <code>{s.get('trading_symbol','—')}</code>\n"
                    f"  Score:  {s.get('score','?')}/{s.get('max_score',8)}\n"
                    f"  Spot:   {fmt_num(s.get('spot',0), 2)}\n"
                )
                for reason in s.get("reasons", [])[:2]:
                    lines += f"  ▸ {reason}\n"

            msg = (
                f"⚡ <b>F&amp;O Signals</b>\n"
                f"VIX <b>{vix:.1f}</b> · {regime} regime\n"
                f"{lines}\n"
                f"<i>Approve on Arthex → arthex.vercel.app</i>"
            )
        await send_message(chat_id, msg)
    except Exception as e:
        await send_message(chat_id, f"⚠️ Signal scan failed: {e}")


async def _send_pcr(chat_id: int):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{API_BASE}/api/pcr")
        data = r.json() if r.status_code == 200 else {}

        nifty_pcr = data.get("NIFTY") or data.get("nifty") or {}
        bnk_pcr   = data.get("BANKNIFTY") or data.get("banknifty") or {}

        def _pcr_line(d) -> str:
            if isinstance(d, dict):
                pcr = d.get("pcr") or d.get("put_call_ratio")
            else:
                pcr = d
            if not pcr:
                return "—"
            v = float(pcr)
            sentiment = "🟢 Bullish" if v < 0.8 else ("🔴 Bearish" if v > 1.25 else "🟡 Neutral")
            return f"<b>{v:.2f}</b>  {sentiment}"

        msg = (
            f"📉 <b>Put-Call Ratio (PCR)</b>\n\n"
            f"  NIFTY      {_pcr_line(nifty_pcr)}\n"
            f"  BANKNIFTY  {_pcr_line(bnk_pcr)}\n\n"
            f"<i>PCR &lt; 0.8 = bullish · PCR &gt; 1.25 = bearish</i>"
        )
        await send_message(chat_id, msg)
    except Exception as e:
        await send_message(chat_id, f"⚠️ Could not fetch PCR: {e}")


async def _send_quote(chat_id: int, symbol: str):
    try:
        yf_sym = symbol if "." in symbol else f"{symbol}.NS"
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{API_BASE}/api/quote/{yf_sym}")
        data = r.json() if r.status_code == 200 else {}

        ltp  = data.get("ltp") or data.get("last_price") or data.get("price")
        chg  = data.get("change_pct") or data.get("change_percent")
        high = data.get("day_high") or data.get("high")
        low  = data.get("day_low")  or data.get("low")
        vol  = data.get("volume")

        if not ltp:
            await send_message(chat_id, f"⚠️ No data for <b>{symbol}</b>. Check symbol (e.g. RELIANCE, TCS, INFY).")
            return

        chg_str = fmt_chg(chg) if chg else "—"
        icon    = "🟢" if (chg and float(chg) >= 0) else "🔴"

        msg = (
            f"{icon} <b>{symbol}</b>\n\n"
            f"  LTP:    <b>₹{fmt_num(ltp)}</b>  {chg_str}\n"
            f"  High:   ₹{fmt_num(high)}\n"
            f"  Low:    ₹{fmt_num(low)}\n"
            f"  Volume: {fmt_num(vol, 0) if vol else '—'}\n\n"
            f"<i>Chart → arthex.vercel.app/?symbol={symbol}</i>"
        )
        await send_message(chat_id, msg)
    except Exception as e:
        await send_message(chat_id, f"⚠️ Quote failed for {symbol}: {e}")


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
