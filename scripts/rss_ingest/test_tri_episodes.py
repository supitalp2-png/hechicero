#!/usr/bin/env python3
"""Tests du tri des épisodes — TICKET-131.

Pourquoi ce fichier existe : le bug signalé par le petit (« les épisodes des
Explorateurs de l'Univers, ils sont à l'envers ») venait de dates de
publication inversées, et le correctif touche l'ordre d'affichage de **tous**
les podcasts. Un tel changement ne se valide pas à l'œil sur un seul podcast :
il faut prouver dans le même mouvement que le cas cassé est réparé ET que les
cas qui marchaient n'ont pas bougé.

Les deux cas de non-régression sont réels, pas inventés :
  · Olma — titres « Episode N. … » mais numérotation qui REDÉMARRE à chaque
    série (1→32, puis 1→20). Trier par numéro l'entrelacerait. 55 épisodes.
  · Tina — saisons détectées via « Nom N/M : », déjà traitées par TICKET-104.

Sans effet de bord : aucune lecture de fichier, aucun réseau.
    python3 scripts/rss_ingest/test_tri_episodes.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from models import Episode          # noqa: E402
from parser import (                # noqa: E402
    numero_episode_explicite,
    tri_par_numero_applicable,
    trier_episodes,
)

echecs: list[str] = []


def ep(titre: str, saison=None) -> Episode:
    return Episode(
        id=titre.lower().replace(" ", ""), title=titre, audio_url="", local_audio="",
        image_url=None, local_image=None, published="", duration=None, season=saison,
    )


def verifie(nom: str, obtenu, attendu) -> None:
    if obtenu == attendu:
        print(f"  ok   {nom}")
    else:
        print(f"  ÉCHEC {nom}\n       obtenu  : {obtenu}\n       attendu : {attendu}")
        echecs.append(nom)


# ── 1. Extraction du numéro ────────────────────────────────────────────────
verifie("« Episode 8 : … » -> 8", numero_episode_explicite("Episode 8 : C'est quoi un trou noir ?"), 8)
verifie("« Episode 7. … » -> 7", numero_episode_explicite("Episode 7. La naissance d’un trou noir"), 7)
verifie("accent « Épisode 3 : » -> 3", numero_episode_explicite("Épisode 3 : Les étoiles"), 3)
# Le numéro doit être EN TÊTE et suivi d'un séparateur, sinon on fabrique des
# faux positifs sur des titres qui contiennent simplement un chiffre.
verifie("numéro au milieu -> None", numero_episode_explicite("Pourquoi y a-t-il 8 planètes ?"), None)
verifie("sans séparateur -> None", numero_episode_explicite("Episode surprise"), None)
verifie("titre vide -> None", numero_episode_explicite(""), None)


# ── 2. Le cas cassé : Explorateurs de l'Univers ────────────────────────────
# Dates réelles du flux : épisode 8 publié à 19:59, épisode 1 à 20:06, la
# présentation à 20:07. Chronologique croissant = 8, 7, 6 … 1 : à l'envers.
base = 1747936740  # 19:59
explorateurs = [
    (base + 0,   None, None, ep("Episode 8 : C'est quoi un trou noir ?")),
    (base + 60,  None, None, ep("Episode 7. La naissance d’un trou noir")),
    (base + 120, None, None, ep("Episode 6. Vie et mort des étoiles")),
    (base + 180, None, None, ep("Episode 5. Le Système solaire, 2e partie")),
    (base + 240, None, None, ep("Episode 4. Exploration du Système solaire")),
    (base + 300, None, None, ep("Episode 3. Pourquoi les étoiles brillent ?")),
    (base + 360, None, None, ep("Episode 2. Comment la Terre se protège")),
    (base + 420, None, None, ep("Episode 1. Pourquoi le ciel est bleu")),
    (base + 480, None, None, ep("Deviens un explorateur de l’Univers !")),
]
verifie("Explorateurs : tri par numéro applicable", tri_par_numero_applicable(explorateurs), True)
verifie(
    "Explorateurs : 1→8 puis la présentation",
    [numero_episode_explicite(e.title) for _, _, _, e in trier_episodes(explorateurs)],
    [1, 2, 3, 4, 5, 6, 7, 8, None],
)


# ── 3. Non-régression Olma : numérotation qui redémarre ────────────────────
olma = [
    (100, None, None, ep("Episode 1. Le Système solaire")),
    (200, None, None, ep("Episode 2. La vie dans l’Univers")),
    (300, None, None, ep("Episode 1. Opération Canopée")),   # la série repart à 1
    (400, None, None, ep("Episode 2. Au cœur de la forêt")),
]
verifie("Olma : tri par numéro NON applicable (doublons)", tri_par_numero_applicable(olma), False)
verifie(
    "Olma : ordre chronologique préservé",
    [e.title for _, _, _, e in trier_episodes(olma)],
    ["Episode 1. Le Système solaire", "Episode 2. La vie dans l’Univers",
     "Episode 1. Opération Canopée", "Episode 2. Au cœur de la forêt"],
)


# ── 4. Non-régression Tina : saisons détectées ─────────────────────────────
# Saison 2 a une date plus ancienne que la saison 1 sur son 1er épisode, et
# l'épisode 2 de la saison 1 a une date incohérente (le bug de TICKET-104).
tina = [
    (500, "Tina et le trésor", 1, ep("Tina et le trésor 1/10 : Le début", "Tina et le trésor")),
    (100, "Tina et le trésor", 2, ep("Tina et le trésor 2/10 : Les lettres", "Tina et le trésor")),
    (900, "Tina et les boucliers", 1, ep("Tina et les boucliers 1/10 : Les anciles", "Tina et les boucliers")),
]
verifie("Tina : tri par numéro NON applicable (saisons)", tri_par_numero_applicable(tina), False)
verifie(
    "Tina : saisons groupées, numéro dans la saison",
    [e.title for _, _, _, e in trier_episodes(tina)],
    ["Tina et le trésor 1/10 : Le début", "Tina et le trésor 2/10 : Les lettres",
     "Tina et les boucliers 1/10 : Les anciles"],
)


# ── 5. Un seul titre numéroté ne doit pas basculer tout l'ordre ────────────
un_seul = [
    (100, None, None, ep("Episode 1 : le seul numéroté")),
    (200, None, None, ep("Un titre libre")),
    (300, None, None, ep("Un autre titre libre")),
    (400, None, None, ep("Encore un titre libre")),
]
verifie("un seul numéroté sur quatre : NON applicable", tri_par_numero_applicable(un_seul), False)


print()
if echecs:
    print(f"⛔ {len(echecs)} test(s) en échec : {', '.join(echecs)}")
    raise SystemExit(1)
print("🟢 tri des épisodes : tous les tests passent")
