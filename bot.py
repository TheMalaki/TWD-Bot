import random
import discord
import yaml
import asyncio
import os
from discord.ext import commands

# -------------------
# ⚡ Configuration bot
# -------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------
# ⚡ Répertoires et fichiers
# -------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSOS_FILE = os.path.join(BASE_DIR, "persos.yaml")
INVENTAIRES_FILE = os.path.join(BASE_DIR, "inventaires.yaml")
ARMES_FILE = os.path.join(BASE_DIR, "armes.yaml")
RODEURS_FILE = os.path.join(BASE_DIR, "rodeurs.yml")

# -------------------
# ⚡ Variables globales
# -------------------
en_veille = {}
combat_actif = {}

GENERAL_CHANNEL_IDS = [
    #bot channels go here
]

# -------------------
# ⚡ Fonctions utilitaires
# -------------------
def charger_yaml(fichier):
    try:
        with open(fichier, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}

def sauvegarder_yaml(fichier, data):
    with open(fichier, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

def get_perso_discord(joueur_discord):
    persos = charger_yaml(PERSOS_FILE)
    for perso_name, data in persos.items():
        if data.get("discord") == joueur_discord:
            return perso_name, data
    return None, None

# -------------------
# ⚡ Events
# -------------------
@bot.event
async def on_ready():
    print(f"Connecté comme {bot.user}")
    for channel_id in GENERAL_CHANNEL_IDS:
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send("✅ Bot opérationnel!")

@bot.check
async def check_veille_et_canal(ctx):
    # Ignore les bots
    if ctx.author.bot:
        return True

    # Autoriser certaines commandes même sans personnage
    if ctx.command.name in ["choisir", "persos"]:
        return True

    joueur_discord = f"{ctx.author.name}#{ctx.author.discriminator}"
    perso_name, p = get_perso_discord(joueur_discord)

    # Vérifie si le joueur a choisi un personnage
    if not p:
        msg = await ctx.send("❌ Tu n’as pas encore choisi de personnage !", delete_after=5)
        await ctx.message.delete()
        return False

    # Vérifie si le joueur est en veille
    if en_veille.get(perso_name):
        msg = await ctx.send(f"💤 {perso_name} est en veille et ne peut pas utiliser de commandes !", delete_after=5)
        await ctx.message.delete()
        return False

    # Vérifie si la commande est dans la catégorie 'jeu' ou le canal 'bots'
    categorie_jeu = discord.utils.get(ctx.guild.categories, name="🎭 | 𝒁𝒐𝒏𝒆-𝑹𝑷 (monde extérieur)")
    canal_bots = discord.utils.get(ctx.guild.text_channels, name="bots")

    if ctx.channel.category != categorie_jeu and ctx.channel != canal_bots:
        msg = await ctx.send(
            "❌ Tu ne peux utiliser les commandes que dans la catégorie '🎭 | Zones RP (monde extérieur)' ou le canal 'bots'.",
            delete_after=5
        )
        await ctx.message.delete()
        return False

    return True

# -------------------
# ⚡ Commande Dé
# -------------------
@bot.command(name="dé")
async def dé(ctx, *, raison: str = "aucune raison"):
    roll = random.randint(1, 20)
    embed = discord.Embed(title="🎲 Jet de dé",
                          description=f"Résultat du dé : **{roll}**",
                          color=discord.Color.blurple())
    embed.add_field(name="Pourquoi ?", value=raison, inline=False)
    await ctx.send(embed=embed)

# -------------------
# ⚡ Commande Persos
# -------------------
@bot.command()
async def persos(ctx):
    persos = charger_yaml(PERSOS_FILE)
    if not persos:
        await ctx.send("❌ Aucun personnage trouvé.")
        return

    persos_items = list(persos.items())
    chunk_size = 25
    pages = []

    # Création des pages
    for i in range(0, len(persos_items), chunk_size):
        embed = discord.Embed(
            title=f"📜 Personnages disponibles ({i//chunk_size + 1})",
            color=discord.Color.blue()
        )
        for nom, data in persos_items[i:i+chunk_size]:
            statut = "✅ Libre" if not data.get("discord") else f"❌ Pris par {data['discord']}"
            embed.add_field(name=nom, value=statut, inline=True)
        pages.append(embed)

    # Envoi de la première page
    message = await ctx.send(embed=pages[0])
    if len(pages) == 1:
        return  # Pas besoin de réactions si une seule page

    # Ajout des réactions pour naviguer
    await message.add_reaction("⬅️")
    await message.add_reaction("➡️")

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == message.id

    current_page = 0
    while True:
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=120.0, check=check)

            if str(reaction.emoji) == "➡️" and current_page < len(pages) - 1:
                current_page += 1
                await message.edit(embed=pages[current_page])
            elif str(reaction.emoji) == "⬅️" and current_page > 0:
                current_page -= 1
                await message.edit(embed=pages[current_page])

            await message.remove_reaction(reaction, user)
        except asyncio.TimeoutError:
            break  # Fin après 2 minutes sans réaction
