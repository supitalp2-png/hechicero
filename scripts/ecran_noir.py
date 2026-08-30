#!/usr/bin/env python3
"""
ecran_noir.py — Constat et corrélation des pannes d'écran noir (TICKET-149).

POURQUOI CET OUTIL EXISTE
─────────────────────────
Le 2026-08-25, en descendant les étages un par un pendant une panne, on a
localisé le défaut : le récepteur HDMI de la dalle décroche et ne se
re-verrouille pas. Le Pi, lui, émet un signal parfaitement valide. Seul un
cycle HPD (débrancher le câble) le réinitialise.

Ce qu'on ignore encore, c'est **ce qui déclenche le décrochage**. La durée sans
signal semblait coupable — 60 s récupère, 1 h 48 non — mais une extinction de
13 h 54 le 22/08 s'est réveillée sans incident. Le phénomène est intermittent,
et *on n'a aucun décompte* : rien n'enregistre si un réveil a réussi ou échoué.

⚠️ La panne est invisible depuis le Pi. Tous les indicateurs sont au vert
pendant qu'elle dure — c'est précisément ce qui a fait chercher au mauvais
étage pendant des mois. **Seul un humain qui regarde la dalle peut la
signaler.** D'où cet outil.

USAGE
─────
    python3 scripts/ecran_noir.py signaler      # PENDANT la panne, avant de débrancher
    python3 scripts/ecran_noir.py rapport       # une fois assez d'occurrences

`signaler` capture l'état complet en quelques secondes et l'archive. À lancer
avant toute tentative de récupération : débrancher le câble détruit les
preuves.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
JOURNAL = DATA_DIR / "ecran_noir.log"
DPMS_LOG = DATA_DIR / "screen_dpms.log"
HEARTBEAT = DATA_DIR / "kiosk_heartbeat.json"

CMD_TIMEOUT = 6


import os   # noqa: E402

# ── Environnement Wayland (TICKET-149, corrigé au 1er essai réel) ────────────
# `wlr-randr` parle au compositeur par une socket du répertoire de session. Le
# daemon des boutons tourne en `User=root`, sans session utilisateur : il n'a ni
# XDG_RUNTIME_DIR ni WAYLAND_DISPLAY. Résultat du premier constat pris au
# bouton : « XDG_RUNTIME_DIR is invalid or not set », et **tout l'étage
# compositeur perdu** — précisément l'un de ceux qu'on doit départager.
# Les mêmes valeurs que `screen_dpms.sh`, qui les pose déjà en repli.
ENV_WAYLAND = {
    **os.environ,
    "XDG_RUNTIME_DIR": os.environ.get("XDG_RUNTIME_DIR") or "/run/user/1000",
    "WAYLAND_DISPLAY": os.environ.get("WAYLAND_DISPLAY") or "wayland-0",
}


def run(cmd: list[str], timeout: int = CMD_TIMEOUT) -> str:
    """Jamais d'exception : un constat partiel vaut mieux que pas de constat."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, env=ENV_WAYLAND)
        return ((p.stdout or "") + (p.stderr or "")).strip() or "(vide)"
    except FileNotFoundError:
        return f"(commande absente : {cmd[0]})"
    except subprocess.TimeoutExpired:
        return f"(délai dépassé après {timeout}s)"
    except Exception as e:  # noqa: BLE001
        return f"(erreur : {e})"


def lire(chemin: str, defaut: str = "?") -> str:
    try:
        return Path(chemin).read_text(encoding="utf-8").strip()
    except Exception:
        return defaut


def temperature_c() -> float | None:
    brut = lire("/sys/class/thermal/thermal_zone0/temp", "")
    try:
        return round(int(brut) / 1000.0, 1)
    except ValueError:
        return None


def charge_cpu() -> float | None:
    try:
        return float(lire("/proc/loadavg", "").split()[0])
    except (ValueError, IndexError):
        return None


