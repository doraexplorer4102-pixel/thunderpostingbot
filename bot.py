import os
import re
import ssl
import json
import logging
import asyncio
from datetime import datetime, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo

import pg8000.native

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MessageEntity,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ---------------------------------------------------------------------------
# Logging (helps you SEE in the console/logs whether the scheduler is running
# and whether it finds posts that are due)
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("thunder_bot")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = -1002478427301
OWNER_ID = 8919616891

# Your local timezone. Scheduling times you type in (DD-MM-YYYY HH:MM) are
# treated as being in THIS timezone. Everything is converted to UTC for
# storage/comparison so it works correctly no matter where the bot server is
# physically hosted.
LOCAL_TZ = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")

# ---------------------------------------------------------------------------
# Button configuration
# ---------------------------------------------------------------------------
# Telegram Bot API 9.4 (Feb 2026) added a real "style" field for inline
# keyboard buttons, with three options:
#   "primary" -> blue
#   "success" -> green
#   "danger"  -> red
# This is exactly what gives the colored full-width buttons you saw in the
# JJ Trader screenshot ("Not Claim 1000$?" = blue/primary, "Click Here To
# Claim" = green/success).
#
# IMPORTANT: this requires python-telegram-bot version that supports the
# `style` argument on InlineKeyboardButton (v22.6+ / anything built on Bot
# API 9.4+). If you're on an older version, run:
#   pip install -U python-telegram-bot
# If your installed version is too old and doesn't recognize `style`, it
# will raise a TypeError on startup - upgrading the library fixes it.
USERNAME = "THUNDERVIPSIGNALS"

