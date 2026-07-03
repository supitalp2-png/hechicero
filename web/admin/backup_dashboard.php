<?php
define('PROJECT_ROOT', is_dir('/home/thomas/hechicero') ? '/home/thomas/hechicero' : dirname(__DIR__, 2));
define('BACKUP_STATE_JSON', PROJECT_ROOT . '/data/backup_state.json');
define('BACKUP_CONFIG_JSON', PROJECT_ROOT . '/data/backup_config.json');

function read_json(string $path): array {
    if (!file_exists($path)) return [];
    $d = json_decode(file_get_contents($path), true);
    return is_array($d) ? $d : [];
}

function fmt_since(?string $iso): string {
    if (!$iso) return '—';
    try {
        $then = new DateTime($iso);
        $now  = new DateTime();
        $secs = max(0, $now->getTimestamp() - $then->getTimestamp());
        if ($secs < 3600)   return floor($secs / 60) . ' min';
        if ($secs < 86400)  return floor($secs / 3600) . 'h';
        return floor($secs / 86400) . ' j';
    } catch (Throwable $e) {
        return '—';
    }
}

$state  = read_json(BACKUP_STATE_JSON);
$config = read_json(BACKUP_CONFIG_JSON);
$daily  = $state['daily']  ?? [];
$durcie = $state['durcie'] ?? [];
$history = array_reverse($daily['history'] ?? []);
$currentPage = basename($_SERVER['PHP_SELF'] ?? 'backup_dashboard.php');

$dailyStatus = $daily['last_status'] ?? null;
$dailyClass  = $dailyStatus === 'ok' ? 'ok' : ($dailyStatus === 'skipped_offline' ? 'warn' : ($dailyStatus ? 'danger' : ''));
$dailyLabel  = ['ok' => 'OK', 'failed' => 'Échec', 'skipped_offline' => 'NAS hors ligne'][$dailyStatus] ?? '—';

$daysSinceSuccess = null;
if (!empty($daily['last_success'])) {
    try {
        $daysSinceSuccess = (new DateTime())->diff(new DateTime($daily['last_success']))->days;
    } catch (Throwable $e) {}
}
$staleWarning = $daysSinceSuccess !== null && $daysSinceSuccess >= 3;
?><!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Hechicero · Sauvegardes</title>
  <link rel="stylesheet" href="/css/hechicero-admin.css">
  <style>
    .status-pill {
      display: inline-flex; align-items: center; gap: 8px; border-radius: 999px; padding: 6px 12px;
      background: rgba(32, 66, 100, 0.42); color: var(--text); font-size: 13px;
    }
    .status-pill.ok     { color: var(--ok); }
    .status-pill.warn   { color: var(--warn); }
    .status-pill.danger { color: var(--danger); }
    .ha-table td, .ha-table th { padding: 10px; border-bottom: 1px solid rgba(32, 66, 100, 0.6); }
    .validate-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 12px; }
    .validate-row input[type=text] {
      flex: 1; min-width: 220px; background: var(--bg); border: 1px solid var(--border);
      border-radius: 8px; color: var(--text); padding: 9px 12px; font-size: 13px;
    }
    .btn-primary {
      background: var(--accent); color: #08111b; border: none; border-radius: 8px;
      padding: 9px 16px; font-size: 13px; font-weight: 700; cursor: pointer;
    }
    .btn-primary:disabled { opacity: .5; cursor: not-allowed; }
    #backup-log {
      background: #050a12; border: 1px solid var(--border); border-radius: 8px;
      padding: 10px; font-family: monospace; font-size: 11px; color: var(--muted);
      max-height: 160px; overflow-y: auto; white-space: pre-wrap; display: none;
    }
    .stale-banner {
      background: rgba(226, 75, 74, 0.12); border: 1px solid var(--danger); color: var(--danger);
      border-radius: 10px; padding: 10px 14px; font-size: 13px; margin-bottom: 16px;
    }
  </style>