# ── Lecture du journal d'écran ───────────────────────────────────────────────

_LIGNE_DPMS = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[([^\]]*)\] (\w+)\s+—\s+(.*)$"
)


def evenements_dpms() -> list[dict]:
    """Journal d'écran analysé, du plus ancien au plus récent."""
    evts: list[dict] = []
    try:
        lignes = DPMS_LOG.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return evts
    for ligne in lignes:
        m = _LIGNE_DPMS.match(ligne.strip())
        if not m:
            continue
        horodatage, appelant, action, detail = m.groups()
        try:
            quand = datetime.strptime(horodatage, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        evts.append({
            "quand": quand, "appelant": appelant,
            "action": action, "detail": detail,
        })
    return evts


def chemin_reveil(appelant: str) -> str:
    """
    Par quel chemin la dalle a-t-elle été rallumée : 'tactile', 'bouton', ou autre.

    ── Hypothèse de Thomas, 2026-08-26 ───────────────────────────────────────
    « J'intuite que ça se passe quand on appuie sur les boutons et pas quand on
    appuie sur l'écran. »

    Elle est testable sans rien ajouter, parce que les deux chemins sont déjà
    distingués dans le journal depuis le TICKET-123 :

      · **tactile** — swayidle observe les entrées Wayland et lance
        `screen_dpms.sh on` lui-même. Appelant : `sh<-swayidle`.
      · **bouton**  — swayidle ne voit JAMAIS le GPIO, lu par un processus
        Python. C'est `buttons_daemon` qui appelle le script directement.
        Appelant : `runuser<-python3` ou `python3<-…`.

    ⛔ **CETTE DISTINCTION NE FONCTIONNE PAS, et il ne faut pas s'y fier.**
    Corrigé le 2026-08-30 après que Thomas ait contesté le résultat — à juste
    titre. Depuis le TICKET-123, `buttons_daemon` envoie une **frappe virtuelle
    au compositeur** à chaque appui, pour que swayidle réarme son compte à
    rebours. Un appui bouton produit donc un réveil `[sh<-swayidle]`,
    strictement indiscernable d'un appui sur la dalle.

    Autrement dit l'appelant décrit **qui a appelé le script**, pas **ce qui a
    réveillé l'appareil**. Le rapport annonçait « tactile » pour la totalité des
    réveils, y compris ceux déclenchés au bouton, et fermait l'hypothèse de
    Thomas sur une mesure qui ne la testait pas.

    On renvoie donc `indéterminé` pour les réveils par swayidle plutôt qu'une
    étiquette fausse. Mieux vaut une case vide qu'une case trompeuse — c'est
    exactement la leçon de `feedback_absence_de_signalement`.

    Pour trancher un jour l'hypothèse, il faudra une trace côté
    `buttons_daemon` : journaliser l'appui AVANT la frappe virtuelle, avec son
    horodatage, et corréler. Tant que ça n'existe pas, la question reste ouverte.
    """
    a = (appelant or "").lower()
    if "swayidle" in a:
        return "indéterminé"      # bouton OU tactile — trancher via la marque
    if "python" in a or "runuser" in a:
        return "bouton"           # appel direct du daemon, sans passer par swayidle
    if "ssh" in a or "bash" in a:
        return "manuel"
    return "autre"


# Fenêtre pendant laquelle une marque d'appui explique le réveil qui suit.
# La frappe virtuelle part juste après la marque, swayidle réagit dans la
# foulée : quelques secondes suffisent largement.
FENETRE_MARQUE_S = 8


def origine_reveil(evts: list[dict], indice: int) -> str:
    """
    Origine RÉELLE d'un réveil : bouton ou tactile (TICKET-153).

    L'appelant du script ne suffit pas — la frappe virtuelle du TICKET-123 fait
    arriver les deux chemins par swayidle. `buttons_daemon` dépose donc une
    marque juste avant d'envoyer cette frappe ; un réveil précédé de cette
    marque de moins de `FENETRE_MARQUE_S` secondes vient d'un bouton.

    ⚠️ C'est cette fonction qui répond à la question ouverte depuis des mois.
    Si elle se trompe, on repart sur une fausse piste — d'où la fenêtre courte
    et l'exigence que la marque PRÉCÈDE le réveil, jamais l'inverse.
    """
    direct = chemin_reveil(evts[indice]["appelant"])
    if direct != "indéterminé":
        return direct
    quand = evts[indice]["quand"]
    for e in reversed(evts[:indice]):
        ecart = (quand - e["quand"]).total_seconds()
        if ecart > FENETRE_MARQUE_S:
            break
        if "buttons_daemon" in e["appelant"] or "appui" in e["action"]:
            return "bouton"
    return "tactile"


def resumer_drm(etat: str) -> str:
    """
    Extrait les seuls objets DRM ACTIFS, avec leur identité.

    Première version : un filtre par motif sur `fb=`, `crtc-pos`, `src-pos`.
    Illisible — le premier constat réel a produit trente lignes `fb=0` sans les
    en-têtes `plane[N]`, donc impossible de savoir de quel plan on parlait. Un
    diagnostic qu'on ne sait pas relire ne diagnostique rien.

    Un objet inactif (`crtc=(null)`, `enable=0`) ne raconte rien : sur ce Pi,
    56 plans sur 57 sont inutilisés en permanence. On ne garde que ce qui
    travaille, et on garde son nom avec.
    """
    blocs: list[str] = []
    courant: list[str] = []
    for ligne in etat.splitlines():
        if re.match(r"^(plane|crtc|connector)\[", ligne):
            if courant:
                blocs.append("\n".join(courant))
            courant = [ligne]
        elif courant:
            courant.append(ligne)
    if courant:
        blocs.append("\n".join(courant))

    garde: list[str] = []
    for bloc in blocs:
        inactif = "crtc=(null)" in bloc or re.search(r"^\s*enable=0", bloc, re.M)
        if inactif:
            continue
        interessantes = [l for l in bloc.splitlines()
                         if re.match(r"^(plane|crtc|connector)\[", l)
                         or re.search(r"(crtc=|active=|enable=|mode:|fb=\d|size=|"
                                      r"crtc-pos|src-pos|tmds_char_rate|output_)", l)]
        garde.append("\n".join(interessantes))

    if not garde:
        return etat[:800] or "(état DRM illisible)"
    return ("\n".join(garde)[:2000]
            + f"\n({len(blocs) - len(garde)} objet(s) inactif(s) omis)")


def instant_demarrage() -> datetime | None:
    """Heure du dernier démarrage, d'après `/proc/uptime`."""
    try:
        secondes = float(lire("/proc/uptime", "").split()[0])
    except (ValueError, IndexError):
        return None
    from datetime import timedelta
    return datetime.now() - timedelta(seconds=secondes)


def dernier_reveil(avant: datetime,
                   depuis_demarrage: datetime | None = None) -> tuple[dict | None, float | None]:
    """
    Dernier réveil précédant `avant`, et la durée d'extinction qui l'a précédé.

    C'est LA donnée du ticket : chaque panne constatée doit pouvoir être
    rattachée à l'extinction dont la dalle n'est pas revenue.

    ⚠️ **Un réveil antérieur au démarrage courant ne compte pas.** Constaté lors
    du premier essai grandeur nature (2026-08-26) : un constat pris 19 min après
    un redémarrage se voyait attribuer le réveil de la veille et une exposition
    de 12,48 h — une donnée entièrement fausse, dans le tableau même qui doit
    trancher la cause. En usage normal la capture précède le redémarrage, donc
    le cas ne se produit pas ; mais un essai, ou un appui parasite après un
    boot, empoisonnerait la statistique sans que rien ne le signale.
    ⚠️⚠️ **Le filtre est facultatif, et il DOIT le rester.** `rapport()` analyse
    des incidents passés, tous antérieurs au démarrage courant : appliquer la
    borne par défaut les effacerait tous, et le rapport annoncerait zéro panne
    sur une base pleine. Seul `signaler()`, qui décrit l'instant présent, passe
    `depuis_demarrage`.
    """
    evts = [e for e in evenements_dpms() if e["quand"] <= avant]
    if depuis_demarrage is not None:
        evts = [e for e in evts if e["quand"] >= depuis_demarrage]
    reveil = None
    for e in reversed(evts):
        if e["action"] == "on" and "rebond" in e["detail"]:
            reveil = e
            break
    if reveil is None:
        return None, None
    extinction = None
    for e in reversed([x for x in evts if x["quand"] < reveil["quand"]]):
        if e["action"] == "off":
            extinction = e
            break
    if extinction is None:
        return reveil, None
    return reveil, (reveil["quand"] - extinction["quand"]).total_seconds()


# ── Constat ─────────────────────────────────────────────────────────────────

def signaler(note: str | None) -> int:
    maintenant = datetime.now()
    # Seul le constat borne au démarrage : il décrit l'instant présent, où un
    # réveil d'avant le boot n'a aucun sens. Le rapport, lui, ne borne jamais.
    reveil, expo = dernier_reveil(maintenant, depuis_demarrage=instant_demarrage())

    battement = "?"
    try:
        d = json.loads(HEARTBEAT.read_text(encoding="utf-8"))
        age = (maintenant.timestamp() - d.get("ts", 0) / 1000.0)
        battement = (f"âge {age:.0f}s · écran={d.get('screen')} "
                     f"· overlay={d.get('overlay')} · page {d.get('page_age_s')}s")
    except Exception:
        pass

    lignes = [
        "=" * 78,
        f"[{maintenant:%Y-%m-%d %H:%M:%S}] ÉCRAN NOIR CONSTATÉ",
        "=" * 78,
    ]
    if note:
        lignes.append(f"note : {note}")

    lignes.append("")
    lignes.append("── exposition (la donnée du ticket) ──")
    if reveil is not None:
        lignes.append(f"dernier réveil : {reveil['quand']:%Y-%m-%d %H:%M:%S} "
                      f"[{reveil['appelant']}]")
        # Hypothèse de Thomas (2026-08-26) : la panne suivrait les réveils par
        # BOUTON et pas les réveils tactiles. Sans cette ligne, la corrélation
        # n'aurait jamais de données du côté des pannes.
        lignes.append(f"chemin réveil  : {chemin_reveil(reveil['appelant'])}")
        lignes.append(f"noir depuis    : {(maintenant - reveil['quand']).total_seconds():.0f}s")
    else:
        # Le plus souvent : aucun réveil depuis le démarrage. Le dire ainsi,
        # plutôt que de remonter un réveil d'avant le boot — mieux vaut une
        # donnée absente qu'une donnée fausse.
        boot = instant_demarrage()
        lignes.append("dernier réveil : AUCUN depuis le démarrage"
                      + (f" ({boot:%Y-%m-%d %H:%M:%S})" if boot else ""))
        lignes.append("chemin réveil  : inconnu")
    lignes.append(f"extinction précédente : "
                  + (f"{expo:.0f}s ({expo/3600:.2f} h)" if expo is not None else "inconnue"))

    lignes.append("")
    lignes.append("── contexte machine ──")
    lignes.append(f"température SoC : {temperature_c()} °C")
    lignes.append(f"charge CPU      : {charge_cpu()}")
    lignes.append(f"throttled       : {run(['vcgencmd', 'get_throttled'])}")
    lignes.append(f"uptime          : {lire('/proc/uptime', '?').split()[0]}s")
    lignes.append(f"battement page  : {battement}")

    lignes.append("")
    lignes.append("── ce que le Pi croit afficher ──")
    lignes.append(run(["wlr-randr"]))

    lignes.append("")
    lignes.append("── vue du noyau ──")
    for nom in ("status", "enabled", "dpms"):
        lignes.append(f"card1-HDMI-A-1/{nom} = "
                      + lire(f"/sys/class/drm/card1-HDMI-A-1/{nom}"))

    lignes.append("")
    lignes.append("── état DRM (CRTC actif ? plan dimensionné ?) ──")
    # ⚠️ Deux chemins, et l'ordre compte. Lancé par buttons_daemon (User=root,
    # NoNewPrivileges=true), `sudo` est CASSÉ — c'est la leçon du TICKET-121 :
    # NoNewPrivileges fait échouer sudo en silence. Mais root n'en a pas besoin,
    # la lecture directe suffit. Lancé à la main depuis SSH par `thomas`, c'est
    # l'inverse. On tente donc le direct, puis sudo.
    etat = lire("/sys/kernel/debug/dri/1/state", "")
    if not etat:
        etat = run(["sudo", "-n", "cat", "/sys/kernel/debug/dri/1/state"])
    lignes.append(resumer_drm(etat))

    lignes.append("")
    lignes.append("── 10 derniers événements écran ──")
    lignes.append("\n".join(
        f"{e['quand']:%m-%d %H:%M:%S} [{e['appelant']}] {e['action']} — {e['detail']}"
        for e in evenements_dpms()[-10:]
    ))
    lignes.append("")
    lignes.append("")

    texte = "\n".join(lignes)
    try:
        with JOURNAL.open("a", encoding="utf-8") as fh:
            fh.write(texte)
    except Exception as e:  # noqa: BLE001
        print(f"⚠️  écriture impossible dans {JOURNAL} : {e}", file=sys.stderr)
        print(texte)
        return 1

    print(f"✅ constat enregistré dans {JOURNAL.name}")
    if expo is not None:
        print(f"   extinction précédente : {expo/3600:.2f} h")
    print(f"   température : {temperature_c()} °C")
    print()
    print("Tu peux maintenant récupérer l'image (débrancher / rebrancher le HDMI).")
    print("Note laquelle de ces étapes a marché, c'est l'information la plus utile :")
    print("  1. ./scripts/screen_dpms.sh rescue")
    print("  2. echo detect | sudo tee /sys/class/drm/card1-HDMI-A-1/status")
    print("  3. débrancher le câble")
    return 0


# ── Corrélation ─────────────────────────────────────────────────────────────

_ENTETE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] ÉCRAN NOIR CONSTATÉ")
_EXPO = re.compile(r"^extinction précédente : (?:(\d+)s|inconnue)")
_TEMP = re.compile(r"^température SoC : ([\d.]+)")
_CHEMIN = re.compile(r"^chemin réveil  : (\w+)")


