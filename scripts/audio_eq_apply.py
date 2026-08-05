#!/usr/bin/env python3
"""
audio_eq_apply.py — Applique l'égaliseur alsaequal (TICKET-030) sur les deux
instances ALSA dédiées (HP et casque) via amixer.

Contexte : la HiFiBerry Amp4 n'a aucun égaliseur matériel (DAC pur). Le
traitement se fait donc en logiciel, via le plugin ALSA "equal" (paquet
libasound2-plugin-equal, guide officiel HiFiBerry :
https://www.hifiberry.com/docs/software/guide-adding-equalization-using-alsaeq/).
Deux instances indépendantes sont définies dans /etc/asound.conf (ctl.eqhp /
ctl.eqcasque) — une par sortie audio — cf. docs/20-SETUP_SYSTEME.md §6.4.

alsaequal ne persiste PAS son état entre deux démarrages du système : ce
script doit être rejoué à chaque boot (service systemd
audio_eq_apply.service) ET à chaque sauvegarde depuis l'admin web
(web/admin/audio_eq.php, qui l'appelle via shell_exec juste après avoir
écrit data/audio_eq.json).

Bandes (ordre fixe, grille ISO 10 bandes) : 31, 62, 125, 250, 500, 1k, 2k,
4k, 8k, 16k Hz. Les gains sont stockés dans data/audio_eq.json en dB
(-12..+12, 0 = neutre) et convertis ici vers l'échelle de contrôle amixer
(0-100, convention CAPS Eq10/alsaequal : 50 ≈ 0 dB).

✅ Confirmé le 2026-07-18 en conditions réelles sur le Pi : `apt-get install
libasound2-plugin-equal` + config asound.conf/mpd.conf (docs/20-SETUP_SYSTEME.md
§6.4) fonctionnent, `eqhp`/`eqcasque` répondent tous les deux à `amixer
scontrols` avec les 10 contrôles attendus (noms confirmés = BAND_LABELS
ci-dessous), lecture MPD toujours OK après bascule des devices.

⚠️ Reste à vérifier :
  1. Que régler `eqhp` n'affecte pas aussi `eqcasque` (état vraiment
     indépendant entre les deux instances) — pas encore testé à l'oreille.
  2. La conversion dB→amixer (db_to_amixer ci-dessous, 0-100 / 50≈0dB) est
     une convention usuelle CAPS Eq10, pas confirmée sur ce système précis —
     comparer au besoin avec `amixer -D eqhp sget '00. 31 Hz'` (affiche la
     plage réelle si le driver expose l'info dB via TLV).
"""
from __future__ import annotations

import argparse
import logging
import subprocess

from battery_common import DATA_DIR, load_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("audio_eq_apply")

CONFIG_PATH = DATA_DIR / "audio_eq.json"

BANDS_HZ = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
# Noms de contrôle amixer réels, confirmés le 2026-07-18 via --list-controls
# sur le Pi (paquet libasound2-plugin-equal 0.6-8+b4 / caps 0.9.26-1+b1,
# Debian trixie arm64) : préfixe numérique "NN. " + espace avant l'unité.
BAND_LABELS = [
    "00. 31 Hz", "01. 63 Hz", "02. 125 Hz", "03. 250 Hz", "04. 500 Hz",
    "05. 1 kHz", "06. 2 kHz", "07. 4 kHz", "08. 8 kHz", "09. 16 kHz",
]

# ctl ALSA (définis dans /etc/asound.conf) par profil — cf. docs/20-SETUP_SYSTEME.md §6.4
PROFILE_CTL = {
    "hp": "eqhp",
    "casque": "eqcasque",
}

DEFAULT_PROFILE = {"preset": "plat", "bands_db": [0.0] * 10}


def db_to_amixer(db: float) -> int:
    """Convention CAPS Eq10/alsaequal : contrôle 0-100, 50 = 0 dB, plage -12..+12 dB.
    Non vérifié en conditions réelles — cf. avertissement en tête de fichier."""
    db = max(-12.0, min(12.0, float(db)))
    return int(round((db + 12.0) / 24.0 * 100))


def list_controls(ctl_name: str) -> None:
    result = subprocess.run(["amixer", "-D", ctl_name, "scontrols"], capture_output=True, text=True)
    print(f"--- amixer -D {ctl_name} scontrols ---")
    print(result.stdout or result.stderr)


