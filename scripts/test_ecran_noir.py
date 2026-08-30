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

# Journal tel que la sonde l'écrit RÉELLEMENT : l'instant du réveil est sur la
# ligne « rebond », l'exposition et la température sur la ligne « terminé »
# trois secondes plus tard. Jamais les deux sur la même ligne.
JOURNAL_SONDE = """\
2026-08-30 09:00:00 [sh<-swayidle] off    — extinction demandée
2026-08-30 10:22:01 [sh<-swayidle] on     — sortie inactive (Enabled: no), rebond 1280x720@60 -> 1024x600@59.821
2026-08-30 10:22:04 [sh<-swayidle] on     — terminé · extinction=4921s temp=79C
2026-08-30 10:47:00 [sh<-swayidle] off    — extinction demandée
2026-08-30 10:51:43 [runuser<-python3] on     — sortie inactive (Enabled: no), rebond 1280x720@60 -> 1024x600@59.821
2026-08-30 10:51:46 [runuser<-python3] on     — terminé · extinction=283s temp=84C
2026-08-30 11:00:00 [smoke_test.sh<-bash] on     — déjà actif (Enabled: yes), aucune action
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
        # ⛔ Surtout PAS « tactile ». Depuis le TICKET-123, un appui bouton
        # envoie une frappe virtuelle au compositeur, donc il produit lui aussi
        # un réveil `[sh<-swayidle]`. L'appelant dit qui a appelé le script, pas
        # ce qui a réveillé l'appareil. Étiqueter « tactile » a fait publier une
        # attribution fausse, et fermé à tort l'hypothèse de Thomas (2026-08-30).
        # Une case vide vaut mieux qu'une case trompeuse.
        verifie("swayidle → indéterminé, jamais 'tactile'",
                en.chemin_reveil("sh<-swayidle") == "indéterminé",
                en.chemin_reveil("sh<-swayidle"))
        verifie("buttons_daemon → bouton", en.chemin_reveil("runuser<-python3") == "bouton")
        verifie("python direct → bouton", en.chemin_reveil("python3<-systemd") == "bouton")
        verifie("SSH → manuel", en.chemin_reveil("bash<-sshd-session") == "manuel")
        verifie("appelant vide → autre, jamais une exception",
                en.chemin_reveil("") == "autre")

        # ── 8. Un réveil d'avant le démarrage ne compte pas ──────────────────
        # Premier essai grandeur nature (2026-08-26) : un constat pris 19 min
        # après un redémarrage s'est vu attribuer le réveil de la veille et une
        # exposition de 12,48 h. Une donnée entièrement fausse, dans le tableau
        # même qui doit trancher la cause.
        apres_boot = datetime(2026, 8, 25, 21, 0, 0)
        r, e = en.dernier_reveil(datetime(2026, 8, 25, 22, 0, 0),
                                 depuis_demarrage=apres_boot)
        verifie("aucun réveil depuis le démarrage → rien plutôt qu'une valeur fausse",
                (r, e) == (None, None), str((r, e)))

        # ⚠️⚠️ LE PIÈGE INVERSE, et il est pire. `rapport()` analyse des pannes
        # PASSÉES, toutes antérieures au démarrage courant. Si la borne
        # s'appliquait par défaut, elles disparaîtraient toutes et le rapport
        # annoncerait zéro panne sur une base pleine — un silence parfaitement
        # crédible, et faux.
        r, e = en.dernier_reveil(datetime(2026, 8, 25, 22, 0, 0))
        verifie("sans borne explicite, l'historique reste visible",
                r is not None and r["quand"] == datetime(2026, 8, 25, 20, 1, 44),
                str(r and r["quand"]))
        verifie("et son exposition reste calculée", e is not None and abs(e - 6489) < 1)

        # ── 9. Journal absent ou illisible → aucune exception ────────────────
        en.DPMS_LOG = Path(tmp) / "inexistant.log"
        verifie("journal absent → liste vide, pas d'exception",
                en.evenements_dpms() == [])
        verifie("rattachement sans journal → (None, None)",
                en.dernier_reveil(datetime.now()) == (None, None))
    finally:
        en.DPMS_LOG = original


# ── Un réveil s'écrit sur DEUX lignes ────────────────────────────────────────
# Le 2026-08-30, le rapport annonçait « 0 réveil enregistré » alors que le
# journal en contenait des dizaines : je cherchais `extinction=` sur la ligne
# « rebond », où il n'est jamais — il est sur la ligne « terminé ». Un compteur
# à zéro sur une base pleine, sans le moindre message d'erreur.
with tempfile.TemporaryDirectory() as tmp:
    chemin = Path(tmp) / "screen_dpms.log"
    chemin.write_text(JOURNAL_SONDE, encoding="utf-8")
    original = en.DPMS_LOG
    try:
        en.DPMS_LOG = chemin
        evts = en.evenements_dpms()
        rebonds = [e for e in evts if e["action"] == "on" and "rebond" in e["detail"]]
        termines = [e for e in evts if e["action"] == "on" and "terminé" in e["detail"]]
        verifie("les deux lignes d'un réveil sont bien distinctes",
                len(rebonds) == 2 and len(termines) == 2,
                f"{len(rebonds)} rebonds, {len(termines)} terminés")
        verifie("aucune ligne ne porte à la fois 'rebond' et 'extinction='",
                not [e for e in evts
                     if "rebond" in e["detail"] and "extinction=" in e["detail"]],
                "le piège du 30/08 : chercher les deux sur la même ligne")
        verifie("l'exposition n'est lisible que sur la ligne 'terminé'",
                all("extinction=" in e["detail"] for e in termines))
        # L'instant retenu doit être celui du REBOND, pas du « terminé » :
        # c'est lui que dernier_reveil() rattache aux pannes. Deux références
        # différentes et le réveil fautif ne serait jamais exclu des réussites.
        r, _ = en.dernier_reveil(datetime(2026, 8, 30, 10, 30, 0))
        verifie("l'instant du réveil est celui du rebond",
                r is not None and r["quand"] == datetime(2026, 8, 30, 10, 22, 1),
                str(r and r["quand"]))
        verifie("le chemin de réveil se lit sur la ligne rebond",
                en.chemin_reveil(rebonds[1]["appelant"]) == "bouton")
    finally:
        en.DPMS_LOG = original


# ── Résumé DRM : garder l'identité, jeter l'inutile ─────────────────────────
# Premier constat réel : trente lignes `fb=0` sans les en-têtes `plane[N]`,
# donc impossible de savoir de quel plan on parlait. Un diagnostic qu'on ne
# sait pas relire ne diagnostique rien.
ETAT_DRM = """\
plane[48]: plane-0
\tcrtc=(null)
\tfb=0
\tcrtc-pos=0x0+0+0
plane[83]: plane-2
\tcrtc=crtc-2
\tfb=682
\t\tsize=1024x600
\tcrtc-pos=1024x600+0+0
\tsrc-pos=1024.000000x600.000000+0.000000+0.000000
crtc[59]: mop
\tenable=0
\tactive=0
\tmode: "": 0 0
crtc[94]: crtc-2
\tenable=1
\tactive=1
\tmode: "1024x600": 60 50250 1024
connector[35]: HDMI-A-1
\tcrtc=crtc-2
\toutput_bpc=8
\ttmds_char_rate=50250000
connector[44]: HDMI-A-2
\tcrtc=(null)
\ttmds_char_rate=0
"""

resume = en.resumer_drm(ETAT_DRM)
verifie("le plan actif garde son identité", "plane[83]: plane-2" in resume, resume[:200])
verifie("le CRTC actif est conservé avec son mode",
        "crtc[94]: crtc-2" in resume and '"1024x600"' in resume)
verifie("le connecteur actif garde son débit TMDS",
        "connector[35]: HDMI-A-1" in resume and "tmds_char_rate=50250000" in resume)
verifie("la géométrie du plan est conservée",
        "crtc-pos=1024x600+0+0" in resume and "src-pos=1024.000000x600" in resume)

verifie("les plans inactifs sont écartés", "plane[48]" not in resume, resume[:300])
verifie("les CRTC désactivés sont écartés", "crtc[59]" not in resume)
verifie("les connecteurs non branchés sont écartés", "connector[44]" not in resume)
verifie("le nombre d'objets omis est indiqué", "inactif(s) omis" in resume,
        resume[-120:])

# Un état illisible ne doit pas rendre une chaîne vide : mieux vaut du brut
# tronqué que rien du tout au moment d'une panne.
verifie("état illisible → on rend quand même quelque chose",
        len(en.resumer_drm("n'importe quoi sans structure")) > 0)


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
