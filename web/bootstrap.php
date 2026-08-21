<?php
// ============================================================
// Hechicero — Amorçage commun à toutes les pages PHP
// ============================================================
//
// ── TICKET-129 — PHP tournait en UTC, tout le reste en heure locale ────────
//
// Sans `date.timezone` dans php.ini, PHP retombe sur UTC. Or les scripts Python
// (`battery_tracker`, `play_tracker`…) et le shell écrivent en heure LOCALE.
// Résultat : deux heures d'écart entre journaux croisés, précisément au moment
// où l'on croise des journaux — c'est-à-dire pendant une panne.
//
// Ce défaut a mordu QUATRE fois avant d'être traité à la racine :
//   1. TICKET-102 — traceur d'écran de veille daté en UTC
//   2. TICKET-127 — chronologie du gel du kiosque décalée de 2 h
//   3. TICKET-136 — la fraîcheur de la mesure batterie paraissait périmée de
//                   2 h en permanence, corrigée par une rustine locale
//   4. TICKET-138 — `sleep_debug.log` en UTC pendant que `screen_dpms.log`
//                   est en local, sur le même diagnostic
//
// Les trois premières fois, on a posé une rustine `new DateTimeZone(...)` à
// l'endroit qui faisait mal. ⚠️ **Une correction posée au point de douleur ne
// corrige que ce point** : le défaut restait entier partout ailleurs, et
// revenait sous un autre visage. D'où ce fichier.
//
// ── POURQUOI ICI ET PAS DANS php.ini ──────────────────────────────────────
// `php.ini` vit hors du dépôt. Une carte SD fraîchement restaurée repartirait
// en UTC sans que rien ne le signale — exactement le type de panne latente
// décrit en zone Z2. Le fuseau doit voyager AVEC le code.
date_default_timezone_set('Europe/Paris');
