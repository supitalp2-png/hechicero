<?php
// --- CONFIG ---
$stream = "https://icecast.radiofrance.fr/monpetitfranceinter-midfi.mp3";
$projectRoot = "/home/thomas/hechicero";
const CONFIG_PATH = '/home/thomas/hechicero/web/lecteur/config.json';
const AUDIO_STATE_PATH = '/home/thomas/hechicero/data/audio_output_state.json';

function read_json_radio(string $path): array {
    if (!file_exists($path)) {
        return [];
    }
    $d = json_decode(file_get_contents($path), true);
    return is_array($d) ? $d : [];
}

// --- État audio partagé (mode + volume mémorisé par mode) ---
// Source unique de vérité côté serveur : que la bascule soit déclenchée par
// l'IHM tactile, un bouton physique (GPIO) ou plus tard une détection
// automatique du casque, le comportement (volume mémorisé, séquence
// "volume d'abord, sortie ensuite") doit être identique — donc géré ici,
// pas dupliqué côté client.
function load_audio_state(): array {
    $d = read_json_radio(AUDIO_STATE_PATH);
    return [
        'mode'          => $d['mode']          ?? 'hp',
        'volume_hp'     => $d['volume_hp']     ?? 70,
        'volume_casque' => $d['volume_casque'] ?? 70,
    ];
}

function save_audio_state(array $state): void {
    $dir = dirname(AUDIO_STATE_PATH);
    if (!is_dir($dir)) {
        @mkdir($dir, 0755, true);
    }
    $tmp = AUDIO_STATE_PATH . '.tmp';
    file_put_contents($tmp, json_encode($state, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES));
    rename($tmp, AUDIO_STATE_PATH);
}

function volume_max_for_mode(string $mode): int {
    $cfg = read_json_radio(CONFIG_PATH);
    if ($mode === 'casque') {
        return (int)($cfg['volume']['headphones_max'] ?? 60);
    }
    return (int)($cfg['volume']['speakers_max'] ?? 40);
}

function mpd_to_ihm_pct(int $mpdVol, string $mode): int {
    $max = max(1, volume_max_for_mode($mode));
    return max(0, min(100, (int)round($mpdVol * 100 / $max)));
}

function ihm_to_mpd_vol(int $ihmPct, string $mode): int {
    $max = volume_max_for_mode($mode);
    return max(0, min(100, (int)round($ihmPct * $max / 100)));
}

function mpd_command(string $command): string {
    $socket = @fsockopen('unix:///run/mpd/socket', 0, $errno, $errstr, 1.5);
    if (!$socket) {
        return "MPD connection failed: $errstr";
    }

    stream_set_timeout($socket, 2);
    fgets($socket); // greeting
    fwrite($socket, $command . "\n");

    $response = '';
    while (!feof($socket)) {
        $line = fgets($socket);
        if ($line === false) {
            break;
        }
        $response .= $line;
        if (trim($line) === 'OK' || str_starts_with($line, 'ACK')) {
            break;
        }
    }

    fclose($socket);
    return $response;
}

function mpd_batch(array $commands): string {
    $socket = @fsockopen('unix:///run/mpd/socket', 0, $errno, $errstr, 1.5);
    if (!$socket) {
        return "MPD connection failed: $errstr";
    }

    stream_set_timeout($socket, 2);
    fgets($socket); // greeting
    fwrite($socket, "command_list_begin\n");
    foreach ($commands as $command) {
        fwrite($socket, $command . "\n");
    }
    fwrite($socket, "command_list_end\n");

    $response = '';
    while (!feof($socket)) {
        $line = fgets($socket);
        if ($line === false) {
            break;
        }
        $response .= $line;
        if (trim($line) === 'OK' || str_starts_with($line, 'ACK')) {
            break;
        }
    }

    fclose($socket);
    return $response;
}

function mpd_output_enabled(string $raw, int $wantedId): ?bool {
    // Découpe la réponse "outputs" en blocs par outputid, puis lit
    // outputenabled dans le bon bloc — plutôt qu'une regex qui suppose un
    // ordre de champs fixe juste après outputname. MPD peut insérer des
    // champs supplémentaires (ex: "plugin: alsa" apparu en 0.24) entre les
    // deux, ce qui cassait silencieusement l'ancienne detection (toujours
    // "hp", jamais "casque").
    $blocks = preg_split('/(?=^outputid: )/m', trim($raw));
    foreach ($blocks as $block) {
        if (!preg_match('/^outputid: (\d+)/m', $block, $idMatch)) {
            continue;
        }
        if ((int)$idMatch[1] !== $wantedId) {
            continue;
        }
        if (preg_match('/^outputenabled: (\d)/m', $block, $enMatch)) {
            return $enMatch[1] === '1';
        }
        return null;
    }
    return null;
}