# -------------------
# ⚡ Commande choisir
# -------------------
@bot.command()
async def choisir(ctx, personnage: str):
    # Vérifie que la commande est dans le bon canal
    if ctx.channel.name != "commence-ton-aventure":
        await ctx.send("❌ Cette commande ne peut être utilisée que dans le canal #commence-ton-aventure.", delete_after=5)
        return

    joueur = ctx.author
    joueur_discord = f"{joueur.name}#{joueur.discriminator}"
    persos = charger_yaml(PERSOS_FILE)
    personnage = personnage.strip()

    if personnage not in persos:
        await ctx.send(f"❌ Personnage `{personnage}` non trouvé.", delete_after=5)
        return
    if persos[personnage].get("discord"):
        await ctx.send(f"❌ `{personnage}` est déjà associé à quelqu’un.", delete_after=5)
        return

    # Associe le joueur au personnage
    persos[personnage]["discord"] = joueur_discord
    sauvegarder_yaml(PERSOS_FILE, persos)

    # Supprime la visibilité du joueur sur ce canal
    await ctx.channel.set_permissions(joueur, read_messages=False)

    # Donne le rôle accès-douane
    role_douane = discord.utils.get(ctx.guild.roles, name="accès-douane")
    if role_douane:
        await joueur.add_roles(role_douane)
        # Optionnel : s'assurer que le joueur peut voir le canal douane
        channel_douane = discord.utils.get(ctx.guild.channels, name="douane")
        if channel_douane:
            await channel_douane.set_permissions(joueur, read_messages=True, send_messages=True)

    # Message de confirmation
    await ctx.send(f"✅ {joueur.mention} est maintenant associé au personnage **{personnage}** !\n"
                   f"🎮 Le jeu peut commencer dans le canal #douane. Bon jeu !", delete_after=60)

    
# -------------------
# ⚡ Commande inventaire
# -------------------
@bot.command()
async def inventaire(ctx):
    joueur_discord = f"{ctx.author.name}#{ctx.author.discriminator}"
    perso_name, _ = get_perso_discord(joueur_discord)

    if not perso_name:
        await ctx.send("❌ Tu n’as pas encore choisi de personnage ! Utilise `!choisir <nom>`.")
        return

    inventaires = charger_yaml(INVENTAIRES_FILE)
    items = inventaires.get(perso_name, {})

    if not items:
        await ctx.send(f"📦 L'inventaire de **{perso_name}** est vide.")
        return

    embed = discord.Embed(
        title=f"📦 Inventaire de {perso_name}",
        color=discord.Color.gold()
    )

    for item, quantite in items.items():
        embed.add_field(name=item, value=f"x{quantite}", inline=True)

    await ctx.send(embed=embed)


