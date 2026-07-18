<?php
// ============================================================
// Hechicero — Admin égaliseur audio (TICKET-030)
// Page dédiée, réseau local, mode Expert uniquement (cf. nav index.php)
// ============================================================

define('PROJECT_ROOT', is_dir('/home/thomas/hechicero') ? '/home/thomas/hechicero' : dirname(__DIR__, 2));
define('CONFIG_PATH', PROJECT_ROOT . '/data/audio_eq.json');
define('APPLY_SCRIPT', PROJECT_ROOT . '/scripts/audio_eq_apply.py');

const BANDS_HZ    = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000];
const BAND_LABELS = ['31 Hz', '63 Hz', '125 Hz', '250 Hz', '500 Hz', '1 kHz', '2 kHz', '4 kHz', '8 kHz', '16 kHz'];

// Presets — points de départ à affiner à l'oreille (cf. docs/90-BACKLOG.md TICKET-030)
const PRESETS = [
    'plat'   => ['label' => 'Plat (neutre)',      'bands' => [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]],
    'basses' => ['label' => 'Basses renforcées',  'bands' => [5, 5, 4, 2, 0, 0, 0, 0, 0, 0]],
    'voix'   => ['label' => 'Voix claire',        'bands' => [-1, -1, 0, -2, -1, 0, 2, 3, 1, 0]],
    'chaud'  => ['label' => 'Chaud et rond',       'bands' => [4, 4, 3, 1, 0, 0, 0, -1, -1, -2]],
];

const DEFAULT_PROFILE = ['preset' => 'plat', 'bands_db' => [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]];

function read_config(): array {
    if (!file_exists(CONFIG_PATH)) {
        return ['profiles' => ['hp' => DEFAULT_PROFILE, 'casque' => DEFAULT_PROFILE]];
    }
    $data = json_decode(file_get_contents(CONFIG_PATH), true);
    if (!is_array($data)) $data = [];
    $data['profiles'] = $data['profiles'] ?? [];
    $data['profiles']['hp']     = $data['profiles']['hp']     ?? DEFAULT_PROFILE;
    $data['profiles']['casque'] = $data['profiles']['casque'] ?? DEFAULT_PROFILE;
    return $data;
}

$message = '';
$messageType = 'ok';

if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'save') {
    $profileName = $_POST['profile'] ?? '';
    $preset      = $_POST['preset'] ?? 'custom';
    $bandsRaw    = $_POST['bands'] ?? [];

    if (!in_array($profileName, ['hp', 'casque'], true)) {
        $message = 'Profil inconnu.';
        $messageType = 'error';
    } else {
        $bands = [];
        for ($i = 0; $i < 10; $i++) {
            $v = isset($bandsRaw[$i]) ? (float)$bandsRaw[$i] : 0.0;
            $bands[] = max(-12.0, min(12.0, $v));
        }

        $config = read_config();
        $config['profiles'][$profileName] = ['preset' => $preset, 'bands_db' => $bands];
        $config['updated'] = date('c');

        if (file_put_contents(CONFIG_PATH, json_encode($config, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)) === false) {
            $message = "Échec de l'écriture de data/audio_eq.json (permissions ?)";
            $messageType = 'error';
        } else {
            $cmd = '/usr/bin/python3 ' . escapeshellarg(APPLY_SCRIPT) . ' --profile ' . escapeshellarg($profileName) . ' 2>&1';
            $output = shell_exec($cmd);
            $message = "Profil « " . ($profileName === 'hp' ? 'Haut-parleurs' : 'Casque') . " » enregistré et appliqué.";
            if ($output && trim($output) !== '') {
                $message .= "\nSortie du script : " . trim($output);
            }
            $messageType = 'ok';
        }
    }
}

$config = read_config();
$currentPage = basename($_SERVER['PHP_SELF'] ?? 'audio_eq.php');
?><!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Hechicero · Égaliseur audio</title>
  <link rel="stylesheet" href="/css/hechicero-admin.css">
  <style>
    .eq-tabs { display: flex; gap: 8px; margin-bottom: 18px; }
    .eq-tab {
      padding: 10px 18px; border-radius: 12px; border: 1px solid var(--border);
      background: var(--surface-2, rgba(13,24,38,0.6)); color: var(--muted);
      cursor: pointer; font-size: 14px; font-weight: 600;
    }
    .eq-tab.active { color: var(--text); border-color: var(--accent); background: rgba(240,190,79,0.12); }
    .eq-profile { display: none; }
    .eq-profile.active { display: block; }
    .eq-presets { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 18px; }
    .eq-preset-btn {
      padding: 8px 14px; border-radius: 999px; border: 1px solid var(--border);
      background: transparent; color: var(--text); font-size: 13px; cursor: pointer;
    }
    .eq-preset-btn:hover { border-color: var(--accent); }
    .eq-sliders {
      display: grid; grid-template-columns: repeat(10, 1fr); gap: 12px;
      align-items: end; margin-bottom: 20px; min-height: 220px;
    }
    .eq-band { display: flex; flex-direction: column; align-items: center; gap: 8px; }
    .eq-band-value { font-size: 12px; color: var(--accent); font-variant-numeric: tabular-nums; min-height: 16px; }
    .eq-band input[type=range] {
      writing-mode: vertical-lr; direction: rtl;
      width: 24px; height: 150px; accent-color: var(--accent);
    }
    .eq-band-label { font-size: 11px; color: var(--muted); }
    .eq-actions { display: flex; align-items: center; gap: 12px; }
    .eq-save-btn {
      padding: 10px 20px; border-radius: 10px; border: none;
      background: var(--accent); color: #08111b; font-weight: 700; font-size: 14px; cursor: pointer;
    }
    .eq-save-btn:hover { filter: brightness(1.08); }
    .eq-message { white-space: pre-wrap; margin-top: 14px; padding: 12px 14px; border-radius: 10px; font-size: 13px; }
    .eq-message.ok { background: rgba(61,186,106,0.12); color: var(--ok); border: 1px solid rgba(61,186,106,0.35); }
    .eq-message.error { background: rgba(226,75,74,0.12); color: var(--danger); border: 1px solid rgba(226,75,74,0.35); }
    .eq-note { color: var(--muted); font-size: 13px; margin-bottom: 18px; }
    @media (max-width: 720px) {
      .eq-sliders { grid-template-columns: repeat(5, 1fr); row-gap: 24px; }
    }
  </style>
