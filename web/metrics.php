<?php
// ============================================================
// Hechicero — Endpoint Prometheus /metrics (TICKET-017)
// Accès : http://<rpi>/metrics.php
// Réseau local uniquement — pas d'authentification requise (cf. health.php)
// Format d'exposition texte Prometheus (https://prometheus.io/docs/instrumenting/exposition_formats/)
// ============================================================

define('PROJECT_ROOT', is_dir('/home/thomas/hechicero') ? '/home/thomas/hechicero' : dirname(__DIR__));
define('DB_PATH', PROJECT_ROOT . '/data/tracking.db');

// battery_tracker.py écrit "last_updated" avec datetime.now() (naïf, heure locale
// du Pi, pas d'offset UTC). Sans ce réglage, strtotime() l'interprète avec le
// fuseau par défaut de PHP (UTC si non configuré), ce qui décale le calcul de
// hechicero_battery_stats_age_seconds d'environ 2h (écart CEST constaté en
// conditions réelles le 2026-07-18 : valeur ~-7185 au lieu d'un petit positif).
date_default_timezone_set('Europe/Paris');

header('Content-Type: text/plain; version=0.0.4; charset=utf-8');
header('Cache-Control: no-store');

$lines = [];

function metric(array &$lines, string $name, string $help, string $type, $value, array $labels = []): void {
    static $declared = [];
    if (!isset($declared[$name])) {
        $lines[] = "# HELP {$name} {$help}";
        $lines[] = "# TYPE {$name} {$type}";
        $declared[$name] = true;
    }
    if ($value === null) return; // pas de donnée : on omet la métrique plutôt que d'exposer un faux 0
    $label_str = '';
    if ($labels) {
        $parts = [];
        foreach ($labels as $k => $v) {
            $v = str_replace(['\\', '"', "\n"], ['\\\\', '\\"', '\\n'], (string)$v);
            $parts[] = "{$k}=\"{$v}\"";
        }
        $label_str = '{' . implode(',', $parts) . '}';
    }
    $lines[] = "{$name}{$label_str} " . (is_bool($value) ? ($value ? 1 : 0) : $value);
}

function read_json(string $path): array {
    if (!file_exists($path)) return [];
    $data = json_decode(file_get_contents($path), true);
    return is_array($data) ? $data : [];
}

// ── hechicero_up : présence de ce script = scrape réussi ──────────────────
metric($lines, 'hechicero_up', 'Toujours 1 si /metrics.php répond', 'gauge', 1);

// ── Batterie (data/battery_stats.json, écrit par battery_tracker.py) ──────
$stats = read_json(PROJECT_ROOT . '/data/battery_stats.json');
if ($stats) {
    $age_s = isset($stats['last_updated']) ? (time() - strtotime($stats['last_updated'])) : null;

    metric($lines, 'hechicero_battery_level_percent', 'Niveau de charge batterie (%)', 'gauge', $stats['current_level'] ?? null);
    metric($lines, 'hechicero_battery_charging', 'Batterie en charge (1) ou non (0)', 'gauge', isset($stats['charging']) ? (bool)$stats['charging'] : null);
    metric($lines, 'hechicero_battery_voltage_volts', 'Tension batterie (V)', 'gauge', $stats['voltage_v'] ?? null);
    metric($lines, 'hechicero_battery_current_milliamps', 'Courant batterie (mA, négatif = décharge)', 'gauge', $stats['current_ma'] ?? null);
    metric($lines, 'hechicero_battery_power_watts', 'Puissance batterie (W)', 'gauge', $stats['power_w'] ?? null);
    metric($lines, 'hechicero_battery_screen_on', 'Écran allumé (1) ou en veille (0)', 'gauge', isset($stats['screen_on']) ? (bool)$stats['screen_on'] : null);
    metric($lines, 'hechicero_battery_estimated_autonomy_minutes', 'Autonomie restante estimée (min, historique)', 'gauge', $stats['estimated_autonomy_minutes'] ?? null);
    metric($lines, 'hechicero_battery_estimated_autonomy_minutes_live', 'Autonomie restante estimée (min, courant INA219 live)', 'gauge', $stats['estimated_autonomy_minutes_live'] ?? null);
    metric($lines, 'hechicero_battery_cycles_recorded', 'Nombre de cycles de décharge complets enregistrés', 'gauge', $stats['cycles_recorded'] ?? null);
    metric($lines, 'hechicero_battery_stats_age_seconds', 'Ancienneté de la dernière mesure batterie (s)', 'gauge', $age_s);
}

