#!/usr/bin/env python3
"""
test_clic_confirmation.py — Tests de garde de l'accusé sonore (TICKET-149).

LE BUG QUE CES TESTS COUVRENT
─────────────────────────────
Première version du client MPD : j'attendais la sous-chaîne `b"OK\\n"` dans le
tampon. Or la bannière d'accueil vaut `OK MPD 0.24.0\\n` — elle ne contient pas
`OK\\n`. Le client attendait donc une réponse déjà reçue, jusqu'au délai de
garde, et annonçait « socket injoignable » sur un MPD en parfaite santé.

⚠️ **Un faux négatif sur la santé de MPD est particulièrement coûteux ici** :
c'est exactement le symptôme du TICKET-122, celui qui déclenche un SIGKILL du
démon. Recopié dans un chien de garde, ce défaut ferait tuer MPD sans raison.

Et le plus instructif : `mpd_watchdog.py` faisait déjà les choses correctement,
trois fichiers plus loin. J'ai écrit une version naïve plutôt que de réutiliser
une implémentation éprouvée.

Les tests dialoguent avec une fausse socket, donc sans Pi, sans MPD et sans son.
"""
from __future__ import annotations

import socket
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import clic_confirmation as cc   # noqa: E402

ok = 0
ko = 0


def verifie(nom: str, condition: bool, detail: str = "") -> None:
    global ok, ko
    if condition:
        ok += 1
    else:
        ko += 1
        print(f"  ❌ {nom}" + (f" — {detail}" if detail else ""))


def faux_mpd(scenario: list[bytes], banniere: bytes = b"OK MPD 0.24.0\n"):
    """
    Monte un faux serveur MPD sur une socketpair.

    `scenario` : une réponse par commande reçue, dans l'ordre.
    Renvoie (socket_client, liste_des_commandes_recues).
    """
    cote_client, cote_serveur = socket.socketpair()
    recues: list[str] = []

    def servir() -> None:
        f = cote_serveur.makefile("rwb")
        f.write(banniere)
        f.flush()
        for reponse in scenario:
            ligne = f.readline()
            if not ligne:
                break
            recues.append(ligne.decode().strip())
            f.write(reponse)
            f.flush()
        f.close()
        cote_serveur.close()

    threading.Thread(target=servir, daemon=True).start()
    return cote_client, recues


# ── 1. LE bug : la bannière doit être lue, pas cherchée comme sous-chaîne ────
cli, _ = faux_mpd([])
try:
    m = cc.MpdBref(cli)
    verifie("bannière 'OK MPD 0.24.0' acceptée", m.banniere == "OK MPD 0.24.0", m.banniere)
    m.fermer()
except Exception as e:  # noqa: BLE001
    verifie("bannière 'OK MPD 0.24.0' acceptée", False, repr(e))

# Toutes les versions de MPD croisées sur ce projet, et une future.
for version in (b"OK MPD 0.23.12\n", b"OK MPD 0.24.0\n", b"OK MPD 0.25.1\n"):
    cli, _ = faux_mpd([], banniere=version)
    try:
        m = cc.MpdBref(cli)
        m.fermer()
        verifie(f"bannière {version.decode().strip()!r} acceptée", True)
    except Exception as e:  # noqa: BLE001
        verifie(f"bannière {version.decode().strip()!r} acceptée", False, repr(e))

# Un serveur qui n'est pas MPD doit être refusé tout de suite, pas au bout du
# délai de garde : un blocage ici gèlerait le daemon des boutons.
cli, _ = faux_mpd([], banniere=b"HTTP/1.1 200 OK\n")
try:
    cc.MpdBref(cli)
    verifie("interlocuteur non-MPD refusé", False, "aucune exception levée")
except RuntimeError:
    verifie("interlocuteur non-MPD refusé", True)
except Exception as e:  # noqa: BLE001
    verifie("interlocuteur non-MPD refusé", False, f"mauvaise exception : {e!r}")


