# Backlog Hechicero

> Convention : `TICKET-### — [type] — Titre — (prio: High/Med/Low) — owner: <nom>`

## En cours / Priorité haute
- [x] TICKET-001 — chore — Refactoriser emplacement web et corriger lien symbolique `/var/www/html` — (prio: High) — owner: infra
- [x] TICKET-002 — infra — Architecture Service : monitoring batterie en service systemd (JSON) — (prio: High) — owner: infra
- [ ] TICKET-003 — feat — Brique Audio : driver HiFiBerry Amp4, config MPD — (prio: High) — owner: audio
- [ ] TICKET-022 — feat — Brique Lecteur : interface embarquée HTML/JS + data.json — (prio: High) — owner: web

## À venir / Priorité moyenne
- [ ] TICKET-004 — feat — Brique Contenu : structure dossiers Podcasts/Radios (ESP/FR) — (prio: Med) — owner: content
- [ ] TICKET-005 — feat — Brique IHM Web : prototype dashboard navigation — (prio: Med) — owner: web
- [ ] TICKET-006 — feat — Brique IHM Physique : écran + boutons (Merlin-like) — (prio: Med) — owner: hw
- [ ] TICKET-007 — feat — Brique Admin : interface configuration flux — (prio: Med) — owner: web

## Backlog / Priorité basse
- [ ] TICKET-008 — chore — Ajouter health endpoint `/health` pour checks automatisés — (prio: Low) — owner: infra
- [ ] TICKET-009 — chore — Mettre en place écriture atomique de `status.json` (tempfile + rename) — (prio: Low) — owner: infra
- [ ] TICKET-010 — chore — Configurer rotation automatique des logs (journalctl / Apache) — (prio: Low) — owner: infra
- [ ] TICKET-011 — chore — Durcir unité systemd (réviser Protect* et ReadOnlyPaths) — (prio: Low) — owner: infra
- [ ] TICKET-012 — test — Ajouter tests unitaires pour `get_status.py` (mock INA219) — (prio: Low) — owner: dev
- [ ] TICKET-013 — ci — Ajouter CI simple (lint, tests, déploiement sur RPi) — (prio: Low) — owner: devops
- [ ] TICKET-014 — docs — Documenter procédure de mise à jour et rollback — (prio: Low) — owner: docs
- [ ] TICKET-015 — ops — Automatiser création du lien symbolique dans le script d'installation — (prio: Low) — owner: infra
- [ ] TICKET-016 — sec — Ajouter TLS pour l’interface web (Let's Encrypt) si exposée — (prio: Low) — owner: infra
- [ ] TICKET-017 — monitoring — Mettre en place monitoring/alerting (ex. Prometheus exporter) — (prio: Low) — owner: infra
- [ ] TICKET-018 — ux — Ajouter option de configuration pour intervalle backend (config.json) — (prio: Low) — owner: web
- [ ] TICKET-019 — ux — Vérifier et corriger les cas d’erreur dans le frontend (messages) — (prio: Low) — owner: web
- [ ] TICKET-020 — feat — Ajouter page d’administration locale (logs, redémarrage) — (prio: Low) — owner: web
- [ ] TICKET-021 — sec — Revue sécurité et pentest basique — (prio: Low) — owner: security
