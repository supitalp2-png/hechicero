#!/usr/bin/env python3
"""
test_ecran_noir.py — Tests de garde du diagnostic d'écran noir (TICKET-149).

L'outil sert à répondre à UNE question : qu'est-ce qui distingue une extinction
dont la dalle revient d'une extinction dont elle ne revient pas ? Si son
appariement panne ↔ réveil est faux, la réponse le sera aussi — et on repartira
sur une fausse piste, comme on l'a déjà fait deux fois sur ce projet.

Ces tests vérifient un comportement sur des journaux fabriqués, pas la présence
d'un mot dans le code.
"""
from __future__ import annotations

import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ecran_noir as en   # noqa: E402

ok = 0
ko = 0


def verifie(nom: str, condition: bool, detail: str = "") -> None:
    global ok, ko
    if condition:
        ok += 1
    else:
        ko += 1
        print(f"  ❌ {nom}" + (f" — {detail}" if detail else ""))


JOURNAL_TYPE = """\
2026-08-22 20:52:30 [sh<-swayidle] off    — extinction demandée
2026-08-23 10:46:44 [sh<-swayidle] on     — sortie inactive (Enabled: no), rebond 1280x720@60 -> 1024x600@59.821
2026-08-23 10:46:47 [sh<-swayidle] on     — terminé
2026-08-25 18:13:35 [sh<-swayidle] off    — extinction demandée
2026-08-25 20:01:44 [sh<-swayidle] on     — sortie inactive (Enabled: no), rebond 1280x720@60 -> 1024x600@59.821
2026-08-25 20:01:47 [sh<-swayidle] on     — terminé
2026-08-25 20:35:12 [smoke_test.sh<-bash] on     — déjà actif (Enabled: yes), aucune action
"""

