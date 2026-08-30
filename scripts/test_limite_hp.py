#!/usr/bin/env python3
"""
test_limite_hp.py — Trouver la vraie limite des haut-parleurs (TICKET-150).

CE QU'ON CHERCHE
────────────────
Les craquements à fort volume existent depuis le début. Deux causes possibles,
qui appellent des remèdes opposés :

  · **butée d'excursion** — le cône arrive en fin de course. Le défaut apparaît
    beaucoup plus tôt dans le grave que dans le médium. Remède : un passe-haut,
    qui *augmente* le volume propre disponible.
  · **écrêtage électrique** — l'ampli ou le signal saturent. Le défaut apparaît
    au même volume à toutes les fréquences. Remède : baisser le plafond, ou
    changer d'ampli.

Une seule mesure les sépare : **le seuil de craquement dépend-il de la
fréquence ?** C'est ce que ce test relève, fréquence par fréquence.

⚠️ Les drivers viennent d'une enceinte Bose. Ils encaissent bien — mais chez
Bose ils travaillaient en volume clos derrière un DSP qui coupait le grave et
limitait les crêtes. Ici ils reçoivent tout le spectre en baffle ouvert. Ce
n'est donc pas leur qualité qui est en cause, c'est la protection qui leur
manque.

CONDITIONS DE VALIDITÉ
──────────────────────
L'égaliseur doit être **plat** : sinon on mesure la courbe de l'égaliseur, pas
la limite des haut-parleurs. Le script refuse de partir autrement.

USAGE
─────
    python3 scripts/test_limite_hp.py            # test complet, interactif
    python3 scripts/test_limite_hp.py --freq 60  # une seule fréquence
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import time
import wave
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from clic_confirmation import MpdBref            # noqa: E402  (client éprouvé)

DATA_DIR = PROJECT_ROOT / "data"
EQ_PATH = DATA_DIR / "audio_eq.json"
CONFIG_PATH = PROJECT_ROOT / "web" / "lecteur" / "config.json"
SORTIE_PATH = DATA_DIR / "audio_output_state.json"
RAPPORT = DATA_DIR / "limite_hp.log"
TONS_DIR = Path("/tmp/hechicero_tons")

# Grille de fréquences. Volontairement resserrée là où ça se joue : sous 250 Hz
# une membrane de 38 mm bouge beaucoup pour ne presque rien produire.
FREQUENCES = [60, 100, 150, 250, 500, 1000, 3000, 0]   # 0 = bruit rose, cf. generer_ton()
DUREE_S = 2.5
# Pas de volume MPD. On part bas : le but est de trouver le seuil, pas de
# maltraiter les drivers en montant d'un coup.
PAS_VOLUME = [20, 30, 40, 45, 50, 55, 60, 66, 75, 85, 100]


def generer_ton(freq: int, chemin: Path) -> None:
    """
    Signal de test. `freq = 0` produit un bruit rose au lieu d'une sinusoïde.

    Les fondus ne sont pas cosmétiques : un signal qui démarre à pleine
    amplitude produit un clic à l'attaque, qu'on confondrait avec le
    craquement qu'on cherche à détecter.

    ── Pourquoi le bruit rose est le signal qui compte (2026-08-26) ──────────
    Le premier essai a donné « propre à 66 % » sur toutes les sinusoïdes, alors
    que Thomas entend craquer à ce volume en usage réel. La contradiction n'est
    qu'apparente : une sinusoïde a un facteur de crête de 3 dB, de la musique
    ou une voix, 10 à 15 dB. À sonie égale, le contenu réel envoie des pointes
    bien plus hautes. **Un test à la sinusoïde surestime donc le seuil.**
    Le bruit rose approche le facteur de crête d'un programme musical : c'est
    lui qui donne le plafond utilisable.
    """
    rate, fondu_ms = 44100, 40
    n = int(rate * DUREE_S)
    nf = int(rate * fondu_ms / 1000)
    trames = []

    if freq == 0:
        # Bruit rose par filtrage récursif (méthode de Voss-McCartney simplifiée) :
        # -3 dB par octave, comme la répartition d'énergie d'un programme réel.
        import random
        random.seed(1)          # reproductible : deux essais comparables
        b = [0.0] * 7
        brut = []
        for _ in range(n):
            blanc = random.uniform(-1, 1)
            b[0] = 0.99886 * b[0] + blanc * 0.0555179
            b[1] = 0.99332 * b[1] + blanc * 0.0750759
            b[2] = 0.96900 * b[2] + blanc * 0.1538520
            b[3] = 0.86650 * b[3] + blanc * 0.3104856
            b[4] = 0.55000 * b[4] + blanc * 0.5329522
            b[5] = -0.7616 * b[5] - blanc * 0.0168980
            rose = sum(b) + b[6] + blanc * 0.5362
            b[6] = blanc * 0.115926
            brut.append(rose)
        crete = max(abs(v) for v in brut) or 1.0
        for i, v in enumerate(brut):
            env = min(1.0, i / nf, (n - i) / nf)
            e = int(32767 * 0.9 * env * v / crete)
            trames.append(struct.pack("<hh", e, e))
        chemin.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(chemin), "w") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(b"".join(trames))
        return

    for i in range(n):
        env = min(1.0, i / nf, (n - i) / nf)
        v = int(32767 * 0.9 * env * math.sin(2 * math.pi * freq * i / rate))
        trames.append(struct.pack("<hh", v, v))
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(chemin), "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(trames))


def egaliseur_plat() -> tuple[bool, str]:
    """L'égaliseur haut-parleurs est-il neutre ? Sinon on mesure sa courbe."""
    try:
        bandes = json.loads(EQ_PATH.read_text(encoding="utf-8")) \
            .get("profiles", {}).get("hp", {}).get("bands_db", [])
    except Exception as e:  # noqa: BLE001
        return False, f"profil illisible : {e}"
    if not bandes:
        return False, "aucune bande définie pour le profil hp"
    if any(abs(float(b)) > 0.01 for b in bandes):
        return False, f"bandes actuelles : {bandes}"
    return True, "plat"


