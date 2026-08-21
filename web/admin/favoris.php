<?php
require_once __DIR__ . '/../bootstrap.php';  // TICKET-129 : fuseau Europe/Paris, sinon PHP tourne en UTC
// ============================================================
// Hechicero — Admin favoris (TICKET-046)
// Page dédiée, réseau local. Voir/gérer les favoris marqués par l'enfant
// (bouton physique GPIO16, cf. scripts/buttons_daemon.py) — ajout possible
// uniquement depuis l'appareil, cette page ne fait que consulter/retirer.
// ============================================================

define('PROJECT_ROOT', is_dir('/home/thomas/hechicero') ? '/home/thomas/hechicero' : dirname(__DIR__, 2));
define('FAVORIS_PATH', PROJECT_ROOT . '/data/favoris.json');
define('DATA_JSON_PATH', PROJECT_ROOT . '/web/lecteur/data.json');

function read_json_favoris(string $path): array {
    if (!file_exists($path)) return [];
    $d = json_decode(file_get_contents($path), true);
    return is_array($d) ? $d : [];
}

function write_favoris_admin(array $data): void {
    $dir = dirname(FAVORIS_PATH);
    if (!is_dir($dir)) @mkdir($dir, 0755, true);
    $tmp = FAVORIS_PATH . '.tmp';
    file_put_contents($tmp, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE));
    rename($tmp, FAVORIS_PATH);
}

$message = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'remove') {
    $key = (string)($_POST['key'] ?? '');
    $favoris = read_json_favoris(FAVORIS_PATH);
    if ($key !== '' && isset($favoris[$key])) {
        unset($favoris[$key]);
        write_favoris_admin($favoris);
        $message = 'Favori retiré.';
    }
}

// Enrichissement — même logique que radio.php::get_favoris (deux types :
// episode/radio, cf. TICKET-046 extension webradio du 2026-07-19). Un favori
// dont l'épisode/la station a disparu de data.json (podcast supprimé/
// ré-ingéré, radio retirée) est filtré plutôt qu'affiché cassé — data.json
// est régénéré par l'ingestion RSS, pas une source stable dans le temps.
$favorisRaw = read_json_favoris(FAVORIS_PATH);
$data = read_json_favoris(DATA_JSON_PATH);
$podcastsById = [];
foreach ($data['podcasts'] ?? [] as $p) {
    if (isset($p['id'])) $podcastsById[$p['id']] = $p;
}
$radiosById = [];
foreach ($data['radios'] ?? [] as $r) {
    if (isset($r['id'])) $radiosById[$r['id']] = $r;
}

$favoris = [];
foreach ($favorisRaw as $key => $entry) {
    $type = $entry['type'] ?? 'episode';

    if ($type === 'radio') {
        $radio = $radiosById[$entry['radio_id'] ?? ''] ?? null;
        if ($radio === null) continue;
        // Icône webradio : le champ "image" est relatif au lecteur
        // ("images/radio/x.jpg") → cassé depuis /admin/. On préfixe par
        // /lecteur/ ; à défaut on retombe sur l'URL distante (image_url).
        $rimg = $radio['image'] ?? '';
        if ($rimg !== '' && !preg_match('#^(https?:)?/#', $rimg)) {
            $rimg = '/lecteur/' . ltrim($rimg, '/');
        }
        if ($rimg === '') $rimg = $radio['image_url'] ?? '';
        $favoris[] = [
            'key'           => $key,
            'type'          => 'radio',
            'podcast_titre' => 'Webradio',
            'titre'         => $radio['name'] ?? '',
            'image'         => $rimg,
            'added_at'      => $entry['added_at'] ?? '',
        ];
        continue;
    }

    $podcast = $podcastsById[$entry['podcast_id'] ?? ''] ?? null;
    if ($podcast === null) continue;
    $chapter = null;
    foreach (($podcast['chapitres'] ?? $podcast['episodes'] ?? []) as $ch) {
        if (($ch['id'] ?? null) === ($entry['episode_id'] ?? null)) { $chapter = $ch; break; }
    }
    if ($chapter === null) continue;

    $favoris[] = [
        'key'           => $key,
        'type'          => 'episode',
        'podcast_titre' => $podcast['titre'] ?? '',
        'titre'         => $chapter['titre'] ?? '',
        'image'         => $chapter['image'] ?? ($podcast['image'] ?? ''),
        'added_at'      => $entry['added_at'] ?? '',
    ];
}
usort($favoris, fn($a, $b) => strcmp($b['added_at'], $a['added_at']));

