<?php
define('PROJECT_ROOT', is_dir('/home/thomas/hechicero') ? '/home/thomas/hechicero' : dirname(__DIR__, 2));
define('BATTERY_HISTORY_JSON', PROJECT_ROOT . '/data/battery_history.json');
define('BATTERY_STATS_JSON', PROJECT_ROOT . '/data/battery_stats.json');

function read_json(string $path): array {
    if (!file_exists($path)) return [];
    $data = json_decode(file_get_contents($path), true);
    return is_array($data) ? $data : [];
}

function fmt_minutes($minutes): string {
    if (!is_numeric($minutes) || $minutes <= 0) return '—';
    $minutes = (int)round($minutes);
    if ($minutes < 60) return $minutes . ' min';
    return floor($minutes / 60) . 'h' . str_pad((string)($minutes % 60), 2, '0', STR_PAD_LEFT);
}

function fmt_since(?string $iso): string {
    if (!$iso) return '—';
    try {
        $start = new DateTime($iso);
        $now = new DateTime();
        $seconds = max(0, $now->getTimestamp() - $start->getTimestamp());
        if ($seconds < 3600) return floor($seconds / 60) . ' min';
        return floor($seconds / 3600) . 'h' . str_pad((string)floor(($seconds % 3600) / 60), 2, '0', STR_PAD_LEFT);
    } catch (Throwable $e) {
        return '—';
    }
}

function cycle_points(array $cycle, bool $charging): array {
    $points = [];
    foreach ($cycle['datapoints'] ?? [] as $point) {
        if (($point['charging'] ?? false) !== $charging) continue;
        $points[] = [
            't' => $point['t'] ?? '',
            'level' => $point['level'] ?? null,
        ];
    }
    return $points;
}

$history = read_json(BATTERY_HISTORY_JSON);
$stats = read_json(BATTERY_STATS_JSON);
$cycles = $history['cycles'] ?? [];
$currentCycle = $cycles ? $cycles[count($cycles) - 1] : [];
$pagedCycles = array_reverse($cycles);
$page = max(1, (int)($_GET['page'] ?? 1));
$perPage = 10;
$pageCount = max(1, (int)ceil(max(1, count($pagedCycles)) / $perPage));
$page = min($page, $pageCount);
$rows = array_slice($pagedCycles, ($page - 1) * $perPage, $perPage);

$dischargeCurves = [];
foreach (array_slice(array_reverse($cycles), 0, 5) as $index => $cycle) {
    $points = cycle_points($cycle, false);
    if (!$points) continue;
    $dischargeCurves[] = [
        'label' => $cycle['discharge_start'] ?? ('Cycle ' . ($index + 1)),
        'points' => $points,
    ];
}

$chargeCurves = [];
foreach (array_slice(array_reverse($cycles), 0, 5) as $index => $cycle) {
    $points = cycle_points($cycle, true);
    if (!$points) continue;
    $chargeCurves[] = [
        'label' => $cycle['charge_start'] ?? ('Recharge ' . ($index + 1)),
        'points' => $points,
    ];
}