</head>
<body>
  <div class="ha-page">
    <div class="ha-header">
      <div>
        <h1>💾 Sauvegardes</h1>
        <div class="ha-subtitle">Ghost complet de la carte SD — version durcie + sauvegardes quotidiennes (TICKET-085)</div>
      </div>
      <nav class="ha-nav">
        <a class="ha-btn <?php echo $currentPage === 'index.php' ? 'active' : ''; ?>" href="/">
          <span class="ha-btn-icon">⚙</span> Admin
        </a>
        <a class="ha-btn <?php echo $currentPage === 'dashboard.php' ? 'active' : ''; ?>" href="/dashboard.php">
          <span class="ha-btn-icon">📊</span> Écoute
        </a>
        <a class="ha-btn <?php echo $currentPage === 'battery_dashboard.php' ? 'active' : ''; ?>" href="/admin/battery_dashboard.php">
          <span class="ha-btn-icon">🔋</span> Batterie
        </a>
        <a class="ha-btn <?php echo $currentPage === 'backup_dashboard.php' ? 'active' : ''; ?>" href="/admin/backup_dashboard.php">
          <span class="ha-btn-icon">💾</span> Sauvegardes
        </a>
        <a class="ha-btn" href="/lecteur/" target="_blank">
          <span class="ha-btn-icon">📻</span> Lecteur
        </a>
      </nav>
    </div>

    <?php if ($staleWarning): ?>
    <div class="stale-banner">
      ⚠️ Dernière sauvegarde réussie il y a <?php echo $daysSinceSuccess; ?> jours — vérifier que le Pi et le NAS sont bien en ligne la nuit.
    </div>
    <?php endif; ?>

    <div class="ha-grid ha-cols-auto" style="margin-bottom:18px;">
      <div class="ha-panel">
        <div class="ha-stat-label">Version durcie actuelle</div>
        <div class="ha-stat-value" style="font-size:16px"><?php echo htmlspecialchars($durcie['file'] ?? 'Aucune'); ?></div>
        <div class="ha-stat-note">
          <?php if (!empty($durcie['validated_at'])): ?>
            Validée il y a <?php echo htmlspecialchars(fmt_since($durcie['validated_at'])); ?>
            <?php if (!empty($durcie['label'])): ?> — "<?php echo htmlspecialchars($durcie['label']); ?>"<?php endif; ?>
          <?php else: ?>
            Aucune version durcie validée pour l'instant
          <?php endif; ?>
        </div>
      </div>
      <div class="ha-panel">
        <div class="ha-stat-label">Dernière sauvegarde quotidienne</div>
        <div class="ha-stat-value"><span class="status-pill <?php echo $dailyClass; ?>"><?php echo htmlspecialchars($dailyLabel); ?></span></div>
        <div class="ha-stat-note">
          <?php echo !empty($daily['last_success']) ? 'Réussie il y a ' . htmlspecialchars(fmt_since($daily['last_success'])) : 'Jamais réussie'; ?>
          <?php if (!empty($daily['last_error'])): ?><br><?php echo htmlspecialchars($daily['last_error']); ?><?php endif; ?>
        </div>
      </div>
      <div class="ha-panel">
        <div class="ha-stat-label">Taille dernière image</div>
        <div class="ha-stat-value"><?php echo isset($daily['last_size_mb']) ? number_format($daily['last_size_mb'] / 1024, 1) . ' Go' : '—'; ?></div>
        <div class="ha-stat-note">Rotation : <?php echo (int)($config['retention']['daily_keep'] ?? 7); ?> sauvegardes conservées</div>
      </div>
      <div class="ha-panel">
        <div class="ha-stat-label">Rythme automatique</div>
        <div class="ha-stat-value" style="font-size:16px">Chaque nuit à 3h</div>
        <div class="ha-stat-note">Rattrapée au prochain démarrage si le Pi était éteint</div>
      </div>
    </div>

    <section class="ha-panel" style="margin-bottom:18px">
      <h2>Valider une nouvelle version durcie</h2>
      <p class="muted" style="font-size:13px;margin-bottom:12px">
        À faire après avoir testé et validé un état stable du projet. Lance un ghost complet
        immédiat (~1h+) et remplace la version durcie précédente une fois terminé avec succès.
      </p>
      <div class="validate-row">
        <input type="text" id="durcie-label" placeholder="Description (ex: widget fatigue auditive + fix audio boot)" maxlength="200">
        <button class="btn-primary" id="btn-validate">Valider une nouvelle version durcie</button>
      </div>
      <div id="backup-log"></div>
    </section>

    <section class="ha-panel">
      <h2>Historique des sauvegardes quotidiennes</h2>
      <?php if (!$history): ?>
        <div class="ha-empty">Aucune sauvegarde encore enregistrée.</div>
      <?php else: ?>
        <table class="ha-table" style="width:100%">
          <thead>
            <tr><th>Date</th><th>Statut</th><th>Taille</th><th>Détail</th></tr>
          </thead>
          <tbody>
            <?php foreach ($history as $h): ?>
              <?php
                $st = $h['status'] ?? '—';
                $cls = $st === 'ok' ? 'ok' : ($st === 'skipped_offline' ? 'warn' : 'danger');
                $lbl = ['ok' => 'OK', 'failed' => 'Échec', 'skipped_offline' => 'NAS hors ligne'][$st] ?? $st;
              ?>
              <tr>
                <td><?php echo htmlspecialchars($h['date'] ?? '—'); ?></td>
                <td><span class="status-pill <?php echo $cls; ?>"><?php echo htmlspecialchars($lbl); ?></span></td>
                <td><?php echo isset($h['size_mb']) ? number_format($h['size_mb'] / 1024, 1) . ' Go' : '—'; ?></td>
                <td style="color:var(--muted);font-size:12px"><?php echo htmlspecialchars($h['error'] ?? ''); ?></td>
              </tr>
            <?php endforeach; ?>
          </tbody>
        </table>
      <?php endif; ?>
    </section>
  </div>

  <script>
    const btn   = document.getElementById('btn-validate');
    const label = document.getElementById('durcie-label');
    const log   = document.getElementById('backup-log');
    let poller  = null;

    async function pollStatus() {
      try {
        const r = await fetch('/index.php?action=backup_status', { cache: 'no-store' });
        const d = await r.json();
        if (d.log) {
          log.style.display = 'block';
          log.textContent = d.log;
          log.scrollTop = log.scrollHeight;
        }
        if (!d.running) {
          clearInterval(poller);
          poller = null;
          btn.disabled = false;
          btn.textContent = 'Valider une nouvelle version durcie';
          setTimeout(() => location.reload(), 1500);
        }
      } catch (e) { /* ignore */ }
    }

    btn.addEventListener('click', async () => {
      btn.disabled = true;
      btn.textContent = 'Sauvegarde en cours…';
      log.style.display = 'block';
      log.textContent = 'Démarrage…';
      const body = new URLSearchParams({ label: label.value || '' });
      try {
        const r = await fetch('/index.php?action=backup_validate', { method: 'POST', body });
        const d = await r.json();
        if (!d.ok) {
          log.textContent = 'Erreur : ' + (d.msg || 'échec du déclenchement');
          btn.disabled = false;
          btn.textContent = 'Valider une nouvelle version durcie';
          return;
        }
        poller = setInterval(pollStatus, 3000);
        pollStatus();
      } catch (e) {
        log.textContent = 'Erreur : ' + e.message;
        btn.disabled = false;
        btn.textContent = 'Valider une nouvelle version durcie';
      }
    });

    // Reprend le suivi si une validation était déjà en cours au chargement de la page
    (async () => {
      const r = await fetch('/index.php?action=backup_status', { cache: 'no-store' });
      const d = await r.json();
      if (d.running) {
        btn.disabled = true;
        btn.textContent = 'Sauvegarde en cours…';
        poller = setInterval(pollStatus, 3000);
        pollStatus();
      }
    })();
  </script>
</body>
</html>
