"""Construction des embeds Discord pour l'affichage des jeux, façon "affiche Steam"."""

import discord
from config import STEAM_TAGS


def _price_text(game: dict) -> str:
    if game.get("is_free"):
        return "🆓 Gratuit"
    if game.get("price_eur") is None:
        return "Prix non annoncé"
    return f"{game['price_eur']:.2f} €"


def _tags_text(game: dict) -> str:
    cats = set(game.get("categories", []))
    labels = [info["label"] for info in STEAM_TAGS.values() if info["id"] in cats]
    return ", ".join(labels) if labels else "—"


def _rating_text(game: dict) -> str:
    reviews = game.get("reviews")
    metacritic = game.get("metacritic")
    parts = []
    if reviews:
        emoji = "🟢" if (reviews["percent_positive"] or 0) >= 70 else (
            "🟡" if (reviews["percent_positive"] or 0) >= 40 else "🔴"
        )
        parts.append(f"{emoji} {reviews['description']} ({reviews['percent_positive']}% sur {reviews['total_reviews']} avis)")
    if metacritic is not None:
        parts.append(f"🏆 Metacritic : {metacritic}/100")
    return "\n".join(parts) if parts else "Pas encore d'avis"


def _embed_color(game: dict) -> int:
    """Couleur dynamique selon la note Steam (vert/orange/rouge), sinon bleu Steam."""
    reviews = game.get("reviews")
    if reviews and reviews.get("percent_positive") is not None:
        pct = reviews["percent_positive"]
        if pct >= 70:
            return 0x66BB6A   # vert
        if pct >= 40:
            return 0xFFA726   # orange
        return 0xEF5350       # rouge
    return 0x1B2838            # bleu steam par défaut (pas d'avis / pas encore sorti)


def build_game_embed(game: dict, upcoming: bool = False, footer_extra: str = None) -> discord.Embed:
    color = _embed_color(game) if not upcoming else 0x66C0F4
    title_prefix = "🔜 Bientôt sur Steam" if upcoming else "🆕 Nouveau sur Steam"

    embed = discord.Embed(
        title=f"🎮 {game['name']}",
        url=game["url"],
        description=game.get("short_description", "")[:300],
        color=color,
    )
    embed.set_author(name=title_prefix, url=game["url"])

    if game.get("header_image"):
        embed.set_image(url=game["header_image"])

    embed.add_field(name="💰 Prix", value=_price_text(game), inline=True)
    embed.add_field(name="📅 Sortie", value=game.get("release_date", "Inconnue"), inline=True)
    embed.add_field(name="🧪 Démo", value="Oui" if game.get("has_demo") else "Non", inline=True)

    embed.add_field(name="🎭 Genres", value=", ".join(game.get("genres", [])) or "—", inline=True)
    embed.add_field(name="🎮 Mode de jeu", value=_tags_text(game), inline=True)
    embed.add_field(
        name="🛠️ Développeur",
        value=", ".join(game.get("developers", [])) or "Inconnu",
        inline=True,
    )

    embed.add_field(name="⭐ Note", value=_rating_text(game), inline=False)

    embed.set_footer(text=footer_extra or "Source : Steam Store", icon_url="https://store.steampowered.com/favicon.ico")
    return embed


def build_steam_link_view(game: dict) -> discord.ui.View:
    """Bouton cliquable qui renvoie directement vers la fiche Steam du jeu."""
    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="🔗 Voir sur Steam", url=game["url"], style=discord.ButtonStyle.link))
    return view