BUTTON_CONFIG = {
    "vip": {
        "toggle_label": "🤔 Want To Join VIP? 💎",
        "post_label": "🤔 Want To Join VIP? 💎",
        "post_entities": [
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=0, length=2, custom_emoji_id="5389006967937184376"),
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=21, length=2, custom_emoji_id="5427168083074628963"),
        ],
        "style": "primary",   # blue
        "message": "Hi Thunder, I want to join Thunder VIP. Please guide me 😊",
    },
    "signals": {
        "toggle_label": "📈 Want Free Signals? ✨",
        "post_label": "📈 Want Free Signals? ✨",
        "post_entities": [
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=0, length=2, custom_emoji_id="5244837092042750681"),
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=22, length=1, custom_emoji_id="5325547803936572038"),
        ],
        "style": "success",   # green
        "message": "Hi Thunder, I want to get Free Signals. Please guide me 😊",
    },
    "contact": {
        "toggle_label": "💬 Contact Thunder ❤️",
        "post_label": "💬 Contact Thunder ❤️",
        "post_entities": [
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=0, length=2, custom_emoji_id="5443038326535759644"),
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=16, length=2, custom_emoji_id="6296218646284863141"),
        ],
        "style": "primary",   # blue
        "message": "Hi Thunder, I have a question. Please help me 😊",
    },
    "join": {
        "toggle_label": "🚀 CLICK HERE TO JOIN ✅",
        "post_label": "🚀 CLICK HERE TO JOIN ✅",
        "post_entities": [
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=0, length=2, custom_emoji_id="5188481279963715781"),
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=22, length=2, custom_emoji_id="5206607081334906820"),
        ],
        "style": "success",   # green
        "message": "Hi Thunder, I want to know the joining process. Please guide me 😊",
    },
    "free_money": {
        "toggle_label": "💸 Want Free Money? 🤑",
        "post_label": "💸 Want Free Money? 🤑",
        "post_entities": [
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=0, length=2, custom_emoji_id="5409048419211682843"),
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=20, length=2, custom_emoji_id="5427107837568360763"),
        ],
        "style": "primary",   # blue
        "message": "hi brother i want to know how i can earn free money",
    },
    "winning_signals": {
        "toggle_label": "🎯 Want 100% Winning Signals? 💯",
        "post_label": "🎯 Want 100% Winning Signals? 💯",
        "post_entities": [
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=0, length=2, custom_emoji_id="6185808707985608949"),
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=30, length=2, custom_emoji_id="5274195706066781810"),
        ],
        "style": "success",   # green
        "message": "hi brother i want 100% winning signals",
    },
    "daily_trades": {
        "toggle_label": "🎯 Want Daily 10-20 Trades? 📊",
        "post_label": "🎯 Want Daily 10-20 Trades? 📊",
        "post_entities": [],
        "style": "success",   # green
        "message": "hi brother i want daily 10-20 non-martingale signals",
    },
    "recover": {
        "toggle_label": "📉 Want To Recover Losses? 🔄",
        "post_label": "📉 Want To Recover Losses? 🔄",
        "post_entities": [
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=0, length=2, custom_emoji_id="5246762912428603768"),
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=27, length=2, custom_emoji_id="5375338737028841420"),
        ],
        "style": "primary",   # blue
        "message": "hi brother i want to recover my losses",
    },
    "learn_trading": {
        "toggle_label": "📚 Want To Learn Trading? ✨",
        "post_label": "📚 Want To Learn Trading? ✨",
        "post_entities": [
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=0, length=2, custom_emoji_id="5222444124698853913"),
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=26, length=1, custom_emoji_id="6154375654822384628"),
        ],
        "style": "success",   # green
        "message": "hi brother please teach me trading for free",
    },
    "start": {
        "toggle_label": "🚀 CLICK HERE TO START ⚡",
        "post_label": "🚀 CLICK HERE TO START ⚡",
        "post_entities": [
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=0, length=2, custom_emoji_id="5188481279963715781"),
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=23, length=1, custom_emoji_id="5411590687663608498"),
        ],
        "style": "primary",   # blue
        "message": "hi brother i want to start my trading journey with you",
    },
    "inr_lakh": {
        "toggle_label": "💰 Want ₹1000 to ₹1 Lakh? 🔥",
        "post_label": "💰 Want ₹1000 to ₹1 Lakh? 🔥",
        "post_entities": [
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=0, length=2, custom_emoji_id="5409048419211682843"),
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=26, length=2, custom_emoji_id="5424972470023104089"),
        ],
        "style": "success",   # green
        "message": "hi brother mujhe ₹1000 se ₹1Lakh bnana hai",
    },
    "giveaway": {
        "toggle_label": "🎁 Want $1000 Giveaway? 💵",
        "post_label": "🎁 Want $1000 Giveaway? 💵",
        "post_entities": [
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=0, length=2, custom_emoji_id="5203996991054432397"),
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=24, length=2, custom_emoji_id="5409048419211682843"),
        ],
        "style": "primary",   # blue
        "message": "Hi bhai mujhe $1000 ka giveaway chahiye",
    },
    "claim": {
        "toggle_label": "🎉 CLICK HERE TO CLAIM 🏆",
        "post_label": "🎉 CLICK HERE TO CLAIM 🏆",
        "post_entities": [
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=0, length=2, custom_emoji_id="5461151367559141950"),
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=23, length=2, custom_emoji_id="5413566144986503832"),
        ],
        "style": "success",   # green
        "message": "Hi bhai I want to claim my Bonus & Join with you",
    },
    "free_vip": {
        "toggle_label": "Free VIP 🤑",
        "post_label": "Free VIP 🤑",
        "post_entities": [
            MessageEntity(type=MessageEntity.CUSTOM_EMOJI, offset=9, length=2, custom_emoji_id="5427107837568360763"),
        ],
        "style": "primary",   # blue
        "message": "Hi Thunder, I want to join your VIP Signal Channel. Please guide me 😊",
    },
    "subscribe": {
        "toggle_label": "🔴 Subscribe Now ▶️",
        "post_label": "🔴 Subscribe Now ▶️",
        "post_entities": [],
        "style": "danger",    # red
        "url": "https://www.youtube.com/@tradewiththunder",  # direct URL button (no Telegram message)
    },
    "create_account": {
        "toggle_label": "✅ CREATE ACCOUNT 🔥",
        "post_label": "✅ CREATE ACCOUNT 🔥",
        "post_entities": [],
        "style": "success",   # green
        "url": "https://broker-qx.pro/sign-up/?lid=2111226",  # direct URL button (no Telegram message)
    },

    # ---- New buttons (Hindi/Hinglish) ----
    "free_training_course": {
        "toggle_label": "🎓 Free Training Course Chahiye 📥",
        "post_label": "🎓 Free Training Course Chahiye 📥",
        "post_entities": [],
        "style": "primary",
        "message": "hi brother i want your free training course pdf or link",
    },
    "trading_course": {
        "toggle_label": "🎓 Trading Course Chahiye 🎓",
        "post_label": "🎓 Trading Course Chahiye 🎓",
        "post_entities": [],
        "style": "success",
        "message": "hi brother trading course chahiye",
    },
    "free_signal_chahiye": {
        "toggle_label": "🎯 Free Signal Chahiye? 📲",
        "post_label": "🎯 Free Signal Chahiye? 📲",
        "post_entities": [],
        "style": "primary",
        "message": "hi brother free signal chahiye",
    },
    "paisa_kamana": {
        "toggle_label": "💰 Paisa Kamana Hai 💰",
        "post_label": "💰 Paisa Kamana Hai 💰",
        "post_entities": [],
        "style": "success",
        "message": "hi brother paisa kamana hai",
    },
    "rs500_shuru": {
        "toggle_label": "💵 ₹500 Se Shuru Karo 💵",
        "post_label": "💵 ₹500 Se Shuru Karo 💵",
        "post_entities": [],
        "style": "primary",
        "message": "hi brother ₹500 se kaise shuru karu",
    },
    "bonus_claim_karo": {
        "toggle_label": "🎁 Bonus Claim Karo 🎁",
        "post_label": "🎁 Bonus Claim Karo 🎁",
        "post_entities": [],
        "style": "success",
        "message": "hi brother bonus claim karna hai",
    },
    "aaj_free_gift": {
        "toggle_label": "🎁 Aaj Ka Free Gift 🎁",
        "post_label": "🎁 Aaj Ka Free Gift 🎁",
        "post_entities": [],
        "style": "primary",
        "message": "hi brother aaj ka free gift chahiye",
    },

    # ---- New buttons (English - VIP / Access) ----
    "unlock_vip_free": {
        "toggle_label": "🔓 Unlock VIP For Free Today 🗝️",
        "post_label": "🔓 Unlock VIP For Free Today 🗝️",
        "post_entities": [],
        "style": "success",
        "message": "hi brother how can i unlock vip for free today",
    },
    "private_group_access": {
        "toggle_label": "🔐 Private Group Access 🚪",
        "post_label": "🔐 Private Group Access 🚪",
        "post_entities": [],
        "style": "primary",
        "message": "hi brother i want access to the private group",
    },
    "vip_earn": {
        "toggle_label": "🤑 See What VIP Members Earn 🤑",
        "post_label": "🤑 See What VIP Members Earn 🤑",
        "post_entities": [],
        "style": "success",
        "message": "hi brother what do vip members actually earn",
    },

    # ---- New buttons (English - Signals) ----
    "free_signals_daily": {
        "toggle_label": "🧃 Free Signals, Daily 🆕",
        "post_label": "🧃 Free Signals, Daily 🆕",
        "post_entities": [],
        "style": "primary",
        "message": "hi brother send me today's fresh signal",
    },
    "accuracy_95": {
        "toggle_label": "🎯 95% Accuracy — See How 🔬",
        "post_label": "🎯 95% Accuracy — See How 🔬",
        "post_entities": [],
        "style": "success",
        "message": "hi brother how do you get 95% accuracy",
    },

    # ---- New buttons (English - Recovery) ----
    "recover_losses_today": {
        "toggle_label": "📉 Recover Your Losses Today ♻️",
        "post_label": "📉 Recover Your Losses Today ♻️",
        "post_entities": [],
        "style": "primary",
        "message": "hi brother help me recover my losses today",
    },
    "still_losing": {
        "toggle_label": "🤔 Still Losing Money? 🔴",
        "post_label": "🤔 Still Losing Money? 🔴",
        "post_entities": [],
        "style": "danger",
        "message": "hi brother i keep losing money, please help me",
    },

    # ---- New buttons (English - Free stuff / Bonus) ----
    "free_pdf": {
        "toggle_label": "📥 Free Trading PDF Inside 📚",
        "post_label": "📥 Free Trading PDF Inside 📚",
        "post_entities": [],
        "style": "success",
        "message": "hi brother send me the free trading pdf",
    },
    "unlock_bonus": {
        "toggle_label": "🎁 Unlock Your Free Bonus 🔓",
        "post_label": "🎁 Unlock Your Free Bonus 🔓",
        "post_entities": [],
        "style": "primary",
        "message": "hi brother how do i unlock my free bonus",
    },
    "new_here_gift": {
        "toggle_label": "🎈 New Here? Get A Free Gift 🎀",
        "post_label": "🎈 New Here? Get A Free Gift 🎀",
        "post_entities": [],
        "style": "success",
        "message": "hi brother i am new, how do i get the free gift",
    },
    "today_only_free": {
        "toggle_label": "🎁 Today Only: Free Access 🎁",
        "post_label": "🎁 Today Only: Free Access 🎁",
        "post_entities": [],
        "style": "primary",
        "message": "hi brother i want today's free access",
    },

    # ---- New buttons (English - Beginners) ----
    "beginner_start": {
        "toggle_label": "🎓 Beginner? Start Here 👶",
        "post_label": "🎓 Beginner? Start Here 👶",
        "post_entities": [],
        "style": "success",
        "message": "hi brother i am a beginner, where do i start",
    },
    "new_trader": {
        "toggle_label": "🐣 New Trader? This Is For You 🐣",
        "post_label": "🐣 New Trader? This Is For You 🐣",
        "post_entities": [],
        "style": "primary",
        "message": "hi brother i'm new, is this for me",
    },
    "zero_to_profit": {
        "toggle_label": "🚀 Zero Experience To Profit 💹",
        "post_label": "🚀 Zero Experience To Profit 💹",
        "post_entities": [],
        "style": "success",
        "message": "hi brother i have zero experience, can i still profit",
    },
    "last_chance_free": {
        "toggle_label": "🚨 Last Chance To Join Free 🚪",
        "post_label": "🚨 Last Chance To Join Free 🚪",
        "post_entities": [],
        "style": "danger",
        "message": "hi brother is it too late to join for free",
    },

    # ---- New buttons (English - Social Proof) ----
    "join_10k": {
        "toggle_label": "🏅 Join 10,000+ Traders 👥",
        "post_label": "🏅 Join 10,000+ Traders 👥",
        "post_entities": [],
        "style": "primary",
        "message": "hi brother i want to join your community of traders",
    },
    "no_fake_gurus": {
        "toggle_label": "🎭 No More Fake Gurus 🎯",
        "post_label": "🎭 No More Fake Gurus 🎯",
        "post_entities": [],
        "style": "success",
        "message": "hi brother prove this is real, not fake",
    },

    # ---- New buttons (CLICK HERE style, grouped last as requested) ----
    "click_begin": {
        "toggle_label": "👉 CLICK HERE TO BEGIN 🚀",
        "post_label": "👉 CLICK HERE TO BEGIN 🚀",
        "post_entities": [],
        "style": "primary",
        "message": "hi brother i want to begin",
    },
    "click_unlock": {
        "toggle_label": "👉 CLICK HERE TO UNLOCK 🔓",
        "post_label": "👉 CLICK HERE TO UNLOCK 🔓",
        "post_entities": [],
        "style": "success",
        "message": "hi brother i want to unlock this",
    },
    "click_profit": {
        "toggle_label": "👉 CLICK HERE TO PROFIT 💰",
        "post_label": "👉 CLICK HERE TO PROFIT 💰",
        "post_entities": [],
        "style": "primary",
        "message": "hi brother i want to start profiting",
    },
    "click_access_vip": {
        "toggle_label": "👉 CLICK HERE TO ACCESS VIP 💎",
        "post_label": "👉 CLICK HERE TO ACCESS VIP 💎",
        "post_entities": [],
        "style": "success",
        "message": "hi brother i want to access vip",
    },
    "click_get_signals": {
        "toggle_label": "👉 CLICK HERE TO GET SIGNALS 📲",
        "post_label": "👉 CLICK HERE TO GET SIGNALS 📲",
        "post_entities": [],
        "style": "primary",
        "message": "hi brother i want to get signals",
    },
    "click_recover": {
        "toggle_label": "👉 CLICK HERE TO RECOVER 📉",
        "post_label": "👉 CLICK HERE TO RECOVER 📉",
        "post_entities": [],
        "style": "success",
        "message": "hi brother i want to recover my losses",
    },
}


