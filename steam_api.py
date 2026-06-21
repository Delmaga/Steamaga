"""
Tout ce qui parle à Steam (et SteamSpy) vit ici :
- récupération des jeux récemment sortis
- récupération des jeux à venir
- détails d'un jeu (prix, catégories, démo...)
- tags communautaires (SteamSpy)
- fonction de correspondance jeu <-> filtre
"""

import re
import asyncio
import aiohttp
from bs4 import BeautifulSoup

from config import STEAM_CC, STEAM_LANG, STEAM_TAGS, STEAM_CATEGORIES

SEARCH_URL = "https://store.steampowered.com/search/results/"
APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"
STEAMSPY_URL = "https://steamspy.com/api.php"
REVIEWS_URL = "https://store.steampowered.com/appreviews/{appid}"


async def _fetch_json(session: aiohttp.ClientSession, url: str, params: dict):
    try:
        async with session.get(url, params=params, timeout=20) as resp:
            if resp.status != 200:
                return None
            return await resp.json(content_type=None)
    except Exception:
        return None


async def _search(session: aiohttp.ClientSession, extra_params: dict, count: int = 50):
    """Interroge la recherche Steam et parse le HTML renvoyé pour extraire les appid."""
    params = {
        "query": "",
        "start": 0,
        "count": count,
        "sort_by": "Released_DESC",
        "category1": 998,  # "Jeux" uniquement (pas DLC/logiciels)
        "cc": STEAM_CC,
        "l": STEAM_LANG,
        "infinite": 1,
    }
    params.update(extra_params)

    data = await _fetch_json(session, SEARCH_URL, params)
    if not data or "results_html" not in data:
        return []

    soup = BeautifulSoup(data["results_html"], "html.parser")
    appids = []
    for row in soup.select("a.search_result_row"):
        appid = row.get("data-ds-appid")
        if appid and appid.isdigit():
            appids.append(int(appid))
    return appids


async def get_new_release_appids(session: aiohttp.ClientSession, count: int = 50):
    """Jeux récemment sortis (déjà disponibles à l'achat)."""
    return await _search(session, {}, count=count)


async def get_upcoming_appids(session: aiohttp.ClientSession, count: int = 50):
    """Jeux à venir (pas encore sortis)."""
    return await _search(session, {"filter": "comingsoon"}, count=count)


async def get_app_details(session: aiohttp.ClientSession, appid: int):
    """Détails complets d'un jeu : nom, prix, image, catégories, démo, date de sortie."""
    params = {"appids": appid, "cc": STEAM_CC, "l": STEAM_LANG}
    data = await _fetch_json(session, APPDETAILS_URL, params)
    if not data:
        return None
    entry = data.get(str(appid))
    if not entry or not entry.get("success"):
        return None
    d = entry["data"]
    if d.get("type") != "game":
        return None

    price_overview = d.get("price_overview")
    is_free = d.get("is_free", False)
    if is_free:
        price_eur = 0.0
    elif price_overview:
        price_eur = price_overview.get("final", 0) / 100
    else:
        price_eur = None  # prix inconnu (souvent pas encore annoncé)

    categories = [c["id"] for c in d.get("categories", [])] if d.get("categories") else []
    has_demo = bool(d.get("demos"))
    metacritic = d.get("metacritic", {}).get("score") if d.get("metacritic") else None

    return {
        "appid": appid,
        "name": d.get("name", "Inconnu"),
        "url": f"https://store.steampowered.com/app/{appid}/",
        "header_image": d.get("header_image"),
        "short_description": d.get("short_description", ""),
        "price_eur": price_eur,
        "is_free": is_free,
        "categories": categories,
        "has_demo": has_demo,
        "metacritic": metacritic,
        "release_date": d.get("release_date", {}).get("date", "Inconnue"),
        "coming_soon": d.get("release_date", {}).get("coming_soon", False),
        "developers": d.get("developers", []),
        "genres": [g["description"] for g in d.get("genres", [])] if d.get("genres") else [],
    }


async def get_steamspy_tags(session: aiohttp.ClientSession, appid: int):
    """
    Tags communautaires (ex: Horror, Adventure...) via SteamSpy, triés par nombre
    de votes réel (du plus voté au moins voté). SteamSpy renvoie les tags avec leur
    nombre de votes, mais ne garantit PAS que l'ordre du JSON corresponde à ce
    classement : on retrie nous-mêmes pour être sûr.
    """
    params = {"request": "appdetails", "appid": appid}
    data = await _fetch_json(session, STEAMSPY_URL, params)
    if not data or "tags" not in data or not isinstance(data["tags"], dict):
        return [], {}
    # data["tags"] est un dict {nom_du_tag: nombre_de_votes}
    raw = {str(t).lower(): int(v) for t, v in data["tags"].items() if isinstance(v, (int, float))}
    ordered_names = [t for t, _ in sorted(raw.items(), key=lambda kv: kv[1], reverse=True)]
    return ordered_names, raw