def sortie_est_hp() -> bool:
    try:
        return json.loads(SORTIE_PATH.read_text(encoding="utf-8")).get("mode") == "hp"
    except Exception:
        return False


def plafond_configure() -> int:
    try:
        v = json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("volume", {})
        return int(v.get("speakers_max", 66))
    except Exception:
        return 66


def courant_ma() -> float | None:
    """
    Courant de décharge pendant la lecture — `None` si la mesure ne veut rien dire.

    ⚠️ L'INA219 mesure le courant **de la batterie**, pas celui de l'ampli. Sur
    secteur, ce qu'on lit est le va-et-vient du chargeur, qui n'a aucun rapport
    avec le volume. Premier essai réel (2026-08-26) : 3 mA à 66 %, puis 1213 mA
    à 75 % — des chiffres sans aucun sens, présentés comme une puissance.
    On ne renvoie donc une valeur que si l'appareil est réellement en décharge,
    et même alors elle inclut tout le reste (Pi, écran). Mieux vaut pas de
    chiffre qu'un chiffre trompeur.
    """
    try:
        from battery_common import init_ina219, load_config, read_sensor_snapshot
        c = load_config()
        s = read_sensor_snapshot(init_ina219(int(c.get("ina219_addr", 0x43))), c)
        if s.get("charging"):
            return None
        return float(s["current_ma"])
    except Exception:
        return None


def vider_tampon() -> None:
    """
    Jette ce qui a été tapé PENDANT la lecture du son.

    Sans ça, une frappe faite pendant les 2,5 s de sinusoïde est mise en
    mémoire par le terminal et lue comme réponse au palier SUIVANT. Constaté
    au premier essai réel (2026-08-26) : des seuils décalés d'un cran, un
    « réponse attendue » parasite, et des `c` affichés au mauvais endroit.
    Un test dont les réponses glissent produit des données fausses en silence
    — le pire des cas, puisqu'elles ont l'air bonnes.
    """
    try:
        import termios
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except Exception:
        pass


