# ══════════════════════════════════════════
#           KONFIGURATSIYA v3.0
# ══════════════════════════════════════════

# 🤖 Telegram Bot Token (@BotFather dan oling)
BOT_TOKEN = "8210349110:AAFEBd3aMHjRsphRQdlOMBCMgImTtviWRw0"

# 👑 Admin foydalanuvchi ID lari
ADMIN_IDS = [7637278929]

# 🗄️ Database fayl nomi
DATABASE_NAME = "anime_bot.db"

# 🌐 AniList API URL (bepul, API kalit kerak emas)
ANILIST_API_URL = "https://graphql.anilist.co"

import os

# ▶️ Bepul striming sayti (ko'rish/qidiruv havolasi uchun)
#    DIQQAT: AniWave (aniwave.ac) 2024-yil avgustda butunlay yopilgan!
#    Shu sababli endi jonli vorisi — HiAnime ishlatiladi.
#    Sayt yoki domen o'zgarsa, faqat shu yerni yangilang.
STREAM_SITE_NAME = "HiAnime"
STREAM_SITE_BASE = "https://hianime.to"
STREAM_SITE_SEARCH = "/search?keyword="   # to'liq havola: {BASE}{SEARCH}{anime nomi}

# 📥 OpenSubtitles API (subtitle yuklash uchun)
#    1) https://www.opensubtitles.com saytida ro'yxatdan o'ting
#    2) Profil > API Consumers bo'limidan API kalit oling
#    3) Kalitni quyiga yoki OPENSUBTITLES_API_KEY env o'zgaruvchiga qo'ying
OPENSUBTITLES_API_URL = "https://api.opensubtitles.com/api/v1"
OPENSUBTITLES_API_KEY = os.getenv("OPENSUBTITLES_API_KEY", "")  # ⬅️ bu yerga kalitingizni qo'ying
OPENSUBTITLES_APP = "AnimeUniverseBot v3.2"  # OpenSubtitles talab qiladigan User-Agent

# 🔑 (Ixtiyoriy) OpenSubtitles login — yuklab olish limitini oshiradi.
#    Bo'sh qoldirilsa, anonim (Api-Key) rejimida ishlaydi (kunlik limit kichik).
OPENSUBTITLES_USERNAME = os.getenv("OPENSUBTITLES_USERNAME", "")
OPENSUBTITLES_PASSWORD = os.getenv("OPENSUBTITLES_PASSWORD", "")

# ⏰ Bildirishnoma vaqti
NOTIFICATION_HOUR = 9
NOTIFICATION_MINUTE = 0

# 📊 Sahifadagi anime soni
ANIMES_PER_PAGE = 10

# 🔍 Qidiruv natijalar soni
SEARCH_RESULTS_LIMIT = 10

# 🎭 Barcha janrlar ro'yxati
ALL_GENRES = [
    "Action", "Adventure", "Comedy", "Drama", "Ecchi",
    "Fantasy", "Horror", "Mahou Shoujo", "Mecha", "Music",
    "Mystery", "Psychological", "Romance", "Sci-Fi", "Slice of Life",
    "Sports", "Supernatural", "Thriller", "Harem", "Isekai"
]

# 🌸 Mavsumlar
SEASONS = ["SPRING", "SUMMER", "FALL", "WINTER"]

# 📺 Formatlar
FORMATS = ["TV", "MOVIE", "OVA", "ONA", "SPECIAL"]
