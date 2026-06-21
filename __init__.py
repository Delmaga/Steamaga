"""
Cog contenant les commandes slash :
  /jeux        -> définit le salon qui reçoit TOUS les nouveaux jeux (aucun filtre)
  /pres        -> définit le salon qui reçoit les jeux À VENIR (aucun filtre)
  /filtre      -> configuration interactive d'un filtre personnel, sauvegardé par compte
  /prefiltre   -> abonne un salon à un pack de filtres prédéfinis

+ une boucle de fond qui vérifie Steam toutes les X minutes et poste les jeux
  correspondants dans tous les salons concernés.
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiohttp

import database as db
import steam_api
from config import (
    PRESETS, CHECK_INTERVAL_MINUTES, STEAM_TAGS, STEAM_CATEGORIES,
)
from embeds import build_game_embed
from views import FilterBuilderView


class PresetSelect(discord.ui.Select):
    def __init__(self, channel: discord.TextChannel):
        self.channel = channel
        options = [
            discord.SelectOption(label=info["label"], value=key, description=self._describe(info))
            for key, info in PRESETS.items()
        ]
        super().__init__(placeholder="Choisis un pack de filtres prédéfinis", options=options)

    @staticmethod
    def _describe(info) -> str:
        tags = ", ".join(STEAM_TAGS[t]["label"] for t in info["tags"]) or "Tous tags"
        cats = ", ".join(STEAM_CATEGORIES[c]["label"] for c in info["categories"]) or "Toutes catégories"
        return f"{tags} | {cats}"[:100]

    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        db.add_preset_subscription(interaction.guild_id, self.channel.id, key)
        embed = discord.Embed(
            title="✅ Préfiltre activé",
            description=f"**{PRESETS[key]['label']}** sera désormais publié dans {self.channel.mention}.",
            color=0x57F287,
        )
        await interaction.response.edit_message(embed=embed, view=None)


class PresetSelectView(discord.ui.View):
    def __init__(self, channel: discord.TextChannel):
        super().__init__(timeout=180)
        self.add_item(PresetSelect(channel))


class SteamCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None
        self.check_steam.start()

    def cog_unload(self):
        self.check_steam.cancel()

    async def cog_load(self):
        self.session = aiohttp.ClientSession()

    # ---------------------------------------------------------------
    # /jeux steam (salon) -> tous les nouveaux jeux, aucun filtre
    # ---------------------------------------------------------------
    @app_commands.command(name="jeux", description="Définit le salon qui reçoit TOUS les nouveaux jeux Steam (sans filtre).")
    @app_commands.describe(salon="Salon où publier tous les nouveaux jeux")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def jeux(self, interaction: discord.Interaction, salon: discord.TextChannel):
        db.set_feed_channel(interaction.guild_id, "new", salon.id)
        await interaction.response.send_message(
            f"✅ Tous les nouveaux jeux Steam seront publiés dans {salon.mention}, sans filtre.",
            ephemeral=True,
        )

    # ---------------------------------------------------------------
    # /pres steam (salon) -> jeux à venir, aucun filtre
    # ---------------------------------------------------------------
    @app_commands.command(name="pres", description="Définit le salon qui reçoit les jeux Steam À VENIR (sans filtre).")
    @app_commands.describe(salon="Salon où publier les jeux à venir")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def pres(self, interaction: discord.Interaction, salon: discord.TextChannel):
        db.set_feed_channel(interaction.guild_id, "upcoming", salon.id)
        await interaction.response.send_message(
            f"✅ Les jeux Steam à venir seront publiés dans {salon.mention}, sans filtre.",
            ephemeral=True,
        )

    # ---------------------------------------------------------------
    # /filtre steam (salon) -> configuration interactive perso, sauvegardée
    # ---------------------------------------------------------------
    @app_commands.command(name="filtre", description="Configure ton filtre Steam personnel (tag, catégorie, prix, démo).")
    @app_commands.describe(salon="Salon où tu veux recevoir TES jeux filtrés")
    async def filtre(self, interaction: discord.Interaction, salon: discord.TextChannel):
        existing = db.get_user_filter(interaction.user.id, interaction.guild_id)
        view = FilterBuilderView(channel=salon, existing=existing)
        await interaction.response.send_message(
            embed=view.build_summary_embed(), view=view, ephemeral=True
        )

    @app_commands.command(name="filtre_supprimer", description="Supprime ton filtre Steam personnel.")
    async def filtre_supprimer(self, interaction: discord.Interaction):
        db.delete_user_filter(interaction.user.id, interaction.guild_id)
        await interaction.response.send_message("🗑️ Ton filtre personnel a été supprimé.", ephemeral=True)

    # ---------------------------------------------------------------
    # /prefiltre (salon) -> packs prédéfinis, abonnement par salon
    # ---------------------------------------------------------------
    @app_commands.command(name="prefiltre", description="Abonne un salon à un pack de filtres Steam prédéfinis.")
    @app_commands.describe(salon="Salon où publier les jeux de ce pack")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def prefiltre(self, interaction: discord.Interaction, salon: discord.TextChannel):
        view = PresetSelectView(salon)
        embed = discord.Embed(
            title="📦 Packs de filtres prédéfinis",
            description="Sélectionne un pack ci-dessous. Tu peux en activer plusieurs un par un.",
            color=0x5865F2,
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ---------------------------------------------------------------
    # Boucle de fond : vérifie Steam et publie
    # ---------------------------------------------------------------
    @tasks.loop(minutes=CHECK_INTERVAL_MINUTES)
    async def check_steam(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        try:
            await self._process_new_releases()
            await self._process_upcoming()
        except Exception as e:
            print(f"[check_steam] Erreur : {e}")

    @check_steam.before_loop
    async def before_check_steam(self):
        await self.bot.wait_until_ready()

    async def _process_new_releases(self):
        appids = await steam_api.get_new_release_appids(self.session, count=30)
        unseen = [a for a in appids if not db.is_already_posted(a, "new")]
        if not unseen:
            return

        all_channels = db.get_feed_channels("new")
        preset_subs = db.get_preset_subscriptions()
        user_filters = db.get_all_user_filters()

        for appid in unseen:
            game = await steam_api.enrich_game(self.session, appid)
            db.mark_posted(appid, "new")
            if not game:
                continue

            embed = build_game_embed(game, upcoming=False)

            # 1) salons "tous les jeux"
            for guild_id, channel_id in all_channels:
                await self._send(channel_id, embed)

            # 2) salons abonnés à un préfiltre
            for guild_id, channel_id, preset_key in preset_subs:
                preset = PRESETS.get(preset_key)
                if not preset:
                    continue
                if steam_api.game_matches_filter(
                    game, preset["tags"], preset["categories"],
                    preset["price_min"], preset["price_max"], preset["demo_mode"],
                ):
                    preset_embed = build_game_embed(game, upcoming=False, footer_extra=f"Préfiltre : {preset['label']}")
                    await self._send(channel_id, preset_embed)

            # 3) filtres personnels
            for uf in user_filters:
                if steam_api.game_matches_filter(
                    game, uf["tags"], uf["categories"],
                    uf["price_min"], uf["price_max"], uf["demo_mode"],
                ):
                    personal_embed = build_game_embed(game, upcoming=False, footer_extra="Filtre personnel")
                    await self._send(uf["channel_id"], personal_embed, mention_user=uf["user_id"])

    async def _process_upcoming(self):
        appids = await steam_api.get_upcoming_appids(self.session, count=30)
        unseen = [a for a in appids if not db.is_already_posted(a, "upcoming")]
        if not unseen:
            return

        channels = db.get_feed_channels("upcoming")
        if not channels:
            for a in unseen:
                db.mark_posted(a, "upcoming")
            return

        for appid in unseen:
            game = await steam_api.enrich_game(self.session, appid)
            db.mark_posted(appid, "upcoming")
            if not game:
                continue
            embed = build_game_embed(game, upcoming=True)
            for guild_id, channel_id in channels:
                await self._send(channel_id, embed)

    async def _send(self, channel_id: int, embed: discord.Embed, mention_user: int = None):
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except discord.HTTPException:
                return
        content = f"<@{mention_user}>" if mention_user else None
        try:
            await channel.send(content=content, embed=embed)
        except discord.HTTPException as e:
            print(f"[_send] Impossible d'envoyer dans {channel_id} : {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(SteamCommands(bot))