def demander(question: str, choix: str) -> str:
    vider_tampon()
    while True:
        r = input(question).strip().lower()
        if r in choix:
            return r
        print(f"   réponse attendue : {' / '.join(choix)}")


def tester_frequence(mpd: MpdBref, freq: int, plafond: int) -> dict:
    """Monte le volume par paliers jusqu'au premier craquement signalé."""
    chemin = TONS_DIR / f"ton_{freq}hz.wav"
    if not chemin.exists():
        generer_ton(freq, chemin)

    print(f"\n──── {freq} Hz ────")
    resultat: dict = {"freq": freq, "seuil": None, "courant_ma": None, "arret": None}

    for volume in PAS_VOLUME:
        rep = mpd.cmd(f'addid "file://{chemin}"')
        ident = next((l.split(": ", 1)[1] for l in rep.splitlines()
                      if l.startswith("Id: ")), None)
        if ident is None:
            print(f"   ⚠️  MPD refuse le fichier : {rep.strip()[:120]}")
            return resultat
        mpd.cmd(f"setvol {volume}")
        mpd.cmd(f"playid {ident}")
        time.sleep(DUREE_S * 0.6)
        i = courant_ma()
        time.sleep(DUREE_S * 0.5)
        mpd.cmd("stop")
        mpd.cmd(f"deleteid {ident}")

        marque = "  ← plafond actuel" if volume == plafond else ""
        suffixe = f", {abs(i):.0f} mA" if i is not None else ""
        r = demander(f"   volume {volume:>3}%{suffixe}{marque} — "
                     f"[Entrée] propre · c = craque · s = arrêter : ",
                     ("", "c", "s"))
        if r == "c":
            resultat["seuil"] = volume
            resultat["courant_ma"] = abs(i) if i is not None else None
            print(f"   → craquement à {volume} %")
            return resultat
        if r == "s":
            resultat["arret"] = volume
            print("   → interrompu")
            return resultat

    print("   → propre jusqu'à 100 %")
    return resultat


