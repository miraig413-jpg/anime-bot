"""
🔗 streaming.py — Tashqi servislar integratsiyasi

1. AniwaveClient     — anime nomini Aniwave saytida qidirib, ko'rish havolasini topadi.
2. OpenSubtitlesClient — OpenSubtitles REST API v1 orqali inglizcha .srt subtitlesni topib yuklaydi.

Bu modul ataylab Telegram'ga bog'liq EMAS — faqat HTTP bilan ishlaydi va sof
ma'lumot (URL / bayt) qaytaradi. Shu sababli mantiqни alohida test qilish oson.
"""

from __future__ import annotations

import re
import logging
import aiohttp
from urllib.parse import quote_plus, urljoin

from config import (
    ANIWAVE_BASE,
    OPENSUBTITLES_API_URL,
    OPENSUBTITLES_API_KEY,
    OPENSUBTITLES_APP,
)

logger = logging.getLogger(__name__)

# Brauzerga o'xshash User-Agent — ba'zi saytlar oddiy klientlarni bloklaydi
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


# ══════════════════════════════════════════════════════════════
#  ANIWAVE — ko'rish havolasi
# ══════════════════════════════════════════════════════════════
class AniwaveClient:
    """Aniwave saytida anime qidirib, /watch/ havolasini topadi."""

    # natija sahifasidagi ko'rish havolalari: href="/watch/<slug>"
    _WATCH_RE = re.compile(r'href="(/watch/[^"#?\s]+)"', re.IGNORECASE)

    def __init__(self):
        self.base = (ANIWAVE_BASE or "https://aniwave.ac").rstrip("/")
        self.session = None

    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15),
                headers={"User-Agent": _BROWSER_UA},
            )
        return self.session

    def search_url(self, title: str) -> str:
        """Foydalanuvchi o'zi qidirib topishi uchun filter havolasi."""
        return f"{self.base}/filter?keyword={quote_plus(title)}"

    def extract_watch_slug(self, html: str) -> str | None:
        """HTML matnidan birinchi /watch/ havolasini ajratadi (test uchun ham)."""
        if not html:
            return None
        m = self._WATCH_RE.search(html)
        return m.group(1) if m else None

    async def resolve(self, title: str) -> dict:
        """
        Anime nomini Aniwave'da qidiradi.
        Qaytaradi: {"watch_url": <url|None>, "search_url": <url>}
        watch_url topilmasa — foydalanuvchi search_url orqali o'zi topadi.
        """
        search = self.search_url(title)
        try:
            session = await self._get_session()
            async with session.get(search) as resp:
                if resp.status != 200:
                    logger.info(f"Aniwave qidiruv status={resp.status}")
                    return {"watch_url": None, "search_url": search}
                html = await resp.text()
            slug = self.extract_watch_slug(html)
            watch_url = urljoin(self.base + "/", slug.lstrip("/")) if slug else None
            return {"watch_url": watch_url, "search_url": search}
        except Exception as e:
            logger.warning(f"Aniwave resolve xato: {e}")
            return {"watch_url": None, "search_url": search}

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


