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


def run(cmd: list[str], timeout: int = CMD_TIMEOUT) -> str:
    """Jamais d'exception : un constat partiel vaut mieux que pas de constat."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
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

    Si l'hypothèse tient, les pannes se concentreront sur un seul chemin — et
    cela désignerait un coupable très différent d'un aléa du récepteur : le
    réveil par bouton ne réarme pas swayidle (TICKET-123), donc la séquence de
    rallumage n'y est pas la même.
    """
    a = (appelant or "").lower()
    if "swayidle" in a:
        return "tactile"
    if "python" in a or "runuser" in a:
        return "bouton"
    if "ssh" in a or "bash" in a:
        return "manuel"
    return "autre"


def dernier_reveil(avant: datetime) -> tuple[dict | None, float | None]:
    """
    Dernier réveil précédant `avant`, et la durée d'extinction qui l'a précédé.

    C'est LA donnée du ticket : chaque panne constatée doit pouvoir être
    rattachée à l'extinction dont la dalle n'est pas revenue.
    """
    evts = [e for e in evenements_dpms() if e["quand"] <= avant]
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
    reveil, expo = dernier_reveil(maintenant)

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
        lignes.append("dernier réveil : introuvable dans le journal")
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
    interessant = [l for l in etat.splitlines()
                   if re.search(r"crtc-2|active=|enable=|tmds_char_rate|"
                                r"crtc-pos|src-pos|fb=|mode:", l)]
    lignes.append("\n".join(interessant[:40]) if interessant else etat[:800])

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
                        "temp": None, "chemin": None}
            continue
        if courante is None:
            continue
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

    pannes = dedoublonner(pannes)

    # Réveils, avec leur exposition.
    #
    # ⚠️ On ne se contente PAS de lire le champ `extinction=` ajouté par
    # screen_dpms.sh : il n'existe que depuis le 2026-08-25, alors que le
    # journal remonte bien plus loin. Or ces réveils anciens sont précisément
    # l'échantillon « sans panne » dont on a besoin pour comparer — dont
    # l'extinction de 13 h 54 du 22/08 qui dément l'hypothèse du seuil.
    # On recalcule donc la durée depuis les événements eux-mêmes, et le champ
    # ne sert que de recoupement.
    evts = evenements_dpms()
    reussis: list[tuple[datetime, float | None, str | None, str]] = []
    derniere_extinction: datetime | None = None
    for e in evts:
        if e["action"] == "off":
            derniere_extinction = e["quand"]
            continue
        if e["action"] != "on" or "rebond" not in e["detail"]:
            continue
        expo_s = None
        if derniere_extinction is not None:
            expo_s = (e["quand"] - derniere_extinction).total_seconds()
        t = re.search(r"temp=(\d+)C", e["detail"])
        reussis.append((e["quand"], expo_s,
                        t.group(1) + " °C" if t else None,
                        chemin_reveil(e["appelant"])))
        derniere_extinction = None

    sains, _fautifs = separer_reveils(pannes, reussis)

    print(f"╭─ TICKET-149 — {len(pannes)} panne(s) constatée(s), "
          f"{len(reussis)} réveil(s) enregistré(s)")

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
    args = ap.parse_args()

    if args.commande == "signaler":
        return signaler(args.note)
    if args.commande == "rapport":
        return rapport()
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