with tempfile.TemporaryDirectory() as tmp:
    chemin = Path(tmp) / "screen_dpms.log"
    chemin.write_text(JOURNAL_TYPE, encoding="utf-8")
    original = en.DPMS_LOG
    try:
        en.DPMS_LOG = chemin

        # ── 1. Analyse du journal ────────────────────────────────────────────
        evts = en.evenements_dpms()
        verifie("les 7 lignes du journal sont analysées", len(evts) == 7, str(len(evts)))
        verifie("l'appelant est extrait", evts[0]["appelant"] == "sh<-swayidle",
                evts[0]["appelant"])

        # ── 2. Rattachement d'une panne à SON réveil ─────────────────────────
        # Le cas réel du 25/08 : réveil à 20:01:44, panne constatée à 20:05.
        # Un appariement à la minute échouerait ici — c'est le bug corrigé.
        reveil, expo = en.dernier_reveil(datetime(2026, 8, 25, 20, 5, 0))
        verifie("panne rattachée au bon réveil",
                reveil is not None and reveil["quand"] == datetime(2026, 8, 25, 20, 1, 44),
                str(reveil and reveil["quand"]))
        verifie("exposition calculée = 1,80 h",
                expo is not None and abs(expo - 6489) < 1, str(expo))

        # ── 3. Un « on — déjà actif » n'est pas un réveil ────────────────────
        # Il ne rallume rien : le compter fausserait le décompte des réveils
        # réussis, qui est l'échantillon de comparaison du ticket.
        reveil2, _ = en.dernier_reveil(datetime(2026, 8, 25, 20, 40, 0))
        verifie("un 'déjà actif' n'est pas compté comme réveil",
                reveil2 is not None and reveil2["quand"] == datetime(2026, 8, 25, 20, 1, 44),
                str(reveil2 and reveil2["quand"]))

        # ── 4. Le réveil de 13,90 h, celui qui dément le seuil ───────────────
        reveil3, expo3 = en.dernier_reveil(datetime(2026, 8, 23, 11, 0, 0))
        verifie("réveil du 23/08 trouvé",
                reveil3 is not None and reveil3["quand"] == datetime(2026, 8, 23, 10, 46, 44))
        verifie("exposition de 13,90 h sans panne",
                expo3 is not None and abs(expo3 / 3600 - 13.90) < 0.02,
                f"{expo3 and expo3/3600:.2f} h")

        # ── 5. LE bug corrigé : un réveil raté compté comme réussi ───────────
        # Le 25/08, réveil à 20:01:44 et constat à 20:05. Un appariement à la
        # minute laissait ce réveil dans les réussites, donc des deux côtés de
        # la comparaison — de quoi conclure « la durée n'explique rien » même
        # si elle expliquait tout.
        reveil_rate = datetime(2026, 8, 25, 20, 1, 44)
        reveil_sain = datetime(2026, 8, 23, 10, 46, 44)
        reussis = [(reveil_sain, 50044.0, None), (reveil_rate, 6489.0, None)]
        pannes = [{"quand": "2026-08-25 20:05:00", "expo_s": 6489, "temp": 80.4}]

        sains, fautifs = en.separer_reveils(pannes, reussis)
        verifie("le réveil fautif est identifié", reveil_rate in fautifs, str(fautifs))
        verifie("le réveil fautif sort des réussites",
                reveil_rate not in [s[0] for s in sains], str([s[0] for s in sains]))
        verifie("le réveil sain reste dans les réussites",
                reveil_sain in [s[0] for s in sains])
        verifie("aucune panne → tous les réveils restent sains",
                len(en.separer_reveils([], reussis)[0]) == 2)
        verifie("horodatage de panne illisible → ignoré sans planter",
                len(en.separer_reveils([{"quand": "pas une date"}], reussis)[0]) == 2)

        # ── 6. Un incident signalé deux fois ne compte qu'une fois ───────────
        # Cas réel du 2026-08-26 : deux constats à 43 s d'écart pour une seule
        # panne — sur un écran noir on doute d'avoir bien appuyé, et on
        # recommence. Compter 2 pannes au lieu d'1 fausse exactement la
        # statistique que le rapport doit établir.
        doubles = [
            {"quand": "2026-08-26 09:15:17", "expo_s": 44928, "temp": 85.3},
            {"quand": "2026-08-26 09:16:00", "expo_s": 44928, "temp": 84.2},
        ]
        # Les deux se rattachent au réveil du 25/08 20:01:44 dans ce journal
        # de test : même réveil, donc même incident.
        verifie("deux constats du même incident → une seule panne",
                len(en.dedoublonner(doubles)) == 1, str(len(en.dedoublonner(doubles))))
        verifie("c'est le PREMIER constat qui est conservé (le plus proche de la panne)",
                en.dedoublonner(doubles)[0]["quand"] == "2026-08-26 09:15:17")

        # Deux pannes séparées par un réveil réussi restent deux pannes : une
        # extinction ne peut échouer qu'une fois, mais deux extinctions le
        # peuvent.
        distinctes = [
            {"quand": "2026-08-23 11:00:00"},   # réveil du 23/08 10:46:44
            {"quand": "2026-08-25 20:05:00"},   # réveil du 25/08 20:01:44
        ]
        verifie("deux incidents sur deux réveils différents → deux pannes",
                len(en.dedoublonner(distinctes)) == 2,
                str(len(en.dedoublonner(distinctes))))

        verifie("horodatage illisible → conservé plutôt que fusionné à l'aveugle",
                len(en.dedoublonner([{"quand": "n'importe quoi"},
                                     {"quand": "autre chose"}])) == 2)

        # ── 7. Chemin de réveil — l'hypothèse bouton / tactile ───────────────
        # swayidle observe les entrées Wayland (tactile) ; il ne voit jamais le
        # GPIO, lu par un processus Python. Les deux chemins se distinguent donc
        # par l'appelant, déjà journalisé depuis le TICKET-123.
        verifie("swayidle → tactile", en.chemin_reveil("sh<-swayidle") == "tactile")
        verifie("buttons_daemon → bouton", en.chemin_reveil("runuser<-python3") == "bouton")
        verifie("python direct → bouton", en.chemin_reveil("python3<-systemd") == "bouton")
        verifie("SSH → manuel", en.chemin_reveil("bash<-sshd-session") == "manuel")
        verifie("appelant vide → autre, jamais une exception",
                en.chemin_reveil("") == "autre")

        # ── 8. Journal absent ou illisible → aucune exception ────────────────
        en.DPMS_LOG = Path(tmp) / "inexistant.log"
        verifie("journal absent → liste vide, pas d'exception",
                en.evenements_dpms() == [])
        verifie("rattachement sans journal → (None, None)",
                en.dernier_reveil(datetime.now()) == (None, None))
    finally:
        en.DPMS_LOG = original


# ── 6. Les sondes ne lèvent jamais, même hors Pi ─────────────────────────────
try:
    t = en.temperature_c()
    c = en.charge_cpu()
    verifie("température : float ou None", t is None or isinstance(t, float))
    verifie("charge CPU : float ou None", c is None or isinstance(c, float))
except Exception as e:  # noqa: BLE001
    verifie("les sondes ne lèvent jamais", False, repr(e))

# ── 7. Une commande absente ne fait pas tomber le constat ────────────────────
verifie("commande absente → message, pas d'exception",
        "absente" in en.run(["commande_qui_nexiste_pas_du_tout"]))

print(f"\n{ok} test(s) OK, {ko} échec(s)")
sys.exit(1 if ko else 0)