$currentCyclePoints = cycle_points($currentCycle, ($stats['status'] ?? '') === 'charging');
$consumption = $stats['consumption_by_mode'] ?? [];
?><!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Hechicero · Batterie</title>
  <style>
    :root {
      --bg: #09111b;
      --surface: rgba(13, 24, 38, 0.94);
      --surface-2: rgba(19, 35, 54, 0.9);
      --border: #204264;
      --accent: #f0be4f;
      --text: #e8f0f6;
      --muted: #86a5c0;
      --ok: #3dba6a;
      --warn: #f5a623;
      --danger: #e24b4a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
      background:
        radial-gradient(circle at top left, rgba(240, 190, 79, 0.12), transparent 28%),
        linear-gradient(180deg, #09111b 0%, #0d1826 100%);
    }
    a { color: inherit; text-decoration: none; }
    .page { max-width: 1400px; margin: 0 auto; padding: 24px; }
    .header { display: flex; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 18px; flex-wrap: wrap; }
    .nav { display: flex; gap: 10px; flex-wrap: wrap; }
    .btn {
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--surface-2);
      padding: 10px 14px;
    }
    h1 { margin: 0; font-size: clamp(28px, 4vw, 42px); }
    h2 { margin: 0 0 14px; font-size: 22px; }
    .sub { color: var(--muted); margin-top: 6px; }
    .grid { display: grid; gap: 18px; }
    .cards { grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }
    .cols { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .panel {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 18px 60px rgba(0, 0, 0, 0.22);
    }
    .label { color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; font-size: 12px; }
    .value { margin-top: 8px; font-size: clamp(22px, 3vw, 34px); font-weight: 700; }
    .status-pill {
      display: inline-flex; align-items: center; gap: 8px; border-radius: 999px; padding: 6px 12px;
      background: rgba(32, 66, 100, 0.42); color: var(--text); font-size: 13px;
    }
    .note { color: var(--muted); font-size: 14px; margin-top: 10px; }
    .chart-wrap { position: relative; min-height: 280px; }
    .empty { color: var(--muted); padding: 24px 0; }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; padding: 10px; border-bottom: 1px solid rgba(32, 66, 100, 0.6); }
    th { color: var(--muted); font-size: 12px; text-transform: uppercase; }
    .pagination { display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px; }
    .metric-list { display: grid; gap: 10px; }
    .metric-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    .metric-bar { flex: 1; height: 12px; border-radius: 999px; background: #08111b; border: 1px solid rgba(32, 66, 100, 0.5); overflow: hidden; }
    .metric-fill { height: 100%; background: linear-gradient(90deg, rgba(240, 190, 79, 0.38), rgba(240, 190, 79, 1)); }
    .confidence.low { color: var(--warn); }
    .confidence.medium { color: var(--accent); }
    .confidence.high { color: var(--ok); }
    @media (max-width: 980px) {
      .cols { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="page">
    <div class="header">
      <div>
        <h1>Dashboard alimentation</h1>
        <div class="sub">Cycles batterie, recharge et estimations d’autonomie</div>
      </div>
      <div class="nav">
        <a class="btn" href="/">⚙ Admin</a>
        <a class="btn" href="/dashboard.php">📊 Dashboard écoute</a>
        <a class="btn" href="/lecteur/" target="_blank">📻 Lecteur</a>
      </div>
    </div>

    <div class="grid cards" style="margin-bottom:18px;">
      <div class="panel">
        <div class="label">Statut</div>
        <div class="value"><span class="status-pill"><?php echo htmlspecialchars($stats['status'] ?? '—'); ?></span></div>
        <div class="note">Depuis <?php echo htmlspecialchars(fmt_since($stats['current_state_since'] ?? null)); ?></div>
      </div>
      <div class="panel">
        <div class="label">Niveau</div>
        <div class="value"><?php echo isset($stats['current_level']) ? (int)$stats['current_level'] . '%' : '—'; ?></div>
        <div class="note">Mode MPD: <?php echo htmlspecialchars($stats['current_mpd_mode'] ?? '—'); ?></div>
      </div>
      <div class="panel">
        <div class="label">Autonomie estimée</div>
        <div class="value"><?php echo htmlspecialchars(fmt_minutes($stats['estimated_autonomy_minutes'] ?? null)); ?></div>
        <div class="note">Recharge estimée: <?php echo htmlspecialchars(fmt_minutes($stats['estimated_charge_time_minutes'] ?? null)); ?></div>
      </div>
      <div class="panel">
        <div class="label">Fiabilité</div>
        <div class="value confidence <?php echo htmlspecialchars($stats['model_confidence'] ?? 'low'); ?>"><?php echo htmlspecialchars($stats['model_confidence'] ?? 'low'); ?></div>
        <div class="note"><?php echo (int)($stats['cycles_recorded'] ?? 0); ?> cycles complets</div>
      </div>
    </div>

    <div class="grid cols" style="margin-bottom:18px;">
      <section class="panel">
        <h2>Cycle en cours</h2>
        <div class="chart-wrap">
          <?php if ($currentCyclePoints): ?>
            <canvas id="current-cycle-chart"></canvas>
          <?php else: ?>
            <div class="empty">Aucun point à afficher pour le cycle en cours.</div>
          <?php endif; ?>
        </div>
      </section>
      <section class="panel">
        <h2>Consommation par mode</h2>
        <div class="chart-wrap">
          <canvas id="mode-chart"></canvas>
        </div>
      </section>
    </div>

    <div class="grid cols" style="margin-bottom:18px;">
      <section class="panel">
        <h2>Historique des cycles</h2>
        <?php if ($rows): ?>
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Durée</th>
                <th>Niveaux</th>
                <th>Mode</th>
                <th>Autonomie réelle</th>
              </tr>
            </thead>
            <tbody>
            <?php foreach ($rows as $cycle): ?>
              <tr>
                <td><?php echo htmlspecialchars(substr((string)($cycle['discharge_start'] ?? $cycle['charge_start'] ?? '—'), 0, 16)); ?></td>
                <td><?php echo htmlspecialchars(fmt_minutes($cycle['duration_minutes'] ?? null)); ?></td>
                <td><?php echo htmlspecialchars(($cycle['level_start'] ?? '—') . ' → ' . ($cycle['level_end'] ?? '—')); ?></td>
                <td><?php echo htmlspecialchars($cycle['dominant_mode'] ?? '—'); ?></td>
                <td><?php echo htmlspecialchars(fmt_minutes($cycle['duration_minutes'] ?? null)); ?></td>
              </tr>
            <?php endforeach; ?>
            </tbody>
          </table>
          <div class="pagination">
            <?php if ($page > 1): ?><a class="btn" href="?page=<?php echo $page - 1; ?>">Précédent</a><?php endif; ?>
            <span class="btn">Page <?php echo $page; ?> / <?php echo $pageCount; ?></span>
            <?php if ($page < $pageCount): ?><a class="btn" href="?page=<?php echo $page + 1; ?>">Suivant</a><?php endif; ?>
          </div>
        <?php else: ?>
          <div class="empty">Aucun cycle enregistré.</div>
        <?php endif; ?>
      </section>
      <section class="panel">
        <h2>Courbes de décharge</h2>
        <div class="chart-wrap">
          <?php if ($dischargeCurves): ?>
            <canvas id="discharge-chart"></canvas>
          <?php else: ?>
            <div class="empty">Les courbes apparaîtront après les premiers cycles de décharge.</div>
          <?php endif; ?>
        </div>
      </section>
    </div>

    <div class="grid cols">
      <section class="panel">
        <h2>Courbes de recharge</h2>
        <div class="chart-wrap">
          <?php if ($chargeCurves): ?>
            <canvas id="charge-chart"></canvas>
          <?php else: ?>
            <div class="empty">Les courbes apparaîtront après les premiers cycles de recharge.</div>
          <?php endif; ?>
        </div>
      </section>
      <section class="panel">
        <h2>Estimations</h2>
        <div class="metric-list">
          <div class="metric-row"><span>Autonomie estimée</span><strong><?php echo htmlspecialchars(fmt_minutes($stats['estimated_autonomy_minutes'] ?? null)); ?></strong></div>
          <div class="metric-row"><span>Temps de recharge estimé</span><strong><?php echo htmlspecialchars(fmt_minutes($stats['estimated_charge_time_minutes'] ?? null)); ?></strong></div>
          <div class="metric-row"><span>Cycles enregistrés</span><strong><?php echo (int)($stats['cycles_recorded'] ?? 0); ?></strong></div>
          <?php foreach (['webradio' => 'Webradio', 'podcast' => 'Podcast', 'idle' => 'Veille'] as $mode => $label):
              $value = $consumption[$mode] ?? null;
              $width = is_numeric($value) ? min(100, (float)$value * 8) : 0;
          ?>
            <div class="metric-row">
              <span><?php echo htmlspecialchars($label); ?></span>
              <div class="metric-bar"><div class="metric-fill" style="width:<?php echo $width; ?>%"></div></div>
              <strong><?php echo is_numeric($value) ? number_format((float)$value, 1, ',', ' ') . ' %/h' : '—'; ?></strong>
            </div>
          <?php endforeach; ?>
        </div>
        <?php if (($stats['model_confidence'] ?? 'low') === 'low'): ?>
          <div class="note">Estimations en cours d’apprentissage (<?php echo (int)($stats['cycles_recorded'] ?? 0); ?> cycles enregistrés).</div>
        <?php endif; ?>
      </section>
    </div>
  </div>

  <script src="/js/chart.min.js"></script>
  <script>
    const currentCyclePoints = <?php echo json_encode($currentCyclePoints, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); ?>;
    const dischargeCurves = <?php echo json_encode($dischargeCurves, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); ?>;
    const chargeCurves = <?php echo json_encode($chargeCurves, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); ?>;
    const consumption = <?php echo json_encode($consumption, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); ?>;

    function chartDatasets(curves, palette) {
      return curves.map((curve, index) => ({
        label: curve.label,
        data: curve.points.map((point, pointIndex) => ({ x: pointIndex, y: point.level })),
        borderColor: palette[index % palette.length],
        backgroundColor: palette[index % palette.length],
        borderWidth: 2,
        tension: 0.22,
        pointRadius: 2,
      }));
    }

    function createLineChart(id, curves, palette) {
      if (!window.Chart || !document.getElementById(id) || !curves.length) return;
      new Chart(document.getElementById(id), {
        type: 'line',
        data: { datasets: chartDatasets(curves, palette) },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          parsing: false,
          scales: {
            x: { title: { display: true, text: 'Points de mesure' }, ticks: { color: '#86a5c0' }, grid: { color: 'rgba(32,66,100,0.25)' } },
            y: { title: { display: true, text: 'Niveau (%)' }, min: 0, max: 100, ticks: { color: '#86a5c0' }, grid: { color: 'rgba(32,66,100,0.25)' } },
          },
          plugins: { legend: { labels: { color: '#e8f0f6' } } }
        }
      });
    }

    if (window.Chart && document.getElementById('mode-chart')) {
      new Chart(document.getElementById('mode-chart'), {
        type: 'bar',
        data: {
          labels: ['Webradio', 'Podcast', 'Veille'],
          datasets: [{
            label: '% / heure',
            data: [consumption.webradio || 0, consumption.podcast || 0, consumption.idle || 0],
            backgroundColor: ['#f0be4f', '#4a9eff', '#6b89a8'],
            borderRadius: 10,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { ticks: { color: '#86a5c0' }, grid: { display: false } },
            y: { ticks: { color: '#86a5c0' }, grid: { color: 'rgba(32,66,100,0.25)' } },
          },
          plugins: { legend: { labels: { color: '#e8f0f6' } } }
        }
      });
    }

    createLineChart('current-cycle-chart', currentCyclePoints.length ? [{ label: 'Cycle en cours', points: currentCyclePoints }] : [], ['#f0be4f']);
    createLineChart('discharge-chart', dischargeCurves, ['#4a9eff', '#f0be4f', '#3dba6a', '#d97706', '#8b5cf6']);
    createLineChart('charge-chart', chargeCurves, ['#3dba6a', '#86efac', '#f0be4f', '#38bdf8', '#fb7185']);
  </script>
</body>
</html>