"""
Vue interactive (boutons + menus déroulants) utilisée par /filtre pour permettre
à chaque utilisateur de construire son propre filtre, étape par étape, de façon
dynamique. Le résultat est sauvegardé en base par utilisateur+serveur.
"""

import discord

from config import STEAM_TAGS, STEAM_CATEGORIES, PRICE_RANGES, DEMO_MODES
import database as db


class TagSelect(discord.ui.Select):
    def __init__(self, current: list):
        options = [
            discord.SelectOption(label=info["label"], value=key, default=(key in current))
            for key, info in STEAM_TAGS.items()
        ]
        super().__init__(
            placeholder="🎮 Tag (mode de jeu) — plusieurs choix possibles",
            min_values=0, max_values=len(options), options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.state["tags"] = self.values
        await self.view.refresh(interaction)


class CategorySelect(discord.ui.Select):
    def __init__(self, current: list):
        options = [
            discord.SelectOption(label=info["label"], value=key, default=(key in current))
            for key, info in STEAM_CATEGORIES.items()
        ]
        super().__init__(
            placeholder="🎭 Catégorie (thème) — plusieurs choix possibles",
            min_values=0, max_values=len(options), options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.state["categories"] = self.values
        await self.view.refresh(interaction)


class PriceSelect(discord.ui.Select):
    def __init__(self, current_min, current_max):
        options = []
        for key, info in PRICE_RANGES.items():
            is_current = (info["min"] == current_min and info["max"] == current_max)
            options.append(discord.SelectOption(label=info["label"], value=key, default=is_current))
        options.append(discord.SelectOption(label="N'importe quel prix", value="any",
                                              default=(current_min == 0 and current_max >= 99999)))
        super().__init__(placeholder="💰 Tranche de prix", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        if value == "any":
            self.view.state["price_min"] = 0
            self.view.state["price_max"] = 99999
        else:
            r = PRICE_RANGES[value]
            self.view.state["price_min"] = r["min"]
            self.view.state["price_max"] = r["max"]
        await self.view.refresh(interaction)


class DemoSelect(discord.ui.Select):
    def __init__(self, current: str):
        options = [
            discord.SelectOption(label=label, value=key, default=(key == current))
            for key, label in DEMO_MODES.items()
        ]
        super().__init__(placeholder="🧪 Démo", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.state["demo_mode"] = self.values[0]
        await self.view.refresh(interaction)


class ConfirmButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="✅ Valider et sauvegarder", style=discord.ButtonStyle.success, row=4)

    async def callback(self, interaction: discord.Interaction):
        state = self.view.state
        db.save_user_filter(
            user_id=interaction.user.id,
            guild_id=interaction.guild_id,
            channel_id=self.view.channel.id,
            tags=state["tags"],
            categories=state["categories"],
            price_min=state["price_min"],
            price_max=state["price_max"],
            demo_mode=state["demo_mode"],
        )
        embed = self.view.build_summary_embed(saved=True)
        await interaction.response.edit_message(embed=embed, view=None)
        self.view.stop()


class CancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="❌ Annuler", style=discord.ButtonStyle.danger, row=4)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content="Configuration annulée, rien n'a été sauvegardé.", embed=None, view=None
        )
        self.view.stop()


class FilterBuilderView(discord.ui.View):
    def __init__(self, channel: discord.TextChannel, existing: dict = None):
        super().__init__(timeout=300)
        self.channel = channel
        self.state = {
            "tags": existing["tags"] if existing else [],
            "categories": existing["categories"] if existing else [],
            "price_min": existing["price_min"] if existing else 0,
            "price_max": existing["price_max"] if existing else 99999,
            "demo_mode": existing["demo_mode"] if existing else "peu_importe",
        }
        self.add_item(TagSelect(self.state["tags"]))
        self.add_item(CategorySelect(self.state["categories"]))
        self.add_item(PriceSelect(self.state["price_min"], self.state["price_max"]))
        self.add_item(DemoSelect(self.state["demo_mode"]))
        self.add_item(ConfirmButton())
        self.add_item(CancelButton())

    def build_summary_embed(self, saved: bool = False) -> discord.Embed:
        tag_labels = [STEAM_TAGS[t]["label"] for t in self.state["tags"]] or ["Tous"]
        cat_labels = [STEAM_CATEGORIES[c]["label"] for c in self.state["categories"]] or ["Toutes"]
        price_min, price_max = self.state["price_min"], self.state["price_max"]
        price_label = "N'importe quel prix" if price_max >= 99999 and price_min == 0 else (
            "Gratuit" if price_max == 0 else f"Entre {price_min}€ et {price_max}€"
        )
        embed = discord.Embed(
            title="✅ Filtre sauvegardé !" if saved else "⚙️ Configuration de ton filtre Steam",
            description=f"Les jeux seront envoyés dans {self.channel.mention}" if saved else
                        "Choisis tes critères dans les menus ci-dessous, puis valide.",
            color=0x57F287 if saved else 0x5865F2,
        )
        embed.add_field(name="🎮 Tag", value=", ".join(tag_labels), inline=False)
        embed.add_field(name="🎭 Catégorie", value=", ".join(cat_labels), inline=False)
        embed.add_field(name="💰 Prix", value=price_label, inline=False)
        embed.add_field(name="🧪 Démo", value=DEMO_MODES[self.state["demo_mode"]], inline=False)
        return embed

    async def refresh(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.build_summary_embed(), view=self)
