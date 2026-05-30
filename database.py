"""
🗄️ SQLite Database — v3.0
Yangi jadvallar: qidiruv tarixi, janr statistika, foydalanuvchi profili
"""

import sqlite3
import logging
from datetime import datetime, date
from config import DATABASE_NAME

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.db_name = DATABASE_NAME
        self._create_tables()

    def _connect(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _create_tables(self):
        with self._connect() as conn:
            conn.executescript("""
                -- Foydalanuvchilar
                CREATE TABLE IF NOT EXISTS users (
                    id          INTEGER PRIMARY KEY,
                    username    TEXT,
                    first_name  TEXT,
                    joined_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active DATE DEFAULT (date('now')),
                    is_blocked  INTEGER DEFAULT 0,
                    total_searches INTEGER DEFAULT 0,
                    language    TEXT DEFAULT 'uz'
                );

                -- Sevimlilar
                CREATE TABLE IF NOT EXISTS favorites (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    anime_id    INTEGER NOT NULL,
                    title       TEXT NOT NULL,
                    added_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, anime_id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                -- Obunalar
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    day         TEXT NOT NULL,
                    UNIQUE(user_id, day),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                -- Qidiruv tarixi
                CREATE TABLE IF NOT EXISTS search_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    query       TEXT NOT NULL,
                    results_count INTEGER DEFAULT 0,
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Janr statistika (qaysi janrlar ko'p qidirilgan)
                CREATE TABLE IF NOT EXISTS genre_stats (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    genre       TEXT NOT NULL,
                    count       INTEGER DEFAULT 1,
                    last_used   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, genre)
                );

                -- Ko'rilgan animelar
                CREATE TABLE IF NOT EXISTS watched (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    anime_id    INTEGER NOT NULL,
                    title       TEXT NOT NULL,
                    added_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, anime_id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                -- Bot statistika logi
                CREATE TABLE IF NOT EXISTS action_log (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER,
                    action      TEXT NOT NULL,
                    detail      TEXT,
                    at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        logger.info("✅ Database jadvallar tayyor (v3.0)")

    # ══════════════════════════════════════════
    #           FOYDALANUVCHILAR
    # ══════════════════════════════════════════

    def add_user(self, user_id: int, username: str, first_name: str):
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO users (id, username, first_name)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_active = date('now')
            """, (user_id, username, first_name))

    def get_all_users(self) -> list:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id FROM users WHERE is_blocked = 0"
            ).fetchall()
            return [row["id"] for row in rows]

    def get_user(self, user_id: int) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            return dict(row) if row else None

    def block_user(self, user_id: int):
        with self._connect() as conn:
            conn.execute("UPDATE users SET is_blocked = 1 WHERE id = ?", (user_id,))

    # ══════════════════════════════════════════
    #           SEVIMLILAR
    # ══════════════════════════════════════════

    def add_favorite(self, user_id: int, anime_id: int, title: str):
        with self._connect() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO favorites (user_id, anime_id, title)
                VALUES (?, ?, ?)
            """, (user_id, anime_id, title))

    def remove_favorite(self, user_id: int, anime_id: int):
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM favorites WHERE user_id = ? AND anime_id = ?",
                (user_id, anime_id)
            )

    def get_favorites(self, user_id: int) -> list:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT anime_id, title FROM favorites
                WHERE user_id = ?
                ORDER BY added_at DESC
            """, (user_id,)).fetchall()
            return [(row["anime_id"], row["title"]) for row in rows]

    def is_favorite(self, user_id: int, anime_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute("""
                SELECT 1 FROM favorites WHERE user_id = ? AND anime_id = ?
            """, (user_id, anime_id)).fetchone()
            return row is not None

    def get_favorites_count(self, user_id: int) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as c FROM favorites WHERE user_id = ?", (user_id,)
            ).fetchone()
            return row["c"] if row else 0

    # ══════════════════════════════════════════
    #           KO'RILGANLAR
    # ══════════════════════════════════════════

    def add_watched(self, user_id: int, anime_id: int, title: str):
        with self._connect() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO watched (user_id, anime_id, title)
                VALUES (?, ?, ?)
            """, (user_id, anime_id, title))

    def remove_watched(self, user_id: int, anime_id: int):
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM watched WHERE user_id = ? AND anime_id = ?",
                (user_id, anime_id)
            )

    def get_watched(self, user_id: int) -> list:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT anime_id, title FROM watched
                WHERE user_id = ? ORDER BY added_at DESC
            """, (user_id,)).fetchall()
            return [(row["anime_id"], row["title"]) for row in rows]

    def is_watched(self, user_id: int, anime_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM watched WHERE user_id = ? AND anime_id = ?",
                (user_id, anime_id)
            ).fetchone()
            return row is not None

    # ══════════════════════════════════════════
    #           OBUNALAR
    # ══════════════════════════════════════════

    def toggle_subscription(self, user_id: int, day: str) -> bool:
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT 1 FROM subscriptions WHERE user_id = ? AND day = ?",
                (user_id, day)
            ).fetchone()
            if existing:
                conn.execute(
                    "DELETE FROM subscriptions WHERE user_id = ? AND day = ?",
                    (user_id, day)
                )
                return False
            else:
                conn.execute(
                    "INSERT INTO subscriptions (user_id, day) VALUES (?, ?)",
                    (user_id, day)
                )
                return True

    def get_day_subscribers(self, day: str) -> list:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT s.user_id FROM subscriptions s
                JOIN users u ON u.id = s.user_id
                WHERE s.day = ? AND u.is_blocked = 0
            """, (day,)).fetchall()
            return [row["user_id"] for row in rows]

    def get_user_subscriptions(self, user_id: int) -> list:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT day FROM subscriptions WHERE user_id = ?", (user_id,)
            ).fetchall()
            return [row["day"] for row in rows]

    # ══════════════════════════════════════════
    #           QIDIRUV TARIXI
    # ══════════════════════════════════════════

    def save_search(self, user_id: int, query: str, results_count: int = 0):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO search_history (user_id, query, results_count) VALUES (?, ?, ?)",
                (user_id, query, results_count)
            )
            conn.execute(
                "UPDATE users SET total_searches = total_searches + 1 WHERE id = ?",
                (user_id,)
            )

    def get_search_history(self, user_id: int, limit: int = 10) -> list:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT DISTINCT query FROM search_history
                WHERE user_id = ?
                ORDER BY searched_at DESC
                LIMIT ?
            """, (user_id, limit)).fetchall()
            return [row["query"] for row in rows]

    def get_popular_searches(self, limit: int = 10) -> list:
        """Eng ko'p qidirgan so'zlar"""
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT query, COUNT(*) as cnt
                FROM search_history
                GROUP BY LOWER(query)
                ORDER BY cnt DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [(row["query"], row["cnt"]) for row in rows]

    # ══════════════════════════════════════════
    #           JANR STATISTIKA
    # ══════════════════════════════════════════

    def track_genre(self, user_id: int, genre: str):
        """Foydalanuvchining janr qidiruvini kuzatish"""
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO genre_stats (user_id, genre, count, last_used)
                VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, genre) DO UPDATE SET
                    count = count + 1,
                    last_used = CURRENT_TIMESTAMP
            """, (user_id, genre))

    def get_user_top_genres(self, user_id: int, limit: int = 5) -> list:
        """Foydalanuvchining sevimli janrlari"""
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT genre, count FROM genre_stats
                WHERE user_id = ?
                ORDER BY count DESC
                LIMIT ?
            """, (user_id, limit)).fetchall()
            return [(row["genre"], row["count"]) for row in rows]

    def get_global_top_genres(self, limit: int = 10) -> list:
        """Global eng mashhur janrlar"""
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT genre, SUM(count) as total
                FROM genre_stats
                GROUP BY genre
                ORDER BY total DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [(row["genre"], row["total"]) for row in rows]

    # ══════════════════════════════════════════
    #           STATISTIKA
    # ══════════════════════════════════════════

    def get_stats(self) -> dict:
        with self._connect() as conn:
            users = conn.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 0").fetchone()[0]
            favorites = conn.execute("SELECT COUNT(*) FROM favorites").fetchone()[0]
            subscriptions = conn.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0]
            today_active = conn.execute(
                "SELECT COUNT(*) FROM users WHERE last_active = date('now')"
            ).fetchone()[0]
            total_searches = conn.execute("SELECT COUNT(*) FROM search_history").fetchone()[0]
            watched_count = conn.execute("SELECT COUNT(*) FROM watched").fetchone()[0]

        return {
            "users": users,
            "favorites": favorites,
            "subscriptions": subscriptions,
            "today_active": today_active,
            "total_searches": total_searches,
            "watched": watched_count,
        }

    def log_action(self, user_id: int, action: str, detail: str = None):
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO action_log (user_id, action, detail) VALUES (?, ?, ?)",
                    (user_id, action, detail)
                )
        except Exception:
            pass