def apply_profile(ctl_name: str, bands_db: list[float], gain_db: float = 0.0,
                  dry_run: bool = False) -> None:
    """Applique la courbe du profil, décalée d'un gain global uniforme.

    TICKET-124 (2026-08-05) — pourquoi un gain séparé des bandes :
    au casque, en voiture, le niveau était insuffisant alors que tout le reste
    était déjà à fond (mixer du DAC à 0 dB, `mpc volume` à 100). Le boost
    alsaequal intervient APRÈS l'étage de volume de MPD : c'est donc du gain
    réellement supplémentaire, et c'est la seule marge qui restait.

    Le garder dans un champ distinct de `bands_db` évite qu'il soit écrasé au
    moindre changement de profil : `bands_db` porte la FORME, `gain_db` porte
    le NIVEAU. Charger « Voix claire » ne fait plus perdre le gain.

    Écrêtage par bande (choix de Thomas) : chaque bande est plafonnée
    indépendamment à +12 dB, limite d'alsaequal. Conséquence assumée — sur un
    profil déjà haut, les bandes saturées s'alignent et la courbe s'aplatit.
    C'est pourquoi on journalise explicitement les bandes écrêtées.
    """
    ecretees = []
    for label, db in zip(BAND_LABELS, bands_db):
        total = db + gain_db
        if total > 12.0:
            ecretees.append(label)
        value = db_to_amixer(total)
        # sset (interface "simple", celle listée par scontrols) prend le nom du
        # contrôle tel quel en argument positionnel — pas cset/name=, qui relève
        # de l'interface "raw" (iface=MIXER,name=...) et échoue sur ces contrôles
        # simples (confirmé en conditions réelles le 2026-07-18, "Cannot find the
        # given element from control eqhp" avec cset).
        cmd = ["amixer", "-D", ctl_name, "sset", label, str(value)]
        LOGGER.info("%s: %s -> %s dB (%+g bande %+g gain, amixer=%s)",
                    ctl_name, label, min(12.0, total), db, gain_db, value)
        if dry_run:
            print(" ".join(cmd))
            continue
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            LOGGER.error("Échec amixer %s %s: %s", ctl_name, label, result.stderr.strip())

    if ecretees:
        LOGGER.warning("%s: %d bande(s) écrêtée(s) à +12 dB par le gain de %+g dB — "
                       "la courbe du profil est aplatie sur : %s",
                       ctl_name, len(ecretees), gain_db, ", ".join(ecretees))


def main() -> int:
    parser = argparse.ArgumentParser(description="Applique l'égaliseur alsaequal (TICKET-030)")
    parser.add_argument("--dry-run", action="store_true", help="Affiche les commandes amixer sans les exécuter")
    parser.add_argument("--profile", choices=["hp", "casque"], help="N'appliquer qu'un seul profil (par défaut : les deux)")
    parser.add_argument("--list-controls", action="store_true", help="Liste les vrais noms de contrôle amixer (à faire en premier sur le Pi réel)")
    args = parser.parse_args()

    targets = [args.profile] if args.profile else list(PROFILE_CTL.keys())

    if args.list_controls:
        for name in targets:
            list_controls(PROFILE_CTL[name])
        return 0

    config = load_json(CONFIG_PATH, {"profiles": {}})
    profiles = config.get("profiles", {})

    for name in targets:
        ctl_name = PROFILE_CTL[name]
        profile = profiles.get(name, DEFAULT_PROFILE)
        bands_db = profile.get("bands_db", DEFAULT_PROFILE["bands_db"])
        if len(bands_db) != 10:
            LOGGER.warning("Profil %s: bands_db invalide (%d valeurs, 10 attendues) — ignoré", name, len(bands_db))
            continue

        # Gain global : casque uniquement (décision Thomas, TICKET-124). Les
        # haut-parleurs restent bornés par speakers_max ≤ 80, invariant de
        # sécurité auditive — on n'ouvre pas de porte dérobée pour le contourner.
        gain_db = 0.0
        if name == "casque":
            try:
                gain_db = max(0.0, min(6.0, float(profile.get("gain_db", 0.0))))
            except (TypeError, ValueError):
                LOGGER.warning("Profil casque: gain_db illisible (%r) — ramené à 0",
                               profile.get("gain_db"))
                gain_db = 0.0
            if gain_db:
                LOGGER.info("Profil casque: gain global de %+g dB appliqué aux 10 bandes", gain_db)

        apply_profile(ctl_name, bands_db, gain_db=gain_db, dry_run=args.dry_run)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
