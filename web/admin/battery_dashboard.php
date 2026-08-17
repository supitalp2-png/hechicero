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
            // TICKET-133 : la TENSION est la mesure primaire — le niveau n'en
            // est qu'une lecture de table (percent_from_voltage). Les points
            // enregistrés avant le 2026-08-17 ne l'ont pas : null accepté.
            'voltage_v' => $point['voltage_v'] ?? null,
            'current_ma' => $point['current_ma'] ?? null,
        ];
    }
    return $points;
}

$history = read_json(BATTERY_HISTORY_JSON);
$stats = read_json(BATTERY_STATS_JSON);
$cycles = $history['cycles'] ?? [];

// Filtre les cycles valides : décharge réelle ≥ 3% et durée ≥ 5 min
function is_valid_cycle(array $c): bool {
    $consumed = ($c['level_start'] ?? 0) - ($c['level_end'] ?? 0);
    $duration = $c['duration_minutes'] ?? 0;
    return !($c['invalid'] ?? false) && $consumed >= 3 && $duration >= 5 && isset($c['discharge_end']);
}
$validCycles = array_values(array_filter($cycles, 'is_valid_cycle'));
$totalCycles = count($cycles);
$validCount  = count($validCycles);

// Pagination sur cycles valides
$pagedCycles = array_reverse($validCycles);
$page = max(1, (int)($_GET['page'] ?? 1));
$perPage = 10;
$pageCount = max(1, (int)ceil(max(1, $validCount) / $perPage));
$page = min($page, $pageCount);
$rows = array_slice($pagedCycles, ($page - 1) * $perPage, $perPage);

// Courbes de décharge / recharge — cycles valides uniquement
$dischargeCurves = [];
foreach (array_slice(array_reverse($validCycles), 0, 5) as $index => $cycle) {
    $points = cycle_points($cycle, false);
    if (!$points) continue;
    $dischargeCurves[] = [
        'label' => $cycle['discharge_start'] ?? ('Cycle ' . ($index + 1)),
        'points' => $points,
    ];
}

$chargeCurves = [];
foreach (array_slice(array_reverse($validCycles), 0, 5) as $index => $cycle) {
    $points = cycle_points($cycle, true);
    if (!$points) continue;
    $chargeCurves[] = [
        'label' => $cycle['charge_start'] ?? ('Recharge ' . ($index + 1)),
        'points' => $points,
    ];
}

// Activité 24h : tous les datapoints des dernières 24h (toutes phases)
$cutoff24h = time() - 86400;
$recentPoints = [];
foreach (array_reverse($cycles) as $cycle) {
    foreach ($cycle['datapoints'] ?? [] as $pt) {
        $ts = strtotime($pt['t'] ?? '');
        if ($ts && $ts >= $cutoff24h) {
            $recentPoints[] = [
                't' => $pt['t'],
                'level' => $pt['level'] ?? null,
                'charging' => $pt['charging'] ?? false,
                'voltage_v' => $pt['voltage_v'] ?? null,
                'current_ma' => $pt['current_ma'] ?? null,
            ];
        }
    }
}
usort($recentPoints, fn($a, $b) => strcmp($a['t'], $b['t']));
$recentPoints = array_values($recentPoints);

// TICKET-133 — combien de points portent la tension ? Elle n'est enregistrée
// que depuis le 2026-08-17 ; sans ce compte, le graphe « tension et courant »
// paraîtrait vide ou cassé sur un historique ancien, au lieu d'expliquer.
$pointsAvecTension = 0;
foreach ($recentPoints as $pt) {
    if ($pt['voltage_v'] !== null) $pointsAvecTension++;
}

// Seuil d'arrêt d'urgence, pour le tracer sur les courbes de décharge : sans
// repère visuel, impossible de juger la marge restante d'un coup d'œil.
$configBatt = read_json(PROJECT_ROOT . '/data/config.json');
$seuilCoupure = (int)($configBatt['critical_level_percent']
    ?? $configBatt['shutdown_threshold_percent'] ?? 15);

