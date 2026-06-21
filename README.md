# 🎮 Steam Discord Bot

Bot Discord qui surveille Steam en continu et publie automatiquement les nouveaux
jeux (et ceux à venir) dans tes salons, avec un système de filtres personnalisés
sauvegardés par compte.

## 📦 Installation

1. **Prérequis** : Python 3.10+

2. Installe les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

3. Crée une application Discord sur https://discord.com/developers/applications,
   ajoute un Bot, récupère son **token**, et invite-le sur ton serveur avec les
   permissions : `Envoyer des messages`, `Intégrer des liens`, `Utiliser les
   commandes slash`.

4. Copie `.env.example` en `.env` et colle ton token :
   ```
   DISCORD_TOKEN=ton_token_ici
   ```

5. Lance le bot :
   ```bash
   python main.py
   ```

   Une base SQLite `steam_bot.db` est créée automatiquement au premier lancement
   (toutes les sauvegardes — salons, filtres, préfiltres — y sont stockées).

## 🤖 Commandes

### `/jeux salon:#salon`
*(réservé aux modérateurs — permission "Gérer le serveur")*
Définit le salon qui reçoit **absolument tous** les nouveaux jeux publiés sur
Steam, sans aucun filtre.

### `/pres salon:#salon`
*(réservé aux modérateurs)*
Définit le salon qui reçoit les jeux **à venir** (pas encore sortis), sans filtre.

### `/filtre salon:#salon`
Ouvre une interface interactive (menus déroulants) pour que **toi seul**
configures ton filtre personnel :
- **Tag** (mode de jeu) : Solo, Multijoueur, Coop, Coop en ligne, PvP en ligne
- **Catégorie** (thème) : Horreur, Aventure, Action, RPG, Indé, Stratégie, etc.
- **Prix** : Gratuit, 0-10€, 10-25€, 25€+, ou n'importe quel prix
- **Démo** : avec démo uniquement / sans démo / peu importe

Ton filtre est sauvegardé en base, lié à ton compte Discord sur ce serveur.
Dès qu'un nouveau jeu correspond, il est posté (et tu es mentionné) dans le
salon choisi. Chaque utilisateur a son propre filtre indépendant — ton pote
peut configurer le sien sans toucher au tien.

Relancer `/filtre` sur le même serveur met simplement à jour ton filtre existant.

### `/filtre_supprimer`
Supprime ton filtre personnel.

### `/prefiltre salon:#salon`
*(réservé aux modérateurs)*
Affiche une liste de **packs prêts à l'emploi** (combinaisons de tag +
catégorie + prix + démo déjà définies, ex : "Horreur Solo", "Multijoueur
Gratuit"...). Tu choisis un pack dans le menu, et le salon est abonné à ce pack.
Tu peux abonner plusieurs salons à plusieurs packs différents.

## ⚙️ Fonctionnement technique

- Tous les fichiers Python sont à plat (pas de sous-dossier), pour éviter tout
  souci de package Python sur les plateformes d'hébergement qui ne gèrent pas
  toujours bien les sous-répertoires.

- Une tâche de fond vérifie Steam toutes les **10 minutes** (configurable dans
  `config.py` via `CHECK_INTERVAL_MINUTES`).
- Le bot utilise le moteur de recherche Steam (tri par date de sortie) pour
  détecter les nouveautés, l'API officielle `appdetails` pour les infos
  complètes (prix, catégories, démo...), et **SteamSpy** pour les tags
  communautaires précis (Horreur, Aventure, etc., absents de l'API officielle).
- Chaque jeu n'est posté **qu'une seule fois** par salon/filtre grâce à un
  historique anti-doublon en base.

## 🛠️ Pour aller plus loin

- Les listes de tags/catégories/presets sont entièrement modifiables dans
  `config.py` sans toucher au reste du code.
- Pour héberger le bot 24/7, utilise un VPS, un service comme Railway/Render,
  ou un Raspberry Pi avec un gestionnaire de process (ex : `systemd`, `pm2`,
  ou `tmux`).