# ── 2. Une réponse se termine sur une ligne valant exactement OK ─────────────
cli, recues = faux_mpd([b"volume: 13\nstate: play\nsong: 0\nelapsed: 517.481\nOK\n"])
m = cc.MpdBref(cli)
st = m.status()
verifie("status analysé", st.get("state") == "play" and st.get("song") == "0", str(st))
verifie("elapsed conservé au centième", st.get("elapsed") == "517.481", str(st.get("elapsed")))
verifie("la commande est bien partie", recues == ["status"], str(recues))
m.fermer()

# `addid` renvoie l'identifiant : sans lui, pas de lecture ni de nettoyage.
cli, _ = faux_mpd([b"Id: 5\nOK\n"])
m = cc.MpdBref(cli)
rep = m.cmd('addid "file:///chemin/son.wav"')
verifie("addid renvoie l'identifiant", "Id: 5" in rep, rep)
m.fermer()

# Une erreur MPD (ACK) doit rendre la main, pas attendre un OK qui ne viendra pas.
cli, _ = faux_mpd([b'ACK [50@0] {addid} No such directory\n'])
m = cc.MpdBref(cli)
rep = m.cmd('addid "file:///introuvable.wav"')
verifie("un ACK termine la réponse sans blocage", "ACK" in rep, rep)
verifie("aucun identifiant extrait d'un ACK", "Id: " not in rep, rep)
m.fermer()


# ── 3. La sortie visée est celle qui joue, pas le périphérique par défaut ────
# `pcm.!default` pointe sur le DAC casque : un aplay nu joue dans le casque
# quelles que soient les enceintes, et renvoie 0. Constaté le 2026-08-26.
import json          # noqa: E402
import tempfile      # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    fichier = Path(tmp) / "audio_output_state.json"
    original = cc.ETAT_SORTIE
    try:
        cc.ETAT_SORTIE = fichier
        for mode, attendu in (("hp", "eqhp"), ("casque", "eqcasque")):
            fichier.write_text(json.dumps({"mode": mode}), encoding="utf-8")
            verifie(f"mode {mode} → {attendu}", cc.periph_actif() == attendu,
                    cc.periph_actif())

        # Jamais `default` en repli : ce serait rejouer le bug du 26/08.
        fichier.write_text(json.dumps({"mode": "inconnu"}), encoding="utf-8")
        verifie("mode inconnu → repli sur une sortie explicite, jamais 'default'",
                cc.periph_actif() in ("eqhp", "eqcasque"), cc.periph_actif())
        cc.ETAT_SORTIE = Path(tmp) / "absent.json"
        verifie("fichier absent → repli sur une sortie explicite",
                cc.periph_actif() in ("eqhp", "eqcasque"), cc.periph_actif())
    finally:
        cc.ETAT_SORTIE = original

verifie("les deux sorties connues sont couvertes",
        sorted(cc.PERIPH_PAR_MODE) == ["casque", "hp"], str(cc.PERIPH_PAR_MODE))


# ── 4. Un échec doit être expliqué, jamais muet ──────────────────────────────
# Le 26/08, « clic de confirmation : aucun » sans un mot de plus : impossible
# de savoir lequel des deux chemins avait échoué. Un outil de diagnostic qui
# tait ses erreurs fait perdre le temps qu'il devait faire gagner.
cc.RAISONS.clear()
original = cc.SON
try:
    cc.SON = Path("/chemin/qui/n/existe/pas.wav")
    verifie("son absent → aplay échoue", cc.jouer_aplay() is False)
    verifie("son absent → mpd échoue", cc.jouer_via_mpd() is False)
    verifie("les deux échecs sont expliqués", len(cc.RAISONS) == 2, str(cc.RAISONS))
    verifie("la raison nomme le fichier manquant",
            all("introuvable" in r for r in cc.RAISONS), str(cc.RAISONS))
finally:
    cc.SON = original
    cc.RAISONS.clear()

print(f"\n{ok} test(s) OK, {ko} échec(s)")
sys.exit(1 if ko else 0)
