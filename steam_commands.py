"""
Cog contenant les commandes slash :
  /jeux            -> définit le salon qui reçoit TOUS les nouveaux jeux (aucun filtre)
  /pres            -> définit le salon qui reçoit les jeux À VENIR (aucun filtre)
  /stteam          -> salon qui reçoit nouveautés ET jeux à venir, toute catégorie/prix
  /filtre          -> configuration interactive d'un filtre personnel, sauvegardé par compte
  /prefiltre       -> abonne un salon à un pack de filtres prédéfinis
  /stcat           -> abonne un salon à UNE catégorie (générique, choix dans la liste)
  /sthorror        -> raccourci /stcat catégorie=horreur
  /stct            -> raccourci /stcat catégorie=casse-tête
  /stall           -> affiche D'UN COUP tous les jeux déjà sortis d'une catégorie
                       (catalogue complet, toute prix confondu) + abonne le salon
                       pour que les futurs jeux de cette catégorie arrivent aussi

+ une boucle de fond qui vérifie Steam toutes les X minutes et poste les jeux
  correspondants dans tous les salons concernés.
"""

import asyncio
import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiohttp

import database as db
import steam_api
from config import (
    PRESETS, CHECK_INTERVAL_MINUTES, STEAM_TAGS, STEAM_CATEGORIES,
)
from embeds import build_game_embed, build_steam_link_view
from views import FilterBuilderView

