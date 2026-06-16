# Backlog Hechicero

> Convention : `TICKET-### — [type] — Titre — (prio: High/Med/Low) — owner: <nom>`

## En cours / Priorité haute
- [x] TICKET-001 — chore — Refactoriser emplacement web et corriger lien symbolique `/var/www/html` — (prio: High) — owner: infra
- [x] TICKET-002 — infra — Monitoring batterie : service systemd + JSON exposé — (prio: High) — owner: infra
- [x] TICKET-003 — feat — Brique Audio : HiFiBerry Amp4 + ALSA + MPD + test lecture locale — (prio: High) — owner: audio
- [x] TICKET-024 — feat — Lecture Webradio : ajout flux Mon Petit France Inter + playlist MPD — (prio: High) — owner: audio
- [ ] TICKET-022 — feat — Brique Lecteur : interface embarquée HTML/JS + data.json — (prio: High) — owner: web

## À venir / Priorité moyenne
- [ ] TICKET-004 — feat — Brique Contenu : structure dossiers Podcasts/Radios (ESP/FR) — (prio: Med) — owner: content
- [ ] TICKET-025 — feat — Ingestion Podcasts : abonnement RSS + téléchargement épisodes (Radio France) — (prio: Med) — owner: content
- [ ] TICKET-026 — feat — Génération automatique de `data.json` (radios + podcasts) — (prio: Med) — owner: web
- [ ] TICKET-005 — feat — Brique IHM Web : prototype dashboard navigation — (prio: Med) — owner: web
- [ ] TICKET-007 — feat — Brique Admin : interface configuration flux — (prio: Med) — owner: web

## Backlog / Priorité basse
- [ ] TICKET-008 — chore — Ajouter health endpoint `/health` pour checks automatisés — (prio: Low) — owner: infra
- [ ] TICKET-009 — chore — Écriture atomique de `status.json` (tempfile + rename) — (prio: Low) — owner: infra
- [ ] TICKET-010 — chore — Rotation automatique des logs (journalctl / Apache) — (prio: Low) — owner: infra
- [ ] TICKET-011 — chore — Durcir unité systemd (réviser Protect* et ReadOnlyPaths) — (prio: Low) — owner: infra
- [ ] TICKET-012 — test — Tests unitaires pour `get_status.py` (mock INA219) — (prio: Low) — owner: dev
- [ ] TICKET-013 — ci — CI simple (lint, tests, déploiement RPi) — (prio: Low) — owner: devops
- [ ] TICKET-014 — docs — Procédure de mise à jour et rollback — (prio: Low) — owner: docs
- [ ] TICKET-015 — ops — Automatiser création du lien symbolique dans le script d'installation — (prio: Low) — owner: infra
- [ ] TICKET-016 — sec — TLS pour interface web (Let's Encrypt) si exposée — (prio: Low) — owner: infra
- [ ] TICKET-017 — monitoring — Monitoring/alerting (Prometheus exporter) — (prio: Low) — owner: infra
- [ ] TICKET-018 — ux — Option de configuration pour intervalle backend (`config.json`) — (prio: Low) — owner: web
- [ ] TICKET-019 — ux — Vérifier et corriger les cas d’erreur frontend — (prio: Low) — owner: web
- [ ] TICKET-020 — feat — Page d’administration locale (logs, redémarrage) — (prio: Low) — owner: web
- [ ] TICKET-021 — sec — Revue sécurité et pentest basique — (prio: Low) — owner: security
- [ ] TICKET-023 — feat — “Startup sound” amusant (MVP+) — (prio: Low) — owner: audio