// ── Santé système (mêmes checks que health.php) ───────────────────────────
$path = PROJECT_ROOT . '/podcasts';
if (!is_dir($path)) $path = PROJECT_ROOT;
$total = disk_total_space($path);
$free  = disk_free_space($path);
if ($total !== false && $free !== false && $total > 0) {
    metric($lines, 'hechicero_disk_used_percent', 'Espace disque utilisé (%)', 'gauge', round(($total - $free) / $total * 100, 1));
    metric($lines, 'hechicero_disk_free_bytes', 'Espace disque libre (octets)', 'gauge', $free);
}

$mpc_output = shell_exec('mpc status 2>&1') ?? '';
$mpd_up = null;
foreach (explode("\n", trim($mpc_output)) as $line) {
    if (str_contains($line, '[playing]') || str_contains($line, '[paused]') || str_contains($line, 'volume:')) {
        $mpd_up = true;
        break;
    }
}
metric($lines, 'hechicero_mpd_up', 'MPD répond (1) ou non (0)', 'gauge', $mpd_up === null ? false : true);

// ── Écoute (data/tracking.db, écrit par play_tracker.php / tracking.php) ──
// Compteurs cumulés depuis le début du suivi : monotones tant que la table
// n'est pas purgée manuellement (comportement standard Prometheus counter).
try {
    if (file_exists(DB_PATH)) {
        $db = new PDO('sqlite:' . DB_PATH);
        $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

        $stmt = $db->query(
            "SELECT langue,
                    CASE WHEN is_radio = 1 THEN 'radio' ELSE 'podcast' END AS type,
                    ROUND(SUM(listened_s), 0) AS seconds
             FROM play_events
             GROUP BY langue, type"
        );
        foreach ($stmt->fetchAll(PDO::FETCH_ASSOC) as $row) {
            metric(
                $lines, 'hechicero_listen_seconds_total',
                "Temps d'écoute cumulé (s), depuis le début du suivi", 'counter',
                (float)$row['seconds'],
                ['langue' => $row['langue'] ?: 'fr', 'type' => $row['type']]
            );
        }

        $stmt = $db->query(
            "SELECT COUNT(*) AS n FROM play_events WHERE completed = 1"
        );
        $row = $stmt->fetch(PDO::FETCH_ASSOC);
        metric($lines, 'hechicero_episodes_completed_total', "Nombre d'épisodes terminés (>=90%), cumulé", 'counter', (float)($row['n'] ?? 0));

        $stmt = $db->query(
            "SELECT COUNT(*) AS n FROM play_events"
        );
        $row = $stmt->fetch(PDO::FETCH_ASSOC);
        metric($lines, 'hechicero_play_sessions_total', 'Nombre de sessions de lecture (podcast + radio), cumulé', 'counter', (float)($row['n'] ?? 0));

        // Casque aujourd'hui : gauge (remise à zéro chaque jour, cf. tracking.php action=headphone_today)
        // max(0, ...) : défense en profondeur contre d'éventuelles lignes listened_s
        // négatives déjà en base (bug corrigé côté source dans play_tracker.py le
        // 2026-07-18, cf. docs/90-BACKLOG.md TICKET-017 — mais les lignes déjà
        // écrites avant le fix restent négatives tant qu'elles ne sont pas purgées).
        $stmt = $db->prepare(
            "SELECT MAX(0, COALESCE(SUM(listened_s), 0)) AS casque_s
             FROM play_events
             WHERE output_mode = 'casque'
               AND date(ts_start, 'unixepoch', 'localtime') = date('now', 'localtime')"
        );
        $stmt->execute();
        $row = $stmt->fetch(PDO::FETCH_ASSOC);
        metric($lines, 'hechicero_headphone_seconds_today', "Temps d'écoute au casque aujourd'hui (s), remis à zéro chaque jour", 'gauge', (float)($row['casque_s'] ?? 0));
    }
} catch (Exception $e) {
    // On n'interrompt pas tout le scrape pour un souci de lecture SQLite —
    // les métriques batterie/santé restent exposées même si tracking.db est verrouillé/absent.
    metric($lines, 'hechicero_tracking_db_error', 'Erreur de lecture de tracking.db (1 = erreur)', 'gauge', true);
}

echo implode("\n", $lines) . "\n";
