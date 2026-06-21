"""
Couche d'accès aux données (SQLite). Toutes les sauvegardes du bot passent par ici :
- salons "tous les jeux" / "à venir"
- abonnements aux présets (/prefiltre)
- filtres personnalisés par utilisateur (/filtre)
- historique des jeux déjà publiés (anti-doublon)
"""

import json
import sqlite3
from contextlib import closing

from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(get_conn()) as conn, conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS feed_channels (
                guild_id INTEGER NOT NULL,
                kind TEXT NOT NULL,           -- 'new' ou 'upcoming'
                channel_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, kind)
            );

            CREATE TABLE IF NOT EXISTS preset_subscriptions (
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                preset_key TEXT NOT NULL,
                PRIMARY KEY (guild_id, channel_id, preset_key)
            );

            CREATE TABLE IF NOT EXISTS user_filters (
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                tags TEXT NOT NULL DEFAULT '[]',
                categories TEXT NOT NULL DEFAULT '[]',
                price_min INTEGER NOT NULL DEFAULT 0,
                price_max INTEGER NOT NULL DEFAULT 99999,
                demo_mode TEXT NOT NULL DEFAULT 'peu_importe',
                PRIMARY KEY (user_id, guild_id)
            );

            CREATE TABLE IF NOT EXISTS posted_games (
                appid INTEGER NOT NULL,
                context TEXT NOT NULL,        -- 'new' ou 'upcoming'
                PRIMARY KEY (appid, context)
            );
            """
        )


# ----------------------------- feed_channels -----------------------------

def set_feed_channel(guild_id: int, kind: str, channel_id: int):
    with closing(get_conn()) as conn, conn:
        conn.execute(
            "INSERT INTO feed_channels (guild_id, kind, channel_id) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, kind) DO UPDATE SET channel_id=excluded.channel_id",
            (guild_id, kind, channel_id),
        )


def get_feed_channels(kind: str):
    with closing(get_conn()) as conn:
        rows = conn.execute(
            "SELECT guild_id, channel_id FROM feed_channels WHERE kind=?", (kind,)
        ).fetchall()
        return [(r["guild_id"], r["channel_id"]) for r in rows]


# -------------------------- preset_subscriptions --------------------------

def add_preset_subscription(guild_id: int, channel_id: int, preset_key: str):
    with closing(get_conn()) as conn, conn:
        conn.execute(
            "INSERT OR IGNORE INTO preset_subscriptions (guild_id, channel_id, preset_key) "
            "VALUES (?, ?, ?)",
            (guild_id, channel_id, preset_key),
        )


def remove_preset_subscription(guild_id: int, channel_id: int, preset_key: str):
    with closing(get_conn()) as conn, conn:
        conn.execute(
            "DELETE FROM preset_subscriptions WHERE guild_id=? AND channel_id=? AND preset_key=?",
            (guild_id, channel_id, preset_key),
        )


def get_preset_subscriptions():
    with closing(get_conn()) as conn:
        rows = conn.execute(
            "SELECT guild_id, channel_id, preset_key FROM preset_subscriptions"
        ).fetchall()
        return [(r["guild_id"], r["channel_id"], r["preset_key"]) for r in rows]


# ----------------------------- user_filters -------------------------------

def save_user_filter(user_id, guild_id, channel_id, tags, categories,
                      price_min, price_max, demo_mode):
    with closing(get_conn()) as conn, conn:
        conn.execute(
            """
            INSERT INTO user_filters
                (user_id, guild_id, channel_id, tags, categories, price_min, price_max, demo_mode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET
                channel_id=excluded.channel_id,
                tags=excluded.tags,
                categories=excluded.categories,
                price_min=excluded.price_min,
                price_max=excluded.price_max,
                demo_mode=excluded.demo_mode
            """,
            (
                user_id, guild_id, channel_id,
                json.dumps(tags), json.dumps(categories),
                price_min, price_max, demo_mode,
            ),
        )


def get_user_filter(user_id, guild_id):
    with closing(get_conn()) as conn:
        row = conn.execute(
            "SELECT * FROM user_filters WHERE user_id=? AND guild_id=?",
            (user_id, guild_id),
        ).fetchone()
        if not row:
            return None
        return {
            "user_id": row["user_id"],
            "guild_id": row["guild_id"],
            "channel_id": row["channel_id"],
            "tags": json.loads(row["tags"]),
            "categories": json.loads(row["categories"]),
            "price_min": row["price_min"],
            "price_max": row["price_max"],
            "demo_mode": row["demo_mode"],
        }


def delete_user_filter(user_id, guild_id):
    with closing(get_conn()) as conn, conn:
        conn.execute(
            "DELETE FROM user_filters WHERE user_id=? AND guild_id=?",
            (user_id, guild_id),
        )


def get_all_user_filters():
    with closing(get_conn()) as conn:
        rows = conn.execute("SELECT * FROM user_filters").fetchall()
        result = []
        for row in rows:
            result.append({
                "user_id": row["user_id"],
                "guild_id": row["guild_id"],
                "channel_id": row["channel_id"],
                "tags": json.loads(row["tags"]),
                "categories": json.loads(row["categories"]),
                "price_min": row["price_min"],
                "price_max": row["price_max"],
                "demo_mode": row["demo_mode"],
            })
        return result


# ----------------------------- posted_games --------------------------------

def is_already_posted(appid: int, context: str) -> bool:
    with closing(get_conn()) as conn:
        row = conn.execute(
            "SELECT 1 FROM posted_games WHERE appid=? AND context=?", (appid, context)
        ).fetchone()
        return row is not None


def mark_posted(appid: int, context: str):
    with closing(get_conn()) as conn, conn:
        conn.execute(
            "INSERT OR IGNORE INTO posted_games (appid, context) VALUES (?, ?)",
            (appid, context),
        )