def make_telegram_link(username: str, text: str) -> str:
    """Build a t.me link that opens a chat with `username` and pre-fills
    the message box with `text`, properly URL-encoded so Telegram decodes
    it back into normal readable text (instead of showing %20, %F0... etc)."""
    return f"https://t.me/{username}?text={quote(text, safe='')}"


def utf16_len(text: str) -> int:
    """Return the length of text in UTF-16 code units (what Telegram uses for offsets)."""
    return len(text.encode("utf-16-le")) // 2


# Broad emoji-range pattern used only for the one-time cleanup below - not a
# strict validator, just good enough to find/strip emoji glyphs from labels.
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F000-\U0001FAFF"
    "\u2190-\u21FF"
    "\u2300-\u27BF"
    "\u2B00-\u2BFF"
    "\uFE0F"
    "]+"
)


def _strip_premium_emoji():
    """Since Telegram silently drops icon_custom_emoji_id / custom_emoji
    entities for bots posting to channels without a Fragment username
    (confirmed via live diagnostics), stop sending them entirely. This
    restores each button to its ORIGINAL plain-text label with BOTH emoji
    characters exactly as first written, and clears post_entities so no
    custom_emoji_id is ever attached to a button icon or message text."""
    for cfg in BUTTON_CONFIG.values():
        # Labels are left untouched here on purpose - they already contain
        # both original plain emoji characters as literal text.
        cfg["post_entities"] = []


_strip_premium_emoji()


# Reverse lookup: post_label -> config key (built once at startup)
_LABEL_TO_KEY = {cfg["post_label"]: key for key, cfg in BUTTON_CONFIG.items()}


def build_inline_keyboard(selected, use_icons=True):
    """Build the InlineKeyboardMarkup for the final post based on the list
    of selected button labels — ORDER PRESERVED exactly as clicked.

    Colors are cycled (blue -> green -> red -> blue -> ...) across the
    buttons in click order, guaranteeing no two adjacent buttons ever share
    the same color, regardless of each button's individually configured
    style. This directly answers "I always want different colors".

    use_icons=True attaches a premium custom-emoji icon to each button
    (icon_custom_emoji_id), taken from that button's single configured
    custom emoji (see _normalize_button_config). This is subject to the
    same Telegram eligibility rule as custom emoji in message text:
    private/group/supergroup chats, or a bot with a paid Fragment
    username. Pass use_icons=False to build a plain fallback keyboard for
    when Telegram rejects the icons."""
    buttons = []
    color_cycle = ["primary", "success", "danger"]

    # Iterate selected IN CLICK ORDER (not BUTTON_CONFIG order)
    for i, label in enumerate(selected):
        key = _LABEL_TO_KEY.get(label)
        if key is None:
            continue
        cfg = BUTTON_CONFIG[key]
        # Support both direct URL buttons and Telegram message buttons
        if "url" in cfg:
            url = cfg["url"]
        else:
            url = make_telegram_link(USERNAME, cfg["message"])

        icon_id = None
        if use_icons:
            post_ents = cfg.get("post_entities", [])
            if post_ents:
                icon_id = post_ents[0].custom_emoji_id

        style = color_cycle[i % len(color_cycle)]

        try:
            button = InlineKeyboardButton(
                cfg["post_label"],
                url=url,
                style=style,
                icon_custom_emoji_id=icon_id,
            )
        except TypeError:
            logger.warning(
                "Your python-telegram-bot version doesn't support "
                "button colors/icons (style=.../icon_custom_emoji_id=...). "
                "Run 'pip install -U python-telegram-bot' to enable them."
            )
            button = InlineKeyboardButton(cfg["post_label"], url=url)
        buttons.append([button])

    return InlineKeyboardMarkup(buttons) if buttons else None


def with_bold(text, base_entities=None):
    """Return an entities list that makes the WHOLE text bold, on top of any
    existing entities (e.g. premium custom emoji). Used everywhere we send a
    caption or text message so formatting is always consistent."""
    if not text:
        return base_entities or None
    entities = list(base_entities) if base_entities else []
    entities.append(MessageEntity(type=MessageEntity.BOLD, offset=0, length=utf16_len(text)))
    return entities


def entities_to_json(entities):
    """Serialize a list of MessageEntity objects to a JSON string for DB storage."""
    if not entities:
        return ""
    return json.dumps([
        {
            "type": e.type,
            "offset": e.offset,
            "length": e.length,
            "custom_emoji_id": getattr(e, "custom_emoji_id", None),
        }
        for e in entities
    ])


def entities_from_json(json_str):
    """Deserialize entities saved via entities_to_json back into MessageEntity objects."""
    if not json_str:
        return []
    try:
        raw = json.loads(json_str)
    except Exception:
        return []
    out = []
    for e in raw:
        kwargs = dict(type=e["type"], offset=e["offset"], length=e["length"])
        if e.get("custom_emoji_id"):
            kwargs["custom_emoji_id"] = e["custom_emoji_id"]
        out.append(MessageEntity(**kwargs))
    return out


async def safe_send(send_fn, entities, markup=None, fallback_markup=None):
    """Send a message/caption (and its keyboard) using premium custom-emoji
    entities and/or button icons. If Telegram rejects them (this happens
    outside private/group/supergroup chats - e.g. channels - unless the bot
    owns a paid Fragment username), automatically retry with the custom
    emoji stripped and the plain fallback keyboard, so the post still goes
    out - just with regular emoji glyphs instead of animated/premium ones,
    and bold formatting still intact.

    send_fn(entities, markup) -> awaitable performing the actual send."""
    try:
        return await send_fn(entities, markup)
    except Exception as e:
        has_custom_emoji = entities and any(
            getattr(ent, "type", None) == MessageEntity.CUSTOM_EMOJI for ent in entities
        )
        has_icon_markup = fallback_markup is not None and fallback_markup is not markup
        if has_custom_emoji or has_icon_markup:
            logger.warning("Premium emoji/icons were rejected for this chat, retrying without them: %s", e)
            stripped = [
                ent for ent in (entities or [])
                if getattr(ent, "type", None) != MessageEntity.CUSTOM_EMOJI
            ]
            return await send_fn(stripped, fallback_markup if fallback_markup is not None else markup)
        raise


