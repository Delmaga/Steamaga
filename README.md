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

### `/stteam salon:#salon`
*(réservé aux modérateurs)*
Équivalent de `/jeux` + `/pres` combinés dans un seul salon : nouveautés **et**
jeux à venir, toute catégorie et tout prix confondus.

### `/stcat salon:#salon categorie:Horreur`
*(réservé aux modérateurs)*
Commande générique : abonne un salon à **une catégorie précise** (toutes celles
listées dans `/filtre`), pour les nouveaux jeux **et** les jeux à venir, sans
filtre de prix ni de tag. Pratique pour créer tes propres raccourcis sans
attendre que j'ajoute une commande dédiée.

### `/sthorror salon:#salon`
*(réservé aux modérateurs)*
Raccourci équivalent à `/stcat categorie:Horreur`. Tous les jeux d'horreur,
peu importe le prix.

### `/stct salon:#salon`
*(réservé aux modérateurs)*
Raccourci équivalent à `/stcat categorie:Casse-tête`.

> 💡 Envie d'horreur **drôle** uniquement ? Utilise plutôt `/prefiltre` et choisis
> le pack **"🤡 Horreur mais drôle"** — celui-ci exige que le jeu soit horreur
> *et* drôle en même temps (pas juste l'un ou l'autre), contrairement à
> `/sthorror` qui prend toute l'horreur sans distinction.

### `/stall salon:#salon categorie:Horreur`
*(réservé aux modérateurs)*
La commande "catalogue" : récupère **tous les jeux déjà sortis** de cette
catégorie (via SteamSpy), les publie d'un coup dans le salon (les ~40 plus
récents, pour ne pas noyer le salon sous des centaines de messages d'un coup),
**et** abonne automatiquement le salon pour que les futurs jeux de cette
catégorie arrivent aussi, peu importe leur prix.

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
Gratuit", "Horreur mais drôle"...). Tu choisis un pack dans le menu, et le
salon est abonné à ce pack. Tu peux abonner plusieurs salons à plusieurs packs
différents.

## 🖼️ À quoi ressemble un message

Chaque jeu posté affiche désormais :
- la grande image officielle Steam du jeu (façon affiche)
- le **lien direct** vers la fiche Steam (titre cliquable + bouton "Voir sur Steam")
- le **prix** exact (ou "Gratuit")
- la **date de sortie**
- le **développeur**
- la **note Steam** (% positif + description type "Très positive") et le score
  **Metacritic** si disponible
- les genres, le mode de jeu (solo/multi/coop) et la présence d'une démo

La couleur de la bordure de l'embed change même selon la note du jeu (vert si
bien noté, orange si mitigé, rouge si mal noté).

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