CATEGORY_CHOICES = [
    app_commands.Choice(name=info["label"], value=key) for key, info in STEAM_CATEGORIES.items()
]


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
    # /stteam (salon) -> nouveautés ET jeux à venir, toute catégorie/prix
    # ---------------------------------------------------------------
    @app_commands.command(name="stteam", description="Publie dans un salon TOUS les jeux Steam (nouveautés + à venir), sans filtre.")
    @app_commands.describe(salon="Salon où tout publier")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def stteam(self, interaction: discord.Interaction, salon: discord.TextChannel):
        db.set_feed_channel(interaction.guild_id, "new", salon.id)
        db.set_feed_channel(interaction.guild_id, "upcoming", salon.id)
        await interaction.response.send_message(
            f"✅ {salon.mention} recevra désormais **tous** les jeux Steam : nouveautés et jeux à venir, "
            f"toute catégorie et tout prix confondus.",
            ephemeral=True,
        )

    # ---------------------------------------------------------------
    # /stcat (salon) (catégorie) -> abonnement générique à une catégorie
    # ---------------------------------------------------------------
    @app_commands.command(name="stcat", description="Abonne un salon à une catégorie de jeux Steam (nouveaux + à venir).")
    @app_commands.describe(salon="Salon où publier", categorie="Catégorie de jeux à suivre")
    @app_commands.choices(categorie=CATEGORY_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def stcat(self, interaction: discord.Interaction, salon: discord.TextChannel, categorie: app_commands.Choice[str]):
        db.add_category_subscription(interaction.guild_id, salon.id, categorie.value)
        label = STEAM_CATEGORIES[categorie.value]["label"]
        await interaction.response.send_message(
            f"✅ Les jeux **{label}** (nouveaux et à venir, tout prix) seront publiés dans {salon.mention}.",
            ephemeral=True,
        )

    # ---------------------------------------------------------------
    # /sthorror (salon) -> raccourci catégorie Horreur
    # ---------------------------------------------------------------
    @app_commands.command(name="sthorror", description="Abonne un salon à tous les jeux Steam d'Horreur (nouveaux + à venir).")
    @app_commands.describe(salon="Salon où publier les jeux d'horreur")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def sthorror(self, interaction: discord.Interaction, salon: discord.TextChannel):
        db.add_category_subscription(interaction.guild_id, salon.id, "horreur")
        await interaction.response.send_message(
            f"🔪 Tous les jeux d'**Horreur** (nouveaux et à venir, tout prix) seront publiés dans {salon.mention}.",
            ephemeral=True,
        )

    # ---------------------------------------------------------------
    # /stct (salon) -> raccourci catégorie Casse-tête
    # ---------------------------------------------------------------
    @app_commands.command(name="stct", description="Abonne un salon à tous les jeux Steam de Casse-tête (nouveaux + à venir).")
    @app_commands.describe(salon="Salon où publier les jeux de casse-tête")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def stct(self, interaction: discord.Interaction, salon: discord.TextChannel):
        db.add_category_subscription(interaction.guild_id, salon.id, "puzzle")
        await interaction.response.send_message(
            f"🧩 Tous les jeux de **Casse-tête** (nouveaux et à venir, tout prix) seront publiés dans {salon.mention}.",
            ephemeral=True,
        )

    # ---------------------------------------------------------------
    # /stall (salon) (catégorie) -> dump immédiat du catalogue existant
    # + abonnement pour les futurs jeux de cette catégorie
    # ---------------------------------------------------------------
    @app_commands.command(
        name="stall",
        description="Affiche d'un coup tous les jeux existants d'une catégorie + abonne le salon aux futurs.",
    )
    @app_commands.describe(salon="Salon où tout publier", categorie="Catégorie de jeux")
    @app_commands.choices(categorie=CATEGORY_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def stall(self, interaction: discord.Interaction, salon: discord.TextChannel, categorie: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True, thinking=True)
        label = STEAM_CATEGORIES[categorie.value]["label"]

        appids = await steam_api.get_appids_by_category(self.session, categorie.value, max_appids=120)
        if not appids:
            await interaction.followup.send(
                f"❌ Aucun jeu trouvé pour la catégorie **{label}** (Steam/SteamSpy a peut-être limité la requête, réessaie plus tard).",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"⏳ Récupération de tous les jeux **{label}**... ({len(appids)} jeux trouvés, "
            f"je publie les {min(40, len(appids))} plus récents dans {salon.mention}, puis j'abonne le salon "
            f"pour que les prochains arrivent automatiquement).",
            ephemeral=True,
        )

        games = []
        for i in range(0, len(appids), 10):
            batch = appids[i:i + 10]
            results = await asyncio.gather(*[steam_api.enrich_game(self.session, a) for a in batch])
            for g in results:
                if g and steam_api.game_has_category(g, categorie.value):
                    games.append(g)
            await asyncio.sleep(1)  # ménage SteamSpy (rate-limit) pour des réponses fiables

        games.sort(key=lambda g: g.get("release_date", ""), reverse=True)
        games = games[:40]

        for game in games:
            embed = build_game_embed(game, upcoming=game.get("coming_soon", False),
                                      footer_extra=f"Catalogue {label} — /stall")
            view = build_steam_link_view(game)
            await self._send(salon.id, embed, view=view)

        db.add_category_subscription(interaction.guild_id, salon.id, categorie.value)

        await interaction.followup.send(
            f"✅ {len(games)} jeux **{label}** publiés dans {salon.mention}. "
            f"Le salon est maintenant abonné : les prochains jeux **{label}** arriveront automatiquement.",
            ephemeral=True,
        )

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
        category_subs = db.get_category_subscriptions()

        for appid in unseen:
            game = await steam_api.enrich_game(self.session, appid)
            db.mark_posted(appid, "new")
            if not game:
                continue

            embed = build_game_embed(game, upcoming=False)
            view = build_steam_link_view(game)

            # 1) salons "tous les jeux"
            for guild_id, channel_id in all_channels:
                await self._send(channel_id, embed, view=view)

            # 2) salons abonnés à une catégorie (/sthorror, /stct, /stcat, /stall)
            for guild_id, channel_id, category_key in category_subs:
                if steam_api.game_has_category(game, category_key):
                    cat_embed = build_game_embed(game, upcoming=False, footer_extra=f"Catégorie : {STEAM_CATEGORIES[category_key]['label']}")
                    await self._send(channel_id, cat_embed, view=build_steam_link_view(game))

            # 3) salons abonnés à un préfiltre
            for guild_id, channel_id, preset_key in preset_subs:
                preset = PRESETS.get(preset_key)
                if not preset:
                    continue
                if steam_api.game_matches_filter(
                    game, preset["tags"], preset["categories"],
                    preset["price_min"], preset["price_max"], preset["demo_mode"],
                    categories_all=preset.get("categories_all", False),
                ):
                    preset_embed = build_game_embed(game, upcoming=False, footer_extra=f"Préfiltre : {preset['label']}")
                    await self._send(channel_id, preset_embed, view=build_steam_link_view(game))

            # 4) filtres personnels
            for uf in user_filters:
                if steam_api.game_matches_filter(
                    game, uf["tags"], uf["categories"],
                    uf["price_min"], uf["price_max"], uf["demo_mode"],
                ):
                    personal_embed = build_game_embed(game, upcoming=False, footer_extra="Filtre personnel")
                    await self._send(uf["channel_id"], personal_embed, mention_user=uf["user_id"], view=build_steam_link_view(game))

    async def _process_upcoming(self):
        appids = await steam_api.get_upcoming_appids(self.session, count=30)
        unseen = [a for a in appids if not db.is_already_posted(a, "upcoming")]
        if not unseen:
            return

        channels = db.get_feed_channels("upcoming")
        category_subs = db.get_category_subscriptions()
        if not channels and not category_subs:
            for a in unseen:
                db.mark_posted(a, "upcoming")
            return

        for appid in unseen:
            game = await steam_api.enrich_game(self.session, appid)
            db.mark_posted(appid, "upcoming")
            if not game:
                continue
            embed = build_game_embed(game, upcoming=True)
            view = build_steam_link_view(game)
            for guild_id, channel_id in channels:
                await self._send(channel_id, embed, view=view)

            # les abonnements catégorie reçoivent aussi les jeux à venir (cf. /stall, /sthorror...)
            for guild_id, channel_id, category_key in category_subs:
                if steam_api.game_has_category(game, category_key):
                    cat_embed = build_game_embed(game, upcoming=True, footer_extra=f"Catégorie : {STEAM_CATEGORIES[category_key]['label']}")
                    await self._send(channel_id, cat_embed, view=build_steam_link_view(game))

    async def _send(self, channel_id: int, embed: discord.Embed, mention_user: int = None, view: discord.ui.View = None):
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except discord.HTTPException:
                return
        content = f"<@{mention_user}>" if mention_user else None
        try:
            await channel.send(content=content, embed=embed, view=view)
        except discord.HTTPException as e:
            print(f"[_send] Impossible d'envoyer dans {channel_id} : {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(SteamCommands(bot))