def build_premium_text(selected):
    """Build a text message with premium emoji entities for selected buttons.
    Returns (text, entities) to be sent as a separate message with buttons.
    ORDER PRESERVED exactly as clicked."""
    lines = []
    entities = []
    offset = 0

    # Iterate selected IN CLICK ORDER (not BUTTON_CONFIG order)
    for label in selected:
        key = _LABEL_TO_KEY.get(label)
        if key is None:
            continue
        cfg = BUTTON_CONFIG[key]
        post_ents = cfg.get("post_entities", [])

        for ent in post_ents:
            entities.append(
                MessageEntity(
                    type=MessageEntity.CUSTOM_EMOJI,
                    offset=offset + ent.offset,
                    length=ent.length,
                    custom_emoji_id=ent.custom_emoji_id,
                )
            )

        lines.append(label)
        offset += utf16_len(label) + 1  # +1 for newline

    if not lines:
        return None, []

    text = "\n".join(lines)
    return text, entities



# ---------------------------------------------------------------------------
# Database (Postgres) — survives restarts/redeploys, unlike the old local file.
# Reads the connection string from the DATABASE_URL environment variable.
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set!")


def _make_ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _parse_db_url(url):
    url = url.replace("postgresql://", "").replace("postgres://", "")
    userpass, rest = url.split("@", 1)
    user, password = userpass.split(":", 1)
    hostport, database = rest.split("/", 1)
    host, port = (hostport.split(":") + ["5432"])[:2]
    return dict(host=host, port=int(port), user=user, password=password, database=database)


_DB_PARAMS = _parse_db_url(DATABASE_URL)
_db_conn = None


def _get_conn():
    global _db_conn
    try:
        if _db_conn is not None:
            _db_conn.run("SELECT 1")
            return _db_conn
    except Exception:
        _db_conn = None
    _db_conn = pg8000.native.Connection(**_DB_PARAMS, ssl_context=_make_ssl_ctx())
    return _db_conn


def db_run(sql, params=()):
    """Run a query using sqlite-style ? placeholders. Returns a list of rows."""
    global _db_conn
    # Translate positional ? into pg8000 named params :p0, :p1, ...
    kwargs = {}
    out = []
    idx = 0
    for ch in sql:
        if ch == "?":
            key = f"p{idx}"
            out.append(f":{key}")
            kwargs[key] = params[idx]
            idx += 1
        else:
            out.append(ch)
    final_sql = "".join(out)
    try:
        return _get_conn().run(final_sql, **kwargs) or []
    except Exception:
        _db_conn = None  # force reconnect once on failure
        return _get_conn().run(final_sql, **kwargs) or []


# Create the table if it doesn't exist (Postgres syntax).
db_run("""
CREATE TABLE IF NOT EXISTS scheduled_posts (
    id SERIAL PRIMARY KEY,
    media_type TEXT,
    file_id TEXT,
    caption TEXT,
    pending_text TEXT,
    buttons TEXT,
    post_time TEXT
)
""")

# Add columns for storing formatting entities (bold + premium emoji) on
# previously-created tables that don't have them yet.
db_run("ALTER TABLE scheduled_posts ADD COLUMN IF NOT EXISTS caption_entities TEXT")
db_run("ALTER TABLE scheduled_posts ADD COLUMN IF NOT EXISTS pending_text_entities TEXT")


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------
MAIN_MENU_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["📢 Create Post"],
        ["🔘 Manage Buttons", "📋 Templates"],
        ["⏰ Schedule Post", "📅 Scheduled Posts"],
        ["👀 Preview", "⚙️ Settings"],
    ],
    resize_keyboard=True,
)



# Explicit display order for the owner's own selection menu. Keeping this
# as an explicit list (rather than dict iteration order) makes the order
# intentional and easy to re-arrange later.
_BUTTON_ORDER = [
    # Hindi / Hinglish
    "free_training_course", "trading_course", "free_signal_chahiye", "paisa_kamana",
    "rs500_shuru", "inr_lakh", "bonus_claim_karo", "aaj_free_gift",
    # VIP / Access
    "vip", "free_vip", "unlock_vip_free", "private_group_access", "vip_earn",
    # Signals
    "signals", "winning_signals", "daily_trades", "free_signals_daily", "accuracy_95",
    # Recovery
    "recover", "recover_losses_today", "still_losing",
    # Free stuff / Bonus
    "free_money", "free_pdf", "unlock_bonus", "new_here_gift", "today_only_free",
    # Beginners
    "beginner_start", "new_trader", "zero_to_profit", "last_chance_free",
    # Social proof
    "join_10k", "no_fake_gurus",
    # Misc originals not otherwise covered above
    "contact", "learn_trading", "giveaway", "subscribe", "create_account",
    # CLICK HERE style, grouped last as requested
    "start", "join", "claim",
    "click_begin", "click_unlock", "click_profit",
    "click_access_vip", "click_get_signals", "click_recover",
]

# Safety check at import time: catch typos/missing keys immediately instead
# of failing silently or at runtime deep inside a handler.
assert set(_BUTTON_ORDER) == set(BUTTON_CONFIG.keys()), (
    "BUTTON_ORDER / BUTTON_CONFIG mismatch! "
    f"In order but not in config: {set(_BUTTON_ORDER) - set(BUTTON_CONFIG.keys())} | "
    f"In config but not in order: {set(BUTTON_CONFIG.keys()) - set(_BUTTON_ORDER)}"
)


def get_selection_keyboard():
    rows = []
    for i in range(0, len(_BUTTON_ORDER), 2):
        pair = _BUTTON_ORDER[i:i + 2]
        rows.append([BUTTON_CONFIG[key]["toggle_label"] for key in pair])

    rows.append(["✏️ Add Caption", "👀 Preview"])
    rows.append(["📤 Post To Channel", "⏰ Schedule Post"])
    rows.append(["📅 Scheduled Posts", "❌ Cancel"])

    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


# ---------------------------------------------------------------------------
# Start command
# ---------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Welcome to Thunder Button Bot!",
        reply_markup=MAIN_MENU_KEYBOARD,
    )


