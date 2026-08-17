#!/usr/bin/env python3
"""restore_lost_podcasts.py — remet dans la config les podcasts disparus (TICKET-130).

CE QUI S'EST PASSÉ
──────────────────
Neuf podcasts ont disparu de `data/podcasts.json` entre le 2026-08-03 et le
2026-08-05, alors que **tous leurs fichiers sont restés intacts** sur le disque
(audio, images, meta.json). Le petit ne les voyait plus, et personne n'a rien
remarqué pendant deux semaines.

Cause : `data/podcasts.json` est **à la fois suivi par git et réécrit à
l'exécution** par l'IHM d'administration. Les neuf avaient été ajoutés depuis
l'admin — donc dans le fichier de travail, jamais dans un commit
(`git log -S'minivulgaire' -- data/podcasts.json` ne renvoie rien, et le
fichier n'a jamais dépassé 24 entrées en 14 commits). Une opération git ayant
restauré les fichiers suivis à leur état HEAD, les neuf ont disparu sans un
message d'erreur.

D'OÙ VIENNENT LES URL RSS
─────────────────────────
`meta.json` ne stocke pas le flux RSS — seulement id, label, language et les
épisodes. Les URL ci-dessous ont été relevées dans
`data/ingest_full_20260802_1928.log`, qui journalise `Podcast : <label> (<id>)`
suivi de `Parsing RSS: <url>`. C'est la dernière trace connue de la config
complète, et c'est la seule raison pour laquelle cette réparation est possible.

⚠️ Ce script est un OUTIL DE RÉPARATION PONCTUEL, pas un utilitaire du projet.
Il ne corrige pas la cause : voir TICKET-130 pour la décision de fond (qui,
entre git et l'admin, fait autorité sur ce fichier).
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path("/home/thomas/hechicero")
CONFIG = PROJECT_ROOT / "data" / "podcasts.json"
PODCASTS_DIR = PROJECT_ROOT / "podcasts"

# id -> URL du flux, relevées dans data/ingest_full_20260802_1928.log.
# Le label et la langue sont lus dans meta.json (source plus sûre qu'une
# retranscription à la main, et ça évite les fautes d'accent).
RSS_PERDUS = {
    "minivulgaire":                     "https://rss-rf.aerion.me/rss/49ba63ae-c4d4-44a3-a89d-dcce0c25726d",
    "lesptitsbateaux":                  "https://rss-rf.aerion.me/rss/3d680a63-ec3d-11e1-a7b7-782bcb76618d",
    "lesptitsbateauxlesinventions":     "https://rss-rf.aerion.me/rss/e925175e-3237-4333-aa9e-d15ad20fa7b9",
    "thomaspesquetdanslesptitsbateaux": "https://rss-rf.aerion.me/rss/09c60cfd-221d-4251-b2cd-3b756991a9e3",
    "cestlarentreedesptitsbateaux":     "https://rss-rf.aerion.me/rss/7390026d-4850-4bcb-b054-30290a0593fa",
    "concdecuentacuentos":              "https://anchor.fm/s/eb445b60/podcast/rss",
    "sapiensantes":                     "https://api.rtve.es/api/adapter/programas/1000883/audios.rss",
    "laestacionazuldelosninoslean":     "https://api.rtve.es/api/programas/50172/audios.rss",
    "cometacolin":                      "https://anchor.fm/s/fc0c894/podcast/rss",
}


def lire_meta(pid: str) -> dict | None:
    p = PODCASTS_DIR / pid / "meta.json"
    if not p.exists():
        return None
    try:
        with p.open(encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠️  {pid} : meta.json illisible ({e})")
        return None


def main() -> int:
    applique = "--apply" in sys.argv

    if not CONFIG.exists():
        print(f"⛔ {CONFIG} introuvable")
        return 1
    with CONFIG.open(encoding="utf-8") as fh:
        cfg = json.load(fh)

    existants = {p.get("id") for p in cfg.get("podcasts", [])}
    print(f"Config actuelle : {len(existants)} podcast(s)\n")

    a_ajouter = []
    for pid, rss in RSS_PERDUS.items():
        if pid in existants:
            print(f"  = {pid} : déjà présent, ignoré")
            continue
        meta = lire_meta(pid)
        if meta is None:
            print(f"  ⛔ {pid} : pas de meta.json — impossible de restaurer sans label ni langue")
            continue
        n_ep = len(meta.get("episodes", []))
        # `image` suit la convention des entrées existantes ; la jaquette a été
        # téléchargée par l'ingest dans web/lecteur/images/<id>.jpg.
        cover = PROJECT_ROOT / "web" / "lecteur" / "images" / f"{pid}.jpg"
        entree = {
            "id": pid,
            "label": meta.get("label") or pid,
            "rss": rss,
            "enabled": True,
            "language": meta.get("language") or "fr",
            "image": f"images/{pid}.jpg",
            "max_episodes": 999,
        }
        marque = "" if cover.exists() else "  (⚠️ jaquette absente, sera retéléchargée)"
        print(f"  + {pid} : {entree['label']} [{entree['language']}] — {n_ep} épisode(s) sur disque{marque}")
        a_ajouter.append(entree)

    if not a_ajouter:
        print("\nRien à restaurer.")
        return 0

    print(f"\n{len(a_ajouter)} podcast(s) à restaurer, {sum(len(lire_meta(e['id']).get('episodes', [])) for e in a_ajouter)} épisode(s) déjà téléchargés.")

    if not applique:
        print("\nSimulation — aucune écriture. Relancer avec --apply pour appliquer.")
        return 0

    # Sauvegarde horodatée AVANT toute écriture : c'est un fichier qu'on a déjà
    # perdu une fois, on ne prend pas le risque une seconde.
    horo = datetime.now().strftime("%Y%m%d_%H%M%S")
    sauvegarde = CONFIG.with_suffix(f".json.avant_restauration_{horo}")
    shutil.copy2(CONFIG, sauvegarde)
    print(f"\nSauvegarde : {sauvegarde}")

    cfg.setdefault("podcasts", []).extend(a_ajouter)

    # Écriture atomique, même motif que write_json_atomic() côté PHP.
    tmp = CONFIG.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=4, ensure_ascii=False)
        fh.write("\n")
    tmp.replace(CONFIG)
    print(f"✅ {CONFIG} : {len(cfg['podcasts'])} podcast(s)")
    print("\nEnsuite :")
    print("  python3 scripts/rss_ingest/check_integrity.py | tail -3")
    print("  # puis une ingestion pour reconstruire data.json (aucun téléchargement,")
    print("  # tous les fichiers sont déjà là) :")
    print("  python3 scripts/rss_ingest/ingest.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