def dedoublonner(pannes: list[dict]) -> list[dict]:
    """
    Un même incident signalé plusieurs fois ne compte qu'une fois.

    ── Pourquoi c'est indispensable ──────────────────────────────────────────
    Constaté dès le premier usage réel (2026-08-26) : deux constats à 43 s
    d'écart pour une seule panne. Rien d'anormal — sur un écran noir on doute
    d'avoir bien appuyé, et on recommence. Mais **gonfler le nombre de pannes
    fausse exactement la statistique que ce rapport doit établir** : on
    comparerait 6 « pannes » à 84 réveils sains alors qu'il y en a 3.

    Règle : **une extinction ne peut échouer qu'une fois.** Deux constats
    rattachés au même réveil décrivent donc le même incident. C'est un critère
    de fond, pas une fenêtre de temps arbitraire — deux pannes réelles sont
    forcément séparées par un réveil réussi.

    On conserve le premier constat de chaque incident : c'est celui pris le
    plus près de la panne, donc le plus fidèle.
    """
    vus: set = set()
    uniques: list[dict] = []
    for p in sorted(pannes, key=lambda x: x.get("quand", "")):
        try:
            quand = datetime.strptime(p["quand"], "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError, KeyError):
            uniques.append(p)      # horodatage illisible : on ne fusionne pas à l'aveugle
            continue
        reveil, _ = dernier_reveil(quand)
        cle = reveil["quand"] if reveil is not None else p["quand"]
        if cle in vus:
            continue
        vus.add(cle)
        uniques.append(p)
    return uniques


def separer_reveils(pannes: list[dict], reussis: list[tuple]) -> tuple[list, set]:
    """
    Sépare les réveils réussis de ceux qui ont produit une panne.

    ⚠️ **Un réveil qui a échoué ne doit surtout pas compter parmi les
    réussites.** Première version : appariement par horodatage à la minute.
    Faux — une panne est constatée quelques minutes après le réveil qui l'a
    produite (le 25/08 : réveil à 20:01:44, constat à 20:05). Le réveil fautif
    se retrouvait alors des DEUX côtés de la comparaison, ce qui biaise
    exactement la statistique que ce rapport doit établir : un échec compté
    comme succès rapproche artificiellement les deux populations et pousse à
    conclure « la durée n'explique rien » même si elle expliquait tout.

    On rattache donc chaque panne à son réveil par la même règle que
    `signaler` : le dernier réveil qui la précède.
    """
    fautifs: set = set()
    for p in pannes:
        try:
            quand = datetime.strptime(p["quand"], "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            continue
        reveil, _ = dernier_reveil(quand)
        if reveil is not None:
            fautifs.add(reveil["quand"])
    return [r for r in reussis if r[0] not in fautifs], fautifs


def ignorer(horodatage: str, raison: str) -> int:
    """
    Marque un constat comme n'étant pas une vraie panne.

    Un essai, un double appui, un doute levé après coup : ces entrées faussent
    le seul chiffre qui compte. Le 2026-08-30, le rapport annonçait deux pannes
    là où Thomas n'en comptait qu'une — et deux pannes contre une, ça change
    tout quand l'échantillon est de cette taille.

    ⚠️ **On n'efface rien.** L'entrée est marquée, pas supprimée : un constat
    écarté par erreur doit rester relisible, et savoir qu'une piste a été
    écartée vaut souvent plus que le résultat final. Le rapport saute les
    entrées portant cette marque.
    """
    try:
        contenu = JOURNAL.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:  # noqa: BLE001
        print(f"⛔ journal illisible : {e}")
        return 1

    entete = f"[{horodatage}] ÉCRAN NOIR CONSTATÉ"
    if entete not in contenu:
        print(f"⛔ aucun constat à « {horodatage} ».")
        print("   Horodatages présents :")
        for m in _ENTETE.finditer(contenu):
            print(f"     {m.group(1)}")
        return 1
    if f"{entete}\nÉCARTÉ" in contenu:
        print(f"Le constat du {horodatage} est déjà écarté.")
        return 0

    contenu = contenu.replace(
        entete,
        f"{entete}\nÉCARTÉ : {raison} "
        f"(marqué le {datetime.now():%Y-%m-%d %H:%M:%S})", 1)
    JOURNAL.write_text(contenu, encoding="utf-8")
    print(f"✅ constat du {horodatage} écarté — {raison}")
    print("   L'entrée est conservée dans le journal, seulement marquée.")
    return 0


def rapport() -> int:
    """
    Croise les pannes constatées avec les réveils réussis.

    La question à laquelle ce rapport doit répondre : **qu'est-ce qui distingue
    une extinction dont la dalle revient d'une extinction dont elle ne revient
    pas ?** Durée ? Température ? Rien de visible ?
    """
    pannes: list[dict] = []
    try:
        contenu = JOURNAL.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        contenu = ""

    courante: dict | None = None
    for ligne in contenu.splitlines():
        m = _ENTETE.match(ligne)
        if m:
            if courante:
                pannes.append(courante)
            courante = {"quand": m.group(1), "expo_s": None,
                        "temp": None, "chemin": None, "ecarte": False}
            continue
        if courante is None:
            continue
        if ligne.startswith("ÉCARTÉ"):
            courante["ecarte"] = True
        m = _EXPO.match(ligne)
        if m:
            courante["expo_s"] = int(m.group(1)) if m.group(1) else None
        m = _TEMP.match(ligne)
        if m:
            courante["temp"] = float(m.group(1))
        m = _CHEMIN.match(ligne)
        if m and m.group(1) != "inconnu":
            courante["chemin"] = m.group(1)
    if courante:
        pannes.append(courante)

    ecartes = [p for p in pannes if p.get("ecarte")]
    pannes = dedoublonner([p for p in pannes if not p.get("ecarte")])

    # Réveils, avec leur exposition.
    #
    # ⚠️⚠️ **Seuls comptent les réveils postérieurs à la mise en place de la
    # sonde.** Un réveil est retenu s'il porte le champ `extinction=`, écrit
    # uniquement par la version instrumentée de `screen_dpms.sh` — le critère
    # est donc porté par la donnée elle-même, sans date en dur.
    #
    # J'avais d'abord fait l'inverse : recalculer les expositions des 88 réveils
    # historiques pour rendre le rapport utile tout de suite. C'était une
    # erreur, et Thomas l'a arrêtée (2026-08-26). **Ces réveils anciens ne sont
    # pas des succès confirmés** : avant le bouton de signalement, une panne ne
    # laissait aucune trace. Les compter comme sains revient à traiter
    # l'absence de signalement comme une preuve de bon fonctionnement — sur un
    # phénomène dont on sait qu'il passait inaperçu des semaines durant.
    #
    # Conséquence assumée : le rapport reste muet plus longtemps. C'est le prix
    # d'une comparaison honnête, et c'est moins cher qu'une fausse piste.
    # ⚠️ UN RÉVEIL S'ÉCRIT SUR DEUX LIGNES, et c'est le piège :
    #   … on — sortie inactive (Enabled: no), rebond 1280x720@60 -> 1024x600
    #   … on — terminé · extinction=89s temp=76C
    # L'instant du réveil est sur la première, l'exposition et la température
    # sur la seconde, trois secondes plus tard. Première version : je cherchais
    # `extinction=` sur la ligne « rebond ». Elles n'y sont jamais, donc le
    # rapport annonçait **zéro réveil enregistré** alors que le journal en
    # contenait des dizaines (constaté le 2026-08-30). Encore un silence
    # crédible et faux.
    #
    # On apparie donc les deux lignes, et on retient l'instant du « rebond » :
    # c'est lui que `dernier_reveil()` rattache aux pannes, les deux côtés
    # doivent parler du même horodatage.
    evts = evenements_dpms()
    reussis: list[tuple[datetime, float | None, str | None, str]] = []
    for i, e in enumerate(evts):
        if e["action"] != "on" or "rebond" not in e["detail"]:
            continue
        # La ligne « terminé » suit immédiatement, sauf réveil interrompu.
        fin = next((x for x in evts[i + 1:i + 3]
                    if x["action"] == "on" and "terminé" in x["detail"]), None)
        if fin is None:
            continue
        m = re.search(r"extinction=(\d+)s", fin["detail"])
        if not m:
            continue          # réveil d'avant la sonde : succès non confirmé
        t = re.search(r"temp=(\d+)C", fin["detail"])
        reussis.append((e["quand"], float(m.group(1)),
                        t.group(1) + " °C" if t else None,
                        origine_reveil(evts, i)))

    sains, _fautifs = separer_reveils(pannes, reussis)

    print(f"╭─ TICKET-149 — {len(pannes)} panne(s) constatée(s), "
          f"{len(reussis)} réveil(s) enregistré(s)"
          + (f", {len(ecartes)} écarté(s)" if ecartes else ""))

    if not pannes:
        print("╰─ Aucune panne signalée pour l'instant.")
        print()
        print("   Au prochain écran noir, AVANT de débrancher :")
        print("     python3 scripts/ecran_noir.py signaler")
        return 0

    print("│")
    print("├─ PANNES")
    for p in pannes:
        expo = f"{p['expo_s']/3600:.2f} h" if p["expo_s"] else "inconnue"
        print(f"│   {p['quand']}  extinction={expo:>10}  temp={p['temp'] or '?'} °C")

    expos_ko = [p["expo_s"] for p in pannes if p["expo_s"]]
    expos_ok = [r[1] for r in sains if r[1]]

    print("│")
    print("├─ RÉVEILS SANS INCIDENT (échantillon récent)")
    for quand, expo, temp, chemin in sains[-8:]:
        e = f"{expo/3600:.2f} h" if expo else "inconnue"
        print(f"│   {quand:%Y-%m-%d %H:%M:%S}  extinction={e:>10}  "
              f"temp={temp or '?':>6}  réveil={chemin}")

    # ── Hypothèse de Thomas : bouton contre tactile (2026-08-26) ────────────
    print("│")
    print("├─ CHEMIN DE RÉVEIL — l'hypothèse bouton / tactile")
    par_chemin: dict[str, int] = {}
    for _q, _e, _t, chemin in reussis:
        par_chemin[chemin] = par_chemin.get(chemin, 0) + 1
    for chemin, n in sorted(par_chemin.items(), key=lambda kv: -kv[1]):
        print(f"│   réveils sans incident par {chemin:<8} : {n}")
    chemins_pannes = [c for c in (p.get("chemin") for p in pannes) if c]
    if chemins_pannes:
        for chemin in sorted(set(chemins_pannes)):
            print(f"│   PANNES survenues sur réveil {chemin:<8} : "
                  f"{chemins_pannes.count(chemin)}")
    else:
        print("│   (chemin des pannes inconnu — il est enregistré depuis le 2026-08-26)")

    print("│")
    print("╰─ VERDICT")
    if not expos_ko or not expos_ok:
        print("   Pas encore de quoi comparer — il faut des durées des deux côtés.")
        return 0

    print(f"   extinctions AVEC panne  : {min(expos_ko)/3600:.2f} à {max(expos_ko)/3600:.2f} h "
          f"(n={len(expos_ko)})")
    print(f"   extinctions SANS panne  : {min(expos_ok)/3600:.2f} à {max(expos_ok)/3600:.2f} h "
          f"(n={len(expos_ok)})")
    if min(expos_ko) > max(expos_ok):
        print(f"   → Les deux populations ne se recouvrent pas : un seuil existe, "
              f"entre {max(expos_ok)/3600:.2f} h et {min(expos_ko)/3600:.2f} h.")
    else:
        print("   → Les deux populations SE RECOUVRENT : la durée seule n'explique pas")
        print("     la panne. Chercher ailleurs — température, ou aléa du récepteur.")
    print()
    print("   ⚠️ Ne pas conclure sous 5 pannes constatées. On s'est déjà trompé")
    print("      deux fois sur ce projet en concluant sur un ou deux points.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="commande")
    s = sub.add_parser("signaler", help="constate une panne en cours (à faire AVANT de débrancher)")
    s.add_argument("--note", help="précision libre : ce que tu voyais, ce que tu venais de faire")
    sub.add_parser("rapport", help="croise les pannes avec les réveils réussis")
    i = sub.add_parser("ignorer", help="écarte un constat qui n'était pas une vraie panne")
    i.add_argument("horodatage", help="début du constat, ex. « 2026-08-28 11:48:47 »")
    i.add_argument("--raison", default="écarté manuellement")
    args = ap.parse_args()

    if args.commande == "signaler":
        return signaler(args.note)
    if args.commande == "ignorer":
        return ignorer(args.horodatage, args.raison)
    if args.commande == "rapport":
        return rapport()
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