# -------------------
# ⚡ Commande fiche
# -------------------
@bot.command()
async def fiche(ctx, joueur: str = None):
    persos = charger_yaml(PERSOS_FILE)
    if joueur is None:
        joueur_discord = f"{ctx.author.name}#{ctx.author.discriminator}"
        for p_name, p_data in persos.items():
            if p_data.get("discord") == joueur_discord:
                joueur = p_name
                break
        if joueur is None:
            await ctx.send("❌ Tu n’as pas encore choisi de personnage !")
            return
    else:
        joueur = joueur.strip()
        if joueur not in persos:
            await ctx.send(f"❌ Joueur `{joueur}` non trouvé.")
            return

    p = persos[joueur]
    embed = discord.Embed(title=f"📋 Fiche de {joueur}", color=discord.Color.green())
    embed.add_field(name="❤️ Santé", value=f"{p['sante']} / {p['sante_max']}", inline=True)
    embed.add_field(name="⚡ Énergie", value=f"{p['energie']} / {p['energie_max']}", inline=True)
    embed.add_field(name="🧠 Moral", value=f"{p['moral']} / {p['moral_max']}", inline=True)
    embed.add_field(name="🥫 Rations", value=f"{p['rations']}", inline=True)
    embed.add_field(name="🧠 Focus", value=f"{p['focus']}", inline=True)
    embed.add_field(name="☠️Humains/Rôdeurs tués", value=f"{p['humains']} / {p['rodeurs']}", inline=False)
    stats_text = "\n".join([f"**{k}**: {v}" for k, v in p["stats"].items()])
    embed.add_field(name="📊 Stats", value=stats_text, inline=False)
    await ctx.send(embed=embed)

# -------------------
# ⚡ Commande setstat
# -------------------


@bot.command()
@commands.has_role("maitre du jeux")  # Remplace "MJ" par le nom exact du rôle de MJ
async def setstat(ctx, joueur: str, champ: str, valeur: int):
    """
    Permet aux MJ de modifier les stats des joueurs.
    Usage: !modif <joueur> <champ> <valeur>
    Exemple: !modif Rick energie 10
    """
    persos = charger_yaml(PERSOS_FILE)
    joueur = joueur.strip()
    champ = champ.lower()

    if joueur not in persos:
        await ctx.send(f"❌ Joueur `{joueur}` non trouvé.")
        return

    p = persos[joueur]

    # Vérifie si c'est une stat principale
    if champ in ["sante", "energie", "moral", "focus", "rations", "humains", "rodeurs"]:
        p[champ] = valeur
    # Vérifie si c'est une stat dans "stats"
    elif champ.upper() in p["stats"]:
        p["stats"][champ.upper()] = valeur
    else:
        await ctx.send(f"❌ Champ `{champ}` invalide.")
        return

    persos[joueur] = p
    sauvegarder_yaml(PERSOS_FILE, persos)
    await ctx.send(f"✅ {champ} de {joueur} modifié à {valeur}.")
 

# -------------------
# ⚡ Veille
# -------------------
en_veille = {}  # perso_name : True/False
tasks_veille = {}  # perso_name : task asyncio
VEILLE_CATEGORIE_ID = ####################  # ID de la catégorie où on bloque les commandes

MAX_FOCUS = 30

@bot.command()
async def veille(ctx):
    joueur_discord = f"{ctx.author.name}#{ctx.author.discriminator}"
    perso_name, p = get_perso_discord(joueur_discord)
    
    if not p:
        await ctx.send("❌ Tu n’as pas encore choisi de personnage !")
        return
    if en_veille.get(perso_name, False):
        await ctx.send(f"💤 {perso_name} est déjà en veille !")
        return
    if p.get("focus", 0) >= MAX_FOCUS:
        await ctx.send("⚠️ Tu as déjà du focus max !")
        return

    en_veille[perso_name] = True

    # Annule tâche précédente si existe
    if perso_name in tasks_veille:
        tasks_veille[perso_name].cancel()

    task = asyncio.create_task(regen_focus(ctx, perso_name, p))
    tasks_veille[perso_name] = task

    await ctx.send(f"😴 {perso_name} se met en veille pour récupérer du focus...", delete_after=5)
    await ctx.message.delete()  # Supprime le message du joueur

