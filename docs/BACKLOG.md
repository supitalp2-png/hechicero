# Backlog Hechicero

> Convention : `TICKET-### — [type] — Titre — (prio) — owner`

---

# ✔️ Terminé

- [x] TICKET-001 — infra — Structure projet + liens Apache
- [x] TICKET-002 — infra — Monitoring batterie (INA219 + service systemd)
- [x] TICKET-003 — audio — HiFiBerry Amp4 + MPD opérationnel
- [x] TICKET-024 — audio — Lecture Webradio
- [x] TICKET-025 — backend — Ingestion RSS (Radio France)
- [x] TICKET-026 — backend — Génération automatique de `data.json`

---

# 🔥 Priorité haute (en cours)

- [ ] TICKET-022 — web — Lecteur embarqué (IHM enfant)
- [ ] TICKET-027 — infra — Service systemd + timer pour ingestion RSS
- [ ] TICKET-028 — web — Nettoyage et finalisation du lecteur
- [ ] TICKET-031 — feature — Ajouter une sortie casque via dongle USB + détection jack sur GPIO (prio: Medium) — owner: audio+backend

---

# 🟡 Priorité moyenne

- [ ] TICKET-004 — content — Gestion multi-podcasts (FR/ES)
- [ ] TICKET-005 — web — Dashboard Admin (config flux)
- [ ] TICKET-007 — web — Interface configuration podcasts.json
- [ ] TICKET-029 — backend — Quotas stockage (max_episodes)

---

# 🟢 Priorité basse

- [ ] TICKET-008 — infra — Endpoint `/health`
- [ ] TICKET-010 — infra — Rotation logs
- [ ] TICKET-011 — sec — Durcir unités systemd
- [ ] TICKET-012 — test — Tests unitaires ingestion RSS
- [ ] TICKET-014 — docs — Procédure de mise à jour
- [ ] TICKET-017 — monitoring — Exporter Prometheus
- [ ] TICKET-020 — web — Page admin avancée
- [ ] TICKET-023 — audio — Startup sound
- [ ] TICKET-030 — feature — Ajouter un système d’égaliseur audio paramétrable depuis l’interface d’administration (prio: Medium) — owner: frontend+audio



###### Description tickets ####


    Description 030 :
    - Permettre à l’administrateur de régler les paramètres audio (basses, aigus, loudness, presets)
      directement depuis l’interface web d’administration.
    - L’interface doit exposer :
        • sliders pour gain par bande (ex : 60 Hz, 120 Hz, 1 kHz, 8 kHz…)
        • un preset “basses + chaleur”
        • un preset “voix claires”
        • un preset “flat”
    - Le backend doit appliquer les réglages en temps réel via le moteur audio choisi (CamillaDSP ou ALSA EQ).
    - Prévoir un endpoint REST pour :
        • récupérer les valeurs actuelles
        • appliquer un preset
        • modifier une bande
    - Prévoir une persistance (fichier JSON ou DB)
    - Prévoir une validation pour éviter le clipping (limiter gain global)



    Description 31 :
    - Ajouter un dongle USB audio simple pour la sortie casque.
    - Ajouter un jack 3.5 mm avec switch de détection (type PJ-307).
    - Connecter le switch du jack à un GPIO du Raspberry Pi 5.
    - Backend : lire l’état du GPIO et basculer automatiquement la sortie audio :
        • HP → HiFiBerry Amp4
        • Casque → USB DAC
    - MPD : configurer deux audio_output et gérer enable/disable.
    - Interface admin : afficher l’état “Casque branché”.

