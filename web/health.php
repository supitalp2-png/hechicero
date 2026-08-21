<?php
require_once __DIR__ . '/bootstrap.php';  // TICKET-129 : fuseau Europe/Paris, sinon PHP tourne en UTC
// ============================================================
// Hechicero — Endpoint /health
// Accès : http://<rpi>/health.php
// Réseau local uniquement — pas d'authentification requise
// Retourne JSON avec statut des composants clés
// ============================================================

define('PROJECT_ROOT', is_dir('/home/thomas/hechicero') ? '/home/thomas/hechicero' : dirname(__DIR__));

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

// --- Helpers ---

function read_json(string $path): array {
    if (!file_exists($path)) return [];
    $data = json_decode(file_get_contents($path), true);
    return is_array($data) ? $data : [];
}

function check_mpd(): array {
    $output = shell_exec('mpc status 2>&1') ?? '';
    $lines  = explode("\n", trim($output));
    $state  = 'unknown';
    foreach ($lines as $line) {
        if (str_contains($line, '[playing]')) { $state = 'playing'; break; }
        if (str_contains($line, '[paused]'))  { $state = 'paused';  break; }
        if (str_contains($line, 'volume:'))   { $state = 'stopped'; break; }
    }
    $ok = ($state !== 'unknown');
    return ['ok' => $ok, 'state' => $state];
}

function check_battery(): array {
    $stats = read_json(PROJECT_ROOT . '/data/battery_stats.json');
    if (empty($stats)) return ['ok' => false, 'error' => 'battery_stats.json absent'];
    $age_s = isset($stats['ts']) ? (time() - strtotime($stats['ts'])) : null;
    $stale = ($age_s !== null && $age_s > 300); // stale si > 5 min
    return [
        'ok'       => !$stale,
        'level'    => $stats['current_level'] ?? null,
        'charging' => $stats['charging'] ?? null,
        'voltage'  => $stats['voltage_v'] ?? null,
        'updated'  => $stats['ts'] ?? null,
        'age_s'    => $age_s,
        'stale'    => $stale,
    ];
}

function check_disk(): array {
    $path = PROJECT_ROOT . '/podcasts';
    if (!is_dir($path)) $path = PROJECT_ROOT;
    $total = disk_total_space($path);
    $free  = disk_free_space($path);
    if ($total === false || $free === false) return ['ok' => false, 'error' => 'disk_info_unavailable'];
    $used_pct = round(($total - $free) / $total * 100, 1);
    $ok = ($used_pct < 90);
    return [
        'ok'       => $ok,
        'used_pct' => $used_pct,
        'free_gb'  => round($free / 1e9, 2),
        'total_gb' => round($total / 1e9, 2),
    ];
}

function check_ingest(): array {
    $log  = '/tmp/hechicero_ingest.log';
    $pid  = '/tmp/hechicero_ingest.pid';
    $running = file_exists($pid) && posix_kill((int)file_get_contents($pid), 0);
    $last_line = '';
    if (file_exists($log)) {
        $lines = file($log, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        $last_line = $lines ? end($lines) : '';
    }
    return [
        'ok'        => !$running, // "ok" = pas en cours (état normal)
        'running'   => $running,
        'last_log'  => $last_line ?: null,
    ];
}

function get_uptime(): ?string {
    $raw = @file_get_contents('/proc/uptime');
    if (!$raw) return null;
    $secs = (int)explode(' ', $raw)[0];
    $d = intdiv($secs, 86400);
    $h = intdiv($secs % 86400, 3600);
    $m = intdiv($secs % 3600, 60);
    return ($d > 0 ? "{$d}j " : '') . "{$h}h{$m}m";
}

// --- Assemblage ---

$mpd     = check_mpd();
$battery = check_battery();
$disk    = check_disk();
$ingest  = check_ingest();

$all_ok = $mpd['ok'] && $battery['ok'] && $disk['ok'];

$response = [
    'status'    => $all_ok ? 'ok' : 'degraded',
    'timestamp' => date('c'),
    'uptime'    => get_uptime(),
    'components' => [
        'mpd'     => $mpd,
        'battery' => $battery,
        'disk'    => $disk,
        'ingest'  => $ingest,
    ],
];

http_response_code($all_ok ? 200 : 503);
echo json_encode($response, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) . "\n";
