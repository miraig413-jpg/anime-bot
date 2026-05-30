"""
💬 Bot Xabarlar Moduli — v3.0
Barcha matnlar, zamonaviy dizayn
"""

from datetime import datetime


class Messages:

    def welcome(self, first_name: str) -> str:
        hour = datetime.now().hour
        if 5 <= hour < 12:
            greeting = "☀️ Xayrli tong"
        elif 12 <= hour < 17:
            greeting = "🌤 Xayrli kun"
        elif 17 <= hour < 21:
            greeting = "🌆 Xayrli kechqurun"
        else:
            greeting = "🌙 Xayrli kecha"

        return (
            f"{greeting}, <b>{first_name}</b>! 👋\n\n"
            "┌─────────────────────────┐\n"
            "│   🎌  ANIME UNIVERSE BOT  │\n"
            "│        v 3 . 0           │\n"
            "└─────────────────────────┘\n\n"
            "📺 Sevimli animelaringizni kuzatib boring!\n\n"
            "✨ <b>Imkoniyatlar:</b>\n"
            "┣ 📅 Bugungi & haftalik jadval\n"
            "┣ 🔥 Trend & ⭐ Top animelar\n"
            "┣ 🎭 Janr bo'yicha qidirish  <b>NEW</b>\n"
            "┣ 🎲 Tasodifiy anime  <b>NEW</b>\n"
            "┣ 🌸 Mavsum bo'yicha  <b>NEW</b>\n"
            "┣ 🔍 Nom bo'yicha qidirish\n"
            "┣ ❤️ Sevimlilar & 👁 Ko'rilganlar  <b>NEW</b>\n"
            "┗ 🔔 Kunlik bildirishnomalar\n\n"
            "👇 <b>Quyidagi tugmalardan birini tanlang:</b>"
        )

    def main_menu(self) -> str:
        return (
            "🎌 <b>ANIME UNIVERSE — BOSH MENU</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔸 <b>Jadval</b> — Bugun & hafta\n"
            "🔸 <b>Kashfiyot</b> — Trend, Top, Ommabop\n"
            "🔸 <b>Janr</b> — Janr bo'yicha qidirish\n"
            "🔸 <b>Mavsum</b> — Mavsumiy animelar\n"
            "🔸 <b>Tasodifiy</b> — Qiziqarli taklif\n"
            "🔸 <b>Qidirish</b> — Nom bo'yicha\n"
            "🔸 <b>Kolleksiya</b> — Sevimlilar & Ko'rilganlar\n"
            "🔸 <b>Obuna</b> — Bildirishnomalar\n\n"
            "👇 Tanlang:"
        )

    def help_text(self) -> str:
        return (
            "ℹ️ <b>YORDAM — ANIME UNIVERSE v3.0</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📋 <b>Komandalar:</b>\n"
            "┣ /start — Botni boshlash\n"
            "┣ /today — Bugungi jadval\n"
            "┣ /weekly — Haftalik jadval\n"
            "┣ /trending — Trend animelar\n"
            "┣ /top — Top animelar\n"
            "┣ /genre — Janr bo'yicha qidirish\n"
            "┣ /random — Tasodifiy anime\n"
            "┣ /favorites — Sevimlilarim\n"
            "┣ /watched — Ko'rilganlar\n"
            "┣ /history — Qidiruv tarixi\n"
            "┣ /profile — Profilim\n"
            "┗ /help — Yordam\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔍 <b>Qidirish:</b>\n"
            "Istalgan matn yozsangiz bot\n"
            "avtomatik qidiradi!\n\n"
            "🎭 <b>Janr qidirish:</b>\n"
            "Janr tugmasini bosing va\n"
            "Action, Romance, Fantasy va\n"
            "boshqalardan tanlang!\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🌐 <b>Ma'lumot manbai:</b> AniList.co\n"
            "📊 <b>Versiya:</b> 3.0.0\n\n"
            "💬 Muammo? Admin bilan bog'laning!"
        )
