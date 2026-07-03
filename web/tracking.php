<?php
define('DB_PATH', '/home/thomas/hechicero/data/tracking.db');

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

function get_db(): PDO {
    $db = new PDO('sqlite:' . DB_PATH);
    $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $db->exec('PRAGMA journal_mode=WAL');
    $db->exec("CREATE TABLE IF NOT EXISTS play_events (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        ts_start     INTEGER NOT NULL,
        ts_end       INTEGER DEFAULT NULL,
        podcast_id   TEXT NOT NULL,
        episode_id   TEXT DEFAULT NULL,
        langue       TEXT NOT NULL DEFAULT 'fr',
        is_radio     INTEGER NOT NULL DEFAULT 0,
        station_name TEXT DEFAULT NULL,
        duration_s   REAL DEFAULT 0,
        listened_s   REAL NOT NULL DEFAULT 0,
        completed    INTEGER NOT NULL DEFAULT 0,
        volume_pct   INTEGER DEFAULT NULL
    )");
    // Migrations : ajout de colonnes sur base existante
    try { $db->exec("ALTER TABLE play_events ADD COLUMN volume_pct  INTEGER DEFAULT NULL"); } catch (Exception $e) {}
    try { $db->exec("ALTER TABLE play_events ADD COLUMN output_mode TEXT    DEFAULT NULL"); } catch (Exception $e) {}
    $db->exec('CREATE INDEX IF NOT EXISTS idx_ts   ON play_events(ts_start)');
    $db->exec('CREATE INDEX IF NOT EXISTS idx_lang ON play_events(langue)');
    $db->exec('CREATE INDEX IF NOT EXISTS idx_pod  ON play_events(podcast_id)');
    return $db;
}

$action = $_REQUEST['action'] ?? '';