</head>
<body>
  <div class="ha-page">
    <div class="ha-header">
      <div>
        <h1>🎚️ Égaliseur audio</h1>
        <div class="ha-subtitle">TICKET-030 — réglages basses/médium/aigus, un profil par sortie</div>
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
        <a class="ha-btn active" href="/admin/audio_eq.php">
          <span class="ha-btn-icon">🎚️</span> Audio
        </a>
        <a class="ha-btn" href="/lecteur/" target="_blank">
          <span class="ha-btn-icon">📻</span> Lecteur
        </a>
      </nav>
    </div>

    <div class="eq-note">
      Réglage indépendant pour les haut-parleurs (HiFiBerry Amp4) et le casque (DAC USB).
      Chaque sauvegarde applique le changement immédiatement, sans redémarrer MPD.
      ⚠️ Config système jamais testée en conditions réelles avant ce premier essai —
      si un profil ne change rien au son, voir <code>journalctl -u audio_eq_apply</code>
      et <code>python3 scripts/audio_eq_apply.py --list-controls</code> sur le Pi.
    </div>

    <div class="eq-tabs">
      <button type="button" class="eq-tab active" data-tab="hp">🔊 Haut-parleurs</button>
      <button type="button" class="eq-tab" data-tab="casque">🎧 Casque</button>
    </div>

    <?php foreach (['hp' => 'Haut-parleurs', 'casque' => 'Casque'] as $profileKey => $profileLabel): ?>
      <?php $profile = $config['profiles'][$profileKey]; $bands = $profile['bands_db'] ?? DEFAULT_PROFILE['bands_db']; ?>
      <form method="post" class="eq-profile <?php echo $profileKey === 'hp' ? 'active' : ''; ?>" data-profile="<?php echo $profileKey; ?>">
        <input type="hidden" name="action" value="save">
        <input type="hidden" name="profile" value="<?php echo $profileKey; ?>">
        <input type="hidden" name="preset" class="eq-preset-input" value="<?php echo htmlspecialchars($profile['preset'] ?? 'custom'); ?>">

        <div class="eq-presets">
          <?php foreach (PRESETS as $key => $preset): ?>
            <button type="button" class="eq-preset-btn" data-preset="<?php echo $key; ?>" data-bands="<?php echo htmlspecialchars(json_encode($preset['bands'])); ?>">
              <?php echo htmlspecialchars($preset['label']); ?>
            </button>
          <?php endforeach; ?>
        </div>

        <div class="eq-sliders">
          <?php foreach (BAND_LABELS as $i => $label): ?>
            <div class="eq-band">
              <div class="eq-band-value"><?php echo number_format($bands[$i] ?? 0, 0); ?> dB</div>
              <input type="range" name="bands[]" min="-12" max="12" step="1" value="<?php echo (float)($bands[$i] ?? 0); ?>">
              <div class="eq-band-label"><?php echo htmlspecialchars($label); ?></div>
            </div>
          <?php endforeach; ?>
        </div>

        <div class="eq-actions">
          <button type="submit" class="eq-save-btn">Enregistrer et appliquer — <?php echo $profileLabel; ?></button>
        </div>

        <?php if ($message && ($_POST['profile'] ?? '') === $profileKey): ?>
          <div class="eq-message <?php echo $messageType; ?>"><?php echo htmlspecialchars($message); ?></div>
        <?php endif; ?>
      </form>
    <?php endforeach; ?>
  </div>

  <script>
    // Onglets
    document.querySelectorAll('.eq-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.eq-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.eq-profile').forEach(p => p.classList.remove('active'));
        tab.classList.add('active');
        document.querySelector(`.eq-profile[data-profile="${tab.dataset.tab}"]`).classList.add('active');
      });
    });

    // Presets : préchargent les 10 curseurs du profil courant
    document.querySelectorAll('.eq-profile').forEach(form => {
      const sliders = form.querySelectorAll('input[type=range]');
      const presetInput = form.querySelector('.eq-preset-input');

      form.querySelectorAll('.eq-preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const bands = JSON.parse(btn.dataset.bands);
          sliders.forEach((slider, i) => {
            slider.value = bands[i];
            slider.dispatchEvent(new Event('input'));
          });
          presetInput.value = btn.dataset.preset;
        });
      });

      sliders.forEach(slider => {
        const valueEl = slider.closest('.eq-band').querySelector('.eq-band-value');
        slider.addEventListener('input', () => {
          valueEl.textContent = `${slider.value} dB`;
          presetInput.value = 'custom';
        });
      });
    });
  </script>
</body>
</html>
