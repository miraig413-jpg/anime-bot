"""
🌐 AniList GraphQL API — v3.0
Yangi: janr qidirish, filtrlar, tavsiyalar, random anime
"""

import aiohttp
import logging
from config import ANILIST_API_URL

logger = logging.getLogger(__name__)

# Barcha kerakli maydonlar uchun fragment
MEDIA_FIELDS = """
    id
    title { romaji english native }
    description(asHtml: false)
    genres
    averageScore
    popularity
    favourites
    episodes
    duration
    status
    season
    seasonYear
    format
    source
    coverImage { large extraLarge }
    bannerImage
    nextAiringEpisode { episode timeUntilAiring }
    studios { nodes { name isAnimationStudio } }
    characters(sort: [ROLE], perPage: 5) { nodes { name { full } } }
    recommendations(sort: [RATING_DESC], perPage: 3) {
        nodes { mediaRecommendation { id title { romaji } coverImage { medium } } }
    }
    tags { name rank }
    trailer { site id }
    siteUrl
"""

MEDIA_BRIEF = """
    id
    title { romaji english }
    genres
    averageScore
    popularity
    episodes
    status
    season
    seasonYear
    format
    coverImage { large }
    nextAiringEpisode { episode timeUntilAiring }
"""


class AnimeAPI:
    def __init__(self):
        self.url = ANILIST_API_URL
        self.session = None

    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=20)
            )
        return self.session

    async def _query(self, query: str, variables: dict = None):
        session = await self._get_session()
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        try:
            async with session.post(
                self.url,
                json=payload,
                headers={"Content-Type": "application/json", "Accept": "application/json"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "errors" in data:
                        logger.warning(f"GraphQL errors: {data['errors']}")
                    return data.get("data")
                elif resp.status == 429:
                    logger.warning("Rate limited by AniList API")
                    return None
                else:
                    logger.error(f"API Error: {resp.status}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Network error: {e}")
            return None
        except Exception as e:
            logger.error(f"Query error: {e}")
            return None

    # ══════════════════════════════════════════
    #         JADVAL
    # ══════════════════════════════════════════

    async def get_schedule_by_day(self, day: str) -> list:
        query = f"""
        query {{
            Page(page: 1, perPage: 30) {{
                airingSchedules(
                    airingAt_greater: 0
                    notYetAired: false
                    sort: [EPISODE_DESC]
                ) {{
                    episode
                    airingAt
                    timeUntilAiring
                    media {{
                        {MEDIA_BRIEF}
                        studios {{ nodes {{ name }} }}
                    }}
                }}
            }}
        }}
        """
        day_to_num = {
            "MONDAY": 1, "TUESDAY": 2, "WEDNESDAY": 3, "THURSDAY": 4,
            "FRIDAY": 5, "SATURDAY": 6, "SUNDAY": 7
        }
        result = await self._query(query)
        if not result:
            return await self._get_seasonal_anime()

        schedules = result.get("Page", {}).get("airingSchedules", [])
        import datetime
        day_num = day_to_num.get(day, 1)
        filtered, seen = [], set()
        for item in schedules:
            media = item.get("media")
            if not media:
                continue
            mid = media.get("id")
            if mid in seen:
                continue
            airing_at = item.get("airingAt", 0)
            wd = datetime.datetime.fromtimestamp(airing_at).isoweekday()
            if wd == day_num:
                filtered.append(media)
                seen.add(mid)

        return filtered[:20] if filtered else await self._get_seasonal_anime()

    async def _get_seasonal_anime(self) -> list:
        query = f"""
        query {{
            Page(page: 1, perPage: 20) {{
                media(type: ANIME status: RELEASING sort: [POPULARITY_DESC]) {{
                    {MEDIA_BRIEF}
                    studios {{ nodes {{ name }} }}
                }}
            }}
        }}
        """
        result = await self._query(query)
        if result:
            return result.get("Page", {}).get("media", [])
        return []

    # ══════════════════════════════════════════
    #         TREND & TOP
    # ══════════════════════════════════════════

    async def get_trending(self, page: int = 1) -> list:
        query = f"""
        query ($page: Int) {{
            Page(page: $page, perPage: 10) {{
                media(type: ANIME sort: [TRENDING_DESC] status_in: [RELEASING, FINISHED]) {{
                    {MEDIA_BRIEF}
                    trending
                }}
            }}
        }}
        """
        result = await self._query(query, {"page": page})
        return result.get("Page", {}).get("media", []) if result else []

    async def get_top_anime(self, page: int = 1) -> list:
        query = f"""
        query ($page: Int) {{
            Page(page: $page, perPage: 10) {{
                media(type: ANIME sort: [SCORE_DESC] averageScore_greater: 70) {{
                    {MEDIA_BRIEF}
                }}
            }}
        }}
        """
        result = await self._query(query, {"page": page})
        return result.get("Page", {}).get("media", []) if result else []

    async def get_popular_anime(self, page: int = 1) -> list:
        """Eng ommabop animelar"""
        query = f"""
        query ($page: Int) {{
            Page(page: $page, perPage: 10) {{
                media(type: ANIME sort: [POPULARITY_DESC]) {{
                    {MEDIA_BRIEF}
                    popularity
                }}
            }}
        }}
        """
        result = await self._query(query, {"page": page})
        return result.get("Page", {}).get("media", []) if result else []

    # ══════════════════════════════════════════
    #         YANGI: JANR BO'YICHA QIDIRISH
    # ══════════════════════════════════════════

    async def get_by_genre(self, genre: str, page: int = 1, sort: str = "SCORE_DESC") -> list:
        """Janr bo'yicha anime olish"""
        query = f"""
        query ($genre: String, $page: Int) {{
            Page(page: $page, perPage: 10) {{
                media(
                    type: ANIME
                    genre: $genre
                    sort: [{sort}]
                    averageScore_greater: 50
                ) {{
                    {MEDIA_BRIEF}
                }}
            }}
        }}
        """
        result = await self._query(query, {"genre": genre, "page": page})
        return result.get("Page", {}).get("media", []) if result else []

    async def get_by_genres_multi(self, genres: list, page: int = 1) -> list:
        """Bir nechta janr bo'yicha (genres_in)"""
        query = f"""
        query ($genres: [String], $page: Int) {{
            Page(page: $page, perPage: 10) {{
                media(
                    type: ANIME
                    genre_in: $genres
                    sort: [SCORE_DESC]
                    averageScore_greater: 60
                ) {{
                    {MEDIA_BRIEF}
                }}
            }}
        }}
        """
        result = await self._query(query, {"genres": genres, "page": page})
        return result.get("Page", {}).get("media", []) if result else []

    # ══════════════════════════════════════════
    #         YANGI: YILGA KO'RA
    # ══════════════════════════════════════════

    async def get_by_year(self, year: int, page: int = 1) -> list:
        """Yilga ko'ra eng yaxshi animelar"""
        query = f"""
        query ($year: Int, $page: Int) {{
            Page(page: $page, perPage: 10) {{
                media(
                    type: ANIME
                    seasonYear: $year
                    sort: [SCORE_DESC]
                    averageScore_greater: 60
                ) {{
                    {MEDIA_BRIEF}
                }}
            }}
        }}
        """
        result = await self._query(query, {"year": year, "page": page})
        return result.get("Page", {}).get("media", []) if result else []

    # ══════════════════════════════════════════
    #         YANGI: RANDOM ANIME
    # ══════════════════════════════════════════

    async def get_random_anime(self) -> dict:
        """Tasodifiy yuqori baholanган anime"""
        import random
        page = random.randint(1, 15)
        query = f"""
        query ($page: Int) {{
            Page(page: $page, perPage: 10) {{
                media(
                    type: ANIME
                    sort: [SCORE_DESC]
                    averageScore_greater: 75
                    status: FINISHED
                ) {{
                    {MEDIA_BRIEF}
                }}
            }}
        }}
        """
        result = await self._query(query, {"page": page})
        if result:
            items = result.get("Page", {}).get("media", [])
            if items:
                return random.choice(items)
        return None

    # ══════════════════════════════════════════
    #         YANGI: MAVSUM
    # ══════════════════════════════════════════

    async def get_seasonal(self, season: str, year: int, page: int = 1) -> list:
        """Mavsum bo'yicha animelar"""
        query = f"""
        query ($season: MediaSeason, $year: Int, $page: Int) {{
            Page(page: $page, perPage: 10) {{
                media(
                    type: ANIME
                    season: $season
                    seasonYear: $year
                    sort: [POPULARITY_DESC]
                ) {{
                    {MEDIA_BRIEF}
                }}
            }}
        }}
        """
        result = await self._query(query, {"season": season, "year": year, "page": page})
        return result.get("Page", {}).get("media", []) if result else []

    # ══════════════════════════════════════════
    #         YANGI: TAVSIYALAR
    # ══════════════════════════════════════════

    async def get_recommendations_for_anime(self, anime_id: int) -> list:
        """Animeга asosланган tavsiyalar"""
        query = """
        query ($id: Int) {
            Media(id: $id, type: ANIME) {
                recommendations(sort: [RATING_DESC], perPage: 6) {
                    nodes {
                        mediaRecommendation {
                            id
                            title { romaji english }
                            genres
                            averageScore
                            episodes
                            status
                            seasonYear
                            coverImage { large }
                        }
                    }
                }
            }
        }
        """
        result = await self._query(query, {"id": anime_id})
        if result and result.get("Media"):
            nodes = result["Media"].get("recommendations", {}).get("nodes", [])
            return [n["mediaRecommendation"] for n in nodes if n.get("mediaRecommendation")]
        return []

    # ══════════════════════════════════════════
    #         YANGI: FORMAT BO'YICHA
    # ══════════════════════════════════════════

    async def get_by_format(self, fmt: str, page: int = 1) -> list:
        """Format bo'yicha (TV, MOVIE, OVA va h.k.)"""
        query = f"""
        query ($format: MediaFormat, $page: Int) {{
            Page(page: $page, perPage: 10) {{
                media(
                    type: ANIME
                    format: $format
                    sort: [SCORE_DESC]
                    averageScore_greater: 70
                ) {{
                    {MEDIA_BRIEF}
                }}
            }}
        }}
        """
        result = await self._query(query, {"format": fmt, "page": page})
        return result.get("Page", {}).get("media", []) if result else []

    # ══════════════════════════════════════════
    #         QIDIRISH
    # ══════════════════════════════════════════

    async def search_anime(self, search_query: str, page: int = 1) -> list:
        query = f"""
        query ($search: String, $page: Int) {{
            Page(page: $page, perPage: 10) {{
                media(type: ANIME search: $search sort: [SEARCH_MATCH]) {{
                    {MEDIA_BRIEF}
                }}
            }}
        }}
        """
        result = await self._query(query, {"search": search_query, "page": page})
        return result.get("Page", {}).get("media", []) if result else []

    # ══════════════════════════════════════════
    #         TAFSILOT
    # ══════════════════════════════════════════

    async def get_anime_details(self, anime_id: int) -> dict:
        query = f"""
        query ($id: Int) {{
            Media(id: $id, type: ANIME) {{
                {MEDIA_FIELDS}
            }}
        }}
        """
        result = await self._query(query, {"id": anime_id})
        return result.get("Media") if result else None

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
