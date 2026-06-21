"""Construction des embeds Discord pour l'affichage des jeux."""

import discord
from config import EMBED_COLOR_NEW, EMBED_COLOR_UPCOMING, STEAM_TAGS


def _price_text(game: dict) -> str:
    if game.get("is_free"):
        return "Gratuit"
    if game.get("price_eur") is None:
        return "Prix non annoncé"
    return f"{game['price_eur']:.2f} €"


def _tags_text(game: dict) -> str:
    cats = set(game.get("categories", []))
    labels = [info["label"] for info in STEAM_TAGS.values() if info["id"] in cats]
    return ", ".join(labels) if labels else "—"


def build_game_embed(game: dict, upcoming: bool = False, footer_extra: str = None) -> discord.Embed:
    color = EMBED_COLOR_UPCOMING if upcoming else EMBED_COLOR_NEW
    title_prefix = "🔜 Bientôt disponible" if upcoming else "🆕 Nouveau sur Steam"

    embed = discord.Embed(
        title=game["name"],
        url=game["url"],
        description=game.get("short_description", "")[:300],
        color=color,
    )
    embed.set_author(name=title_prefix)
    if game.get("header_image"):
        embed.set_image(url=game["header_image"])

    embed.add_field(name="💰 Prix", value=_price_text(game), inline=True)
    embed.add_field(name="🎮 Mode de jeu", value=_tags_text(game), inline=True)
    embed.add_field(name="🎭 Genres", value=", ".join(game.get("genres", [])) or "—", inline=True)
    embed.add_field(name="📅 Sortie", value=game.get("release_date", "Inconnue"), inline=True)
    embed.add_field(name="🧪 Démo", value="Oui" if game.get("has_demo") else "Non", inline=True)
    if game.get("developers"):
        embed.add_field(name="🛠️ Développeur", value=", ".join(game["developers"]), inline=True)

    embed.set_footer(text=footer_extra or "Source : Steam Store")
    return embed
