# 🎌 Anime Universe Bot — v3.0

Telegram uchun to'liq anime bot. AniList.co API asosida ishlaydi (bepul, kalit kerak emas).

## ✨ Yangi imkoniyatlar (v3.0)

| Funksiya | Tavsif |
|---|---|
| 🎭 Janr qidirish | 20+ janr bo'yicha filter + saralash |
| 🌸 Mavsum filter | Bahor/Yoz/Kuz/Qish + yil bo'yicha |
| 🎲 Random anime | Tasodifiy yuqori baholanган anime |
| 👁 Ko'rilganlar | Anime ko'rish ro'yxati |
| 🎯 Tavsiyalar | Anime asosida o'xshashlar |
| 👤 Profil | Foydalanuvchi statistikasi va sevimli janrlar |
| 📜 Qidiruv tarixi | So'nggi qidiruvlar |
| 👥 Ommabop | Eng ommabop animelar sahifasi |
| 📊 Janr statistika | Kim qaysi janrni ko'p qidirgan |

## 🚀 Ishga tushirish

```bash
pip install -r requirements.txt
python bot.py
```

## 📋 Komandalar

```
/start    — Botni boshlash
/today    — Bugungi jadval
/weekly   — Haftalik jadval
/trending — Trend animelar
/top      — Top animelar
/genre    — Janr bo'yicha qidirish  ← YANGI
/random   — Tasodifiy anime         ← YANGI
/favorites — Sevimlilarim
/watched  — Ko'rilganlar            ← YANGI
/history  — Qidiruv tarixi          ← YANGI
/profile  — Profilim                ← YANGI
/help     — Yordam
```

## ⚙️ Sozlash (config.py)

```python
BOT_TOKEN = "..."        # @BotFather dan oling
ADMIN_IDS = [123456789]  # Sizning Telegram ID
```

## 🗄️ Database

SQLite avtomatik yaratiladi. Jadvallar:
- `users` — foydalanuvchilar
- `favorites` — sevimlilar
- `watched` — ko'rilganlar ← YANGI
- `subscriptions` — obunalar
- `search_history` — qidiruv tarixi
- `genre_stats` — janr statistika ← YANGI
- `action_log` — harakat logi ← YANGI