# ---------------------------------------------------------------------------
# Main message handler
# ---------------------------------------------------------------------------
async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    # Security Check
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text(
            "⛔ You are not authorized to use this bot."
        )
        return

    text = update.message.text or ""

    # Cancel
    if text == "❌ Cancel":
        context.user_data.clear()

        await update.message.reply_text(
            "❌ Post creation cancelled.",
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return

    # Add Caption
    if text == "✏️ Add Caption":

        if not context.user_data.get("media_type"):
            await update.message.reply_text(
                "❌ No media found."
            )
            return

        context.user_data["waiting_for_caption"] = True

        await update.message.reply_text(
            "✏️ Please send the new caption."
        )
        return

    # Save Caption
    if context.user_data.get("waiting_for_caption"):

        # Save plain text + original entities (preserves premium emojis)
        context.user_data["caption"] = text
        context.user_data["caption_entities"] = list(update.message.entities or [])
        context.user_data["waiting_for_caption"] = False

        await update.message.reply_text(
            "✅ Caption updated successfully.",
            reply_markup=get_selection_keyboard(),
        )
        return

    # (Scheduling by typing has been replaced by the tap-based date/time
    #  picker — see schedule_callback below. Nothing to handle here anymore.)

    # Create Post
    if text == "📢 Create Post":
        # Fully reset any leftover state from a previous post (media,
        # caption, selected buttons, cancelled-schedule leftovers, etc.)
        # so a new post always starts with a clean slate.
        context.user_data.clear()
        context.user_data["creating_post"] = True

        await update.message.reply_text(
            "📝 Please send the media you want to post."
        )
        return

    # Circular Video
    if update.message.video_note and context.user_data.get("creating_post"):

        context.user_data["media_type"] = "video_note"
        context.user_data["pending_media"] = update.message.video_note.file_id
        context.user_data["creating_post"] = False

        if "selected_buttons" not in context.user_data:
            context.user_data["selected_buttons"] = []

        await update.message.reply_text(
            "✅ Circular video received!\n\n"
            "Now select the buttons you want to add.",
            reply_markup=get_selection_keyboard(),
        )
        return

    # Normal Video
    if update.message.video and context.user_data.get("creating_post"):

        caption = update.message.caption or ""
        caption_entities = list(update.message.caption_entities or [])

        context.user_data["media_type"] = "video"
        context.user_data["pending_media"] = update.message.video.file_id
        context.user_data["caption"] = caption
        context.user_data["caption_entities"] = caption_entities
        context.user_data["creating_post"] = False

        if "selected_buttons" not in context.user_data:
            context.user_data["selected_buttons"] = []

        await update.message.reply_text(
            "✅ Video received!\n\n"
            "Now select the buttons you want to add.",
            reply_markup=get_selection_keyboard(),
        )
        return

    # Photo
    if update.message.photo and context.user_data.get("creating_post"):

        caption = update.message.caption or ""
        caption_entities = list(update.message.caption_entities or [])

        context.user_data["media_type"] = "photo"
        context.user_data["pending_media"] = update.message.photo[-1].file_id
        context.user_data["caption"] = caption
        context.user_data["caption_entities"] = caption_entities
        context.user_data["creating_post"] = False

        if "selected_buttons" not in context.user_data:
            context.user_data["selected_buttons"] = []

        await update.message.reply_text(
            "✅ Photo received!\n\n"
            "Now select the buttons you want to add.",
            reply_markup=get_selection_keyboard(),
        )
        return

    # Voice Message
    if update.message.voice and context.user_data.get("creating_post"):

        caption = update.message.caption or ""
        caption_entities = list(update.message.caption_entities or [])

        context.user_data["media_type"] = "voice"
        context.user_data["pending_media"] = update.message.voice.file_id
        context.user_data["caption"] = caption
        context.user_data["caption_entities"] = caption_entities
        context.user_data["creating_post"] = False

        if "selected_buttons" not in context.user_data:
            context.user_data["selected_buttons"] = []

        await update.message.reply_text(
            "✅ Voice message received!\n\n"
            "You can add a caption with ✏️ Add Caption, then select the "
            "buttons you want to add.",
            reply_markup=get_selection_keyboard(),
        )
        return

    # Text Only
    if text and context.user_data.get("creating_post"):

        context.user_data["media_type"] = "text"
        context.user_data["pending_text"] = text
        context.user_data["pending_text_entities"] = list(update.message.entities or [])
        context.user_data["creating_post"] = False

        if "selected_buttons" not in context.user_data:
            context.user_data["selected_buttons"] = []

        await update.message.reply_text(
            "✅ Message received!\n\n"
            "Now select the buttons you want to add.",
            reply_markup=get_selection_keyboard(),
        )
        return

    # ------------------------------------------------------------------
    # Toggle Buttons
    # ------------------------------------------------------------------
    selected = context.user_data.get("selected_buttons", [])

    toggle_messages = {
        cfg["toggle_label"]: (key.replace("_", " ").title(), cfg["post_label"])
        for key, cfg in BUTTON_CONFIG.items()
    }

    if text in toggle_messages:
        name, label = toggle_messages[text]

        if label in selected:
            selected.remove(label)
            await update.message.reply_text(
                f"❌ {name} button removed",
                reply_markup=get_selection_keyboard(),
            )
        else:
            selected.append(label)
            await update.message.reply_text(
                f"✅ {name} button added",
                reply_markup=get_selection_keyboard(),
            )

        context.user_data["selected_buttons"] = selected
        return

    # Schedule Post
    if text == "⏰ Schedule Post":

        media_type = context.user_data.get("media_type")

        if not media_type:
            await update.message.reply_text(
                "❌ No media found to schedule."
            )
            return

        # Show a preview of the post first, then ask to confirm.
        await update.message.reply_text(
            "👀 Here's a preview of the post you're about to schedule:"
        )
        await send_post_preview(update.message, context)
        await update.message.reply_text(
            "Do you want to schedule this post?",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Confirm", callback_data="sched_confirm"),
                    InlineKeyboardButton("❌ Cancel", callback_data="sched_cancel"),
                ],
            ]),
        )
        return

    # Post To Channel
    if text == "📤 Post To Channel":

        media_type = context.user_data.get("media_type")
        file_id = context.user_data.get("pending_media")
        caption = context.user_data.get("caption", "")
        caption_entities = context.user_data.get("caption_entities", None)
        pending_text = context.user_data.get("pending_text", "")

        if not media_type:
            await update.message.reply_text(
                "❌ No media found to post."
            )
            return

        selected = context.user_data.get("selected_buttons", [])
        reply_markup = build_inline_keyboard(selected, use_icons=True)
        fallback_markup = build_inline_keyboard(selected, use_icons=False)

        if media_type == "video_note":
            await safe_send(
                lambda e, m: context.bot.send_video_note(
                    chat_id=CHANNEL_ID,
                    video_note=file_id,
                    reply_markup=m,
                ),
                None, reply_markup, fallback_markup,
            )

        elif media_type == "video":
            ents = with_bold(caption, caption_entities)
            await safe_send(
                lambda e, m: context.bot.send_video(
                    chat_id=CHANNEL_ID,
                    video=file_id,
                    caption=caption if caption else None,
                    caption_entities=e,
                    parse_mode=None,
                    reply_markup=m,
                ),
                ents, reply_markup, fallback_markup,
            )

        elif media_type == "photo":
            ents = with_bold(caption, caption_entities)
            await safe_send(
                lambda e, m: context.bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=file_id,
                    caption=caption if caption else None,
                    caption_entities=e,
                    parse_mode=None,
                    reply_markup=m,
                ),
                ents, reply_markup, fallback_markup,
            )

        elif media_type == "voice":
            ents = with_bold(caption, caption_entities)
            await safe_send(
                lambda e, m: context.bot.send_voice(
                    chat_id=CHANNEL_ID,
                    voice=file_id,
                    caption=caption if caption else None,
                    caption_entities=e,
                    parse_mode=None,
                    reply_markup=m,
                ),
                ents, reply_markup, fallback_markup,
            )

        elif media_type == "text":
            pending_text_entities = context.user_data.get("pending_text_entities") or None
            ents = with_bold(pending_text, pending_text_entities)
            await safe_send(
                lambda e, m: context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=pending_text,
                    entities=e,
                    parse_mode=None,
                    reply_markup=m,
                ),
                ents, reply_markup, fallback_markup,
            )

        context.user_data.clear()

        await update.message.reply_text(
            "✅ Successfully posted to channel!",
            reply_markup=MAIN_MENU_KEYBOARD,
        )

        return

    # Manage Buttons
    if "Manage Buttons" in text:
        await update.message.reply_text(
            "1️⃣ VIP Join\n"
            "2️⃣ Free Signals\n"
            "3️⃣ Contact Thunder\n"
            "4️⃣ VIP Direct Join"
        )
        return

    # Scheduled Posts - list what's pending (each with a delete button)
    if text == "📅 Scheduled Posts":
        body, markup = build_scheduled_list()
        await update.message.reply_text(body, reply_markup=markup)
        return

    # Preview
    if text.upper() in ["PREVIEW", "👀 PREVIEW"]:

        media_type = context.user_data.get("media_type")
        file_id = context.user_data.get("pending_media")
        caption = context.user_data.get("caption", "")
        caption_entities = context.user_data.get("caption_entities", None)
        pending_text = context.user_data.get("pending_text", "")

        if not media_type:
            await update.message.reply_text(
                "❌ No media found."
            )
            return

        selected = context.user_data.get("selected_buttons", [])
        reply_markup = build_inline_keyboard(selected, use_icons=True)
        fallback_markup = build_inline_keyboard(selected, use_icons=False)

        if media_type == "video_note":
            await safe_send(
                lambda e, m: update.message.reply_video_note(
                    video_note=file_id,
                    reply_markup=m,
                ),
                None, reply_markup, fallback_markup,
            )

        elif media_type == "video":
            ents = with_bold(caption, caption_entities)
            await safe_send(
                lambda e, m: update.message.reply_video(
                    video=file_id,
                    caption=caption if caption else None,
                    caption_entities=e,
                    parse_mode=None,
                    reply_markup=m,
                ),
                ents, reply_markup, fallback_markup,
            )

        elif media_type == "photo":
            ents = with_bold(caption, caption_entities)
            await safe_send(
                lambda e, m: update.message.reply_photo(
                    photo=file_id,
                    caption=caption if caption else None,
                    caption_entities=e,
                    parse_mode=None,
                    reply_markup=m,
                ),
                ents, reply_markup, fallback_markup,
            )

        elif media_type == "voice":
            ents = with_bold(caption, caption_entities)
            await safe_send(
                lambda e, m: update.message.reply_voice(
                    voice=file_id,
                    caption=caption if caption else None,
                    caption_entities=e,
                    parse_mode=None,
                    reply_markup=m,
                ),
                ents, reply_markup, fallback_markup,
            )

        elif media_type == "text":
            pending_text_entities = context.user_data.get("pending_text_entities") or None
            ents = with_bold(pending_text, pending_text_entities)
            await safe_send(
                lambda e, m: update.message.reply_text(
                    text=pending_text,
                    entities=e,
                    parse_mode=None,
                    reply_markup=m,
                ),
                ents, reply_markup, fallback_markup,
            )

        return


