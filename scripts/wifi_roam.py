#!/usr/bin/env python3
"""
Roaming automatique multi-AP "El CORAL GOURMET" (box Freebox + répéteur Free) — TICKET-110

Hechicero est mobile (bureau <-> salon). Ce daemon scanne périodiquement les BSSID
diffusant le SSID du projet et rebascule le BSSID épinglé de la connexion
NetworkManager vers le signal le plus fort, pour que le Pi se connecte toujours au
point d'accès le plus proche (box ou répéteur) plutôt que de rester figé sur celui
choisi au démarrage.

Garde-fous :
- Exclut les fréquences DFS (~5250-5725 MHz, canaux 52-140 ETSI) : ce sont elles qui
  ont causé l'épisode 2 de TICKET-109 (CAC radar -> échecs d'association en boucle,
  indépendamment de la force du signal). On ne bascule jamais dessus.
- Anti-flapping : ne bascule que si le nouveau BSSID est meilleur d'au moins
  MARGIN_DB, confirmé sur CONFIRM_COUNT scans consécutifs — évite les allers-retours
  en zone limite entre deux pièces.

Tourne en root (iw scan actif nécessite CAP_NET_ADMIN).
"""
import subprocess
import re
import time
import datetime

CONN = "El CORAL GOURMET"
IFACE = "wlan0"
LOG = "/home/thomas/hechicero/data/wifi_roam.log"
MARGIN_DB = 8         # gain minimum requis pour basculer
CONFIRM_COUNT = 2     # scans consécutifs avant de basculer (anti-flapping)
INTERVAL_S = 60

DFS_FREQ_MIN = 5250
DFS_FREQ_MAX = 5725


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


# ── TICKET-152 — toute commande externe porte un délai de garde ─────────────
# Le 2026-08-30, un `iw dev wlan0 scan` lancé à 00:50:40 tournait encore
# **18 h 15 plus tard**, à 100 % d'un cœur. Conséquences en chaîne :
#   · le Pi chauffait de 60 à 80 °C et bridait sa fréquence (`throttled=0xe0000`) ;
#   · ce daemon était MORT depuis 00:50 — bloqué dans `subprocess.run`, plus un
#     seul roaming en dix-huit heures ;
#   · et rien ne le signalait : le service restait `active (running)`.
#
# C'est mot pour mot la leçon du TICKET-122 avec `mpc` : une commande externe
# qui n'échoue pas mais ATTEND emporte tout son appelant avec elle. On l'avait
# écrite pour MPD, on ne l'avait pas généralisée.
#
# 📌 Règle : dans ce projet, `subprocess.run` sans `timeout=` est un défaut.
# Le smoke test le vérifie sur tous les scripts.
def lancer(cmd, delai, defaut=""):
    """Exécute une commande, jamais plus longtemps que `delai` secondes.

    Sur expiration, Python tue l'enfant avant de lever — le processus ne reste
    donc pas à tourner derrière nous, ce qui était tout le problème.
    """
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=delai)
        return r.stdout
    except subprocess.TimeoutExpired:
        log(f"⚠️ délai de garde dépassé ({delai}s) : {' '.join(cmd)} — commande tuée")
        return defaut
    except Exception as e:
        log(f"⚠️ échec de {' '.join(cmd)} : {type(e).__name__}: {e}")
        return defaut


def is_dfs(freq):
    return DFS_FREQ_MIN <= freq <= DFS_FREQ_MAX


def get_current_bssid():
    out = lancer(["iw", "dev", IFACE, "link"], delai=5)
    m = re.search(r"Connected to ([0-9a-fA-F:]+)", out)
    return m.group(1).upper() if m else None


def scan():
    """Retourne [(bssid, freq, signal_dbm), ...] pour les BSS diffusant CONN."""
    # 20 s : un scan honnête prend 2 à 10 s. Au-delà, il ne reviendra pas.
    out = lancer(["iw", "dev", IFACE, "scan"], delai=20)
    results = []
    bssid = ssid = freq = signal = None

    def flush():
        if bssid and ssid == CONN and freq is not None and signal is not None:
            results.append((bssid, freq, signal))

    for raw in out.splitlines():
        line = raw.strip()
        m = re.match(r"BSS ([0-9a-fA-F:]+)", line)
        if m:
            flush()
            bssid, ssid, freq, signal = m.group(1).upper(), None, None, None
            continue
        m = re.match(r"freq:\s*(\d+)", line)
        if m:
            freq = int(m.group(1))
            continue
        m = re.match(r"signal:\s*(-?\d+(?:\.\d+)?)", line)
        if m:
            signal = float(m.group(1))
            continue
        m = re.match(r"SSID:\s*(.*)", line)
        if m:
            ssid = m.group(1)
            continue
    flush()
    return results


def switch_to(bssid):
    lancer(["nmcli", "connection", "modify", CONN, "802-11-wireless.bssid", bssid], delai=15)
    lancer(["nmcli", "connection", "up", CONN], delai=45)


def main():
    streak = 0
    candidate = None

    while True:
        try:
            current = get_current_bssid()
            seen = scan()
            safe = [r for r in seen if not is_dfs(r[1])]
            cur_signal = next((s for b, f, s in seen if b == current), None)
            best = max(safe, key=lambda r: r[2], default=None)

            if best:
                best_bssid, best_freq, best_signal = best
            else:
                best_bssid = best_freq = best_signal = None

            log(f"current={current} cur_signal={cur_signal} "
                f"best={best_bssid} best_signal={best_signal} freq={best_freq}")

            if best_bssid and best_bssid != current:
                gain_ok = cur_signal is None or (best_signal - cur_signal) >= MARGIN_DB
                if gain_ok:
                    streak = streak + 1 if candidate == best_bssid else 1
                    candidate = best_bssid
                else:
                    candidate, streak = None, 0

                if streak >= CONFIRM_COUNT:
                    log(f"SWITCH -> {best_bssid} (gain confirme {streak}x)")
                    switch_to(best_bssid)
                    candidate, streak = None, 0
            else:
                candidate, streak = None, 0

        except Exception as e:
            log(f"ERROR {e}")

        time.sleep(INTERVAL_S)


if __name__ == "__main__":
    main()