try {
    $db = get_db();

    if ($action === 'start') {
        $podcast_id = trim($_REQUEST['podcast_id'] ?? '');
        $episode_id = trim($_REQUEST['episode_id'] ?? '') ?: null;
        $langue = trim($_REQUEST['langue'] ?? 'fr');
        $is_radio = (int)($_REQUEST['is_radio'] ?? 0);
        $station_name = trim($_REQUEST['station_name'] ?? '') ?: null;
        $duration_s = (float)($_REQUEST['duration_s'] ?? 0);

        if ($podcast_id === '') {
            echo json_encode(['ok' => false, 'error' => 'podcast_id manquant']);
            exit;
        }

        $stmt = $db->prepare(
            'INSERT INTO play_events (ts_start, podcast_id, episode_id, langue, is_radio, station_name, duration_s)
             VALUES (?, ?, ?, ?, ?, ?, ?)'
        );
        $stmt->execute([time(), $podcast_id, $episode_id, $langue, $is_radio, $station_name, $duration_s]);
        echo json_encode(['ok' => true, 'id' => (int)$db->lastInsertId()]);
    } elseif ($action === 'progress') {
        $id = (int)($_REQUEST['id'] ?? 0);
        $listened_s = (float)($_REQUEST['listened_s'] ?? 0);
        if ($id > 0) {
            $stmt = $db->prepare('UPDATE play_events SET listened_s = ? WHERE id = ?');
            $stmt->execute([$listened_s, $id]);
        }
        echo json_encode(['ok' => true]);
    } elseif ($action === 'end') {
        $id = (int)($_REQUEST['id'] ?? 0);
        $listened_s = (float)($_REQUEST['listened_s'] ?? 0);
        if ($id > 0) {
            $stmt = $db->prepare('SELECT duration_s FROM play_events WHERE id = ?');
            $stmt->execute([$id]);
            $row = $stmt->fetch(PDO::FETCH_ASSOC);
            $duration_s = $row ? (float)$row['duration_s'] : 0;
            $completed = ($duration_s > 0 && $listened_s >= 0.9 * $duration_s) ? 1 : 0;
            $stmt = $db->prepare(
                'UPDATE play_events SET ts_end = ?, listened_s = ?, completed = ? WHERE id = ?'
            );
            $stmt->execute([time(), $listened_s, $completed, $id]);
        }
        echo json_encode(['ok' => true]);
    } elseif ($action === 'stats') {
        $days = max(1, min(90, (int)($_REQUEST['days'] ?? 7)));
        $since = time() - $days * 86400;

        $stmt = $db->prepare(
            "SELECT date(ts_start, 'unixepoch', 'localtime') AS jour,
                    langue,
                    ROUND(SUM(listened_s) / 60.0, 1) AS minutes
             FROM play_events
             WHERE ts_start >= ? AND is_radio = 0
             GROUP BY jour, langue
             ORDER BY jour ASC"
        );
        $stmt->execute([$since]);
        $by_day = $stmt->fetchAll(PDO::FETCH_ASSOC);

        $stmt = $db->prepare(
            "SELECT podcast_id,
                    langue,
                    COUNT(*) AS nb_ecoutes,
                    ROUND(SUM(listened_s) / 60.0, 1) AS minutes_totales,
                    ROUND(AVG(CASE WHEN duration_s > 0
                        THEN MIN(listened_s * 100.0 / duration_s, 100.0) ELSE NULL END), 0) AS pct_completion
             FROM play_events
             WHERE ts_start >= ? AND is_radio = 0
             GROUP BY podcast_id
             ORDER BY minutes_totales DESC"
        );
        $stmt->execute([$since]);
        $top_pods = $stmt->fetchAll(PDO::FETCH_ASSOC);

        $stmt = $db->prepare(
            "SELECT podcast_id,
                    episode_id,
                    langue,
                    listened_s,
                    duration_s,
                    completed,
                    datetime(ts_start, 'unixepoch', 'localtime') AS started_at
             FROM play_events
             WHERE ts_start >= ? AND is_radio = 0
             ORDER BY ts_start DESC
             LIMIT 20"
        );
        $stmt->execute([$since]);
        $recent = $stmt->fetchAll(PDO::FETCH_ASSOC);

        $stmt = $db->prepare(
            "SELECT ROUND(SUM(listened_s) / 3600.0, 1) AS total_heures,
                    COUNT(*) AS total_episodes,
                    SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) AS episodes_termines,
                    ROUND(SUM(CASE WHEN langue = 'es' THEN listened_s ELSE 0 END)
                        / NULLIF(SUM(listened_s), 0) * 100, 0) AS pct_es
             FROM play_events
             WHERE ts_start >= ? AND is_radio = 0"
        );
        $stmt->execute([$since]);
        $summary = $stmt->fetch(PDO::FETCH_ASSOC);

        $stmt = $db->prepare(
            "SELECT SUM(CASE WHEN duration_s > 0 AND listened_s < duration_s * 0.25 THEN 1 ELSE 0 END) AS q0,
                    SUM(CASE WHEN duration_s > 0 AND listened_s >= duration_s * 0.25
                        AND listened_s < duration_s * 0.5 THEN 1 ELSE 0 END) AS q1,
                    SUM(CASE WHEN duration_s > 0 AND listened_s >= duration_s * 0.5
                        AND listened_s < duration_s * 0.75 THEN 1 ELSE 0 END) AS q2,
                    SUM(CASE WHEN duration_s > 0 AND listened_s >= duration_s * 0.75
                        AND completed = 0 THEN 1 ELSE 0 END) AS q3,
                    SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) AS q4
             FROM play_events
             WHERE is_radio = 0 AND duration_s > 0 AND ts_start >= ?"
        );
        $stmt->execute([$since]);
        $funnel = $stmt->fetch(PDO::FETCH_ASSOC) ?: ['q0' => 0, 'q1' => 0, 'q2' => 0, 'q3' => 0, 'q4' => 0];

        $stmt = $db->prepare(
            "SELECT podcast_id,
                    episode_id,
                    langue,
                    COUNT(*) AS replays,
                    ROUND(AVG(listened_s) / 60.0, 1) AS avg_minutes
             FROM play_events
             WHERE is_radio = 0 AND ts_start >= ?
             GROUP BY podcast_id, episode_id
             ORDER BY replays DESC
             LIMIT 10"
        );
        $stmt->execute([$since]);
        $top_episodes = $stmt->fetchAll(PDO::FETCH_ASSOC);

        $stmt = $db->prepare(
            "SELECT CAST(strftime('%w', datetime(ts_start, 'unixepoch', 'localtime')) AS INTEGER) AS dow,
                    CAST(strftime('%H', datetime(ts_start, 'unixepoch', 'localtime')) AS INTEGER) AS hour,
                    ROUND(SUM(listened_s) / 60.0, 1) AS minutes
             FROM play_events
             WHERE is_radio = 0 AND ts_start >= ?
             GROUP BY dow, hour
             ORDER BY dow, hour"
        );
        $stmt->execute([$since]);
        $heatmap = $stmt->fetchAll(PDO::FETCH_ASSOC);

        $stmt = $db->query(
            "SELECT DISTINCT date(ts_start, 'unixepoch', 'localtime') AS jour
             FROM play_events
             WHERE is_radio = 0
             ORDER BY jour DESC"
        );
        $streak_rows = $stmt->fetchAll(PDO::FETCH_ASSOC);

        $streak = 0;
        $prev = date('Y-m-d');
        foreach ($streak_rows as $r) {
            if (($r['jour'] ?? '') === $prev) {
                $streak++;
                $prev = date('Y-m-d', strtotime($prev . ' -1 day'));
            } else {
                break;
            }
        }

        // Moyenne par jour de la semaine (0=Dim … 6=Sam)
        $stmt = $db->prepare(
            "SELECT
                CAST(strftime('%w', datetime(ts_start,'unixepoch','localtime')) AS INTEGER) AS dow,
                ROUND(SUM(listened_s)/60.0, 1) AS total_minutes,
                COUNT(DISTINCT date(ts_start,'unixepoch','localtime')) AS n_days,
                ROUND(SUM(listened_s)/60.0 /
                    NULLIF(COUNT(DISTINCT date(ts_start,'unixepoch','localtime')),0), 1) AS avg_minutes
             FROM play_events
             WHERE is_radio = 0 AND ts_start >= ?
             GROUP BY dow ORDER BY dow"
        );
        $stmt->execute([$since]);
        $by_dow = $stmt->fetchAll(PDO::FETCH_ASSOC);

        // Radio : par jour
        $stmt = $db->prepare(
            "SELECT date(ts_start, 'unixepoch', 'localtime') AS jour,
                    langue,
                    ROUND(SUM(listened_s) / 60.0, 1) AS minutes
             FROM play_events
             WHERE ts_start >= ? AND is_radio = 1
             GROUP BY jour, langue
             ORDER BY jour ASC"
        );
        $stmt->execute([$since]);
        $radio_by_day = $stmt->fetchAll(PDO::FETCH_ASSOC);

        // Radio : résumé
        $stmt = $db->prepare(
            "SELECT ROUND(SUM(listened_s) / 3600.0, 1) AS total_heures,
                    COUNT(*) AS total_sessions,
                    ROUND(SUM(CASE WHEN langue = 'es' THEN listened_s ELSE 0 END)
                        / NULLIF(SUM(listened_s), 0) * 100, 0) AS pct_es
             FROM play_events
             WHERE ts_start >= ? AND is_radio = 1"
        );
        $stmt->execute([$since]);
        $radio_summary = $stmt->fetch(PDO::FETCH_ASSOC)
            ?: ['total_heures' => 0, 'total_sessions' => 0, 'pct_es' => 0];

        // Radio : top stations
        $stmt = $db->prepare(
            "SELECT COALESCE(station_name, podcast_id) AS station,
                    langue,
                    COUNT(*) AS nb_sessions,
                    ROUND(SUM(listened_s) / 60.0, 1) AS minutes
             FROM play_events
             WHERE ts_start >= ? AND is_radio = 1
             GROUP BY COALESCE(station_name, podcast_id)
             ORDER BY minutes DESC
             LIMIT 10"
        );
        $stmt->execute([$since]);
        $radio_top_stations = $stmt->fetchAll(PDO::FETCH_ASSOC);

        echo json_encode([
            'ok'                 => true,
            'by_day'             => $by_day,
            'by_dow'             => $by_dow,
            'top_pods'           => $top_pods,
            'recent'             => $recent,
            'summary'            => $summary,
            'funnel'             => $funnel,
            'top_episodes'       => $top_episodes,
            'heatmap'            => $heatmap,
            'streak'             => $streak,
            'radio_by_day'       => $radio_by_day,
            'radio_summary'      => $radio_summary,
            'radio_top_stations' => $radio_top_stations,
        ]);
    } elseif ($action === 'headphone_today') {
        $stmt = $db->prepare(
            "SELECT COALESCE(SUM(listened_s), 0) AS casque_s
             FROM play_events
             WHERE output_mode = 'casque'
               AND date(ts_start, 'unixepoch', 'localtime') = date('now', 'localtime')"
        );
        $stmt->execute();
        $row      = $stmt->fetch(PDO::FETCH_ASSOC);
        $casque_s = (float)($row['casque_s'] ?? 0);
        $max_s    = 7200.0;
        $pct      = min(100, round($casque_s / $max_s * 100, 1));
        echo json_encode([
            'ok'         => true,
            'casque_s'   => round($casque_s),
            'casque_min' => round($casque_s / 60, 1),
            'pct'        => $pct,
            'level'      => $pct >= 90 ? 'danger' : ($pct >= 75 ? 'alerte' : ($pct >= 50 ? 'attention' : 'ok')),
        ]);
    } elseif ($action === 'headphone_history') {
        $n_days = 14;
        $max_s  = 7200.0;
        $today  = date('Y-m-d');
        $since  = mktime(0, 0, 0, (int)date('m'), (int)date('d') - $n_days + 1, (int)date('Y'));
        $stmt = $db->prepare(
            "SELECT date(ts_start, 'unixepoch', 'localtime') AS jour,
                    COALESCE(SUM(listened_s), 0) AS casque_s
             FROM play_events
             WHERE output_mode = 'casque' AND ts_start >= ?
             GROUP BY jour ORDER BY jour ASC"
        );
        $stmt->execute([$since]);
        $by_day = [];
        foreach ($stmt->fetchAll(PDO::FETCH_ASSOC) as $r) {
            $by_day[$r['jour']] = (float)$r['casque_s'];
        }
        $days = [];
        for ($i = $n_days - 1; $i >= 0; $i--) {
            $jour = date('Y-m-d', mktime(0, 0, 0, (int)date('m'), (int)date('d') - $i, (int)date('Y')));
            $cs   = $by_day[$jour] ?? 0.0;
            $pct  = min(100, round($cs / $max_s * 100, 1));
            $days[] = ['jour' => $jour, 'casque_s' => round($cs), 'pct' => $pct, 'is_today' => ($jour === $today)];
        }
        $today_s   = $by_day[$today] ?? 0.0;
        $today_pct = min(100, round($today_s / $max_s * 100, 1));
        echo json_encode([
            'ok'    => true,
            'days'  => $days,
            'today' => [
                'casque_s'   => round($today_s),
                'casque_min' => round($today_s / 60, 1),
                'pct'        => $today_pct,
                'level'      => $today_pct >= 90 ? 'danger' : ($today_pct >= 75 ? 'alerte' : ($today_pct >= 50 ? 'attention' : 'ok')),
            ],
        ]);
    } else {
        echo json_encode(['ok' => false, 'error' => 'action inconnue: ' . htmlspecialchars($action)]);
    }
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => $e->getMessage()]);
}