async def enrich_game(session: aiohttp.ClientSession, appid: int):
    """Récupère détails + tags communautaires (triés par votes) + note Steam en parallèle."""
    details, (tags_ordered, tags_votes), reviews = await asyncio.gather(
        get_app_details(session, appid),
        get_steamspy_tags(session, appid),
        get_review_summary(session, appid),
    )
    if not details:
        return None
    details["community_tags"] = tags_ordered      # noms triés du + voté au - voté
    details["community_tags_votes"] = tags_votes  # {nom: nombre de votes}
    details["reviews"] = reviews
    return details


async def get_review_summary(session: aiohttp.ClientSession, appid: int):
    """Note des joueurs Steam (% positif, description type 'Très positive')."""
    params = {
        "json": 1,
        "language": "all",
        "purchase_type": "all",
        "num_per_page": 0,
    }
    url = REVIEWS_URL.format(appid=appid)
    data = await _fetch_json(session, url, params)
    if not data or "query_summary" not in data:
        return None
    qs = data["query_summary"]
    total = qs.get("total_reviews", 0)
    if total == 0:
        return None
    positive = qs.get("total_positive", 0)
    percent = round((positive / total) * 100) if total else None
    return {
        "description": qs.get("review_score_desc", ""),  # ex: "Très positive"
        "percent_positive": percent,
        "total_reviews": total,
    }


async def get_appids_by_category(session: aiohttp.ClientSession, category_key: str, max_appids: int = 120):
    """Liste des appid (jeux déjà sortis) pour une catégorie/tag donné, via SteamSpy."""
    info = STEAM_CATEGORIES.get(category_key)
    if not info:
        return []
    params = {"request": "tag", "tag": info["steamspy_tag"]}
    data = await _fetch_json(session, STEAMSPY_URL, params)
    if not data or not isinstance(data, dict):
        return []
    appids = [int(appid) for appid in list(data.keys())[:max_appids]]
    return appids


# ----------------------------------------------------------------------
# Logique de filtrage : est-ce que ce jeu correspond à ce filtre ?
# ----------------------------------------------------------------------

def game_has_category(game: dict, category_key: str, top_n: int = 8, min_vote_ratio: float = 0.12) -> bool:
    """
    Vérifie si un jeu correspond vraiment à une catégorie donnée (horreur, casse-tête...).
    Le tag doit à la fois :
      - être parmi les `top_n` tags les plus votés du jeu, ET
      - avoir au moins `min_vote_ratio` (12% par défaut) des votes du tag n°1
    Ça élimine les jeux où un tag est présent de façon anecdotique (ex: quelques
    votes "Horror" sur un jeu Battle Royale comme Apex Legends ou Fall Guys), qui
    ne devraient clairement pas apparaître comme "jeux d'horreur".
    """
    info = STEAM_CATEGORIES.get(category_key)
    if not info:
        return False

    votes = game.get("community_tags_votes")
    if votes:
        ordered = sorted(votes.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
        if not ordered:
            return False
        max_votes = ordered[0][1]
        if max_votes <= 0:
            return False
        for tag, v in ordered:
            if info["keyword"] in tag and v >= max_votes * min_vote_ratio:
                return True
        return False

    # Repli si jamais on n'a pas les votes (ne devrait pas arriver) : ordre simple
    community_tags = game.get("community_tags", [])[:top_n]
    return any(info["keyword"] in tag for tag in community_tags)


def game_matches_filter(game: dict, tags: list, categories: list,
                         price_min: int, price_max: int, demo_mode: str,
                         categories_all: bool = False) -> bool:
    # --- Tag (mode de jeu : solo, multijoueur, coop...) ---
    if tags:
        wanted_ids = {STEAM_TAGS[t]["id"] for t in tags if t in STEAM_TAGS}
        if not wanted_ids.intersection(game["categories"]):
            return False

    # --- Catégorie (thème : horreur, aventure...) ---
    if categories:
        matches = [game_has_category(game, c) for c in categories]
        if categories_all:
            if not all(matches):
                return False
        else:
            if not any(matches):
                return False

    # --- Prix ---
    price = game.get("price_eur")
    if price is None:
        # prix inconnu : on l'exclut des filtres payants stricts, mais on l'accepte
        # si le filtre est totalement ouvert (0 -> 99999)
        if not (price_min == 0 and price_max >= 99999):
            return False
    else:
        if price < price_min or price > price_max:
            return False

    # --- Démo ---
    if demo_mode == "avec_demo" and not game.get("has_demo"):
        return False
    if demo_mode == "sans_demo" and game.get("has_demo"):
        return False

    return True