async def regen_focus(ctx, perso_name, p):
    try:
        while p["focus"] < MAX_FOCUS:
            await asyncio.sleep(10)
            p["focus"] = min(p["focus"] + 1, MAX_FOCUS)

            # Sauvegarde chaque cycle
            persos = charger_yaml(PERSOS_FILE)
            persos[perso_name] = p
            sauvegarder_yaml(PERSOS_FILE, persos)

            print(f"[VEILLE] {perso_name} → focus = {p['focus']}/{MAX_FOCUS}")
            await ctx.send(f"💤 {perso_name} a récupéré du focus ({p['focus']}/{MAX_FOCUS})", delete_after=5)

        en_veille[perso_name] = False
        await ctx.send(f"✅ {perso_name} a récupéré tout son focus !", delete_after=5)

    except asyncio.CancelledError:
        en_veille[perso_name] = False
        await ctx.send(f"⚠️ {perso_name} a interrompu sa veille !", delete_after=5)
        print(f"[VEILLE] Tâche annulée pour {perso_name}")

@bot.command()
async def reveil(ctx):
    joueur_discord = f"{ctx.author.name}#{ctx.author.discriminator}"
    perso_name, _ = get_perso_discord(joueur_discord)

    if perso_name not in en_veille or not en_veille[perso_name]:
        await ctx.send(f"⚠️ {perso_name} n'est pas en veille.", delete_after=5)
        return

    # Annule la tâche de veille
    if perso_name in tasks_veille:
        tasks_veille[perso_name].cancel()
        tasks_veille.pop(perso_name, None)

    en_veille[perso_name] = False
    await ctx.send(f"⏰ {perso_name} se réveille !", delete_after=5)

# -------------------
# ⚡ Blocage des commandes si en veille
# -------------------
@bot.check
async def check_veille(ctx):
    if ctx.author.bot:
        return True

    joueur_discord = f"{ctx.author.name}#{ctx.author.discriminator}"
    perso_name, _ = get_perso_discord(joueur_discord)

    if en_veille.get(perso_name, False):
        # Autorise uniquement !reveil
        if ctx.command.name != "reveil":
            await ctx.message.delete()
            warning = await ctx.send(f"❌ {perso_name} est en veille et ne peut pas utiliser cette commande !", delete_after=5)
            await asyncio.sleep(3)
            await warning.delete()
            return False

    return True


# -------------------
# ⚡ Systeme de mouvement
# -------------------

# Channels et les destinations accessibles
MAP_CHANNELS = {
    "douane": ["atlanta", "routes-dangeureuses"],
    "atlanta": ["douane", "ferme-hershel", "routes-dangeureuses"],
    "ferme-hershel": ["atlanta", "la-prison"],
    "la-prison": ["ferme-hershel", "woodbury"],
    "woodbury": ["la-prison", "routes-dangeureuses"],
    "routes-dangeureuses": ["douane", "atlanta", "woodbury", "rencontres-ennemis", "horde"],
    "rencontres-ennemis": ["routes-dangeureuses"],
    "horde": ["routes-dangeureuses"]
}

EMOJI_MAP = {
    "1️⃣": 0,
    "2️⃣": 1,
    "3️⃣": 2,
    "4️⃣": 3,
    "5️⃣": 4
}

@bot.command()
async def deplacer(ctx):
    joueur = ctx.author
    await ctx.message.delete()  # Supprime le message du joueur

    # Détecte channel actuel par nom
    current_channel = ctx.channel.name.lower().replace(" ", "-")
    if current_channel not in MAP_CHANNELS:
        await ctx.send("❌ Tu ne peux pas te déplacer depuis ce channel.", delete_after=5)
        return

    destinations = MAP_CHANNELS[current_channel]
    embed = discord.Embed(
        title=f"🗺️ Déplacements depuis {current_channel}",
        description="\n".join([f"{list(EMOJI_MAP.keys())[i]} : {dest}" for i, dest in enumerate(destinations)]),
        color=discord.Color.blue()
    )
    msg = await ctx.send(embed=embed)

    # Ajoute réactions pour choix
    for i in range(len(destinations)):
        await msg.add_reaction(list(EMOJI_MAP.keys())[i])

    def check(reaction, user):
        return user == joueur and str(reaction.emoji) in EMOJI_MAP

    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        choix_index = EMOJI_MAP[str(reaction.emoji)]
        nouvelle_dest = destinations[choix_index]

        # Nettoyage du nom pour correspondre au rôle
        old_role_name = f"accès-{current_channel}".lower().replace(" ", "-")
        new_role_name = f"accès-{nouvelle_dest}".lower().replace(" ", "-")

        old_role = discord.utils.find(lambda r: r.name.lower().replace(" ", "-") == old_role_name, ctx.guild.roles)
        new_role = discord.utils.find(lambda r: r.name.lower().replace(" ", "-") == new_role_name, ctx.guild.roles)

        if old_role:
            await joueur.remove_roles(old_role)
        if new_role:
            await joueur.add_roles(new_role)

        await ctx.send(f"✅ {joueur.mention} se déplace vers **{nouvelle_dest}** !", delete_after=5)
        await msg.delete()

    except asyncio.TimeoutError:
        await ctx.send("⏱️ Temps écoulé, déplacement annulé.", delete_after=5)
        await msg.delete()