function mpd_status(): array {
    $raw = mpd_command('status');
    $status = [];

    foreach (preg_split('/\r?\n/', $raw) as $line) {
        if (strpos($line, ': ') !== false) {
            [$key, $value] = explode(': ', $line, 2);
            $status[$key] = $value;
        }
    }

    $status['_raw'] = $raw;
    return $status;
}

function mpd_add_and_play(string $uri): array {
    $responses = [];
    $responses['clear'] = mpd_command('clear');
    $responses['addid'] = mpd_command('addid ' . $uri);

    if (preg_match('/^Id: (\d+)/m', $responses['addid'], $matches)) {
        $responses['playid'] = mpd_command('playid ' . $matches[1]);
        return $responses;
    }

    $responses['play'] = mpd_command('play');
    return $responses;
}

// --- Navigation épisode next/précédent (TICKET-091, boutons GPIO) ---
// Source de vérité = fichier réellement en cours sur MPD (jamais un état
// mémorisé côté serveur ou côté client) — même principe que get_output pour
// TICKET-031 : ça marche identiquement que la piste ait été lancée depuis
// l'IHM tactile ou changée par un bouton physique.
function mpd_file_to_relative_audio(string $mpdFile, string $projectRoot): string {
    // Inverse de normalize_path() : "file:///home/.../podcasts/x/y.mp3"
    // -> "/podcasts/x/y.mp3" (même format que le champ "audio" de data.json)
    $prefix = 'file://' . $projectRoot;
    if (str_starts_with($mpdFile, $prefix)) {
        return substr($mpdFile, strlen($prefix));
    }
    return $mpdFile; // webradio (URL http/https) ou chemin déjà étranger — pas d'épisode
}

// Retourne les épisodes d'un podcast dans le même ordre que getDisplayItems()
// côté JS (web/lecteur/index.html) : chapitres/episodes, ordre inversé
// (ep1 en premier).
function podcast_display_items(array $podcast): array {
    $raw = $podcast['chapitres'] ?? $podcast['episodes'] ?? [];
    return array_values(array_reverse($raw));
}

// Cherche l'épisode actuellement en lecture dans data.json à partir du
// chemin audio relatif. Retourne null si ce n'est pas un épisode de podcast
// (ex : webradio en cours).
function find_current_episode(string $relativeAudio, array $data): ?array {
    foreach ($data['podcasts'] ?? [] as $podcast) {
        $items = podcast_display_items($podcast);
        foreach ($items as $idx => $ch) {
            if (($ch['audio'] ?? null) === $relativeAudio) {
                return ['podcast' => $podcast, 'chapter' => $ch, 'idx' => $idx, 'items' => $items];
            }
        }
    }
    return null;
}

function normalize_path(string $path, string $projectRoot): string {
    $path = trim($path);
    if ($path === '') {
        return '';
    }

    // /podcasts/... → file:///home/thomas/hechicero/podcasts/...
    if (str_starts_with($path, '/podcasts/')) {
        return 'file://' . $projectRoot . $path;
    }

    // Chemin absolu déjà complet → file://...
    if (str_starts_with($path, $projectRoot)) {
        return 'file://' . $path;
    }

    // URI déjà formée (file://, http://)
    if (str_starts_with($path, 'file://') || str_starts_with($path, 'http')) {
        return $path;
    }

    return $path;
}

