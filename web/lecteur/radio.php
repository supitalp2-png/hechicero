<?php
// --- CONFIG ---
$stream = "https://icecast.radiofrance.fr/monpetitfranceinter-midfi.mp3";

// --- ACTIONS ---
if (isset($_GET['action'])) {
    $action = $_GET['action'];

    if ($action === "play") {
        exec("mpc clear");
        exec("mpc add $stream");
        exec("mpc play");
    }

    if ($action === "pause") {
        exec("mpc toggle");
    }

    if ($action === "volup") {
        exec("mpc volume +5");
    }

    if ($action === "voldown") {
        exec("mpc volume -5");
    }

    if ($action === "status") {
        $status = shell_exec("mpc status");
        echo $status;
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
