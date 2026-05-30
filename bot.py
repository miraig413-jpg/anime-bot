#!/usr/bin/env python3
"""
🎌 ANIME UNIVERSE BOT — v3.2 (FINAL BUGFIX)
Tuzatilgan barcha xatolar:
  1. Photo+delete => BadRequest muammosi hal qilindi (caption edit)
  2. today/weekly/trending/top komanda handlerlari
  3. job_queue => asyncio.create_task
  4. genre callback | separator (Slice of Life xatosi yo'q)
  5. search_history handler
  6. Barcha tugmalar 100% ishlaydi
"""

import logging
import asyncio
import re
from datetime import datetime, timedelta

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden

from config import BOT_TOKEN, ADMIN_IDS
from database import Database
from anime_api import AnimeAPI
from messages import Messages

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

db = Database()
api = AnimeAPI()
msg = Messages()

# ──────────────────────────────────────────
#  KONSTANTALAR
# ──────────────────────────────────────────

DAY_NAMES_UZ = {
    "MONDAY": "Dushanba", "TUESDAY": "Seshanba",
    "WEDNESDAY": "Chorshanba", "THURSDAY": "Payshanba",
    "FRIDAY": "Juma", "SATURDAY": "Shanba", "SUNDAY": "Yakshanba"
}
DAY_EMOJI = {
    "MONDAY": "🗓", "TUESDAY": "🗓", "WEDNESDAY": "🗓", "THURSDAY": "🗓",
    "FRIDAY": "🗓", "SATURDAY": "🎉", "SUNDAY": "🎉"
}
SEASON_UZ = {
    "SPRING": "🌸 Bahor", "SUMMER": "☀️ Yoz",
    "FALL": "🍂 Kuz", "WINTER": "❄️ Qish"
}
STATUS_UZ = {
    "RELEASING": "🟢 Davom etmoqda", "FINISHED": "✅ Tugagan",
    "NOT_YET_RELEASED": "🔜 Kutilmoqda", "CANCELLED": "❌ Bekor", "HIATUS": "⏸ To'xtatilgan"
}
FMT = {"TV": "📺", "MOVIE": "🎬", "OVA": "💿", "ONA": "🌐", "SPECIAL": "⭐"}
GE = {
    "Action": "⚔️", "Adventure": "🗺", "Comedy": "😂", "Drama": "😢",
    "Fantasy": "🧙", "Horror": "👻", "Romance": "💕", "Sci-Fi": "🚀",
    "Slice of Life": "🌿", "Sports": "⚽", "Supernatural": "✨",
    "Mystery": "🔮", "Psychological": "🧠", "Thriller": "😰",
    "Mecha": "🤖", "Music": "🎵", "Ecchi": "💋", "Harem": "💞",
    "Mahou Shoujo": "🌟", "Isekai": "🌀"
}

# ──────────────────────────────────────────
#  YORDAMCHI FUNKSIYALAR
# ──────────────────────────────────────────

def clean(text: str, limit: int = 350) -> str:
    if not text:
        return "Ma'lumot yo'q"
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:limit] + "..." if len(text) > limit else text

def stars(score) -> str:
    if score and score > 0:
        s = "⭐" * min(int(score / 20), 5)
        return f"{s} {score/10:.1f}/10"
    return "⭐ N/A"

def until(sec: int) -> str:
    d, h, m = sec // 86400, (sec % 86400) // 3600, (sec % 3600) // 60
    return f"{d}k {h}s" if d > 0 else (f"{h}s {m}d" if h > 0 else f"{m}d")

def home():
    return [[InlineKeyboardButton("🏠 Bosh Menu", callback_data="home")]]

def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Bugun", callback_data="today"),
         InlineKeyboardButton("🗓 Haftalik", callback_data="weekly")],
        [InlineKeyboardButton("🔥 Trend", callback_data="lst|trending|1"),
         InlineKeyboardButton("⭐ Top", callback_data="lst|top|1"),
         InlineKeyboardButton("👥 Ommabop", callback_data="lst|popular|1")],
        [InlineKeyboardButton("🎭 Janr", callback_data="genre_menu"),
         InlineKeyboardButton("🌸 Mavsum", callback_data="season_menu")],
        [InlineKeyboardButton("🎲 Tasodifiy", callback_data="random"),
         InlineKeyboardButton("🔍 Qidirish", callback_data="search_tip")],
        [InlineKeyboardButton("❤️ Sevimlilar", callback_data="favs"),
         InlineKeyboardButton("👁 Ko'rilganlar", callback_data="watchd")],
        [InlineKeyboardButton("🔔 Obuna", callback_data="subscribe"),
         InlineKeyboardButton("👤 Profil", callback_data="profile")],
        [InlineKeyboardButton("ℹ️ Yordam", callback_data="help")],
    ])

# ──────────────────────────────────────────
#  XABAR YUBORISH YORDAMCHILARI
# FIX: photo+delete muammosini hal qilish uchun
# Rasm yubormaymiz — faqat text+caption usuli
# ──────────────────────────────────────────