// --- ACTIONS ---
if (isset($_GET['action'])) {
    $action = $_GET['action'];

    if ($action === "play") {
        $playUrl = $stream;
        if (isset($_GET['url']) && $_GET['url'] !== '') {
            $candidate = (string)$_GET['url'];
            if (filter_var($candidate, FILTER_VALIDATE_URL) &&
                (str_starts_with($candidate, 'https://') || str_starts_with($candidate, 'http://'))) {
                $playUrl = $candidate;
            }
        }
        mpd_add_and_play($playUrl);
    }

    if ($action === "pause") {
        $status = mpd_status();
        $state = $status['state'] ?? '';
        if ($state === 'play') {
            mpd_command('pause 1');
        } else {
            mpd_command('play');
        }
    }

    if ($action === "playfile" && isset($_GET['path'])) {
        $path = normalize_path((string)$_GET['path'], $projectRoot);
        if ($path !== '') {
            $responses = mpd_add_and_play($path);
            if (isset($_GET['debug'])) {
                header('Content-Type: application/json; charset=utf-8');
                echo json_encode($responses, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
                exit;
            }
        }
    }

    if ($action === "volup") {
        $status = mpd_status();
        $volume = isset($status['volume']) ? (int)$status['volume'] : 10;
        mpd_command('setvol ' . min(100, $volume + 5));
    }

    if ($action === 'setvol' && isset($_GET['vol'])) {
        $vol = max(0, min(100, (int)$_GET['vol']));
        mpd_command("setvol $vol");
    }

    if ($action === 'seekcur' && isset($_GET['time'])) {
        $time = (int)$_GET['time'];
        mpd_command("seekcur $time");
    }

    if ($action === "voldown") {
        $status = mpd_status();
        $volume = isset($status['volume']) ? (int)$status['volume'] : 10;
        mpd_command('setvol ' . max(0, $volume - 5));
    }

    if ($action === "status") {
        echo mpd_status()['_raw'];
        exit;
    }

    if ($action === 'parental_status') {
        header('Content-Type: application/json; charset=utf-8');
        $p = read_json_radio($projectRoot . '/data/parental.json');
        $c = read_json_radio($projectRoot . '/web/lecteur/config.json');
        echo json_encode([
            'schedule_enabled' => (bool)($p['schedule_enabled'] ?? $p['enabled'] ?? false),
            'lang_enabled'     => (bool)($p['lang_enabled']     ?? false),
            'schedule'         => $p['schedule']  ?? [],
            'languages'        => $p['languages'] ?? ['fr', 'es'],
            // veille : config.json uniquement (admin avancée) — pas de fallback parental.json
            // pour éviter qu'un ancien save avec sleep_enabled:false bloque la veille
            'sleep_enabled'    => (bool)($c['sleep_enabled'] ?? true),
            'sleep_delay'      => (int)($c['sleep_delay']    ?? 15),
            'sleep_mode'       => $c['sleep_mode']           ?? 'retro',
            // son de démarrage
            'chime_enabled'    => (bool)($c['chime_enabled'] ?? true),
            'chime_volume'     => (int)($c['chime_volume']   ?? 15),
            'chime_sound'      => $c['chime_sound']          ?? 'chime.wav',
        ]);
        exit;
    }

    if ($action === 'save_config') {
        header('Content-Type: application/json; charset=utf-8');
        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            http_response_code(405);
            echo json_encode(['ok' => false, 'error' => 'method_not_allowed']);
            exit;
        }

        $cfg = read_json_radio(CONFIG_PATH);
        $input = json_decode(file_get_contents('php://input'), true) ?? [];
        $allowed = ['sleep_enabled', 'sleep_delay', 'sleep_mode', 'chime_enabled', 'chime_volume', 'chime_sound'];
        foreach ($allowed as $k) {
            if (array_key_exists($k, $input)) {
                $cfg[$k] = $input[$k];
            }
        }

        file_put_contents(CONFIG_PATH, json_encode($cfg, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
        echo json_encode(['ok' => true]);
        exit;
    }

    if ($action === "seekid" && isset($_GET['id']) && isset($_GET['time'])) {
        $songid = (int)$_GET['id'];
        $secs   = (int)$_GET['time'];
        mpd_command('seekid ' . $songid . ' ' . $secs);
    }

    // Bascule HP/casque — TICKET-031 (bouton physique GPIO + IHM tactile,
    // même comportement des deux côtés : volume mémorisé par mode, volume
    // réglé avant la sortie pour éviter le pic sonore). État partagé dans
    // data/audio_output_state.json (cf. load_audio_state/save_audio_state).
    // output 0 = HiFiBerry (haut-parleurs), output 1 = KT USB Audio (casque)
    if ($action === 'get_output') {
        header('Content-Type: application/json; charset=utf-8');
        $raw    = mpd_command('outputs');
        $mode   = mpd_output_enabled($raw, 1) === true ? 'casque' : 'hp';
        $status = mpd_status();
        $volPct = isset($status['volume']) ? mpd_to_ihm_pct((int)$status['volume'], $mode) : null;
        echo json_encode(['mode' => $mode, 'volume_pct' => $volPct]);
        exit;
    }

    if ($action === 'set_output' && isset($_GET['mode'])) {
        header('Content-Type: application/json; charset=utf-8');
        $targetMode = $_GET['mode'] === 'casque' ? 'casque' : 'hp';

        $state = load_audio_state();

        // Mode réellement actif côté MPD (pas la valeur mémorisée dans le
        // fichier d'état, qui peut dériver si l'état MPD a changé sans
        // passer par ici — ex: état laissé par un bug précédent, ou premier
        // appel avant que le fichier d'état existe). Évite toute
        // incohérence entre "on pense quitter X" et "on quitte vraiment Y".
        $rawOutputs  = mpd_command('outputs');
        $leavingMode = mpd_output_enabled($rawOutputs, 1) === true ? 'casque' : 'hp';

        // Mémorise le volume actuel (lu depuis MPD, pas besoin que l'appelant
        // le transmette) pour le mode qu'on quitte — identique que ce soit
        // l'IHM, le bouton physique ou une détection automatique qui appelle.
        $status = mpd_status();
        if (isset($status['volume'])) {
            $state['volume_' . $leavingMode] = mpd_to_ihm_pct((int)$status['volume'], $leavingMode);
        }

        // Volume mémorisé pour le mode cible, appliqué AVANT la bascule de
        // sortie — évite le pic sonore (même séquence que l'ancien code IHM).
        $targetPct = $state['volume_' . $targetMode] ?? 70;
        mpd_command('setvol ' . ihm_to_mpd_vol($targetPct, $targetMode));

        if ($targetMode === 'casque') {
            $res = mpd_batch(['enableoutput 1', 'disableoutput 0']);
        } else {
            $res = mpd_batch(['enableoutput 0', 'disableoutput 1']);
        }

        $state['mode'] = $targetMode;
        save_audio_state($state);

        // Ne pas répondre ok:true si la commande n'a en fait jamais atteint
        // MPD (socket pas encore prêt, typiquement au boot) — sinon un
        // script qui poll cet endpoint croit avoir réussi dès le 1er essai.
        $ok = !str_starts_with($res, 'MPD connection failed');
        echo json_encode(['ok' => $ok, 'mode' => $targetMode, 'volume_pct' => $targetPct]);
        exit;
    }

    // Navigation épisode — TICKET-091 (boutons GPIO physiques next/précédent).
    // 'now_playing' : lecture seule, utilisée par l'IHM (index.html) pour se
    // resynchroniser périodiquement sur l'épisode réellement joué (utile si
    // la piste a été changée par un bouton physique plutôt que par un tap
    // écran). 'next_episode'/'prev_episode' : déclenchent la bascule réelle.
    if ($action === 'now_playing' || $action === 'next_episode' || $action === 'prev_episode') {
        header('Content-Type: application/json; charset=utf-8');

        $status  = mpd_status();
        $mpdFile = $status['file'] ?? '';
        $relative = mpd_file_to_relative_audio($mpdFile, $projectRoot);
        $data = read_json_radio($projectRoot . '/web/lecteur/data.json');
        $found = find_current_episode($relative, $data);

        if ($found === null) {
            // Rien en cours qui corresponde à un épisode de podcast (webradio,
            // MPD à l'arrêt, ou piste inconnue) — pas une erreur en soi.
            echo json_encode(['ok' => false, 'reason' => 'no_current_episode']);
            exit;
        }

        if ($action === 'now_playing') {
            echo json_encode([
                'ok'         => true,
                'podcast_id' => $found['podcast']['id']  ?? null,
                'episode_id' => $found['chapter']['id']  ?? null,
                'idx'        => $found['idx'],
                'titre'      => $found['chapter']['titre'] ?? null,
            ]);
            exit;
        }

        $delta     = $action === 'next_episode' ? 1 : -1;
        $targetIdx = $found['idx'] + $delta;
        if ($targetIdx < 0 || $targetIdx >= count($found['items'])) {
            echo json_encode([
                'ok'         => false,
                'reason'     => 'out_of_bounds',
                'podcast_id' => $found['podcast']['id'] ?? null,
                'idx'        => $found['idx'],
            ]);
            exit;
        }

        $target = $found['items'][$targetIdx];
        mpd_add_and_play(normalize_path((string)($target['audio'] ?? ''), $projectRoot));

        echo json_encode([
            'ok'         => true,
            'podcast_id' => $found['podcast']['id'] ?? null,
            'episode_id' => $target['id']    ?? null,
            'idx'        => $targetIdx,
            'titre'      => $target['titre'] ?? null,
        ]);
        exit;
    }
}
?>
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Radio – Mon Petit France Inter</title>
<style>
body {
    background: #f7f3e9;
    font-family: Arial, sans-serif;
    text-align: center;
    padding-top: 40px;
}
h1 {
    font-size: 32px;
    color: #333;
}
button {
    width: 200px;
    height: 80px;
    margin: 20px;
    font-size: 28px;
    border-radius: 20px;
    border: none;
    background: #ff6f61;
    color: white;
    box-shadow: 0 4px 0 #d85a50;
}
button:active {
    transform: translateY(3px);
    box-shadow: 0 1px 0 #d85a50;
}
#status {
    margin-top: 30px;
    font-size: 22px;
    color: #444;
}
</style>
<script>
function send(action) {
    fetch("radio.php?action=" + action)
        .then(r => r.text())
        .then(updateStatus);
}

function updateStatus() {
    fetch("radio.php?action=status")
        .then(r => r.text())
        .then(text => {
            document.getElementById("status").innerText = text;
        });
}

setInterval(updateStatus, 1000);
</script>
</head>
<body>

<h1>🎧 Mon Petit France Inter</h1>

<button onclick="send('play')">▶️ Play</button>
<button onclick="send('pause')">⏸ Pause</button>
<br>
<button onclick="send('volup')">🔊 Volume +</button>
<button onclick="send('voldown')">🔉 Volume -</button>

<div id="status">Chargement…</div>

</body>
</html>