async def send_post_preview(message, context):
    """Send a preview of the currently-built post to the user's chat. Returns True if sent."""
    media_type = context.user_data.get("media_type")
    if not media_type:
        return False

    caption = context.user_data.get("caption", "")
    caption_entities = context.user_data.get("caption_entities", None)
    pending_text = context.user_data.get("pending_text", "")
    file_id = context.user_data.get("pending_media")
    selected = context.user_data.get("selected_buttons", [])
    reply_markup = build_inline_keyboard(selected, use_icons=True)
    fallback_markup = build_inline_keyboard(selected, use_icons=False)

    if media_type == "video_note":
        await safe_send(
            lambda e, m: message.reply_video_note(video_note=file_id, reply_markup=m),
            None, reply_markup, fallback_markup,
        )
    elif media_type == "video":
        ents = with_bold(caption, caption_entities)
        await safe_send(
            lambda e, m: message.reply_video(
                video=file_id, caption=caption if caption else None,
                caption_entities=e, parse_mode=None, reply_markup=m,
            ),
            ents, reply_markup, fallback_markup,
        )
    elif media_type == "photo":
        ents = with_bold(caption, caption_entities)
        await safe_send(
            lambda e, m: message.reply_photo(
                photo=file_id, caption=caption if caption else None,
                caption_entities=e, parse_mode=None, reply_markup=m,
            ),
            ents, reply_markup, fallback_markup,
        )
    elif media_type == "voice":
        ents = with_bold(caption, caption_entities)
        await safe_send(
            lambda e, m: message.reply_voice(
                voice=file_id, caption=caption if caption else None,
                caption_entities=e, parse_mode=None, reply_markup=m,
            ),
            ents, reply_markup, fallback_markup,
        )
    elif media_type == "text":
        pending_text_entities = context.user_data.get("pending_text_entities") or None
        ents = with_bold(pending_text, pending_text_entities)
        await safe_send(
            lambda e, m: message.reply_text(
                text=pending_text,
                entities=e,
                parse_mode=None,
                reply_markup=m,
            ),
            ents, reply_markup, fallback_markup,
        )
    return True


def build_scheduled_list():
    """Return (text, inline_markup) listing scheduled posts, each with a delete button."""
    rows = db_run(
        "SELECT id, media_type, post_time FROM scheduled_posts ORDER BY post_time"
    )
    if not rows:
        return "📅 No posts are currently scheduled.", None

    lines = ["📅 Scheduled posts (your local time):\n"]
    kb = []
    for post_id, media_type, post_time_utc in rows:
        utc_dt = datetime.strptime(post_time_utc, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        local_dt = utc_dt.astimezone(LOCAL_TZ)
        when = local_dt.strftime("%d-%m-%Y %H:%M")
        lines.append(f"#{post_id} • {media_type} • {when}")
        kb.append([
            InlineKeyboardButton(
                f"👀 View #{post_id}",
                callback_data=f"viewpost:{post_id}",
            ),
        ])
        kb.append([
            InlineKeyboardButton(
                f"🔄 Change #{post_id}",
                callback_data=f"changepost:{post_id}",
            ),
            InlineKeyboardButton(
                f"🗑 Delete #{post_id}",
                callback_data=f"delpost:{post_id}",
            ),
        ])
    return "\n".join(lines), InlineKeyboardMarkup(kb)


async def view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the real content of one scheduled post so the user can check it, with a delete button."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if not data.startswith("viewpost:"):
        return

    post_id = data.split(":", 1)[1]
    rows = db_run(
        "SELECT media_type, file_id, caption, pending_text, buttons, post_time, "
        "caption_entities, pending_text_entities "
        "FROM scheduled_posts WHERE id=?",
        (int(post_id),),
    )
    if not rows:
        await query.answer("That post no longer exists.", show_alert=True)
        return

    (
        media_type, file_id, caption, pending_text, buttons_str, post_time_utc,
        caption_entities_json, pending_text_entities_json,
    ) = rows[0]
    selected = buttons_str.split(",") if buttons_str else []
    reply_markup = build_inline_keyboard(selected, use_icons=True)
    fallback_markup = build_inline_keyboard(selected, use_icons=False)
    caption_entities = entities_from_json(caption_entities_json)
    pending_text_entities = entities_from_json(pending_text_entities_json)

    utc_dt = datetime.strptime(post_time_utc, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    local_dt = utc_dt.astimezone(LOCAL_TZ)
    when = local_dt.strftime("%d-%m-%Y %H:%M")
    chat_id = query.message.chat_id

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"👀 Preview of scheduled post #{post_id}\n📅 {when} (your local time):",
    )

    # Send the actual content exactly as it will be posted
    if media_type == "video_note":
        await safe_send(
            lambda e, m: context.bot.send_video_note(
                chat_id=chat_id, video_note=file_id, reply_markup=m
            ),
            None, reply_markup, fallback_markup,
        )
    elif media_type == "video":
        ents = with_bold(caption, caption_entities)
        await safe_send(
            lambda e, m: context.bot.send_video(
                chat_id=chat_id, video=file_id, caption=caption or None,
                caption_entities=e, parse_mode=None, reply_markup=m,
            ),
            ents, reply_markup, fallback_markup,
        )
    elif media_type == "photo":
        ents = with_bold(caption, caption_entities)
        await safe_send(
            lambda e, m: context.bot.send_photo(
                chat_id=chat_id, photo=file_id, caption=caption or None,
                caption_entities=e, parse_mode=None, reply_markup=m,
            ),
            ents, reply_markup, fallback_markup,
        )
    elif media_type == "voice":
        ents = with_bold(caption, caption_entities)
        await safe_send(
            lambda e, m: context.bot.send_voice(
                chat_id=chat_id, voice=file_id, caption=caption or None,
                caption_entities=e, parse_mode=None, reply_markup=m,
            ),
            ents, reply_markup, fallback_markup,
        )
    elif media_type == "text":
        ents = with_bold(pending_text, pending_text_entities)
        await safe_send(
            lambda e, m: context.bot.send_message(
                chat_id=chat_id, text=pending_text,
                entities=e, parse_mode=None, reply_markup=m,
            ),
            ents, reply_markup, fallback_markup,
        )

    # Offer to change or delete this specific post
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Want to make changes to this post?",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 Change", callback_data=f"changepost:{post_id}"),
            InlineKeyboardButton(f"🗑 Delete #{post_id}", callback_data=f"delpost:{post_id}"),
        ]]),
    )


