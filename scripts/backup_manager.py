#!/usr/bin/env python3
"""TICKET-085 — Sauvegarde de la carte SD (ghost complet, dd|gzip) vers un NAS
distant (Freebox, monté en CIFS).

Sauvegarde manuelle uniquement, déclenchée depuis la page admin quand Thomas
valide un état stable du projet ("version durcie") — pas de sauvegarde
automatique quotidienne : les évolutions du projet ne sont pas assez
fréquentes/critiques pour le justifier, et ça évite de gaspiller de l'espace
NAS et de la bande passante pour rien.

Une seule version durcie à la fois, remplacée à chaque validation (écriture
sur un fichier temporaire puis bascule atomique, pour ne jamais laisser un
état sans durcie valide si le process est interrompu).

Le NAS ou le réseau peuvent être indisponibles : ce script ne plante jamais
dans ce cas, il enregistre l'échec dans data/backup_state.json (lu par la
page admin) et sort proprement.

Usage :
    python3 backup_manager.py validate [--label "texte libre"]
    python3 backup_manager.py status
    python3 backup_manager.py sync_private   # copie private/ vers le NAS (jamais sur GitHub)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "data" / "backup_config.json"
STATE_PATH = PROJECT_ROOT / "data" / "backup_state.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("backup_manager")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        LOGGER.warning("Impossible de lire %s: %s", path, e)
        return default


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.rename(path)


def load_config() -> dict[str, Any]:
    return load_json(CONFIG_PATH, {})


def load_state() -> dict[str, Any]:
    return load_json(STATE_PATH, {"durcie": {}})


def save_state(state: dict[str, Any]) -> None:
    atomic_write_json(STATE_PATH, state)


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def nas_reachable(host: str, timeout: int = 3) -> bool:
    try:
        r = subprocess.run(
            ["ping", "-c", "1", "-W", str(timeout), host],
            capture_output=True, timeout=timeout + 2,
        )
        return r.returncode == 0
    except Exception:
        return False


def is_mounted(mount_point: str) -> bool:
    try:
        with open("/proc/mounts") as f:
            return any(line.split()[1] == mount_point for line in f)
    except Exception:
        return False


def nas_mount(cfg: dict[str, Any]) -> tuple[bool, str]:
    nas = cfg["nas"]
    mount_point = nas["mount_point"]
    if is_mounted(mount_point):
        return True, ""

    if not nas_reachable(nas["host"]):
        return False, f"NAS injoignable ({nas['host']}) — Pi hors réseau ou NAS éteint"

    creds_file = Path(nas["credentials_file"])
    if not creds_file.exists():
        return False, f"Fichier d'identifiants manquant : {creds_file} (voir docs/85-SAUVEGARDE_RESTAURATION.md)"

    os.makedirs(mount_point, exist_ok=True)
    cmd = [
        "mount", "-t", "cifs", f"//{nas['host']}/{nas['share']}", mount_point,
        "-o", f"credentials={creds_file},vers=3.0,uid=0,gid=0,iocharset=utf8",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        return False, f"Échec montage CIFS : {r.stderr.strip()[:300]}"
    return True, ""


def nas_unmount(cfg: dict[str, Any]) -> None:
    mount_point = cfg["nas"]["mount_point"]
    if is_mounted(mount_point):
        subprocess.run(["umount", mount_point], capture_output=True, timeout=15)


def nas_backup_dir(cfg: dict[str, Any]) -> Path:
    return Path(cfg["nas"]["mount_point"]) / cfg["nas"]["subdir"]


def nas_private_dir(cfg: dict[str, Any]) -> Path:
    sub = cfg["nas"].get("private_subdir") or (cfg["nas"]["subdir"] + "/private")
    return Path(cfg["nas"]["mount_point"]) / sub


def source_device() -> str:
    out = subprocess.run(
        ["findmnt", "-n", "-o", "SOURCE", "/"], capture_output=True, text=True, timeout=5,
    )
    src = out.stdout.strip()
    return re.sub(r"p?\d+$", "", src)


def run_ghost(dest_file: Path) -> tuple[bool, str, int]:
    """dd | gzip vers dest_file. Retourne (ok, erreur, taille_octets)."""
    src = source_device()
    if not src:
        return False, "Impossible de déterminer le périphérique source (findmnt)", 0

    dest_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_dest = dest_file.with_suffix(dest_file.suffix + ".part")

    shell_cmd = (
        f"set -o pipefail; "
        f"dd if={src} bs=4M status=none conv=noerror,sync | gzip -c > {tmp_dest}"
    )
    LOGGER.info("Ghost en cours : %s -> %s", src, dest_file)
    r = subprocess.run(["bash", "-c", shell_cmd], capture_output=True, text=True)
    if r.returncode != 0 or not tmp_dest.exists():
        tmp_dest.unlink(missing_ok=True)
        return False, f"dd|gzip a échoué (code {r.returncode}) : {r.stderr.strip()[:300]}", 0

    size = tmp_dest.stat().st_size
    if size < 100 * 1024 * 1024:  # sanity check : une carte de 100+ Go compressée ne devrait jamais faire <100 Mo
        tmp_dest.unlink(missing_ok=True)
        return False, f"Image suspecte ({size} octets) — abandon, rien n'est écrasé", 0

    tmp_dest.rename(dest_file)
    return True, "", size


def write_readme(cfg: dict[str, Any], state: dict[str, Any]) -> None:
    durcie = state.get("durcie", {})
    content = f"""# Sauvegardes Hechicero — LIS-MOI D'ABORD

