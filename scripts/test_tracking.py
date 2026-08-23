#!/usr/bin/env python3
"""
test_tracking.py — Tests de garde du suivi d'écoute (play_tracker).

TICKET-146 : la langue d'un podcast était lue sous une clé qui n'existe pas
(`langue`/`lang` au lieu de `language`), donc *tous* les podcasts étaient
enregistrés en français. Le graphique « temps par langue » n'a jamais compté
une seule minute de podcast espagnol.

Ces tests vérifient un comportement — la langue effectivement retenue pour une
entrée réelle de podcasts.json — et non la présence d'un mot dans le code.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import play_tracker as pt        # noqa: E402
from battery_common import DATA_DIR   # noqa: E402

ok = 0
ko = 0


def verifie(nom: str, condition: bool, detail: str = "") -> None:
    global ok, ko
    if condition:
        ok += 1
    else:
        ko += 1
        print(f"  ❌ {nom}" + (f" — {detail}" if detail else ""))


# ── 1. Lecture de la langue selon le nom de champ réellement utilisé ─────────
# Les podcasts déclarent `language`, les radios `lang`. Les deux doivent marcher.

verifie("podcast avec 'language'", pt.lire_langue({"language": "es"}) == "es",
        f"obtenu {pt.lire_langue({'language': 'es'})!r}")
verifie("radio avec 'lang'", pt.lire_langue({"lang": "es"}) == "es")
verifie("champ 'langue' toléré", pt.lire_langue({"langue": "es"}) == "es")
verifie("aucun champ → fr", pt.lire_langue({}) == "fr")
verifie("champ vide → fr", pt.lire_langue({"language": "   "}) == "fr")
verifie("casse et espaces normalisés", pt.lire_langue({"language": " ES "}) == "es")
verifie("valeur non textuelle ignorée", pt.lire_langue({"language": None, "lang": "es"}) == "es")


# ── 2. L'index construit depuis un podcasts.json réaliste ────────────────────
# Le piège du 146 : un fichier bien formé, un podcast bien déclaré espagnol,
# et pourtant 'fr' en sortie. On rejoue exactement cette structure.

exemple = {
    "podcasts": [
        {"id": "cuentos_es", "label": "Cuentos", "language": "es", "enabled": True},
        {"id": "encyclo_fr", "label": "Encyclo", "language": "fr", "enabled": True},
        {"id": "sans_langue", "label": "Sans", "enabled": True},
    ],
    "radios": [
        {"id": "radio_es", "name": "La Mega", "lang": "es", "url": "http://exemple/es"},
        {"id": "radio_fr", "name": "Inter", "lang": "fr", "url": "http://exemple/fr"},
    ],
}

with tempfile.TemporaryDirectory() as tmp:
    chemin = Path(tmp) / "podcasts.json"
    chemin.write_text(json.dumps(exemple), encoding="utf-8")

    original = pt.PODCASTS_PATH
    try:
        pt.PODCASTS_PATH = chemin
        idx = pt.build_track_index()

        verifie("index : podcast espagnol → es", idx["pods"].get("cuentos_es") == "es",
                f"obtenu {idx['pods'].get('cuentos_es')!r}")
        verifie("index : podcast français → fr", idx["pods"].get("encyclo_fr") == "fr")
        verifie("index : podcast sans langue → fr", idx["pods"].get("sans_langue") == "fr")
        verifie("index : radio espagnole → es",
                idx["radios"]["http://exemple/es"]["langue"] == "es")

        # ── 3. identify() attribue la bonne langue à un fichier de podcast ───
        meta = pt.identify(f"{pt.PROJECT_ROOT}/podcasts/cuentos_es/ep001.mp3", 600.0, idx)
        verifie("identify : épisode espagnol → es", meta and meta["langue"] == "es",
                f"obtenu {meta and meta['langue']!r}")
        meta_fr = pt.identify("podcasts/encyclo_fr/ep001.mp3", 600.0, idx)
        verifie("identify : épisode français → fr", meta_fr and meta_fr["langue"] == "fr")
        meta_inc = pt.identify("podcasts/jamais_vu/ep001.mp3", 600.0, idx)
        verifie("identify : podcast inconnu → fr par défaut",
                meta_inc and meta_inc["langue"] == "fr")

        # ── 4. L'index se recharge quand podcasts.json change ────────────────
        # Le service tourne des semaines : un podcast ajouté après le démarrage
        # doit être reconnu sans redémarrer le service.
        pt._INDEX_CACHE = {}
        pt._INDEX_MTIME = None
        verifie("cache : premier appel construit l'index",
                pt.index_courant()["pods"].get("cuentos_es") == "es")

        exemple["podcasts"].append({"id": "nouveau_es", "label": "N", "language": "es"})
        time.sleep(0.01)
        chemin.write_text(json.dumps(exemple), encoding="utf-8")
        import os
        os.utime(chemin, (time.time() + 1, time.time() + 1))

        verifie("cache : podcast ajouté après démarrage reconnu",
                pt.index_courant()["pods"].get("nouveau_es") == "es",
                "l'index n'a pas été rechargé après modification de podcasts.json")
    finally:
        pt.PODCASTS_PATH = original
        pt._INDEX_CACHE = {}
        pt._INDEX_MTIME = None


# ── 5. Cohérence du catalogue réel avec la base ──────────────────────────────
# Garde de terrain : si un podcast déclaré espagnol n'a que des événements
# français en base, c'est le 146 qui recommence.

reel = DATA_DIR / "podcasts.json"
base = DATA_DIR / "tracking.db"
if reel.exists() and base.exists():
    import sqlite3
    catalogue = {p["id"]: pt.lire_langue(p)
                 for p in json.loads(reel.read_text(encoding="utf-8")).get("podcasts", [])
                 if p.get("id")}
    conn = sqlite3.connect(f"file:{base}?mode=ro", uri=True)
    incoherents = []
    for pid, langue, n in conn.execute(
        "SELECT podcast_id, langue, COUNT(*) FROM play_events "
        "WHERE is_radio=0 GROUP BY podcast_id, langue"
    ):
        attendue = catalogue.get(pid)
        if attendue and attendue != langue:
            incoherents.append(f"{pid}: base={langue} catalogue={attendue} ({n} évts)")
    conn.close()
    verifie("base : aucune langue en désaccord avec le catalogue",
            not incoherents, "; ".join(incoherents[:4]))
else:
    print("  ⏭️  contrôle base réelle ignoré (fichiers absents)")

print(f"\n{ok} test(s) OK, {ko} échec(s)")
sys.exit(1 if ko else 0)
