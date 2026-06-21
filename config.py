"""
Configuration centrale du bot : mapping des tags Steam, des tags communautaires
SteamSpy (catégories), des tranches de prix, et des présets pour /prefiltre.
"""

# -------------------------------------------------------------------------
# TAGS (mode de jeu) -> catégories officielles Steam (appdetails -> categories)
# id officiel Steam : description affichée dans le bot
# -------------------------------------------------------------------------
STEAM_TAGS = {
    "solo": {"id": 2, "label": "Solo"},
    "multijoueur": {"id": 1, "label": "Multijoueur"},
    "coop": {"id": 9, "label": "Coop"},
    "coop_en_ligne": {"id": 38, "label": "Coop en ligne"},
    "pvp_en_ligne": {"id": 36, "label": "PvP en ligne"},
}

# -------------------------------------------------------------------------
# CATEGORIES (thème/genre) -> tags communautaires SteamSpy
# clé interne : (label affiché, mot-clé à chercher dans les tags SteamSpy)
# -------------------------------------------------------------------------
STEAM_CATEGORIES = {
    "horreur": {"label": "Horreur", "keyword": "horror", "steamspy_tag": "Horror"},
    "aventure": {"label": "Aventure", "keyword": "adventure", "steamspy_tag": "Adventure"},
    "action": {"label": "Action", "keyword": "action", "steamspy_tag": "Action"},
    "indie": {"label": "Indé", "keyword": "indie", "steamspy_tag": "Indie"},
    "rpg": {"label": "RPG", "keyword": "rpg", "steamspy_tag": "RPG"},
    "strategie": {"label": "Stratégie", "keyword": "strategy", "steamspy_tag": "Strategy"},
    "simulation": {"label": "Simulation", "keyword": "simulation", "steamspy_tag": "Simulation"},
    "casual": {"label": "Casual", "keyword": "casual", "steamspy_tag": "Casual"},
    "puzzle": {"label": "Casse-tête", "keyword": "puzzle", "steamspy_tag": "Puzzle"},
    "course": {"label": "Course", "keyword": "racing", "steamspy_tag": "Racing"},
    "sport": {"label": "Sport", "keyword": "sports", "steamspy_tag": "Sports"},
    "survie": {"label": "Survie", "keyword": "survival", "steamspy_tag": "Survival"},
    "monde_ouvert": {"label": "Monde ouvert", "keyword": "open world", "steamspy_tag": "Open World"},
    "fun": {"label": "Fun / Drôle", "keyword": "funny", "steamspy_tag": "Funny"},
    "crazy": {"label": "Crazy / Fou", "keyword": "psychological", "steamspy_tag": "Psychological Horror"},
}

# -------------------------------------------------------------------------
# PRIX
# -------------------------------------------------------------------------
PRICE_RANGES = {
    "gratuit": {"label": "Gratuit", "min": 0, "max": 0},
    "0_10": {"label": "Entre 0€ et 10€", "min": 0, "max": 10},
    "10_25": {"label": "Entre 10€ et 25€", "min": 10, "max": 25},
    "25_plus": {"label": "25€ et plus", "min": 25, "max": 99999},
}

# -------------------------------------------------------------------------
# STYLE (démo)
# -------------------------------------------------------------------------
DEMO_MODES = {
    "avec_demo": "Avec démo uniquement",
    "sans_demo": "Sans démo",
    "peu_importe": "Peu importe",
}

# -------------------------------------------------------------------------
# PRESETS pour /prefiltre : des packs tout prêts, non personnalisables.
# Chaque preset combine tag + catégorie + prix + démo.
# -------------------------------------------------------------------------
PRESETS = {
    "horreur_solo": {
        "label": "🔪 Horreur Solo",
        "tags": ["solo"],
        "categories": ["horreur"],
        "price_min": 0,
        "price_max": 99999,
        "demo_mode": "peu_importe",
    },
    "multi_gratuit": {
        "label": "🆓 Multijoueur Gratuit",
        "tags": ["multijoueur", "coop_en_ligne"],
        "categories": [],
        "price_min": 0,
        "price_max": 0,
        "demo_mode": "peu_importe",
    },
    "coop_demo": {
        "label": "🎮 Coop en ligne + Démo",
        "tags": ["coop_en_ligne", "coop"],
        "categories": [],
        "price_min": 0,
        "price_max": 99999,
        "demo_mode": "avec_demo",
    },
    "aventure_petits_prix": {
        "label": "🗺️ Aventure entre 1€ et 25€",
        "tags": [],
        "categories": ["aventure"],
        "price_min": 1,
        "price_max": 25,
        "demo_mode": "peu_importe",
    },
    "fun_crazy": {
        "label": "🤪 Fun & Crazy",
        "tags": [],
        "categories": ["fun", "crazy"],
        "price_min": 0,
        "price_max": 99999,
        "demo_mode": "peu_importe",
    },
    "rpg_solo_payant": {
        "label": "⚔️ RPG Solo (payant)",
        "tags": ["solo"],
        "categories": ["rpg"],
        "price_min": 1,
        "price_max": 99999,
        "demo_mode": "peu_importe",
    },
    "horreur_drole": {
        "label": "🤡 Horreur mais drôle",
        "tags": [],
        "categories": ["horreur", "fun"],
        "categories_all": True,  # le jeu doit être horreur ET drôle, pas l'un ou l'autre
        "price_min": 0,
        "price_max": 99999,
        "demo_mode": "peu_importe",
    },
}

# -------------------------------------------------------------------------
# Divers
# -------------------------------------------------------------------------
STEAM_CC = "fr"        # code pays pour les prix
STEAM_LANG = "french"  # langue d'affichage steam
CHECK_INTERVAL_MINUTES = 10
EMBED_COLOR_NEW = 0x1B2838       # bleu steam
EMBED_COLOR_UPCOMING = 0x66C0F4  # bleu clair steam
DB_PATH = "steam_bot.db"
