<?php
// --- CONFIG ---
$stream = "https://icecast.radiofrance.fr/monpetitfranceinter-midfi.mp3";
$projectRoot = "/home/thomas/hechicero";

function mpd_command(string $command): string {
    $socket = @fsockopen('127.0.0.1', 6600, $errno, $errstr, 1.5);
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
    $socket = @fsockopen('127.0.0.1', 6600, $errno, $errstr, 1.5);
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

    if (str_starts_with($path, '/podcasts/')) {
        return 'podcasts/' . ltrim(substr($path, strlen('/podcasts/')), '/');
    }

    if (str_starts_with($path, $projectRoot . '/podcasts/')) {
        return 'podcasts/' . ltrim(substr($path, strlen($projectRoot . '/podcasts/')), '/');
    }

    return $path;
}

// --- ACTIONS ---
if (isset($_GET['action'])) {
    $action = $_GET['action'];

    if ($action === "play") {
        mpd_add_and_play($stream);
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

    if ($action === "voldown") {
        $status = mpd_status();
        $volume = isset($status['volume']) ? (int)$status['volume'] : 10;
        mpd_command('setvol ' . max(0, $volume - 5));
    }

    if ($action === "status") {
        echo mpd_status()['_raw'];
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