# -------------------
# ⚡ Exploration
# -------------------

# --- Liste des encounters ---
encounters = [
    {"type": "zombie", "description": "Un rôdeur surgit de nulle part !", "degats": 2, "stat": "AGI"},
    {"type": "humain", "description": "Un humain hostile vous attaque !", "degats": 3, "stat": "AGI"},
    {"type": "piege", "description": "Tu marches dans un piège !", "degats": 1, "stat": "AGI"},
    {"type": "forcer", "description": "Tu pousses un mur lourd pour passer.", "stat": "FOR", "succes": "💪 Tu réussis à pousser le mur !", "echec": "❌ Impossible de le bouger..."},
    {"type": "technique", "description": "Tu tentes de crocheter une porte.", "stat": "TEC", "succes": "🔧 La porte s'ouvre !", "echec": "❌ Échec, la serrure est trop complexe."},
    {"type": "perception", "description": "Tu fouilles un bâtiment à la recherche d'objets.", "stat": "PER", "items": {"pistolet": 6}},
    {"type": "perception", "description": "Tu cherches des rations dans un supermarché abandonné.", "stat": "PER", "rations": 10},
    {"type": "bonus", "description": "Tu trouves un petit refuge.", "moral": 1},
    {"type": "forcer", "description": "Tu déplaces un débris pour progresser.", "stat": "FOR", "succes": "💪 Débris déplacé avec succès !", "echec": "❌ Trop lourd à déplacer."},
    {"type": "technique", "description": "Tu désactives un piège mécanique.", "stat": "TEC", "succes": "🔧 Piège désactivé !", "echec": "❌ Tu n'arrives pas à le désactiver."},
    {"type": "perception", "description": "Tu observes les alentours à la recherche de danger.", "stat": "PER", "succes": "👀 Rien à signaler, tu avances prudemment.", "echec": "⚠️ Tu rates un signe important et trébuches."},
    {"type": "zombie", "description": "Une horde de rôdeurs surgit !", "degats": 4, "stat": "AGI"},
    {"type": "trouve", "description": "Tu découvres un coffre abandonné.", "stat": "PER", "items": {"fusil": 10}},
    {"type": "trouve", "description": "Tu découvres un coffre abandonné.", "stat": "PER", "items": {"batte": 10}},
    {"type": "trouve", "description": "Tu découvres un coffre abandonné.", "stat": "PER", "items": {"caillou": 10}},
    {"type": "trouve", "description": "Tu découvres un coffre abandonné.", "stat": "PER", "items": {"pied_de_biche": 10}},
    {"type": "trouve", "description": "Tu découvres un coffre abandonné.", "stat": "PER", "items": {"carabine": 10}},
    {"type": "trouve", "description": "Tu découvres un coffre abandonné.", "stat": "PER", "items": {"fusil": 10}},
    {"type": "trouve", "description": "Tu découvres un coffre abandonné.", "stat": "PER", "items": {"fusil_assault": 5}},
    {"type": "trouve", "description": "Tu découvres un coffre abandonné.", "stat": "PER", "items": {"fusil_sniper": 1}},
    {"type": "bonus", "description": "Tu trouves un endroit tranquille pour te reposer.", "moral": 2},
    {"type": "trouve", "description": "Tu récupères quelques rations oubliées.", "stat": "PER", "rations": 2},
]