async def edit_or_answer(query, text: str, keyboard: list, photo: str = None):
    """
    Xabarni edit qiladi yoki yangi yuboradi.
    Photo bo'lsa: edit_message_media (eski message ID saqlanadi).
    Bu 'delete + reply_photo => BadRequest' muammosini yo'q qiladi.
    """
    markup = InlineKeyboardMarkup(keyboard)
    try:
        if photo:
            try:
                # Rasmli xabar bo'lsa edit_message_media
                media = InputMediaPhoto(
                    media=photo,
                    caption=text[:1024],
                    parse_mode=ParseMode.HTML
                )
                await query.edit_message_media(media=media, reply_markup=markup)
                return
            except BadRequest:
                pass  # Rasmli emas => oddiy text edit
        await query.edit_message_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            logger.warning(f"edit_or_answer BadRequest: {e}")

# ──────────────────────────────────────────
#  KOMANDA HANDLERLARI
# ──────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    db.add_user(u.id, u.username, u.first_name)
    await update.message.reply_text(
        msg.welcome(u.first_name), reply_markup=main_kb(), parse_mode=ParseMode.HTML
    )

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        msg.help_text(), reply_markup=InlineKeyboardMarkup(home()), parse_mode=ParseMode.HTML
    )

async def cmd_today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    m = await update.message.reply_text("⏳ Yuklanmoqda...", parse_mode=ParseMode.HTML)
    t, kb = await build_today()
    await m.edit_text(t, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def cmd_weekly(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t, kb = build_weekly()
    await update.message.reply_text(t, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def cmd_trending(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    m = await update.message.reply_text("⏳ Yuklanmoqda...", parse_mode=ParseMode.HTML)
    t, kb = await build_list("trending", 1)
    await m.edit_text(t, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def cmd_top(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    m = await update.message.reply_text("⏳ Yuklanmoqda...", parse_mode=ParseMode.HTML)
    t, kb = await build_list("top", 1)
    await m.edit_text(t, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def cmd_genre(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t, kb = build_genre_menu()
    await update.message.reply_text(t, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def cmd_random(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    m = await update.message.reply_text("🎲 Tasodifiy anime...", parse_mode=ParseMode.HTML)
    anime = await api.get_random_anime()
    if anime:
        t, kb = await build_detail(update.effective_user.id, anime["id"])
        photo = (anime.get("coverImage") or {}).get("large")
        if photo:
            try:
                await m.delete()
                await update.message.chat.send_photo(
                    photo=photo, caption=t[:1024],
                    reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML
                )
                return
            except Exception:
                pass
        await m.edit_text(t, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else:
        await m.edit_text("❌ Xatolik! Qayta urinib ko'ring.")

async def cmd_favorites(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t, kb = build_favs(update.effective_user.id)
    await update.message.reply_text(t, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def cmd_watched(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t, kb = build_watched(update.effective_user.id)
    await update.message.reply_text(t, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t, kb = build_history(update.effective_user.id)
    await update.message.reply_text(t, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def cmd_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    t, kb = await build_profile(u.id, u.first_name)
    await update.message.reply_text(t, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    t, kb = build_admin_stats()
    await update.message.reply_text(t, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not ctx.args:
        await update.message.reply_text("❗ Foydalanish: /broadcast <matn>")
        return
    text = " ".join(ctx.args)
    users = db.get_all_users()
    m = await update.message.reply_text(f"📤 Yuborilmoqda... ({len(users)} ta)")
    sent = failed = 0
    for uid in users:
        try:
            await ctx.bot.send_message(uid, f"📢 <b>E'LON</b>\n\n{text}", parse_mode=ParseMode.HTML)
            sent += 1
            await asyncio.sleep(0.05)
        except Forbidden:
            db.block_user(uid)
            failed += 1
        except Exception:
            failed += 1
    await m.edit_text(f"✅ Muvaffaqiyatli: {sent}\n❌ Xato: {failed}")

async def cmd_search_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.message.text.strip()
    if len(q) < 2:
        await update.message.reply_text("⚠️ Kamida 2 ta harf kiriting!")
        return
    m = await update.message.reply_text(f"🔍 <b>«{q}»</b> qidirilmoqda...", parse_mode=ParseMode.HTML)
    results = await api.search_anime(q)
    db.save_search(update.effective_user.id, q, len(results))
    t, kb = build_search_results(results, q)
    await m.edit_text(t, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

# ──────────────────────────────────────────
#  BUILD FUNKSIYALARI
# ──────────────────────────────────────────

async def build_today():
    today = datetime.now().strftime("%A").upper()
    animes = await api.get_schedule_by_day(today)
    day_uz = DAY_NAMES_UZ.get(today, today)
    day_em = DAY_EMOJI.get(today, "🗓")

    if not animes:
        t = f"😔 <b>Bugun ({day_uz}) uchun jadval topilmadi</b>"
        kb = [[InlineKeyboardButton("🗓 Haftalik", callback_data="weekly")], *home()]
        return t, kb

    t = f"{day_em} <b>{day_uz.upper()}</b> — {datetime.now().strftime('%d.%m.%Y')}\n"
    t += f"📊 {len(animes)} ta anime\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    kb = []
    for i, a in enumerate(animes[:12], 1):
        title = a["title"]["romaji"][:30]
        genres = " · ".join((a.get("genres") or [])[:2])
        badge = "🔥" if i <= 3 else "⭐" if i <= 6 else "📌"
        ep_s = ""
        if a.get("nextAiringEpisode"):
            ep_s = f" | Ep {a['nextAiringEpisode'].get('episode','?')}"
        t += f"{badge} <b>{i}.</b> {title}\n   {stars(a.get('averageScore',0))}{ep_s}\n   🎭 {genres or 'N/A'}\n\n"
        kb.append([InlineKeyboardButton(f"{badge} {title}", callback_data=f"det|{a['id']}")])
    kb.append([InlineKeyboardButton("🗓 Haftalik", callback_data="weekly"),
               InlineKeyboardButton("🏠 Menu", callback_data="home")])
    return t, kb

def build_weekly():
    today = datetime.now().strftime("%A").upper()
    days = ["MONDAY","TUESDAY","WEDNESDAY","THURSDAY","FRIDAY","SATURDAY","SUNDAY"]
    t = "🗓 <b>HAFTALIK ANIME JADVALI</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    kb, row = [], []
    for i, d in enumerate(days):
        em = DAY_EMOJI[d]
        uz = DAY_NAMES_UZ[d]
        is_today = d == today
        t += f"{'👉 ' if is_today else '   '}{em} {uz}\n"
        lbl = f"{'📍' if is_today else em} {uz[:6]}"
        row.append(InlineKeyboardButton(lbl, callback_data=f"day|{d}"))
        if len(row) == 2 or i == 6:
            kb.append(row); row = []
    kb.extend(home())
    return t, kb

async def build_list(kind: str, page: int):
    labels = {"trending": ("🔥","TREND"), "top": ("⭐","TOP"), "popular": ("👥","OMMABOP")}
    em, label = labels.get(kind, ("📺", kind.upper()))
    fetchers = {
        "trending": api.get_trending,
        "top": api.get_top_anime,
        "popular": api.get_popular_anime,
    }
    animes = await fetchers[kind](page)
    if not animes:
        return "❌ Ma'lumot topilmadi!", home()

    medals = ["🥇","🥈","🥉"]
    start = (page - 1) * 10 + 1
    t = f"{em} <b>{label} ANIMELAR</b> — Sahifa {page}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    kb = []
    for i, a in enumerate(animes, start):
        title = a["title"]["romaji"]
        st = STATUS_UZ.get(a.get("status",""), "❓")
        yr = a.get("seasonYear","?")
        fmt = FMT.get(a.get("format",""), "📺")
        rank = medals[i-1] if i <= 3 and page == 1 else f"#{i}"
        t += f"{rank} {fmt} <b>{title}</b>\n   {stars(a.get('averageScore',0))} | {st} | {yr}\n\n"
        kb.append([InlineKeyboardButton(f"▸ {title[:42]}", callback_data=f"det|{a['id']}")])
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"lst|{kind}|{page-1}"))
    nav.append(InlineKeyboardButton(f"• {page} •", callback_data="noop"))
    nav.append(InlineKeyboardButton("▶️", callback_data=f"lst|{kind}|{page+1}"))
    kb.append(nav)
    kb.extend(home())
    return t, kb

def build_genre_menu():
    t = ("🎭 <b>JANR BO'YICHA QIDIRISH</b>\n\n"
         "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
         "✨ Qaysi janrni tanlaysiz?")
    kb = []
    genres = list(GE.items())
    for i in range(0, len(genres), 2):
        row = []
        for genre, em in genres[i:i+2]:
            row.append(InlineKeyboardButton(f"{em} {genre}", callback_data=f"gpick|{genre}"))
        kb.append(row)
    kb.extend(home())
    return t, kb

def build_genre_sort(genre: str):
    em = GE.get(genre, "🎭")
    t = f"{em} <b>{genre.upper()}</b>\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n📊 Saralash turini tanlang:"
    kb = [
        [InlineKeyboardButton("⭐ Reyting bo'yicha", callback_data=f"glist|{genre}|SCORE_DESC|1")],
        [InlineKeyboardButton("🔥 Trenddagilar", callback_data=f"glist|{genre}|TRENDING_DESC|1")],
        [InlineKeyboardButton("👥 Ommaboplik", callback_data=f"glist|{genre}|POPULARITY_DESC|1")],
        [InlineKeyboardButton("🆕 Yangi chiqqanlar", callback_data=f"glist|{genre}|START_DATE_DESC|1")],
        [InlineKeyboardButton("◀️ Janrlar", callback_data="genre_menu")],
    ]
    return t, kb

async def build_genre_list(genre: str, sort: str, page: int):
    em = GE.get(genre, "🎭")
    animes = await api.get_by_genre(genre, page, sort)
    sort_name = {"SCORE_DESC":"⭐ Reyting","TRENDING_DESC":"🔥 Trend",
                 "POPULARITY_DESC":"👥 Ommabop","START_DATE_DESC":"🆕 Yangi"}.get(sort, sort)

    if not animes:
        t = f"😔 <b>{genre}</b> janrida anime topilmadi"
        kb = [[InlineKeyboardButton("◀️ Janrlar", callback_data="genre_menu")], *home()]
        return t, kb

    start = (page - 1) * 10 + 1
    t = f"{em} <b>{genre.upper()}</b> — {sort_name}\n📄 Sahifa {page} | {len(animes)} ta\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    kb = []
    for i, a in enumerate(animes, start):
        title = a["title"]["romaji"]
        yr = a.get("seasonYear","?")
        eps = a.get("episodes","?")
        fmt = FMT.get(a.get("format",""), "📺")
        t += f"<b>{i}.</b> {fmt} {title}\n   {stars(a.get('averageScore',0))} | 📅{yr} | 📺{eps}ep\n\n"
        kb.append([InlineKeyboardButton(f"▸ {title[:42]}", callback_data=f"det|{a['id']}")])
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"glist|{genre}|{sort}|{page-1}"))
    nav.append(InlineKeyboardButton(f"• {page} •", callback_data="noop"))
    nav.append(InlineKeyboardButton("▶️", callback_data=f"glist|{genre}|{sort}|{page+1}"))
    kb.append(nav)
    kb.append([InlineKeyboardButton("🔄 Sort", callback_data=f"gpick|{genre}"),
               InlineKeyboardButton("◀️ Janrlar", callback_data="genre_menu")])
    kb.extend(home())
    return t, kb

def build_season_menu():
    cur = datetime.now().year
    t = "🌸 <b>MAVSUM BO'YICHA ANIMELAR</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n📅 Mavsumni tanlang:"
    kb = []
    for season, name in SEASON_UZ.items():
        row = [InlineKeyboardButton(f"{name.split()[0]} {y}", callback_data=f"seas|{season}|{y}|1")
               for y in [cur, cur-1, cur-2]]
        kb.append(row)
    kb.extend(home())
    return t, kb

async def build_season_list(season: str, year: int, page: int):
    sname = SEASON_UZ.get(season, season)
    animes = await api.get_seasonal(season, year, page)
    if not animes:
        t = f"😔 <b>{sname} {year}</b> da anime topilmadi"
        kb = [[InlineKeyboardButton("◀️ Mavsum", callback_data="season_menu")], *home()]
        return t, kb
    t = f"{sname} <b>{year}</b>\n📊 {len(animes)} ta | Sahifa {page}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    kb = []
    start = (page-1)*10+1
    for i, a in enumerate(animes, start):
        title = a["title"]["romaji"]
        genres = " · ".join((a.get("genres") or [])[:2])
        t += f"<b>{i}.</b> {title}\n   {stars(a.get('averageScore',0))} | 🎭{genres or 'N/A'}\n\n"
        kb.append([InlineKeyboardButton(f"▸ {title[:42]}", callback_data=f"det|{a['id']}")])
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"seas|{season}|{year}|{page-1}"))
    nav.append(InlineKeyboardButton(f"• {page} •", callback_data="noop"))
    nav.append(InlineKeyboardButton("▶️", callback_data=f"seas|{season}|{year}|{page+1}"))
    kb.append(nav)
    kb.append([InlineKeyboardButton("◀️ Mavsum", callback_data="season_menu")])
    kb.extend(home())
    return t, kb

async def build_detail(user_id: int, anime_id: int):
    """Anime detail text va keyboard qaytaradi. Rasm alohida qaytariladi."""
    anime = await api.get_anime_details(anime_id)
    if not anime:
        return "❌ Anime topilmadi!", home()
    t = _anime_text(anime)
    kb = _anime_kb(user_id, anime_id)
    return t, kb

def _anime_text(a: dict) -> str:
    tl = a.get("title", {})
    romaji = tl.get("romaji","N/A")
    english = tl.get("english") or ""
    native = tl.get("native") or ""
    score = a.get("averageScore", 0)
    status = STATUS_UZ.get(a.get("status",""), "❓")
    fmt = FMT.get(a.get("format",""), "📺")
    season = SEASON_UZ.get(a.get("season") or "", "")
    year = a.get("seasonYear","")
    eps = a.get("episodes") or "?"
    dur = a.get("duration") or "?"
    pop = a.get("popularity") or 0
    favs = a.get("favourites") or 0
    genres = a.get("genres") or []
    genre_str = "  ".join([f"{GE.get(g,'🏷')}{g}" for g in genres[:5]]) or "N/A"
    studios = (a.get("studios") or {}).get("nodes") or []
    studio = " · ".join([s["name"] for s in studios if s.get("isAnimationStudio")][:2]) or "N/A"
    chars = (a.get("characters") or {}).get("nodes") or []
    char_str = ", ".join([c["name"]["full"] for c in chars[:4]]) or "N/A"
    desc = clean(a.get("description") or "")
    nep = a.get("nextAiringEpisode")
    nep_s = f"\n⏰ <b>Keyingi:</b> #{nep.get('episode','?')} — {until(nep.get('timeUntilAiring',0))} ichida" if nep else ""

    t  = f"🎌 <b>{romaji}</b>\n"
    if english and english != romaji:
        t += f"🌐 <i>{english}</i>\n"
    if native:
        t += f"🇯🇵 <code>{native}</code>\n"
    t += f"\n┌─────────────────────────\n"
    t += f"│ {stars(score)}\n"
    t += f"│ {fmt} {status}\n"
    t += f"│ 📺 {eps} ep  ⏱ {dur} min\n"
    if season:
        t += f"│ 🗓 {season} {year}\n"
    t += f"│ 🏢 {studio}\n"
    t += f"│ 👥 {pop:,}  ❤️ {favs:,}\n"
    t += f"└─────────────────────────"
    if nep_s:
        t += nep_s
    t += f"\n\n🎭 <b>Janrlar:</b> {genre_str}\n"
    t += f"👤 <b>Qahramonlar:</b> <i>{char_str}</i>\n\n"
    t += f"📖 <b>Tavsif:</b>\n<i>{desc}</i>"
    return t

def _anime_kb(user_id: int, anime_id: int) -> list:
    is_fav = db.is_favorite(user_id, anime_id)
    is_wch = db.is_watched(user_id, anime_id)
    fav_txt = "💔 Sevimlilardan o'chirish" if is_fav else "❤️ Sevimlilarga qo'shish"
    fav_cb  = f"fdel|{anime_id}" if is_fav else f"fadd|{anime_id}"
    wch_txt = "🗑 Ko'rilganlardan o'chirish" if is_wch else "✅ Ko'rilganlarga qo'shish"
    wch_cb  = f"wdel|{anime_id}" if is_wch else f"wadd|{anime_id}"
    return [
        [InlineKeyboardButton(fav_txt, callback_data=fav_cb)],
        [InlineKeyboardButton(wch_txt, callback_data=wch_cb)],
        [InlineKeyboardButton("🎯 Tavsiyalar", callback_data=f"recs|{anime_id}")],
        [InlineKeyboardButton("🌐 AniList", url=f"https://anilist.co/anime/{anime_id}"),
         InlineKeyboardButton("🎲 Tasodifiy", callback_data="random")],
        [InlineKeyboardButton("🏠 Bosh Menu", callback_data="home")],
    ]

async def build_recs(anime_id: int):
    recs = await api.get_recommendations_for_anime(anime_id)
    if not recs:
        t = "😔 <b>Tavsiyalar topilmadi</b>"
        kb = [[InlineKeyboardButton("◀️ Orqaga", callback_data=f"det|{anime_id}")], *home()]
        return t, kb
    t = "🎯 <b>TAVSIYA ETILGAN ANIMELAR</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    kb = []
    for i, a in enumerate(recs[:6], 1):
        if not a:
            continue
        title = a["title"]["romaji"]
        genres = " · ".join((a.get("genres") or [])[:2])
        t += f"<b>{i}.</b> {title}\n   {stars(a.get('averageScore',0))} | 🎭{genres or 'N/A'}\n\n"
        kb.append([InlineKeyboardButton(f"▸ {title[:42]}", callback_data=f"det|{a['id']}")])
    kb.append([InlineKeyboardButton("◀️ Orqaga", callback_data=f"det|{anime_id}")])
    kb.extend(home())
    return t, kb

def build_search_results(results: list, q: str):
    if not results:
        t = f"😔 <b>«{q}»</b> bo'yicha hech narsa topilmadi!\n\n<i>Boshqa nom bilan qidirib ko'ring.</i>"
        return t, home()
    t = f"🔍 <b>«{q}»</b> — {len(results)} ta natija\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    kb = []
    for i, a in enumerate(results[:10], 1):
        title = a["title"]["romaji"]
        yr = a.get("seasonYear","?")
        fmt = FMT.get(a.get("format",""), "📺")
        t += f"{i}. {fmt} <b>{title}</b>\n   {stars(a.get('averageScore',0))} | 📅{yr}\n\n"
        kb.append([InlineKeyboardButton(f"🎬 {title[:42]}", callback_data=f"det|{a['id']}")])
    kb.extend(home())
    return t, kb

def build_favs(user_id: int):
    favs = db.get_favorites(user_id)
    if not favs:
        t = ("❤️ <b>SEVIMLILAR</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
             "😔 Hali sevimli anime yo'q!\n\n<i>Anime sahifasidan ❤️ tugmasini bosing.</i>")
        kb = [[InlineKeyboardButton("🔥 Trend", callback_data="lst|trending|1")], *home()]
        return t, kb
    t = f"❤️ <b>SEVIMLI ANIMELAR</b> — {len(favs)} ta\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    kb = []
    for i, (aid, title) in enumerate(favs, 1):
        t += f"{i}. {title}\n"
        kb.append([InlineKeyboardButton(f"❤️ {title[:42]}", callback_data=f"det|{aid}")])
    kb.extend(home())
    return t, kb

def build_watched(user_id: int):
    wlist = db.get_watched(user_id)
    if not wlist:
        t = ("👁 <b>KO'RILGANLAR</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
             "😔 Hali ko'rilgan anime yo'q!\n\n<i>Anime sahifasidan ✅ tugmasini bosing.</i>")
        kb = [[InlineKeyboardButton("🔍 Qidirish", callback_data="search_tip")], *home()]
        return t, kb
    t = f"👁 <b>KO'RILGAN ANIMELAR</b> — {len(wlist)} ta\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    kb = []
    for i, (aid, title) in enumerate(wlist, 1):
        t += f"{i}. {title}\n"
        kb.append([InlineKeyboardButton(f"✅ {title[:42]}", callback_data=f"det|{aid}")])
    kb.extend(home())
    return t, kb

def build_history(user_id: int):
    history = db.get_search_history(user_id, 10)
    if not history:
        t = "📜 <b>Qidiruv tarixi bo'sh</b>\n\n<i>Hali hech narsa qidirmagansiz.</i>"
        return t, home()
    t = "📜 <b>SO'NGGI QIDIRUVLAR</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    kb = []
    for i, q in enumerate(history, 1):
        t += f"{i}. <code>{q}</code>\n"
        kb.append([InlineKeyboardButton(f"🔍 {q[:42]}", callback_data=f"redo|{q[:50]}")])
    kb.extend(home())
    return t, kb

def build_subscribe_menu(user_id: int):
    subs = db.get_user_subscriptions(user_id)
    days = ["MONDAY","TUESDAY","WEDNESDAY","THURSDAY","FRIDAY","SATURDAY","SUNDAY"]
    t = ("🔔 <b>OBUNA SOZLAMALARI</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
         "✅ = Obuna bor  |  ☑️ = Obuna yo'q\n\nTanlangan kunlarda ertalab xabar olasiz!")
    kb = []
    for d in days:
        icon = "✅" if d in subs else "☑️"
        em = DAY_EMOJI[d]
        kb.append([InlineKeyboardButton(f"{icon} {em} {DAY_NAMES_UZ[d]}", callback_data=f"sub|{d}")])
    kb.extend(home())
    return t, kb

async def build_profile(user_id: int, first_name: str = None):
    user = db.get_user(user_id)
    fname = first_name or (user or {}).get("first_name", "Foydalanuvchi")
    favs_n = db.get_favorites_count(user_id)
    wch_n = len(db.get_watched(user_id))
    subs_n = len(db.get_user_subscriptions(user_id))
    srch_n = (user or {}).get("total_searches", 0)
    joined = ((user or {}).get("joined_at") or "N/A")[:10]
    top_g = db.get_user_top_genres(user_id, 5)

    t = (f"👤 <b>PROFIL</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
         f"🙋 <b>Ism:</b> {fname}\n"
         f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
         f"📅 <b>A'zo:</b> {joined}\n\n"
         f"📊 <b>Statistika:</b>\n"
         f"┣ ❤️ Sevimlilar: <b>{favs_n}</b> ta\n"
         f"┣ 👁 Ko'rilganlar: <b>{wch_n}</b> ta\n"
         f"┣ 🔔 Obunalar: <b>{subs_n}</b> kun\n"
         f"┗ 🔍 Qidiruvlar: <b>{srch_n}</b> ta\n")
    if top_g:
        t += "\n🎭 <b>Sevimli janrlar:</b>\n"
        for g, c in top_g:
            t += f"  {GE.get(g,'🏷')} {g} — {c} marta\n"
    kb = [
        [InlineKeyboardButton("📜 Qidiruv tarixi", callback_data="history")],
        *home()
    ]
    return t, kb

def build_admin_stats():
    s = db.get_stats()
    top_g = db.get_global_top_genres(5)
    popular = db.get_popular_searches(5)
    t = (f"📊 <b>BOT STATISTIKASI</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
         f"👥 Foydalanuvchilar: <b>{s['users']}</b>\n"
         f"📅 Bugun faol: <b>{s['today_active']}</b>\n"
         f"❤️ Sevimlilar: <b>{s['favorites']}</b>\n"
         f"👁 Ko'rilganlar: <b>{s['watched']}</b>\n"
         f"🔔 Obunalar: <b>{s['subscriptions']}</b>\n"
         f"🔍 Qidiruvlar: <b>{s['total_searches']}</b>\n")
    if top_g:
        t += "\n🎭 <b>Top janrlar:</b>\n"
        for g, c in top_g:
            t += f"  {GE.get(g,'🏷')} {g}: {c}\n"
    if popular:
        t += "\n🔍 <b>Top qidiruvlar:</b>\n"
        for q, c in popular:
            t += f"  «{q}»: {c} marta\n"
    return t, home()

# ──────────────────────────────────────────
#  MARKAZIY CALLBACK HANDLER
# ──────────────────────────────────────────

async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    uid = q.from_user.id

    try:
        # ── Asosiy menyu ──
        if d == "home":
            await edit_or_answer(q, msg.main_menu(), main_kb().inline_keyboard)

        elif d == "help":
            await edit_or_answer(q, msg.help_text(), home())

        # ── Jadval ──
        elif d == "today":
            t, kb = await build_today()
            await edit_or_answer(q, t, kb)

        elif d == "weekly":
            t, kb = build_weekly()
            await edit_or_answer(q, t, kb)

        elif d.startswith("day|"):
            day = d[4:]
            day_uz = DAY_NAMES_UZ.get(day, day)
            await edit_or_answer(q, f"⏳ {day_uz} yuklanmoqda...", [])
            animes = await api.get_schedule_by_day(day)
            em = DAY_EMOJI.get(day, "🗓")
            if not animes:
                t = f"😔 <b>{day_uz} uchun anime topilmadi</b>"
                kb = [[InlineKeyboardButton("◀️ Haftalik", callback_data="weekly")], *home()]
            else:
                t = f"{em} <b>{day_uz.upper()}</b> — {len(animes)} ta\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                kb = []
                for i, a in enumerate(animes[:15], 1):
                    title = a["title"]["romaji"][:30]
                    genres = " · ".join((a.get("genres") or [])[:2])
                    t += f"<b>{i}.</b> {title}\n   {stars(a.get('averageScore',0))} | 🎭{genres or 'N/A'}\n\n"
                    kb.append([InlineKeyboardButton(f"🎬 {title}", callback_data=f"det|{a['id']}")])
                kb.append([InlineKeyboardButton("◀️ Haftalik", callback_data="weekly"),
                           InlineKeyboardButton("🏠 Menu", callback_data="home")])
            await edit_or_answer(q, t, kb)

        # ── Kashfiyot ──
        elif d.startswith("lst|"):
            _, kind, page = d.split("|")
            t, kb = await build_list(kind, int(page))
            await edit_or_answer(q, t, kb)

        # ── Janr ──
        elif d == "genre_menu":
            t, kb = build_genre_menu()
            await edit_or_answer(q, t, kb)

        elif d.startswith("gpick|"):
            genre = d[6:]
            db.track_genre(uid, genre)
            t, kb = build_genre_sort(genre)
            await edit_or_answer(q, t, kb)

        elif d.startswith("glist|"):
            parts = d.split("|")
            genre, sort, page = parts[1], parts[2], int(parts[3])
            db.track_genre(uid, genre)
            t, kb = await build_genre_list(genre, sort, page)
            await edit_or_answer(q, t, kb)

        # ── Mavsum ──
        elif d == "season_menu":
            t, kb = build_season_menu()
            await edit_or_answer(q, t, kb)

        elif d.startswith("seas|"):
            parts = d.split("|")
            season, year, page = parts[1], int(parts[2]), int(parts[3])
            t, kb = await build_season_list(season, year, page)
            await edit_or_answer(q, t, kb)

        # ── Random ──
        elif d == "random":
            await edit_or_answer(q, "🎲 <b>Tasodifiy anime qidirilmoqda...</b>", [])
            anime = await api.get_random_anime()
            if not anime:
                await edit_or_answer(q, "❌ Xatolik!", [[InlineKeyboardButton("🔄 Qayta", callback_data="random"), InlineKeyboardButton("🏠", callback_data="home")]])
                return
            t, kb = await build_detail(uid, anime["id"])
            await edit_or_answer(q, t, kb)

        # ── Qidirish ──
        elif d == "search_tip":
            t = ("🔍 <b>ANIME QIDIRISH</b>\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                 "📝 Anime nomini <b>chat ga yozing</b>:\n\n"
                 "<i>Misol: Naruto, One Piece, Bleach...</i>\n\n"
                 "💡 Inglizcha, Yaponcha yoki Romaji bo'lishi mumkin!\n\n"
                 "🎭 Janr bo'yicha izlash:")
            kb = [[InlineKeyboardButton("🎭 Janr bo'yicha", callback_data="genre_menu")],
                  [InlineKeyboardButton("❌ Bekor qilish", callback_data="home")]]
            await edit_or_answer(q, t, kb)

        elif d.startswith("redo|"):
            search_q = d[5:]
            await edit_or_answer(q, f"🔍 <b>«{search_q}»</b> qidirilmoqda...", [])
            results = await api.search_anime(search_q)
            db.save_search(uid, search_q, len(results))
            t, kb = build_search_results(results, search_q)
            await edit_or_answer(q, t, kb)

        # ── Anime detail ──
        elif d.startswith("det|"):
            anime_id = int(d[4:])
            await edit_or_answer(q, "⏳ <b>Ma'lumot yuklanmoqda...</b>", [])
            anime = await api.get_anime_details(anime_id)
            if not anime:
                await edit_or_answer(q, "❌ Anime topilmadi!", home())
                return
            t = _anime_text(anime)
            kb = _anime_kb(uid, anime_id)
            # FIX: edit_message_media ishlatiladi - message ID o'zgarmaydi
            photo = (anime.get("coverImage") or {}).get("extraLarge") or \
                    (anime.get("coverImage") or {}).get("large")
            await edit_or_answer(q, t, kb, photo=photo)

        # ── Tavsiyalar ──
        elif d.startswith("recs|"):
            anime_id = int(d[5:])
            t, kb = await build_recs(anime_id)
            await edit_or_answer(q, t, kb)

        # ── Sevimlilar ──
        elif d == "favs":
            t, kb = build_favs(uid)
            await edit_or_answer(q, t, kb)

        elif d.startswith("fadd|"):
            anime_id = int(d[5:])
            anime = await api.get_anime_details(anime_id)
            if anime:
                db.add_favorite(uid, anime_id, anime["title"]["romaji"])
                await q.answer(f"❤️ Sevimlilarga qo'shildi!", show_alert=True)
            t = _anime_text(anime)
            kb = _anime_kb(uid, anime_id)
            photo = (anime.get("coverImage") or {}).get("large")
            await edit_or_answer(q, t, kb, photo=photo)

        elif d.startswith("fdel|"):
            anime_id = int(d[5:])
            db.remove_favorite(uid, anime_id)
            await q.answer("💔 Sevimlilardan olib tashlandi!", show_alert=True)
            anime = await api.get_anime_details(anime_id)
            if anime:
                t = _anime_text(anime)
                kb = _anime_kb(uid, anime_id)
                photo = (anime.get("coverImage") or {}).get("large")
                await edit_or_answer(q, t, kb, photo=photo)

        # ── Ko'rilganlar ──
        elif d == "watchd":
            t, kb = build_watched(uid)
            await edit_or_answer(q, t, kb)

        elif d.startswith("wadd|"):
            anime_id = int(d[5:])
            anime = await api.get_anime_details(anime_id)
            if anime:
                db.add_watched(uid, anime_id, anime["title"]["romaji"])
                await q.answer("✅ Ko'rilganlarga qo'shildi!", show_alert=True)
            t = _anime_text(anime)
            kb = _anime_kb(uid, anime_id)
            photo = (anime.get("coverImage") or {}).get("large")
            await edit_or_answer(q, t, kb, photo=photo)

        elif d.startswith("wdel|"):
            anime_id = int(d[5:])
            db.remove_watched(uid, anime_id)
            await q.answer("🗑 Ko'rilganlardan olib tashlandi!", show_alert=True)
            anime = await api.get_anime_details(anime_id)
            if anime:
                t = _anime_text(anime)
                kb = _anime_kb(uid, anime_id)
                photo = (anime.get("coverImage") or {}).get("large")
                await edit_or_answer(q, t, kb, photo=photo)

        # ── Obuna ──
        elif d == "subscribe":
            t, kb = build_subscribe_menu(uid)
            await edit_or_answer(q, t, kb)

        elif d.startswith("sub|"):
            day = d[4:]
            is_sub = db.toggle_subscription(uid, day)
            day_uz = DAY_NAMES_UZ.get(day, day)
            status_msg = "obuna yoqildi" if is_sub else "obuna o'chirildi"
            await q.answer(f"{'✅' if is_sub else '❌'} {day_uz} {status_msg}!", show_alert=True)
            t, kb = build_subscribe_menu(uid)
            await edit_or_answer(q, t, kb)

        # ── Profil ──
        elif d == "profile":
            t, kb = await build_profile(uid, q.from_user.first_name)
            await edit_or_answer(q, t, kb)

        elif d == "history":
            t, kb = build_history(uid)
            await edit_or_answer(q, t, kb)

        # ── Admin ──
        elif d == "admin_stats" and uid in ADMIN_IDS:
            t, kb = build_admin_stats()
            await edit_or_answer(q, t, kb)

        elif d == "noop":
            pass

    except BadRequest as e:
        if "Message is not modified" not in str(e):
            logger.warning(f"BadRequest ({d}): {e}")
    except Exception as e:
        logger.error(f"Callback error ({d}): {e}", exc_info=True)
        try:
            await edit_or_answer(q, "❌ <b>Xatolik yuz berdi!</b>\n\nQayta urinib ko'ring.",
                                 [[InlineKeyboardButton("🔄 Qayta", callback_data=d),
                                   InlineKeyboardButton("🏠", callback_data="home")]])
        except Exception:
            pass

# ──────────────────────────────────────────
#  BILDIRISHNOMALAR
# ──────────────────────────────────────────

async def daily_notify(bot):
    while True:
        now = datetime.now()
        target = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())

        today = datetime.now().strftime("%A").upper()
        subscribers = db.get_day_subscribers(today)
        if not subscribers:
            continue

        animes = await api.get_schedule_by_day(today)
        if not animes:
            continue

        day_uz = DAY_NAMES_UZ.get(today, today)
        t = f"🌅 <b>BUGUNGI ANIME JADVALI</b>\n📅 {day_uz} — {datetime.now().strftime('%d.%m.%Y')}\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for i, a in enumerate(animes[:10], 1):
            title = a["title"]["romaji"][:35]
            sc = a.get("averageScore", 0)
            t += f"{i}. <b>{title}</b>{f' ⭐{sc/10:.1f}' if sc else ''}\n"
        t += "\n🎌 <i>Anime Universe Bot</i>"

        kb = [[InlineKeyboardButton("📅 To'liq Jadval", callback_data="today")]]
        for uid in subscribers:
            try:
                await bot.send_message(uid, t, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
                await asyncio.sleep(0.05)
            except Forbidden:
                db.block_user(uid)
            except Exception as e:
                logger.error(f"Notify error {uid}: {e}")

# ──────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────

async def post_init(app: Application):
    await app.bot.set_my_commands([
        BotCommand("start", "🏠 Botni boshlash"),
        BotCommand("help", "ℹ️ Yordam"),
        BotCommand("today", "📅 Bugungi jadval"),
        BotCommand("weekly", "🗓 Haftalik jadval"),
        BotCommand("trending", "🔥 Trend animelar"),
        BotCommand("top", "⭐ Top animelar"),
        BotCommand("genre", "🎭 Janr bo'yicha"),
        BotCommand("random", "🎲 Tasodifiy anime"),
        BotCommand("favorites", "❤️ Sevimlilarim"),
        BotCommand("watched", "👁 Ko'rilganlar"),
        BotCommand("history", "📜 Qidiruv tarixi"),
        BotCommand("profile", "👤 Profilim"),
    ])
    asyncio.create_task(daily_notify(app.bot))
    logger.info("✅ Bot tayyor (v3.2)")

def main():
    logger.info("🚀 Anime Universe Bot v3.2 ishga tushmoqda...")
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("weekly", cmd_weekly))
    app.add_handler(CommandHandler("trending", cmd_trending))
    app.add_handler(CommandHandler("top", cmd_top))
    app.add_handler(CommandHandler("genre", cmd_genre))
    app.add_handler(CommandHandler("random", cmd_random))
    app.add_handler(CommandHandler("favorites", cmd_favorites))
    app.add_handler(CommandHandler("watched", cmd_watched))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_search_text))

    logger.info("✅ Anime Universe Bot v3.2 ishga tushdi! 🎌")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
