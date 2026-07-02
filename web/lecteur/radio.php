<?php
// --- CONFIG ---
$stream = "https://icecast.radiofrance.fr/monpetitfranceinter-midfi.mp3";
$projectRoot = "/home/thomas/hechicero";
const CONFIG_PATH = '/home/thomas/hechicero/web/lecteur/config.json';

function read_json_radio(string $path): array {
    if (!file_exists($path)) {
        return [];
    }
    $d = json_decode(file_get_contents($path), true);
    return is_array($d) ? $d : [];
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
        mpd_command('setvol ' . min(50, $volume + 5));
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

    // ⚠️ TEMPORAIRE — bascule manuelle HP/casque en attendant le câblage LM393 (TICKET-031)
    // output 0 = HiFiBerry (haut-parleurs), output 1 = KT USB Audio (casque)
    if ($action === 'get_output') {
        header('Content-Type: application/json; charset=utf-8');
        $raw  = mpd_command('outputs');
        // outputid 1 activé → mode casque ; sinon → mode hp
        $mode = preg_match('/outputid: 1\s+outputname:[^\n]+\s+outputenabled: 1/s', $raw) ? 'casque' : 'hp';
        echo json_encode(['mode' => $mode]);
        exit;
    }

    if ($action === 'set_output' && isset($_GET['mode'])) {
        header('Content-Type: application/json; charset=utf-8');
        if ($_GET['mode'] === 'casque') {
            mpd_batch(['enableoutput 1', 'disableoutput 0']);
        } else {
            mpd_batch(['enableoutput 0', 'disableoutput 1']);
        }
        echo json_encode(['ok' => true, 'mode' => $_GET['mode']]);
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