$currentPage = basename($_SERVER['PHP_SELF'] ?? 'favoris.php');
?><!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Hechicero · Favoris</title>
  <link rel="stylesheet" href="/css/hechicero-admin.css">
  <style>
    .fav-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
    .fav-card {
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 16px; overflow: hidden; display: flex; flex-direction: column;
      box-shadow: 0 18px 60px rgba(0,0,0,0.22);
    }
    .fav-card img { width: 100%; aspect-ratio: 1/1; object-fit: cover; display: block; }
    .fav-card-body { padding: 12px 14px; display: flex; flex-direction: column; gap: 4px; flex: 1; }
    .fav-card-titre { font-weight: 600; font-size: 14px; }
    .fav-card-podcast { font-size: 12px; color: var(--muted); }
    .fav-card-date { font-size: 11px; color: var(--muted); margin-top: auto; }
    .fav-remove-btn {
      margin-top: 8px; padding: 8px 12px; border-radius: 8px; border: 1px solid var(--border);
      background: transparent; color: var(--danger, #e24b4a); font-size: 13px; cursor: pointer;
    }
    .fav-remove-btn:hover { background: rgba(226,75,74,0.12); }
    .fav-empty { color: var(--muted); padding: 20px 0; }
    .fav-message { margin-bottom: 16px; padding: 12px 14px; border-radius: 10px; font-size: 13px;
      background: rgba(61,186,106,0.12); color: var(--ok); border: 1px solid rgba(61,186,106,0.35); }
  </style>
</head>
<body>
  <div class="ha-page">
    <div class="ha-header">
      <div>
        <h1>❤️ Favoris</h1>
        <div class="ha-subtitle">Épisodes et webradios marqués d’un cœur</div>
      </div>
      <nav class="ha-nav">
        <a class="ha-btn" href="/"><span class="ha-btn-icon">‹</span> Bureau</a>
        <a class="ha-btn" href="/lecteur/" target="_blank"><span class="ha-btn-icon">📻</span> Lecteur</a>
      </nav>
    </div>

    <?php if ($message): ?>
      <div class="fav-message"><?php echo htmlspecialchars($message); ?></div>
    <?php endif; ?>

    <?php if (!$favoris): ?>
      <div class="fav-empty">Aucun favori pour l'instant — ils apparaissent ici dès qu'un épisode ou une webradio est marqué avec le bouton ♥ sur l'enceinte.</div>
    <?php else: ?>
      <div class="fav-grid">
        <?php foreach ($favoris as $f): ?>
          <div class="fav-card">
            <img src="<?php echo htmlspecialchars($f['image']); ?>" alt="" loading="lazy">
            <div class="fav-card-body">
              <div class="fav-card-titre"><?php echo htmlspecialchars($f['titre']); ?></div>
              <div class="fav-card-podcast"><?php echo htmlspecialchars($f['podcast_titre']); ?></div>
              <div class="fav-card-date"><?php echo $f['added_at'] ? 'Ajouté le ' . date('d/m/Y à H:i', strtotime($f['added_at'])) : ''; ?></div>
              <form method="post">
                <input type="hidden" name="action" value="remove">
                <input type="hidden" name="key" value="<?php echo htmlspecialchars($f['key']); ?>">
                <button type="submit" class="fav-remove-btn">Retirer</button>
              </form>
            </div>
          </div>
        <?php endforeach; ?>
      </div>
    <?php endif; ?>
  </div>
</body>
</html>