async def change_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows a small menu (Reschedule / Delete) for one scheduled post when
    its 🔄 Change button is tapped."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if not data.startswith("changepost:"):
        return

    post_id = data.split(":", 1)[1]
    rows = db_run("SELECT id FROM scheduled_posts WHERE id=?", (int(post_id),))
    if not rows:
        await query.answer("That post no longer exists.", show_alert=True)
        return

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"🔄 What do you want to do with post #{post_id}?",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📅 Reschedule", callback_data=f"reschedule:{post_id}"),
            InlineKeyboardButton("🗑 Delete", callback_data=f"delpost:{post_id}"),
        ]]),
    )


async def reschedule_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the date/hour/minute picker for an EXISTING post, so tapping
    through it updates that post's time instead of creating a new post."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if not data.startswith("reschedule:"):
        return

    post_id = data.split(":", 1)[1]
    rows = db_run("SELECT id FROM scheduled_posts WHERE id=?", (int(post_id),))
    if not rows:
        await query.answer("That post no longer exists.", show_alert=True)
        return

    # Mark that the upcoming date/hour/minute taps are for RESCHEDULING
    # this existing post, not building a brand new one.
    context.user_data["rescheduling_post_id"] = int(post_id)

    await query.edit_message_text(
        f"📅 Pick a NEW date for post #{post_id}:",
        reply_markup=build_date_keyboard(),
    )


async def delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deletes one scheduled post when its 🗑 button is tapped, then refreshes the list."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("delpost:"):
        post_id = data.split(":", 1)[1]
        try:
            db_run("DELETE FROM scheduled_posts WHERE id=?", (int(post_id),))
            logger.info("Deleted scheduled post #%s by user request.", post_id)
        except Exception:
            logger.exception("Failed to delete scheduled post #%s", post_id)
            await query.answer("Could not delete that post.", show_alert=True)
            return

        body, markup = build_scheduled_list()
        try:
            await query.edit_message_text(
                f"🗑 Deleted post #{post_id}.\n\n{body}",
                reply_markup=markup,
            )
        except Exception:
            # If the message can't be edited (e.g. unchanged), ignore quietly.
            pass
        return


# ---------------------------------------------------------------------------
# Tap-based date/time picker (replaces typing DD-MM-YYYY HH:MM)
# ---------------------------------------------------------------------------
def build_date_keyboard():
    """Inline keyboard of the next 8 days (today + 7)."""
    now_local = datetime.now(LOCAL_TZ)
    rows, row = [], []
    for i in range(8):
        d = now_local + timedelta(days=i)
        if i == 0:
            label = f"Today {d.strftime('%d %b')}"
        elif i == 1:
            label = f"Tomorrow {d.strftime('%d %b')}"
        else:
            label = d.strftime("%a %d %b")
        row.append(
            InlineKeyboardButton(label, callback_data=f"sched_date:{d.strftime('%Y-%m-%d')}")
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def build_hour_keyboard():
    """Inline keyboard of hours 00-23 (24h), 6 per row."""
    rows, row = [], []
    for h in range(24):
        row.append(InlineKeyboardButton(f"{h:02d}", callback_data=f"sched_hour:{h:02d}"))
        if len(row) == 6:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("« Back to date", callback_data="sched_back_date")])
    return InlineKeyboardMarkup(rows)


def build_minute_keyboard():
    """Inline keyboard of minutes in 5-minute steps, 4 per row."""
    rows, row = [], []
    for m in range(0, 60, 5):
        row.append(InlineKeyboardButton(f"{m:02d}", callback_data=f"sched_min:{m:02d}"))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("« Back to hour", callback_data="sched_back_hour")])
    return InlineKeyboardMarkup(rows)