# --- Commande explorer ---
@bot.command()
async def explorer(ctx):
    joueur_discord = f"{ctx.author.name}#{ctx.author.discriminator}"

    # Charger personnages
    try:
        with open(PERSOS_FILE, "r", encoding="utf-8") as f:
            persos = yaml.safe_load(f) or {}
    except FileNotFoundError:
        await ctx.send("❌ Fichier persos.yaml introuvable.")
        return

    # Identifier le personnage
    personnage = None
    for p_name, p_data in persos.items():
        if p_data.get("discord") == joueur_discord:
            personnage = p_name
            break
    if not personnage:
        await ctx.send("❌ Tu n’as pas encore choisi de personnage !")
        return

    p = persos[personnage]

    # Vérifier énergie
    if p["energie"] <= 0:
        await ctx.send("⚠️ Tu n’as plus d’énergie pour explorer !")
        return
    p["energie"] -= 1
    effects = [f"⚡ Énergie -1 ! Énergie restante : {p['energie']}/{p['energie_max']}"]

    # Tirage encounter
    event = random.choice(encounters)
    desc = event["description"]
    stat = event.get("stat")

    # Calcul chance selon stat
    chance = 0.5
    if stat:
        value = p["stats"].get(stat, 10)
        chance = min(max((value - 10) / (18 - 10), 0), 0.95)

    # Charger inventaires
    try:
        with open(INVENTAIRES_FILE, "r", encoding="utf-8") as f:
            inventaires = yaml.safe_load(f) or {}
    except FileNotFoundError:
        inventaires = {}
    if personnage not in inventaires:
        inventaires[personnage] = {}

    # Traitement selon type
    if event["type"] in ["zombie", "humain", "piege"]:
        if random.random() < chance:
            effects.append(f"😅 Tu esquives l'attaque ou le piège !")
        else:
            degats = event.get("degats", 1)
            p["sante"] = max(p["sante"] - degats, 0)
            effects.append(f"💀 Tu subis {degats} dégâts ! Santé : {p['sante']}/{p['sante_max']}")

    elif event["type"] in ["trouve", "item"]:
        if random.random() < chance:
            if "rations" in event:
                p["rations"] += event["rations"]
                effects.append(f"🥫 Tu trouves {event['rations']} rations ! Total : {p['rations']}")
            if "items" in event:
                for item, qty in event["items"].items():
                    inventaires[personnage][item] = inventaires[personnage].get(item, 0) + qty
                    effects.append(f"🎁 Tu trouves {qty} x **{item}** !")
        else:
            effects.append("❌ Tu ne trouves rien cette fois-ci…")

    elif event["type"] in ["bonus", "forcer", "technique", "perception"]:
        if random.random() < chance:
            succes = event.get("succes") or f"Réussite !"
            if "moral" in event:
                p["moral"] = min(p["moral"] + event["moral"], p["moral_max"])
                succes += f" 🧠 Moral +{event['moral']}"
            effects.append(succes)
        else:
            echec = event.get("echec") or "Échec."
            effects.append(echec)

    # Sauvegarder personnage et inventaire
    with open(PERSOS_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(persos, f, sort_keys=False, allow_unicode=True)
    with open(INVENTAIRES_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(inventaires, f, sort_keys=False, allow_unicode=True)

    # Embed
    embed = discord.Embed(title=f"🌲 Exploration de {personnage}", description=desc, color=discord.Color.orange())
    embed.add_field(name="Effets", value="\n".join(effects), inline=False)
    embed.add_field(name="⚡ Énergie restante", value=f"{p['energie']}/{p['energie_max']}", inline=False)
    await ctx.send(embed=embed)

# -------------------
# ⚡ Commande donner (MJ)
# -------------------
@bot.command()
@commands.has_role("maitre du jeux")
async def donner(ctx, personnage: str, item: str, quantite: int):
    """Donne un item à un personnage."""
    personnage = personnage.strip()
    item = item.strip()
    
    # Charger inventaires
    inventaires = charger_yaml(INVENTAIRES_FILE)
    if personnage not in inventaires:
        inventaires[personnage] = {}

    # Ajouter la quantité (même si l'item n'existait pas)
    inventaires[personnage][item] = inventaires[personnage].get(item, 0) + quantite

    # Sauvegarder
    sauvegarder_yaml(INVENTAIRES_FILE, inventaires)

    await ctx.send(f"✅ {quantite} x **{item}** ont été ajoutés à **{personnage}**.")

# -------------------
# ⚡ Commande pêche
# -------------------
@bot.command()
async def peche(ctx):
    joueur_discord = f"{ctx.author.name}#{ctx.author.discriminator}"
    perso_name, p = get_perso_discord(joueur_discord)
    
    if not p:
        await ctx.send("❌ Tu n’as pas encore choisi de personnage !")
        return

    if p["focus"] <= 0:
        await ctx.send("⚠️ Tu n’as plus de focus pour pêcher ! Utilise !veille pour récupérer du focus.")
        return

    # Dépense 1 point de focus
    p["focus"] -= 1

    # Calcul de la chance avec base 30%, augmente selon TEC, max 100% si TEC >= 18
    tec = p["stats"].get("TEC", 10)
    chance = min(max(0.6 + (tec - 10) * 0.1, 0), 1.0)
    if tec >= 18:
        chance = 1.0

    # Résultat de la pêche
    if random.random() < chance:
        rations_gagnees = random.randint(5, 15)
        p["rations"] += rations_gagnees
        result_text = f"🥫 Tu as pêché du poisson, assez pour te faire {rations_gagnees} rations ! Total : {p['rations']}"
    else:
        result_text = "❌ Tu n'as rien trouvé malgré tes efforts !"

    # Sauvegarde
    persos = charger_yaml(PERSOS_FILE)
    persos[perso_name] = p
    sauvegarder_yaml(PERSOS_FILE, persos)

    # Embed résultat
    embed = discord.Embed(
        title=f"🎣 Pêche de {perso_name}",
        description=f"Chance de succès : {int(chance*100)}%\n{result_text}\n⚡ Focus restant : {p['focus']}",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

# -------------------
# ⚡ Commande manger
# -------------------
@bot.command()
async def manger(ctx, quantite: int = 5):
    joueur_discord = f"{ctx.author.name}#{ctx.author.discriminator}"
    perso_name, p = get_perso_discord(joueur_discord)
    if not p:
        await ctx.send("❌ Tu n’as pas encore choisi de personnage !")
        return
    if quantite <= 0:
        await ctx.send("⚠️ La quantité doit être supérieure à 0.")
        return
    if p["rations"] < quantite:
        await ctx.send(f"⚠️ Tu n’as pas assez de rations pour manger {quantite} rations !")
        return

    energie_gagnee = quantite // 5
    if energie_gagnee == 0:
        await ctx.send("⚠️ Il te faut au moins 5 rations pour récupérer 1 point d'énergie.")
        return

    p["rations"] -= quantite
    p["energie"] = min(p["energie"] + energie_gagnee, p["energie_max"])
    p["sante"] = min(p["sante"] + energie_gagnee, p["sante_max"])
    persos = charger_yaml(PERSOS_FILE)
    persos[perso_name] = p
    sauvegarder_yaml(PERSOS_FILE, persos)

    embed = discord.Embed(
        title=f"🍽️ {perso_name} mange {quantite} rations",
        description=f"✅ {energie_gagnee} point(s) d'énergie récupéré(s) !\n⚡ Énergie actuelle : {p['energie']}/{p['energie_max']}\n🥫 Rations restantes : {p['rations']}",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# -------------------
# ⚡ Commande combat public
# -------------------
@bot.command()
@commands.has_role("maitre du jeux")
async def combat(ctx, nom_rodeur: str):
    global combat_actif
    rodeurs = charger_yaml(RODEURS_FILE)
    if nom_rodeur not in rodeurs:
        await ctx.send(f"❌ Rôdeur `{nom_rodeur}` introuvable.")
        return

    combat_actif = {
        "rodeur": rodeurs[nom_rodeur].copy(),
        "participants": {}
    }

    embed = discord.Embed(
        title=f"⚔️ Combat public contre {nom_rodeur}",
        color=discord.Color.orange()
    )
    embed.add_field(name="PV rôdeur", value=f"{combat_actif['rodeur']['sante']}")
    await ctx.send(embed=embed)

# -------------------
# ⚡ Commande attaque
# -------------------
@bot.command()
async def attaque(ctx, arme: str):
    global combat_actif
    if "rodeur" not in combat_actif or not combat_actif["rodeur"]:
        await ctx.send("❌ Aucun rôdeur n’est présent actuellement.")
        return

    joueur_discord = f"{ctx.author.name}#{ctx.author.discriminator}"
    perso_name, p = get_perso_discord(joueur_discord)
    if not p:
        await ctx.send("❌ Aucun personnage associé à ton compte.")
        return

    # Vérifie inventaire
    inventaires = charger_yaml(INVENTAIRES_FILE)
    if perso_name not in inventaires:
        inventaires[perso_name] = {}
    if inventaires[perso_name].get(arme, 0) <= 0:
        await ctx.send(f"❌ {perso_name} n'a plus de {arme} pour attaquer !")
        return

    # Consomme l'arme
    inventaires[perso_name][arme] -= 1
    sauvegarder_yaml(INVENTAIRES_FILE, inventaires)

    # Met à jour le participant
    if joueur_discord not in combat_actif["participants"]:
        combat_actif["participants"][joueur_discord] = p.copy()
    participant = combat_actif["participants"][joueur_discord]

    bonus = charger_yaml(ARMES_FILE).get(arme, {}).get("bonus", 0)
    z = combat_actif["rodeur"]

    actions = []

    # Attaque du joueur
    de = random.randint(1, 6)
    total = de + bonus
    esquive_rodeur = random.randint(1, 20)
    if esquive_rodeur <= z.get("AGI", 10):
        actions.append(f"💨 {z['nom']} esquive l'attaque de {perso_name} avec son **{arme}** !")
    else:
        z["sante"] -= total
        pv_rodeur = max(z["sante"], 0)
        actions.append(f"🎯 {perso_name} attaque avec son **{arme}** et inflige {total} dégâts ! PV rôdeur : {pv_rodeur}")

        # Vérifie si le rôdeur est mort
        if z["sante"] <= 0:
            actions.append(f"✅ {z['nom']} a été vaincu !")
            combat_actif = {}
            embed = discord.Embed(
                title="⚔️ Combat terminé",
                description="\n".join(actions),
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            return

    # Contre-attaque du rôdeur
    de_contre = random.randint(1, 6)
    total_contre = de_contre + z.get("bonus", 0)
    esquive_joueur = random.randint(1, 20)
    if esquive_joueur <= participant.get("stats", {}).get("AGI", 10):
        actions.append(f"💨 {perso_name} esquive la contre-attaque de {z['nom']} !")
    else:
        participant["sante"] -= total_contre
        pv_joueur = max(participant["sante"], 0)
        actions.append(f"⚔️ {z['nom']} contre-attaque et inflige {total_contre} dégâts à {perso_name} ! PV restant : {pv_joueur}")

        # Vérifie si le joueur est mort
        if participant["sante"] <= 0:
            actions.append(f"💀 {perso_name} est tombé au combat !")

    # Embed résultat
    embed = discord.Embed(
        title=f"⚔️ Combat contre {z['nom']}",
        description="\n".join(actions),
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed)

    # Sauvegarder PV joueurs dans persos
    persos = charger_yaml(PERSOS_FILE)
    for j, stats in combat_actif.get("participants", {}).items():
        nom_perso, _ = get_perso_discord(j)
        if nom_perso:
            persos[nom_perso]["sante"] = stats["sante"]
    sauvegarder_yaml(PERSOS_FILE, persos)



bot.run("#discord bot token here")