Ce dossier contient des images complètes (ghost) de la carte SD du Raspberry Pi
"Hechicero". Sauvegarde manuelle uniquement, faite après chaque évolution
majeure validée par Thomas — pas de rythme automatique. Mis à jour à chaque
validation — dernière mise à jour : {now_iso()}

## État actuel

- **Version durcie actuelle** : `{durcie.get('file', '—')}` — validée le {durcie.get('validated_at', '—')}
  {("(" + durcie.get('label') + ")") if durcie.get('label') else ''}

## Comment restaurer une carte SD (depuis un PC Windows)

1. Récupère `hechicero_durcie.img.gz` dans ce dossier
2. Télécharge et installe **Raspberry Pi Imager** si ce n'est pas déjà fait : https://www.raspberrypi.com/software/
3. Ouvre Raspberry Pi Imager
4. Clique sur **"CHOOSE OS"** → tout en bas → **"Use custom"** → sélectionne le fichier `.img.gz` directement dans ce dossier réseau (pas besoin de le décompresser, Raspberry Pi Imager le fait automatiquement)
5. Clique sur **"CHOOSE STORAGE"** → sélectionne la nouvelle carte SD (⚠️ vérifie bien que c'est la bonne carte, tout son contenu sera effacé)
6. Clique sur **"WRITE"** et attends la fin (plusieurs minutes)
7. Retire la carte, insère-la dans le Raspberry Pi, branche l'alimentation
8. Hechicero doit redémarrer directement dans sa configuration habituelle

**Optionnel — code à jour :** cette image ne contient que le code du moment de
cette validation. Si du code plus récent a été poussé sur GitHub depuis,
`cd ~/hechicero && git pull` sur le Pi une fois redémarré (le dépôt git est
déjà sur l'image, pas besoin de le re-cloner). Sans risque pour la config
système, qui n'est pas suivie par git.

Détail complet (avec dépannage) : `docs/85-SAUVEGARDE_RESTAURATION.md`
dans le dépôt du projet (accessible via Q:\\ si le partage Samba fonctionne,
sinon sur GitHub).

## Ce que cette image contient

Un ghost complet et bootable de la carte SD : système d'exploitation, toute la
configuration (MPD, Apache, Plymouth, ALSA...), le code du projet, et les
données (podcasts déjà téléchargés, statistiques). Il suffit de la restaurer
et de brancher — pas d'étape de configuration supplémentaire.
"""
    backup_dir = nas_backup_dir(cfg)
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        (backup_dir / "README.md").write_text(content, encoding="utf-8")
    except Exception as e:
        LOGGER.warning("Impossible d'écrire le README sur le NAS : %s", e)


def cmd_validate(label: str) -> int:
    cfg = load_config()
    state = load_state()
    now = now_iso()

    ok, err = nas_mount(cfg)
    if not ok:
        LOGGER.error("Validation durcie impossible : %s", err)
        state.setdefault("durcie", {})["last_validation_error"] = err
        save_state(state)
        return 1

    prefix = cfg.get("image_prefix", "hechicero")
    final_dest = nas_backup_dir(cfg) / f"{prefix}_durcie.img.gz"
    staging_dest = nas_backup_dir(cfg) / f"{prefix}_durcie_STAGING.img.gz"

    success, error, size = run_ghost(staging_dest)
    if not success:
        LOGGER.error("Validation durcie échouée : %s", error)
        state.setdefault("durcie", {})["last_validation_error"] = error
        save_state(state)
        nas_unmount(cfg)
        return 1

    # Bascule atomique : ne remplace la durcie existante qu'une fois la nouvelle
    # image confirmée valide (jamais de trou sans durcie valide).
    staging_dest.rename(final_dest)

    state["durcie"] = {
        "validated_at": now,
        "label": label or "",
        "size_mb": round(size / 1024 / 1024),
        "file": final_dest.name,
        "git_commit": git_commit(),
        "last_validation_error": None,
    }
    write_readme(cfg, state)
    save_state(state)
    nas_unmount(cfg)
    LOGGER.info("Version durcie validée : %s (%s Mo)", final_dest.name, state["durcie"]["size_mb"])
    return 0


def cmd_status() -> int:
    print(json.dumps(load_state(), indent=2, ensure_ascii=False))
    return 0


def cmd_sync_private() -> int:
    """Synchronise private/ (jamais dans git, jamais sur GitHub) vers un dossier
    dédié sur le NAS. Déclenché automatiquement par le hook git post-commit —
    ne doit jamais faire échouer un commit : toute erreur est juste consignée
    dans data/backup_state.json (clé private_sync) et le script sort proprement.
    Ne supprime jamais rien côté NAS (rsync sans --delete) : accumulation
    volontaire, on ne veut pas qu'une suppression locale accidentelle efface
    aussi la copie de sauvegarde.
    """
    cfg = load_config()
    state = load_state()
    now = now_iso()
    private_src = PROJECT_ROOT / "private"

    if not private_src.is_dir():
        return 0  # rien a synchroniser

    ok, err = nas_mount(cfg)
    if not ok:
        LOGGER.warning("Sync private/ ignorée : %s", err)
        state["private_sync"] = {"last_attempt": now, "ok": False, "error": err}
        save_state(state)
        return 0

    dest = nas_private_dir(cfg)
    dest.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["rsync", "-a", f"{private_src}/", f"{dest}/"],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0:
        err = r.stderr.strip()[:300]
        LOGGER.warning("rsync private/ échoué : %s", err)
        state["private_sync"] = {"last_attempt": now, "ok": False, "error": err}
    else:
        LOGGER.info("private/ synchronisé vers le NAS")
        state["private_sync"] = {"last_attempt": now, "ok": True, "error": None}
    save_state(state)
    nas_unmount(cfg)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_validate = sub.add_parser("validate")
    p_validate.add_argument("--label", default="", help="Description libre de cette version durcie")
    sub.add_parser("status")
    sub.add_parser("sync_private")
    args = parser.parse_args()

    if args.cmd == "validate":
        return cmd_validate(args.label)
    if args.cmd == "status":
        return cmd_status()
    if args.cmd == "sync_private":
        return cmd_sync_private()
    return 1


if __name__ == "__main__":
    sys.exit(main())