def save_scheduled_post(context, utc_time):
    """Insert the currently-built post into the DB. Returns True on success."""
    media_type = context.user_data.get("media_type")
    if not media_type:
        return False
    selected = context.user_data.get("selected_buttons", [])
    db_run(
        """
        INSERT INTO scheduled_posts (
            media_type, file_id, caption, pending_text, buttons, post_time,
            caption_entities, pending_text_entities
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            media_type,
            context.user_data.get("pending_media"),
            context.user_data.get("caption", ""),
            context.user_data.get("pending_text", ""),
            ",".join(selected),
            utc_time.strftime("%Y-%m-%d %H:%M:%S"),
            entities_to_json(context.user_data.get("caption_entities")),
            entities_to_json(context.user_data.get("pending_text_entities")),
        ),
    )
    return True


async def schedule_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles every tap in the date -> hour -> minute picker."""
    query = update.callback_query
    await query.answer()
    data = query.data

    # Confirm preview -> start the date picker
    if data == "sched_confirm":
        # Safety net: make sure we're not accidentally in a leftover
        # "reschedule an existing post" session from earlier.
        context.user_data.pop("rescheduling_post_id", None)
        await query.edit_message_text(
            "📅 Choose a date to schedule your post:",
            reply_markup=build_date_keyboard(),
        )
        return

    # Cancel -> abort scheduling, keep the built post, return to menu
    if data == "sched_cancel":
        await query.edit_message_text("❌ Scheduling cancelled.")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Back to menu 👇",
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return

    # Step 1: a date was picked -> ask for the hour
    if data.startswith("sched_date:"):
        context.user_data["sched_date"] = data.split(":", 1)[1]
        await query.edit_message_text(
            f"📅 Date: {context.user_data['sched_date']}\n\n⏰ Now choose the HOUR (24-hour):",
            reply_markup=build_hour_keyboard(),
        )
        return

    if data == "sched_back_date":
        await query.edit_message_text(
            "📅 Choose a date to schedule your post:",
            reply_markup=build_date_keyboard(),
        )
        return

    # Step 2: an hour was picked -> ask for the minute
    if data.startswith("sched_hour:"):
        context.user_data["sched_hour"] = data.split(":", 1)[1]
        await query.edit_message_text(
            f"📅 {context.user_data.get('sched_date')}   ⏰ {context.user_data['sched_hour']}:__\n\n"
            "Now choose the MINUTE:",
            reply_markup=build_minute_keyboard(),
        )
        return

    if data == "sched_back_hour":
        await query.edit_message_text(
            f"📅 Date: {context.user_data.get('sched_date')}\n\n⏰ Choose the HOUR (24-hour):",
            reply_markup=build_hour_keyboard(),
        )
        return

    # Step 3: a minute was picked -> finalise and save
    if data.startswith("sched_min:"):
        minute = data.split(":", 1)[1]
        date_str = context.user_data.get("sched_date")
        hour = context.user_data.get("sched_hour")

        if not date_str or hour is None:
            await query.edit_message_text(
                "❌ Something went wrong. Please tap ⏰ Schedule Post again."
            )
            return

        try:
            naive = datetime.strptime(f"{date_str} {hour}:{minute}", "%Y-%m-%d %H:%M")
        except ValueError:
            await query.edit_message_text("❌ Invalid time. Please try again.")
            return

        local_time = naive.replace(tzinfo=LOCAL_TZ)
        now_local = datetime.now(LOCAL_TZ)

        if local_time <= now_local:
            await query.edit_message_text(
                "❌ That time is in the past. Please pick a future date/time:",
                reply_markup=build_date_keyboard(),
            )
            return

        utc_time = local_time.astimezone(UTC)

        rescheduling_post_id = context.user_data.get("rescheduling_post_id")

        if rescheduling_post_id is not None:
            # Reschedule flow: update the existing post's time only.
            db_run(
                "UPDATE scheduled_posts SET post_time=? WHERE id=?",
                (utc_time.strftime("%Y-%m-%d %H:%M:%S"), rescheduling_post_id),
            )
            logger.info(
                "Rescheduled post #%s to %s (local) / %s (UTC)",
                rescheduling_post_id,
                local_time.strftime("%d-%m-%Y %H:%M"),
                utc_time.strftime("%Y-%m-%d %H:%M:%S"),
            )

            context.user_data.pop("rescheduling_post_id", None)
            context.user_data.pop("sched_date", None)
            context.user_data.pop("sched_hour", None)

            await query.edit_message_text(
                f"✅ Post #{rescheduling_post_id} rescheduled!\n\n"
                f"📅 {local_time.strftime('%d-%m-%Y')}\n"
                f"⏰ {local_time.strftime('%H:%M')} (your local time)"
            )
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Back to menu 👇",
                reply_markup=MAIN_MENU_KEYBOARD,
            )
            return

        if not save_scheduled_post(context, utc_time):
            await query.edit_message_text(
                "❌ No media found to schedule. Please create the post again."
            )
            return

        logger.info(
            "Scheduled new post for %s (local) / %s (UTC)",
            local_time.strftime("%d-%m-%Y %H:%M"),
            utc_time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        # Clear the picker + post-building state
        context.user_data.clear()

        await query.edit_message_text(
            "✅ Post scheduled successfully!\n\n"
            f"📅 {local_time.strftime('%d-%m-%Y')}\n"
            f"⏰ {local_time.strftime('%H:%M')} (your local time)"
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Back to menu 👇",
            reply_markup=MAIN_MENU_KEYBOARD,
        )
        return


# ---------------------------------------------------------------------------
# Scheduler worker
# ---------------------------------------------------------------------------
async def scheduled_post_worker(application):

    logger.info("Scheduler worker loop started.")

    while True:

        try:
            now_utc = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

            posts = db_run(
                """
                SELECT id, media_type, file_id, caption, pending_text, buttons, post_time,
                       caption_entities, pending_text_entities
                FROM scheduled_posts
                WHERE post_time <= ?
                ORDER BY id
                """,
                (now_utc,),
            )

            if posts:
                logger.info("Found %d scheduled post(s) due at %s UTC", len(posts), now_utc)

            for post in posts:

                (
                    post_id,
                    media_type,
                    file_id,
                    caption,
                    pending_text,
                    buttons_str,
                    post_time,
                    caption_entities_json,
                    pending_text_entities_json,
                ) = post

                selected = (
                    buttons_str.split(",") if buttons_str else []
                )

                reply_markup = build_inline_keyboard(selected, use_icons=True)
                fallback_markup = build_inline_keyboard(selected, use_icons=False)
                caption_entities = entities_from_json(caption_entities_json)
                pending_text_entities = entities_from_json(pending_text_entities_json)

                try:

                    if media_type == "video_note":
                        await safe_send(
                            lambda e, m: application.bot.send_video_note(
                                chat_id=CHANNEL_ID,
                                video_note=file_id,
                                reply_markup=m,
                            ),
                            None, reply_markup, fallback_markup,
                        )

                    elif media_type == "video":
                        ents = with_bold(caption, caption_entities)
                        await safe_send(
                            lambda e, m: application.bot.send_video(
                                chat_id=CHANNEL_ID,
                                video=file_id,
                                caption=caption,
                                caption_entities=e,
                                parse_mode=None,
                                reply_markup=m,
                            ),
                            ents, reply_markup, fallback_markup,
                        )

                    elif media_type == "photo":
                        ents = with_bold(caption, caption_entities)
                        await safe_send(
                            lambda e, m: application.bot.send_photo(
                                chat_id=CHANNEL_ID,
                                photo=file_id,
                                caption=caption,
                                caption_entities=e,
                                parse_mode=None,
                                reply_markup=m,
                            ),
                            ents, reply_markup, fallback_markup,
                        )

                    elif media_type == "voice":
                        ents = with_bold(caption, caption_entities)
                        await safe_send(
                            lambda e, m: application.bot.send_voice(
                                chat_id=CHANNEL_ID,
                                voice=file_id,
                                caption=caption,
                                caption_entities=e,
                                parse_mode=None,
                                reply_markup=m,
                            ),
                            ents, reply_markup, fallback_markup,
                        )

                    elif media_type == "text":
                        ents = with_bold(pending_text, pending_text_entities)
                        await safe_send(
                            lambda e, m: application.bot.send_message(
                                chat_id=CHANNEL_ID,
                                text=pending_text,
                                entities=e,
                                parse_mode=None,
                                reply_markup=m,
                            ),
                            ents, reply_markup, fallback_markup,
                        )

                    db_run(
                        "DELETE FROM scheduled_posts WHERE id=?",
                        (post_id,),
                    )

                    logger.info("Scheduled post %s posted successfully.", post_id)

                except Exception:
                    logger.exception("Error posting scheduled post %s", post_id)

        except Exception:
            # Catch-all so the loop NEVER dies silently. If something goes
            # wrong, it's logged and the loop tries again on the next tick.
            logger.exception("Error in scheduler worker loop")

        await asyncio.sleep(30)


async def scheduler_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug command: /schedulerstatus
    Shows the bot's current view of time (UTC and local) plus every
    scheduled post still pending - useful to confirm the scheduler is
    alive and to sanity-check that times were stored correctly."""

    if update.effective_user.id != OWNER_ID:
        return

    now_utc = datetime.now(UTC)
    now_local = now_utc.astimezone(LOCAL_TZ)

    rows = db_run(
        "SELECT id, media_type, post_time FROM scheduled_posts ORDER BY post_time"
    )

    lines = [
        "🟢 Scheduler is running.",
        f"UTC now: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Local now ({LOCAL_TZ.key}): {now_local.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    if not rows:
        lines.append("No posts currently pending.")
    else:
        lines.append("Pending posts:")
        for post_id, media_type, post_time_utc in rows:
            utc_dt = datetime.strptime(post_time_utc, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
            local_dt = utc_dt.astimezone(LOCAL_TZ)
            due = "DUE NOW" if utc_dt <= now_utc else "upcoming"
            lines.append(
                f"#{post_id} • {media_type} • {local_dt.strftime('%d-%m-%Y %H:%M')} local "
                f"({utc_dt.strftime('%Y-%m-%d %H:%M:%S')} UTC) • {due}"
            )

    await update.message.reply_text("\n".join(lines))


async def post_init(application):
    asyncio.create_task(scheduled_post_worker(application))
    logger.info("Scheduler Worker Started...")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set!")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Commands
    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        CommandHandler(
            "schedulerstatus",
            scheduler_status,
        )
    )

    # Date/time picker taps (callback buttons starting with "sched_")
    app.add_handler(
        CallbackQueryHandler(schedule_callback, pattern="^sched_")
    )

    # View a scheduled post's real content (callback "viewpost:")
    app.add_handler(
        CallbackQueryHandler(view_callback, pattern="^viewpost:")
    )

    # Delete-scheduled-post taps (callback buttons starting with "delpost:")
    app.add_handler(
        CallbackQueryHandler(delete_callback, pattern="^delpost:")
    )

    # Change menu (Reschedule / Delete) for a scheduled post
    app.add_handler(
        CallbackQueryHandler(change_callback, pattern="^changepost:")
    )

    # Reschedule taps (callback buttons starting with "reschedule:")
    app.add_handler(
        CallbackQueryHandler(reschedule_callback, pattern="^reschedule:")
    )

    # Messages
    app.add_handler(
        MessageHandler(
            (
                filters.TEXT
                | filters.PHOTO
                | filters.VIDEO
                | filters.VIDEO_NOTE
                | filters.VOICE
            )
            & ~filters.COMMAND,
            handle_message,
        )
    )

    logger.info("Thunder Button Bot Started...")

    app.run_polling()


if __name__ == "__main__":
    main()