def conclure(resultats: list[dict]) -> str:
    """
    Excursion ou écrêtage ? La réponse est dans la dépendance en fréquence.
    """
    seuils = {r["freq"]: r["seuil"] for r in resultats if r["seuil"] is not None}
    if len(seuils) < 2:
        return ("Pas assez de seuils relevés pour trancher. Il en faut au moins "
                "deux, dont un dans le grave et un dans le médium.")

    graves = [v for f, v in seuils.items() if f <= 150]
    mediums = [v for f, v in seuils.items() if f >= 500]
    if not graves or not mediums:
        return ("Il manque un seuil dans le grave (≤150 Hz) ou dans le médium "
                "(≥500 Hz) — ce sont eux qui séparent les deux causes.")

    # ⚠️ On compare les deux seuils LES PLUS BAS, un par zone : c'est la
    # première fréquence qui lâche qui renseigne, pas la dernière. Première
    # version : `max(graves)` affiché comme « seuil le plus bas dans le grave »
    # — un maximum nommé minimum, qui inversait le signe de l'écart.
    ecart = min(mediums) - min(graves)
    lignes = [f"seuil le plus bas dans le grave  ({min(seuils, key=lambda f: (seuils[f], f))} Hz) : {min(graves)} %",
              f"seuil le plus bas dans le médium : {min(mediums)} %",
              f"écart : {ecart:+d} points"]
    if ecart >= 10:
        lignes += [
            "",
            "→ BUTÉE D'EXCURSION. Le grave lâche bien avant le médium : les cônes",
            "  arrivent en fin de course, l'ampli n'y est pour rien.",
            "  Remède : un passe-haut. Couper sous ~150 Hz ne retire rien d'audible",
            "  sur des membranes de 38 mm en baffle ouvert, et rend au médium toute",
            "  la marge que l'excursion lui volait. Le volume propre AUGMENTE.",
        ]
    elif ecart <= 3:
        lignes += [
            "",
            "→ ÉCRÊTAGE ÉLECTRIQUE. Le seuil ne dépend pas de la fréquence : c'est",
            "  la chaîne qui sature, pas les cônes. Aucun filtrage n'y changera rien.",
            "  Remède : plafonner le volume à ce seuil, ou revoir l'ampli.",
        ]
    else:
        lignes += [
            "",
            "→ INDÉTERMINÉ. L'écart est trop faible pour trancher franchement.",
            "  Refaire le test en resserrant les paliers autour des seuils trouvés.",
        ]
    return "\n".join(lignes)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--freq", type=int, help="ne tester qu'une fréquence")
    args = ap.parse_args()

    print("═" * 62)
    print(" Limite des haut-parleurs — TICKET-150")
    print("═" * 62)

    plat, detail = egaliseur_plat()
    if not plat:
        print(f"\n⛔ L'égaliseur haut-parleurs n'est pas plat ({detail}).")
        print("   Avec une courbe active, on mesure l'égaliseur, pas les enceintes.")
        print("   Mets toutes les bandes à 0 dans l'admin, puis relance.")
        return 1
    if not sortie_est_hp():
        print("\n⛔ La sortie active n'est pas les haut-parleurs.")
        print("   Débranche le casque, puis relance.")
        return 1

    plafond = plafond_configure()
    print(f"\nÉgaliseur plat ✓   sortie haut-parleurs ✓   plafond actuel : {plafond} %")
    print("\nChaque palier joue une sinusoïde de 2,5 s, puis attend ton verdict.")
    print("Signale le craquement dès que tu l'entends — inutile d'insister,")
    print("maintenir une membrane en butée finit par l'abîmer pour de bon.")
    if demander("\nPrêt ? [Entrée] pour commencer · s pour renoncer : ", ("", "s")) == "s":
        return 0

    frequences = [args.freq] if args.freq else FREQUENCES
    resultats: list[dict] = []
    mpd = None
    try:
        mpd = MpdBref()
        etat = mpd.status()
        volume_initial = etat.get("volume", "50")
        piste, position = etat.get("song"), etat.get("elapsed")
        mpd.cmd("pause 1")

        for f in frequences:
            resultats.append(tester_frequence(mpd, f, plafond))
    except KeyboardInterrupt:
        print("\n\nInterrompu.")
    except Exception as e:  # noqa: BLE001
        print(f"\n⛔ {type(e).__name__}: {e}")
        return 1
    finally:
        if mpd is not None:
            try:
                mpd.cmd(f"setvol {volume_initial}")
                if piste is not None:
                    mpd.cmd(f"play {piste}")
                    if position:
                        mpd.cmd(f"seekcur {position}")
                    mpd.cmd("pause 1")
            except Exception:
                pass
            mpd.fermer()

    print("\n" + "═" * 62)
    print(" Résultats")
    print("═" * 62)
    print(f"{'fréquence':>10} {'seuil':>8} {'courant':>10}")
    for r in resultats:
        seuil = f"{r['seuil']} %" if r["seuil"] else ("arrêté" if r["arret"] else "propre")
        cour = f"{r['courant_ma']:.0f} mA" if r["courant_ma"] else "—"
        print(f"{r['freq']:>8} Hz {seuil:>8} {cour:>10}")

    verdict = conclure(resultats)
    print("\n" + verdict)

    try:
        with RAPPORT.open("a", encoding="utf-8") as fh:
            fh.write(f"\n{'='*62}\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                     f"test limite HP (plafond configuré : {plafond} %)\n")
            for r in resultats:
                fh.write(f"  {r['freq']:>5} Hz : seuil={r['seuil']} "
                         f"courant={r['courant_ma']} arret={r['arret']}\n")
            fh.write(verdict + "\n")
        print(f"\nRelevé ajouté à {RAPPORT.name}")
    except Exception as e:  # noqa: BLE001
        print(f"\n⚠️  écriture du relevé impossible : {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