# ══════════════════════════════════════════════════════════════
#  OPENSUBTITLES — inglizcha .srt subtitle
# ══════════════════════════════════════════════════════════════
class OpenSubtitlesClient:
    """
    OpenSubtitles REST API v1 klienti.
    Oqim: /subtitles (qidirish) -> /download (link olish) -> link orqali faylni yuklash.
    """

    def __init__(self):
        self.base = (OPENSUBTITLES_API_URL or "https://api.opensubtitles.com/api/v1").rstrip("/")
        self.api_key = OPENSUBTITLES_API_KEY or ""
        self.app = OPENSUBTITLES_APP or "AnimeUniverseBot v3.2"
        self.session = None

    def configured(self) -> bool:
        return bool(self.api_key)

    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=25)
            )
        return self.session

    def _headers(self, json_body: bool = False) -> dict:
        h = {
            "Api-Key": self.api_key,
            "User-Agent": self.app,
            "Accept": "application/json",
        }
        if json_body:
            h["Content-Type"] = "application/json"
        return h

    # ── ichki yordamchilar (test qilinadigan sof mantiq) ──
    @staticmethod
    def pick_best_file(search_json: dict) -> dict | None:
        """
        /subtitles javobidan eng ko'p yuklab olingan, file_id'ga ega
        natijani tanlaydi. Qaytaradi: {"file_id", "file_name", "release"} yoki None.
        """
        data = (search_json or {}).get("data") or []
        best = None
        best_dl = -1
        for item in data:
            attrs = item.get("attributes") or {}
            files = attrs.get("files") or []
            if not files:
                continue
            file_id = files[0].get("file_id")
            if not file_id:
                continue
            dl = attrs.get("download_count") or 0
            if dl > best_dl:
                best_dl = dl
                best = {
                    "file_id": file_id,
                    "file_name": files[0].get("file_name") or attrs.get("release") or "subtitle",
                    "release": attrs.get("release") or "",
                }
        return best

    @staticmethod
    def _safe_srt_name(name: str) -> str:
        name = (name or "subtitle").strip()
        name = re.sub(r"[^\w.\- ]+", "", name)[:80].strip() or "subtitle"
        if not name.lower().endswith(".srt"):
            name += ".srt"
        return name

    # ── asosiy oqim ──
    async def fetch_subtitle(self, query: str, language: str = "en",
                             season: int | None = None,
                             episode: int | None = None) -> dict:
        """
        Subtitle topib, .srt faylini yuklaydi.
        Qaytaradi:
          {"ok": True, "filename": str, "content": bytes, "remaining": int|None}
          {"ok": False, "reason": "no_key"|"not_found"|"quota"|"error", "message": str}
        """
        if not self.configured():
            return {"ok": False, "reason": "no_key",
                    "message": "OPENSUBTITLES_API_KEY config.py da sozlanmagan."}

        try:
            session = await self._get_session()

            # 1) Qidirish
            params = {"query": query, "languages": language}
            if season is not None:
                params["season_number"] = season
            if episode is not None:
                params["episode_number"] = episode
            async with session.get(f"{self.base}/subtitles",
                                   params=params, headers=self._headers()) as r:
                if r.status in (401, 403):
                    return {"ok": False, "reason": "no_key",
                            "message": f"API kalit rad etildi (status {r.status})."}
                if r.status != 200:
                    return {"ok": False, "reason": "error",
                            "message": f"Qidiruv xatosi: status {r.status}."}
                search_json = await r.json()

            best = self.pick_best_file(search_json)
            if not best:
                return {"ok": False, "reason": "not_found",
                        "message": f"«{query}» uchun inglizcha subtitle topilmadi."}

            # 2) Yuklash havolasini olish
            async with session.post(f"{self.base}/download",
                                    json={"file_id": best["file_id"]},
                                    headers=self._headers(json_body=True)) as r:
                dl_json = await r.json() if r.content_type == "application/json" else {}
                if r.status == 406 or (r.status == 200 and not dl_json.get("link")):
                    # 406 odatda kunlik limit tugaganda qaytadi
                    msg = dl_json.get("message") or "Kunlik yuklab olish limiti tugagan bo'lishi mumkin."
                    return {"ok": False, "reason": "quota", "message": msg}
                if r.status in (401, 403):
                    return {"ok": False, "reason": "no_key",
                            "message": f"API kalit rad etildi (status {r.status})."}
                if r.status != 200:
                    return {"ok": False, "reason": "error",
                            "message": f"Yuklash xatosi: status {r.status}."}
                link = dl_json.get("link")
                remaining = dl_json.get("remaining")
                fname = dl_json.get("file_name") or best["file_name"]

            if not link:
                return {"ok": False, "reason": "error", "message": "Yuklash havolasi bo'sh."}

            # 3) Fayl mazmunini yuklab olish
            async with session.get(link) as r:
                if r.status != 200:
                    return {"ok": False, "reason": "error",
                            "message": f"Fayl yuklanmadi: status {r.status}."}
                content = await r.read()

            return {
                "ok": True,
                "filename": self._safe_srt_name(fname),
                "content": content,
                "remaining": remaining,
            }
        except Exception as e:
            logger.error(f"OpenSubtitles xato: {e}", exc_info=True)
            return {"ok": False, "reason": "error", "message": str(e)}

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
