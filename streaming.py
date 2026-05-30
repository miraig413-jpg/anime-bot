"""
🔗 streaming.py — Tashqi servislar integratsiyasi

1. StreamSiteClient    — anime nomi uchun jonli striming saytida (HiAnime) qidiruv havolasini quradi.
                         (AniWave 2024-yilda yopilgani uchun endi ishlatilmaydi.)
2. OpenSubtitlesClient — OpenSubtitles REST API v1 orqali inglizcha .srt subtitlesni topib yuklaydi.

Bu modul ataylab Telegram'ga bog'liq EMAS — faqat HTTP/URL bilan ishlaydi va sof
ma'lumot (URL / bayt) qaytaradi. Shu sababli mantiqни alohida test qilish oson.
"""

from __future__ import annotations

import re
import logging
import aiohttp
from urllib.parse import quote_plus

from config import (
    STREAM_SITE_NAME,
    STREAM_SITE_BASE,
    STREAM_SITE_SEARCH,
    OPENSUBTITLES_API_URL,
    OPENSUBTITLES_API_KEY,
    OPENSUBTITLES_APP,
    OPENSUBTITLES_USERNAME,
    OPENSUBTITLES_PASSWORD,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
#  JONLI STRIMING SAYTI — qidiruv havolasi
# ══════════════════════════════════════════════════════════════
class StreamSiteClient:
    """
    Jonli striming saytida (default: HiAnime) anime qidiruv havolasini quradi.

    Eslatma: bu kabi saytlar Cloudflare himoyasi ostida bo'lgani uchun
    server tomonidan to'g'ridan-to'g'ri /watch havolasini ishonchli ravishda
    olib bo'lmaydi. Shuning uchun foydalanuvchini qidiruv sahifasiga
    yo'naltiramiz (bosilganda 100% ishlaydi). Rasmiy striming havolalari esa
    bot tomonidan AniList'dan olinadi.
    """

    def __init__(self):
        self.name = STREAM_SITE_NAME or "HiAnime"
        self.base = (STREAM_SITE_BASE or "https://hianime.to").rstrip("/")
        self.search_path = STREAM_SITE_SEARCH or "/search?keyword="

    def search_url(self, title: str) -> str:
        return f"{self.base}{self.search_path}{quote_plus(title)}"


# ══════════════════════════════════════════════════════════════
#  OPENSUBTITLES — inglizcha .srt subtitle
# ══════════════════════════════════════════════════════════════
class OpenSubtitlesClient:
    """
    OpenSubtitles REST API v1 klienti.
    Oqim: (ixtiyoriy /login) -> /subtitles (qidirish) -> /download (link) -> faylni yuklash.
    """

    def __init__(self):
        self.base = (OPENSUBTITLES_API_URL or "https://api.opensubtitles.com/api/v1").rstrip("/")
        self.api_key = OPENSUBTITLES_API_KEY or ""
        self.app = OPENSUBTITLES_APP or "AnimeUniverseBot v3.2"
        self.username = OPENSUBTITLES_USERNAME or ""
        self.password = OPENSUBTITLES_PASSWORD or ""
        self.session = None
        self._token = None  # /login dan olingan JWT (agar bo'lsa)

    def configured(self) -> bool:
        return bool(self.api_key)

    def has_credentials(self) -> bool:
        return bool(self.username and self.password)

    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=25)
            )
        return self.session

    def _headers(self, json_body: bool = False, token: str | None = None) -> dict:
        h = {
            "Api-Key": self.api_key,
            "User-Agent": self.app,
            "Accept": "application/json",
        }
        if json_body:
            h["Content-Type"] = "application/json"
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    # ── ichki yordamchilar (sof mantiq — test qilinadi) ──
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

    async def _login(self) -> str | None:
        """Ixtiyoriy: login qilib JWT token oladi (yuklab olish limitini oshiradi)."""
        if self._token:
            return self._token
        if not self.has_credentials():
            return None
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base}/login",
                json={"username": self.username, "password": self.password},
                headers=self._headers(json_body=True),
            ) as r:
                if r.status == 200:
                    data = await r.json()
                    self._token = data.get("token")
                    if self._token:
                        logger.info("OpenSubtitles: login muvaffaqiyatli")
                    return self._token
                logger.warning(f"OpenSubtitles login muvaffaqiyatsiz: status {r.status}")
        except Exception as e:
            logger.warning(f"OpenSubtitles login xato: {e}")
        return None

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

            # 0) Ixtiyoriy login (token kerak bo'lsa)
            token = await self._login()

            # 1) Qidirish
            params = {"query": query, "languages": language}
            if season is not None:
                params["season_number"] = season
            if episode is not None:
                params["episode_number"] = episode
            async with session.get(f"{self.base}/subtitles",
                                   params=params, headers=self._headers(token=token)) as r:
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
                                    headers=self._headers(json_body=True, token=token)) as r:
                dl_json = await r.json() if r.content_type == "application/json" else {}
                if r.status == 406 or (r.status == 200 and not dl_json.get("link")):
                    # 406 odatda kunlik limit tugaganda qaytadi
                    msg = dl_json.get("message") or \
                        "Kunlik yuklab olish limiti tugagan bo'lishi mumkin."
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