$consumption = $stats['consumption_by_mode'] ?? [];
$currentPage = basename($_SERVER['PHP_SELF'] ?? 'battery_dashboard.php');
?><!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hechicero · Batterie</title>
  <link rel="stylesheet" href="/css/hechicero-admin.css">
  <style>
    .status-pill {
      display: inline-flex; align-items: center; gap: 8px; border-radius: 999px; padding: 6px 12px;
      background: rgba(32, 66, 100, 0.42); color: var(--text); font-size: 13px;
    }
    .ha-table td, .ha-table th { padding: 10px; border-bottom: 1px solid rgba(32, 66, 100, 0.6); }
    .pagination { display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px; }
    .metric-list { display: grid; gap: 10px; }
    .metric-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    .metric-bar { flex: 1; height: 12px; border-radius: 999px; background: #08111b; border: 1px solid rgba(32, 66, 100, 0.5); overflow: hidden; }
    .metric-fill { height: 100%; background: linear-gradient(90deg, rgba(240, 190, 79, 0.38), rgba(240, 190, 79, 1)); }
    .confidence.low { color: var(--warn); }
    .confidence.medium { color: var(--accent); }
    .confidence.high { color: var(--ok); }
  </style>
</head>
<body>
  <div class="ha-page">
    <div class="ha-header">
      <div>
        <h1>Dashboard alimentation</h1>
        <div class="ha-subtitle">Cycles batterie, recharge et estimations d’autonomie</div>
      </div>
      <nav class="ha-nav">
        <a class="ha-btn" href="/"><span class="ha-btn-icon">‹</span> Bureau</a>
        <a class="ha-btn" href="/lecteur/" target="_blank"><span class="ha-btn-icon">📻</span> Lecteur</a>
      </nav>
    </div>

    <div class="ha-grid ha-cols-auto" style="margin-bottom:18px;">
      <div class="ha-panel">
        <div class="ha-stat-label">Statut</div>
        <div class="ha-stat-value"><span class="status-pill"><?php echo htmlspecialchars($stats['status'] ?? '—'); ?></span></div>
        <div class="ha-stat-note">Depuis <?php echo htmlspecialchars(fmt_since($stats['current_state_since'] ?? null)); ?></div>
      </div>
      <div class="ha-panel">
        <div class="ha-stat-label">Niveau</div>
        <div class="ha-stat-value"><?php echo isset($stats['current_level']) ? (int)$stats['current_level'] . '%' : '—'; ?></div>
        <div class="ha-stat-note">
          <?php echo number_format((float)($stats['voltage_v'] ?? 0), 2, '.', '') . ' V'; ?>
          · <?php echo number_format(abs((float)($stats['current_ma'] ?? 0)), 0) . ' mA'; ?>
          · <?php echo number_format((float)($stats['power_w'] ?? 0), 1, '.', '') . ' W'; ?>
        </div>
      </div>
      <?php
        $autoLive  = $stats['estimated_autonomy_minutes_live']  ?? null;
        $autoRatio = $stats['estimated_autonomy_minutes']        ?? null;
        $chrgLive  = $stats['estimated_charge_time_minutes_live'] ?? null;
        $chrgRatio = $stats['estimated_charge_time_minutes']      ?? null;
        $autoVal   = $autoLive  ?? $autoRatio;
        $chrgVal   = $chrgLive  ?? $chrgRatio;
        $autoNote  = $autoLive  !== null ? '(courant réel)' : ($autoRatio !== null ? '(moyenne cycles)' : '');
        $chrgNote  = $chrgLive  !== null ? '(courant réel)' : ($chrgRatio !== null ? '(moyenne cycles)' : '');
      ?>
      <div class="ha-panel">
        <div class="ha-stat-label">Autonomie estimée</div>
        <div class="ha-stat-value"><?php echo htmlspecialchars(fmt_minutes($autoVal)); ?></div>
        <div class="ha-stat-note"><?php echo $autoNote; ?> · Recharge: <?php echo htmlspecialchars(fmt_minutes($chrgVal)); ?> <?php echo $chrgNote; ?></div>
      </div>
      <div class="ha-panel">
        <div class="ha-stat-label">Fiabilité modèle</div>
        <div class="ha-stat-value confidence <?php echo htmlspecialchars($stats['model_confidence'] ?? 'low'); ?>"><?php echo htmlspecialchars($stats['model_confidence'] ?? 'low'); ?></div>
        <div class="ha-stat-note"><?php echo $validCount; ?> cycles valides / <?php echo $totalCycles; ?> total</div>
      </div>
    </div>

    <div class="ha-grid ha-cols-2" style="margin-bottom:18px;">
      <section class="ha-panel">
        <h2>Activité des dernières 24h</h2>
        <div class="ha-chart">
          <?php if ($recentPoints): ?>
            <canvas id="current-cycle-chart"></canvas>
          <?php else: ?>
            <div class="ha-empty">Aucun relevé dans les dernières 24h.</div>
          <?php endif; ?>
        </div>
      </section>
      <section class="ha-panel">
        <h2>Consommation par mode</h2>
        <div class="ha-chart">
          <canvas id="mode-chart"></canvas>
        </div>
        <?php
          // TICKET-133 : une batterie ne peut pas perdre plus de 100 %/h sans
          // se vider en moins d'une heure. Une valeur au-dessus vient d'un
          // cycle mal mesuré (le 2026-08-17 : « podcast 102 %/h », calculé sur
          // une décharge dont la fin manquait). On le dit au lieu de l'afficher
          // comme un fait.
          $suspect = [];
          foreach ($consumption as $mode => $v) {
              if (is_numeric($v) && $v > 100) $suspect[] = $mode;
          }
        ?>
        <?php if ($suspect): ?>
          <div class="ha-stat-note" style="margin-top:10px;color:#e2a03f;">
            ⚠ Valeur impossible pour <?php echo htmlspecialchars(implode(', ', $suspect)); ?> :
            au-delà de 100 %/h la batterie se viderait en moins d'une heure.
            Signe d'un cycle incomplet dans l'historique — voir la colonne « Fiabilité ».
          </div>
        <?php endif; ?>
      </section>
    </div>

    <div class="ha-grid" style="margin-bottom:18px;">
      <section class="ha-panel">
        <h2>Tension et courant (24 h)</h2>
        <div class="ha-stat-note" style="margin-bottom:10px;color:var(--muted);">
          La <strong>tension</strong> est la seule grandeur réellement mesurée : le pourcentage
          n'en est qu'une lecture de table. Le <strong>courant</strong> est positif en charge,
          négatif en décharge — c'est son signe qui décide de l'état depuis le 2026-08-17.
        </div>
        <div class="ha-chart">
          <?php if ($pointsAvecTension >= 2): ?>
            <canvas id="volt-chart"></canvas>
          <?php else: ?>
            <div class="ha-empty">
              La tension n'est enregistrée que depuis le 2026-08-17 (TICKET-133).
              Le graphe apparaîtra dès les prochains relevés.
            </div>
          <?php endif; ?>
        </div>
      </section>
    </div>

    <div class="ha-grid ha-cols-2" style="margin-bottom:18px;">
      <section class="ha-panel">
        <h2>Historique des cycles valides</h2>
        <?php if ($totalCycles > $validCount): ?>
          <div class="ha-stat-note" style="margin-bottom:10px;color:var(--muted);">
            <?php echo $totalCycles - $validCount; ?> micro-cycles filtrés (phase CV / bruit mesure)
          </div>
        <?php endif; ?>
        <?php if ($rows): ?>
          <table class="ha-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Durée</th>
                <th>Niveaux</th>
                <th>Décharge</th>
                <th>Mode</th>
                <th>Fiabilité</th>
              </tr>
            </thead>
            <tbody>
            <?php foreach ($rows as $cycle): ?>
              <?php
                $consumed = ($cycle['level_start'] ?? 0) - ($cycle['level_end'] ?? 0);
                // TICKET-133 : un cycle dont le tracker s'est interrompu (arrêt
                // d'urgence) est enregistré incomplet. Le signaler ICI plutôt
                // que de laisser croire à une mesure propre — c'est exactement
                // ce qui m'a fait lire « décharge jusqu'à 28 % » alors que la
                // vraie descente allait à 15 %.
                $trou = $cycle['gap_minutes'] ?? null;
              ?>
              <tr>
                <td><?php echo htmlspecialchars(substr((string)($cycle['discharge_start'] ?? '—'), 0, 16)); ?></td>
                <td><?php echo htmlspecialchars(fmt_minutes($cycle['duration_minutes'] ?? null)); ?></td>
                <td><?php echo htmlspecialchars(($cycle['level_start'] ?? '—') . '% → ' . ($cycle['level_end'] ?? '—') . '%'); ?></td>
                <td><?php echo $consumed > 0 ? '-' . $consumed . '%' : '—'; ?></td>
                <td><?php echo htmlspecialchars($cycle['dominant_mode'] ?? '—'); ?></td>
                <td>
                  <?php if ($trou !== null): ?>
                    <span title="Le tracker ne tournait plus pendant <?php echo (int)$trou; ?> min — appareil probablement éteint (arrêt d'urgence). Le point bas et la durée sont sous-estimés."
                          style="color:#e2a03f;">⚠ trou <?php echo (int)$trou; ?> min</span>
                  <?php else: ?>
                    <span style="color:var(--muted);">complet</span>
                  <?php endif; ?>
                </td>
              </tr>
            <?php endforeach; ?>
            </tbody>
          </table>
          <div class="pagination">
            <?php if ($page > 1): ?><a class="ha-btn" href="?page=<?php echo $page - 1; ?>">Précédent</a><?php endif; ?>
            <span class="ha-btn">Page <?php echo $page; ?> / <?php echo $pageCount; ?></span>
            <?php if ($page < $pageCount): ?><a class="ha-btn" href="?page=<?php echo $page + 1; ?>">Suivant</a><?php endif; ?>
          </div>
        <?php else: ?>
          <div class="ha-empty">Aucun cycle valide — les cycles apparaîtront après une vraie décharge (≥ 3% sur ≥ 5 min).</div>
        <?php endif; ?>
      </section>
      <section class="ha-panel">
        <h2>Courbes de décharge</h2>
        <div class="ha-chart">
          <?php if ($dischargeCurves): ?>
            <canvas id="discharge-chart"></canvas>
          <?php else: ?>
            <div class="ha-empty">Les courbes apparaîtront après les premiers cycles de décharge.</div>
          <?php endif; ?>
        </div>
      </section>
    </div>

    <div class="ha-grid ha-cols-2">
      <section class="ha-panel">
        <h2>Courbes de recharge</h2>
        <div class="ha-chart">
          <?php if ($chargeCurves): ?>
            <canvas id="charge-chart"></canvas>
          <?php else: ?>
            <div class="ha-empty">Les courbes apparaîtront après les premiers cycles de recharge.</div>
          <?php endif; ?>
        </div>
      </section>
      <section class="ha-panel">
        <h2>Estimations</h2>
        <div class="metric-list">
          <div class="metric-row"><span>Autonomie estimée <?php echo $autoNote; ?></span><strong><?php echo htmlspecialchars(fmt_minutes($autoVal)); ?></strong></div>
          <div class="metric-row"><span>Temps de recharge <?php echo $chrgNote; ?></span><strong><?php echo htmlspecialchars(fmt_minutes($chrgVal)); ?></strong></div>
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
          <div class="ha-stat-note">Estimations en cours d’apprentissage (<?php echo (int)($stats['cycles_recorded'] ?? 0); ?> cycles enregistrés).</div>
        <?php endif; ?>
      </section>
    </div>
  </div>

  <script src="/js/chart.min.js"></script>
  <script>
    const recentPoints = <?php echo json_encode($recentPoints, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); ?>;
    const dischargeCurves = <?php echo json_encode($dischargeCurves, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); ?>;
    const chargeCurves = <?php echo json_encode($chargeCurves, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); ?>;
    const consumption = <?php echo json_encode($consumption, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); ?>;
    // Seuil d'arrêt d'urgence, tracé sur les courbes de décharge : sans repère
    // visuel, impossible de juger d'un coup d'œil la marge qui restait.
    const SEUIL_COUPURE = <?php echo (int)$seuilCoupure; ?>;

    const GAP_MS = 2 * 3600 * 1000; // coupure de courbe si écart > 2h

    // Axe absolu : x = ms epoch (utilisé pour le cycle en cours)
    function chartDatasets(curves, palette) {
      return curves.map((curve, index) => {
        const data = [];
        curve.points.forEach((point, i) => {
          const ms = new Date(point.t).getTime();
          if (i > 0) {
            const prevMs = new Date(curve.points[i - 1].t).getTime();
            if (ms - prevMs > GAP_MS) data.push({ x: prevMs + 1, y: null });
          }
          data.push({ x: ms, y: point.level });
        });
        return {
          label: curve.label,
          data,
          borderColor: palette[index % palette.length],
          backgroundColor: palette[index % palette.length],
          borderWidth: 2,
          tension: 0.22,
          pointRadius: 4,
          spanGaps: false,
        };
      });
    }

    // Axe relatif : x = minutes depuis le 1er point du cycle (pour superposer les cycles)
    function chartDatasetsRelative(curves, palette) {
      return curves.map((curve, index) => {
        if (!curve.points.length) return null;
        const t0 = new Date(curve.points[0].t).getTime();
        const data = [];
        curve.points.forEach((point, i) => {
          const ms = new Date(point.t).getTime();
          const xMin = (ms - t0) / 60000;
          if (i > 0) {
            const prevMs = new Date(curve.points[i - 1].t).getTime();
            if (ms - prevMs > GAP_MS) data.push({ x: (prevMs - t0) / 60000 + 0.01, y: null });
          }
          data.push({ x: xMin, y: point.level });
        });
        // Raccourcir le label : garder seulement la date+heure de départ
        const startLabel = curve.label.replace('T', ' ').substring(0, 16);
        return {
          label: startLabel,
          data,
          borderColor: palette[index % palette.length],
          backgroundColor: palette[index % palette.length],
          borderWidth: 2,
          tension: 0.22,
          pointRadius: 4,
          spanGaps: false,
        };
      }).filter(Boolean);
    }

    function fmtTime(ms) {
      const d = new Date(ms);
      return String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0');
    }

    function fmtMin(min) {
      if (min < 60) return Math.round(min) + ' min';
      return Math.floor(min / 60) + 'h' + String(Math.round(min % 60)).padStart(2, '0');
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
            x: {
              type: 'linear',
              title: { display: true, text: 'Heure', color: '#86a5c0' },
              ticks: { color: '#86a5c0', callback: v => fmtTime(v) },
              grid: { color: 'rgba(32,66,100,0.25)' }
            },
            y: { title: { display: true, text: 'Niveau (%)' }, min: 0, ticks: { color: '#86a5c0' }, grid: { color: 'rgba(32,66,100,0.25)' } },
          },
          plugins: { legend: { labels: { color: '#e8f0f6' } } }
        }
      });
    }

    function createRelativeChart(id, curves, palette, seuil) {
      if (!window.Chart || !document.getElementById(id) || !curves.length) return;
      const datasets = chartDatasetsRelative(curves, palette);

      // Ligne horizontale du seuil d'arrêt d'urgence. Tracée comme un jeu de
      // données à deux points plutôt qu'avec un greffon d'annotation : Chart.js
      // est servi en local et sans extension (cf. /js/chart.min.js), donc on
      // reste sur ce que la bibliothèque de base sait faire.
      if (seuil) {
        let xmax = 0;
        datasets.forEach(d => d.data.forEach(p => { if (p && p.x > xmax) xmax = p.x; }));
        if (xmax > 0) {
          datasets.push({
            label: 'Arrêt d’urgence (' + seuil + ' %)',
            data: [{ x: 0, y: seuil }, { x: xmax, y: seuil }],
            borderColor: '#e2574c',
            borderDash: [6, 4],
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false,
          });
        }
      }

      new Chart(document.getElementById(id), {
        type: 'line',
        data: { datasets: datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          parsing: false,
          scales: {
            x: {
              type: 'linear',
              title: { display: true, text: 'Durée depuis début du cycle', color: '#86a5c0' },
              ticks: { color: '#86a5c0', callback: v => fmtMin(v) },
              grid: { color: 'rgba(32,66,100,0.25)' }
            },
            y: { title: { display: true, text: 'Niveau (%)' }, min: 0, ticks: { color: '#86a5c0' }, grid: { color: 'rgba(32,66,100,0.25)' } },
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

    createLineChart('current-cycle-chart', recentPoints.length ? [{ label: 'Niveau batterie 24h', points: recentPoints }] : [], ['#f0be4f']);
    createRelativeChart('discharge-chart', dischargeCurves, ['#4a9eff', '#f0be4f', '#3dba6a', '#d97706', '#8b5cf6'], SEUIL_COUPURE);
    createRelativeChart('charge-chart', chargeCurves, ['#3dba6a', '#86efac', '#f0be4f', '#38bdf8', '#fb7185']);

    // ── TICKET-133 — tension et courant sur 24 h ──────────────────────────
    // Deux axes : la tension (V) à gauche, le courant (mA) à droite. Les deux
    // grandeurs sont réellement mesurées par l'INA219 ; le pourcentage affiché
    // partout ailleurs n'est qu'une conversion de la première.
    // Le zéro du courant est la frontière charge/décharge — d'où la ligne à 0.
    (function () {
      const el = document.getElementById('volt-chart');
      if (!window.Chart || !el) return;
      const volts = recentPoints
        .filter(p => p.voltage_v !== null && p.voltage_v !== undefined)
        .map(p => ({ x: new Date(p.t).getTime(), y: p.voltage_v }));
      const amps = recentPoints
        .filter(p => p.current_ma !== null && p.current_ma !== undefined)
        .map(p => ({ x: new Date(p.t).getTime(), y: p.current_ma }));
      if (volts.length < 2) return;

      new Chart(el, {
        type: 'line',
        data: {
          datasets: [
            {
              label: 'Tension (V)', data: volts, yAxisID: 'yV',
              borderColor: '#f0be4f', backgroundColor: '#f0be4f',
              borderWidth: 2, pointRadius: 0, tension: 0.25,
            },
            {
              label: 'Courant (mA)', data: amps, yAxisID: 'yA',
              borderColor: '#4a9eff', backgroundColor: '#4a9eff',
              borderWidth: 1.5, pointRadius: 0, tension: 0.25,
            },
          ]
        },
        options: {
          responsive: true, maintainAspectRatio: false, parsing: false,
          interaction: { mode: 'index', intersect: false },
          scales: {
            x: {
              type: 'linear',
              title: { display: true, text: 'Heure', color: '#86a5c0' },
              ticks: { color: '#86a5c0', callback: v => fmtTime(v) },
              grid: { color: 'rgba(32,66,100,0.25)' }
            },
            yV: {
              position: 'left',
              title: { display: true, text: 'Tension (V)', color: '#f0be4f' },
              ticks: { color: '#f0be4f' },
              grid: { color: 'rgba(32,66,100,0.25)' }
            },
            yA: {
              position: 'right',
              title: { display: true, text: 'Courant (mA)', color: '#4a9eff' },
              ticks: { color: '#4a9eff' },
              // Pas de quadrillage à droite : il se superposerait à celui de
              // gauche et rendrait les deux illisibles.
              grid: { drawOnChartArea: false },
            },
          },
          plugins: {
            legend: { labels: { color: '#e8f0f6' } },
            tooltip: {
              callbacks: {
                afterBody: (items) => {
                  const a = items.find(i => i.dataset.yAxisID === 'yA');
                  if (!a) return '';
                  return a.parsed.y >= 0 ? 'Courant positif → charge'
                                         : 'Courant négatif → décharge';
                }
              }
            }
          }
        }
      });
    })();
  </script>
</body>
</html>