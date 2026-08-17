<?php
// --- CONFIG ---
$stream = "https://icecast.radiofrance.fr/monpetitfranceinter-midfi.mp3";
$projectRoot = "/home/thomas/hechicero";
const CONFIG_PATH = '/home/thomas/hechicero/web/lecteur/config.json';
const AUDIO_STATE_PATH = '/home/thomas/hechicero/data/audio_output_state.json';
// TICKET pause/reprise webradio (2026-07-09) : mémorise l'URL du flux live
// en cours quand on le coupe pour une "pause", cf. is_webradio_uri() plus bas.
const RADIO_PAUSE_STATE_PATH = '/home/thomas/hechicero/data/radio_pause_state.json';
// TICKET-046 (favoris) : favori par épisode, clé composite "podcastId/episodeId"
// — les id d'épisode seuls (slug du titre, cf. rss_ingest/parser.py::normalize_id)
// ne sont pas garantis uniques entre deux podcasts différents.
const FAVORIS_PATH = '/home/thomas/hechicero/data/favoris.json';
// TICKET-046 : demande d'ouverture d'écran depuis un bouton physique (appui
// long GPIO16 → écran favoris). Pas de canal direct entre buttons_daemon.py
// (process Python séparé) et le navigateur — le daemon écrit sa demande ici,
// index.html la consomme par polling (même principe que now_playing pour
// TICKET-091).
const UI_REQUEST_PATH = '/home/thomas/hechicero/data/ui_request.json';
// TICKET-046 (extension du 2026-07-19) : contexte de navigation partagé
// entre l'écran tactile ET le bouton physique GPIO17/27, posé par
// index.html (action=set_nav_context) quand un épisode/webradio est lancé
// depuis l'écran favoris. Sans ce fichier, next_episode/prev_episode
// n'auraient aucun moyen de savoir qu'on veut naviguer dans la liste des
// favoris plutôt que dans le podcast d'origine — les deux déclencheurs
// (tap écran, appui physique) appellent la même action serveur, donc un seul
// contexte côté serveur suffit à couvrir les deux.
const NAV_CONTEXT_PATH = '/home/thomas/hechicero/data/nav_context.json';
// TICKET-127 (2026-08-17) — battement de cœur du kiosque. Le 2026-08-17 la page
// a CESSÉ d'exécuter du JavaScript entre 07:52:48 et 07:57:48, en laissant
// l'overlay de veille comme dernière image peinte : écran noir figé, tactile
// sans effet, alors que MPD, les boutons GPIO et wlr-randr allaient très bien
// (`Enabled: yes`). Rien ne permettait de dater cette mort ni de savoir dans
// quel état l'IHM se trouvait juste avant.
// Ce fichier est ÉCRASÉ à chaque battement (jamais en append) : il ne grossit
// pas, contrairement à data/sleep_debug.log qui a fini à plusieurs Mo avec des
// octets NUL après une coupure de courant. C'est un état, pas un journal.
const KIOSK_HEARTBEAT_PATH = '/home/thomas/hechicero/data/kiosk_heartbeat.json';

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

// La commande MPD "status" ne contient PAS le fichier en cours de lecture
// (contrairement à ce qu'on pourrait supposer) — seule "currentsong" le donne
// (champ "file"). Bug trouvé le 2026-07-08 : next_episode/prev_episode
// lisaient $status['file'] (toujours absent -> chaîne vide -> jamais de
// correspondance dans data.json -> "no_current_episode" en permanence, même
// en plein podcast).
function mpd_currentsong(): array {
    $raw = mpd_command('currentsong');
    $result = [];

    foreach (preg_split('/\r?\n/', $raw) as $line) {
        if (strpos($line, ': ') !== false) {
            [$key, $value] = explode(': ', $line, 2);
            $result[$key] = $value;
        }
    }

    $result['_raw'] = $raw;
    return $result;
}

// Bug pause/reprise webradio (2026-07-09) : sur un flux live, MPD "pause 1"
// coupe la sortie audio mais garde la connexion réseau ouverte et continue à
// bufferiser le flux en arrière-plan. À la reprise, "play" rejoue ce buffer
// devenu obsolète -> décalage grandissant, puis le serveur source finit
// souvent par fermer la connexion (client resté "en retard" trop longtemps)
// -> coupure du flux. Pas de souci pour un épisode de podcast (fichier
// local, pas de notion de direct à rattraper) — donc on ne cible que les
// URL http/https, cf. mpd_file_to_relative_audio() qui fait déjà cette
// distinction ailleurs dans ce fichier.
function is_webradio_uri(string $uri): bool {
    return str_starts_with($uri, 'http://') || str_starts_with($uri, 'https://');
}

function save_radio_pause_url(string $url): void {
    $dir = dirname(RADIO_PAUSE_STATE_PATH);
    if (!is_dir($dir)) {
        @mkdir($dir, 0755, true);
    }
    $tmp = RADIO_PAUSE_STATE_PATH . '.tmp';
    file_put_contents($tmp, json_encode(['url' => $url], JSON_UNESCAPED_SLASHES));
    rename($tmp, RADIO_PAUSE_STATE_PATH);
}

// Consomme (et efface) l'URL mémorisée par save_radio_pause_url(), s'il y en
// a une. Effacer immédiatement évite qu'un flag oublié fausse une reprise
// ultérieure sans rapport (ex: après un "play" manuel d'un autre flux).
function pop_radio_pause_url(): ?string {
    $data = read_json_radio(RADIO_PAUSE_STATE_PATH);
    if (empty($data['url'])) {
        return null;
    }
    @unlink(RADIO_PAUSE_STATE_PATH);
    return (string)$data['url'];
}

function clear_radio_pause_state(): void {
    @unlink(RADIO_PAUSE_STATE_PATH);
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
    // -> "/podcasts/x/y.mp3" (même format que le champ "audio" de data.json).
    // MPD peut renvoyer le champ "file" de currentsong avec OU sans le
    // préfixe "file://" selon la version/config (pas vérifié en conditions
    // réelles) — on gère les deux plutôt que de supposer un seul format.
    foreach (['file://' . $projectRoot, $projectRoot] as $prefix) {
        if (str_starts_with($mpdFile, $prefix)) {
            return substr($mpdFile, strlen($prefix));
        }
    }
    return $mpdFile; // webradio (URL http/https) ou chemin déjà étranger — pas d'épisode
}

// Retourne les épisodes d'un podcast dans le même ordre que getDisplayItems()
// côté JS (web/lecteur/index.html) : chapitres/episodes, ep1 en premier.
// L'ingest (rss_ingest/parser.py, TICKET-103bis, 2026-07-09) trie désormais
// les épisodes chronologiquement directement dans data.json : plus besoin
// d'inverser ici (cf. bug TINA : l'ordre brut du flux RSS n'était pas fiable
// sur toute sa longueur, un simple array_reverse() ne suffisait pas).
function podcast_display_items(array $podcast): array {
    return array_values($podcast['chapitres'] ?? $podcast['episodes'] ?? []);
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

// Favoris webradio (TICKET-046, extension du 2026-07-19) — les stations n'ont
// pas d'épisode, on favorise la station elle-même. Match par URL exacte
// (champ "file" de currentsong pour une webradio = l'URL du flux, pas de
// chemin local à convertir contrairement à mpd_file_to_relative_audio()).
function find_current_radio(string $url, array $data): ?array {
    foreach ($data['radios'] ?? [] as $radio) {
        if (($radio['url'] ?? null) === $url) {
            return $radio;
        }
    }
    return null;
}

// --- Contexte de navigation (TICKET-046, extension du 2026-07-19) ---
function read_nav_context(): array {
    $d = read_json_radio(NAV_CONTEXT_PATH);
    if (!is_array($d) || ($d['mode'] ?? 'normal') !== 'favoris' || empty($d['keys']) || empty($d['active_key'])) {
        return ['mode' => 'normal'];
    }
    return $d;
}

function write_nav_context(array $data): void {
    $dir = dirname(NAV_CONTEXT_PATH);
    if (!is_dir($dir)) {
        @mkdir($dir, 0755, true);
    }
    $tmp = NAV_CONTEXT_PATH . '.tmp';
    file_put_contents($tmp, json_encode($data, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE));
    rename($tmp, NAV_CONTEXT_PATH);
}

// Résout une clé favori ("episode:podcastId/episodeId" ou "radio:radioId")
// en cible jouable, à partir de data.json (jamais d'un état mémorisé) —
// même logique défensive que get_favoris : une clé qui ne correspond plus à
// rien (podcast supprimé/ré-ingéré, radio retirée) renvoie null plutôt que
// de planter la navigation.
function resolve_favori_key(string $key, array $data): ?array {
    if (str_starts_with($key, 'radio:')) {
        $radioId = substr($key, strlen('radio:'));
        foreach ($data['radios'] ?? [] as $r) {
            if (($r['id'] ?? null) === $radioId) {
                return ['type' => 'radio', 'radio_id' => $radioId, 'url' => $r['url'] ?? '', 'titre' => $r['name'] ?? ''];
            }
        }
        return null;
    }
    if (str_starts_with($key, 'episode:')) {
        $rest = substr($key, strlen('episode:'));
        $parts = explode('/', $rest, 2);
        $podcastId = $parts[0] ?? '';
        $episodeId = $parts[1] ?? '';
        foreach ($data['podcasts'] ?? [] as $podcast) {
            if (($podcast['id'] ?? null) !== $podcastId) continue;
            foreach (podcast_display_items($podcast) as $ch) {
                if (($ch['id'] ?? null) === $episodeId) {
                    return [
                        'type'       => 'episode',
                        'podcast_id' => $podcastId,
                        'episode_id' => $episodeId,
                        'audio'      => $ch['audio'] ?? '',
                        'titre'      => $ch['titre'] ?? '',
                    ];
                }
            }
            break;
        }
        return null;
    }
    return null;
}

// --- Favoris (TICKET-046) ---
// Clé composite préfixée par type ("episode:podcastId/episodeId" ou
// "radio:radioId") — les webradios n'ont pas d'episode_id, et un id de radio
// pourrait théoriquement entrer en collision avec un id de podcast sans ce
// préfixe.
function favori_key(string $type, string $a, string $b = ''): string {
    return $type . ':' . $a . ($b !== '' ? '/' . $b : '');
}

function read_favoris(): array {
    $d = read_json_radio(FAVORIS_PATH);
    return is_array($d) ? $d : [];
}

function write_favoris(array $data): void {
    $dir = dirname(FAVORIS_PATH);
    if (!is_dir($dir)) {
        @mkdir($dir, 0755, true);
    }
    $tmp = FAVORIS_PATH . '.tmp';
    file_put_contents($tmp, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE));
    rename($tmp, FAVORIS_PATH);
}

// --- Demande d'ouverture d'écran (TICKET-046, appui long bouton favori) ---
function write_ui_request(string $screen): void {
    $dir = dirname(UI_REQUEST_PATH);
    if (!is_dir($dir)) {
        @mkdir($dir, 0755, true);
    }
    $payload = ['screen' => $screen, 'ts' => (int) round(microtime(true) * 1000)];
    $tmp = UI_REQUEST_PATH . '.tmp';
    file_put_contents($tmp, json_encode($payload, JSON_UNESCAPED_SLASHES));
    rename($tmp, UI_REQUEST_PATH);
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
        clear_radio_pause_state(); // nouvelle lecture explicite : tout flag de reprise en attente est obsolète
        mpd_add_and_play($playUrl);
    }

    if ($action === "pause") {
        $status = mpd_status();
        $state = $status['state'] ?? '';

        if ($state === 'play') {
            $current = mpd_currentsong();
            $file = $current['file'] ?? '';
            if (is_webradio_uri($file)) {
                // Voir is_webradio_uri() : on coupe complètement plutôt que de
                // laisser MPD bufferiser le direct pendant la pause.
                save_radio_pause_url($file);
                mpd_command('stop');
            } else {
                mpd_command('pause 1');
            }
        } else {
            $radioUrl = pop_radio_pause_url();
            if ($radioUrl !== null) {
                mpd_add_and_play($radioUrl); // reconnexion fraîche au direct, pas de reprise du buffer figé
            } else {
                mpd_command('play');
            }
        }
    }

    if ($action === "playfile" && isset($_GET['path'])) {
        $path = normalize_path((string)$_GET['path'], $projectRoot);
        if ($path !== '') {
            clear_radio_pause_state(); // idem : sélection explicite d'un épisode invalide un flag de reprise webradio
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

    // Recherche relative — TICKET-091, maintien des boutons physiques
    // suivant/précédent (avance/recul de quelques secondes dans l'épisode en
    // cours, plutôt qu'un saut d'épisode entier). MPD accepte "seekcur +N"/
    // "seekcur -N" pour une recherche relative à la position actuelle — mais
    // (int)$_GET['delta'] suffit à reconstruire le signe correctement tant
    // qu'on rebâtit la chaîne nous-même (un simple cast perdrait le signe
    // "+" pour les valeurs positives si on utilisait directement le paramètre
    // brut sans le repasser par (int) puis reformater).
    if ($action === 'seek_relative' && isset($_GET['delta'])) {
        $delta = (int)$_GET['delta'];
        $sign  = $delta >= 0 ? '+' : '';
        mpd_command('seekcur ' . $sign . $delta);
    }

    // TICKET-102 (récidive 2026-07-08 soir) — traceur temporaire pour l'écran
    // de veille : le JS (index.html) appelle cette action à chaque appel de
    // resetSleepTimer()/activateSleep()/wakeUp()/applySleepConfig() pour
    // qu'on puisse observer sur le Pi (tail -f) ce qui réinitialise le timer
    // au moment exact où le bug se reproduit, plutôt que de re-diagnostiquer
    // à l'aveugle après coup. Écrit en pur append, jamais de lecture/relecture
    // ni de verrou — pas critique si une écriture se perd occasionnellement.
    // À retirer (ou a minima désactiver) une fois la cause trouvée : ce n'est
    // pas un outil destiné à rester en prod indéfiniment.
    if ($action === 'sleep_log') {
        header('Content-Type: application/json; charset=utf-8');
        $event = (string)($_GET['event'] ?? '?');
        $extra = (string)($_GET['extra'] ?? '');
        $line  = sprintf("[%s] %s %s\n", date('Y-m-d H:i:s'), $event, $extra);
        @file_put_contents($projectRoot . '/data/sleep_debug.log', $line, FILE_APPEND | LOCK_EX);
        echo json_encode(['ok' => true]);
        exit;
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

    // Navigation épisode/webradio — TICKET-091 (boutons GPIO physiques
    // next/précédent) puis étendu TICKET-046 le 2026-07-19 (navigation au
    // sein des favoris) : quand data/nav_context.json indique le mode
    // "favoris" (posé par index.html via set_nav_context lorsqu'un
    // épisode/webradio est lancé depuis l'écran favoris), next/précédent
    // avancent dans CETTE liste plutôt que dans le podcast d'origine — pour
    // le bouton physique ET le tap écran, puisque les deux appellent cette
    // même action serveur (le bouton physique n'a pas de canal direct vers
    // le navigateur, donc un contexte côté serveur est la seule façon de
    // lui faire connaître "on navigue dans les favoris").
    // 'now_playing' : lecture seule, pour que l'IHM se resynchronise
    // périodiquement — répond aussi pour une webradio désormais (avant
    // TICKET-046 ça ne couvrait que les épisodes de podcast).
    if ($action === 'now_playing' || $action === 'next_episode' || $action === 'prev_episode') {
        header('Content-Type: application/json; charset=utf-8');

        $current = mpd_currentsong();
        $mpdFile = $current['file'] ?? '';
        $data    = read_json_radio($projectRoot . '/web/lecteur/data.json');
        $navCtx  = read_nav_context();
        $navMode = $navCtx['mode'] ?? 'normal';

        if ($action === 'now_playing') {
            if (is_webradio_uri($mpdFile)) {
                $radio = find_current_radio($mpdFile, $data);
                if ($radio === null) {
                    echo json_encode(['ok' => false, 'reason' => 'no_current_radio']);
                    exit;
                }
                echo json_encode([
                    'ok'         => true,
                    'type'       => 'radio',
                    'radio_id'   => $radio['id'],
                    'titre'      => $radio['name'] ?? null,
                    'nav_mode'   => $navMode,
                    'nav_keys'   => $navCtx['keys'] ?? [],
                    'nav_active' => $navCtx['active_key'] ?? null,
                ]);
                exit;
            }

            $relative = mpd_file_to_relative_audio($mpdFile, $projectRoot);
            $found = find_current_episode($relative, $data);
            if ($found === null) {
                // Rien en cours qui corresponde à un épisode de podcast ni une
                // webradio connue (MPD à l'arrêt, piste inconnue) — pas une
                // erreur en soi.
                echo json_encode(['ok' => false, 'reason' => 'no_current_episode']);
                exit;
            }
            echo json_encode([
                'ok'         => true,
                'type'       => 'episode',
                'podcast_id' => $found['podcast']['id']  ?? null,
                'episode_id' => $found['chapter']['id']  ?? null,
                'idx'        => $found['idx'],
                'titre'      => $found['chapter']['titre'] ?? null,
                'nav_mode'   => $navMode,
                'nav_keys'   => $navCtx['keys'] ?? [],
                'nav_active' => $navCtx['active_key'] ?? null,
            ]);
            exit;
        }

        // next_episode / prev_episode à partir d'ici.
        $delta = $action === 'next_episode' ? 1 : -1;

        if ($navMode === 'favoris') {
            $keys = $navCtx['keys'];
            $pos  = array_search($navCtx['active_key'], $keys, true);
            if ($pos === false) {
                echo json_encode(['ok' => false, 'reason' => 'invalid_nav_context']);
                exit;
            }
            $targetPos = $pos + $delta;
            if ($targetPos < 0 || $targetPos >= count($keys)) {
                echo json_encode(['ok' => false, 'reason' => 'out_of_bounds', 'nav_mode' => 'favoris']);
                exit;
            }
            $targetKey = $keys[$targetPos];
            $target = resolve_favori_key($targetKey, $data);
            if ($target === null) {
                echo json_encode(['ok' => false, 'reason' => 'broken_favori', 'nav_mode' => 'favoris']);
                exit;
            }

            if ($target['type'] === 'radio') {
                clear_radio_pause_state();
                mpd_add_and_play((string)$target['url']);
            } else {
                mpd_add_and_play(normalize_path((string)$target['audio'], $projectRoot));
            }

            $navCtx['active_key'] = $targetKey;
            write_nav_context($navCtx);

            echo json_encode(array_merge(['ok' => true, 'nav_mode' => 'favoris', 'idx' => $targetPos], $target));
            exit;
        }

        // Mode normal — comportement historique, scope podcast uniquement.
        $relative = mpd_file_to_relative_audio($mpdFile, $projectRoot);
        $found = find_current_episode($relative, $data);
        if ($found === null) {
            echo json_encode(['ok' => false, 'reason' => 'no_current_episode']);
            exit;
        }

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

    // Pose/efface le contexte de navigation favoris (TICKET-046, extension
    // du 2026-07-19) — appelé par index.html au clic initial sur l'écran
    // favoris, à chaque suivant/précédent (pour garder active_key à jour),
    // et remis à "normal" dès qu'on relance depuis un écran classique.
    if ($action === 'set_nav_context') {
        header('Content-Type: application/json; charset=utf-8');
        $mode = ($_GET['mode'] ?? 'normal') === 'favoris' ? 'favoris' : 'normal';

        if ($mode === 'normal') {
            write_nav_context(['mode' => 'normal']);
            echo json_encode(['ok' => true, 'mode' => 'normal']);
            exit;
        }

        $keysRaw = $_GET['keys'] ?? [];
        $keys = is_array($keysRaw) ? array_values(array_filter($keysRaw, fn($k) => is_string($k) && $k !== '')) : [];
        $active = (string)($_GET['active'] ?? '');

        if (!$keys || $active === '' || !in_array($active, $keys, true)) {
            echo json_encode(['ok' => false, 'reason' => 'invalid_context']);
            exit;
        }

        write_nav_context(['mode' => 'favoris', 'keys' => $keys, 'active_key' => $active]);
        echo json_encode(['ok' => true, 'mode' => 'favoris']);
        exit;
    }

    // Favoris (TICKET-046) — bascule le favori sur ce qui est réellement en
    // cours d'écoute (résolu comme next_episode/prev_episode, jamais un état
    // mémorisé). Deux cas : webradio (favori = la station elle-même, pas de
    // notion d'épisode) ou épisode de podcast. Re-appuyer sur le même
    // élément retire le favori (toggle symétrique, même code des deux côtés).
    // Sans effet si rien ne joue ou si ni l'un ni l'autre ne correspond :
    // ok:false, même convention que next_episode/prev_episode.
    if ($action === 'toggle_favori') {
        header('Content-Type: application/json; charset=utf-8');

        $current = mpd_currentsong();
        $mpdFile = $current['file'] ?? '';
        $data = read_json_radio($projectRoot . '/web/lecteur/data.json');
        $favoris = read_favoris();

        if (is_webradio_uri($mpdFile)) {
            $radio = find_current_radio($mpdFile, $data);
            $radioId = $radio['id'] ?? '';
            if ($radio === null || $radioId === '') {
                echo json_encode(['ok' => false, 'reason' => 'no_current_radio']);
                exit;
            }

            $key = favori_key('radio', $radioId);
            if (isset($favoris[$key])) {
                unset($favoris[$key]);
                $isFavori = false;
            } else {
                $favoris[$key] = ['type' => 'radio', 'radio_id' => $radioId, 'added_at' => date('c')];
                $isFavori = true;
            }
            write_favoris($favoris);

            echo json_encode(['ok' => true, 'favori' => $isFavori, 'type' => 'radio', 'radio_id' => $radioId]);
            exit;
        }

        $relative = mpd_file_to_relative_audio($mpdFile, $projectRoot);
        $found = find_current_episode($relative, $data);
        if ($found === null) {
            echo json_encode(['ok' => false, 'reason' => 'no_current_episode']);
            exit;
        }

        $podcastId = $found['podcast']['id'] ?? '';
        $episodeId = $found['chapter']['id'] ?? '';
        if ($podcastId === '' || $episodeId === '') {
            echo json_encode(['ok' => false, 'reason' => 'no_current_episode']);
            exit;
        }

        $key = favori_key('episode', $podcastId, $episodeId);
        if (isset($favoris[$key])) {
            unset($favoris[$key]);
            $isFavori = false;
        } else {
            $favoris[$key] = [
                'type'       => 'episode',
                'podcast_id' => $podcastId,
                'episode_id' => $episodeId,
                'added_at'   => date('c'),
            ];
            $isFavori = true;
        }
        write_favoris($favoris);

        echo json_encode([
            'ok'         => true,
            'favori'     => $isFavori,
            'type'       => 'episode',
            'podcast_id' => $podcastId,
            'episode_id' => $episodeId,
        ]);
        exit;
    }

    // Retrait explicite (admin) — cible une clé précise plutôt que "ce qui
    // joue en ce moment". La clé vient telle quelle de get_favoris (champ
    // "key"), pas besoin de la reconstruire côté appelant.
    if ($action === 'remove_favori' && isset($_GET['key'])) {
        header('Content-Type: application/json; charset=utf-8');
        $key = (string)$_GET['key'];
        $favoris = read_favoris();
        $existed = isset($favoris[$key]);
        unset($favoris[$key]);
        write_favoris($favoris);
        echo json_encode(['ok' => true, 'removed' => $existed]);
        exit;
    }

    // Liste enrichie des favoris (titre/jaquette + podcast ou webradio),
    // utilisée par l'écran dédié tactile ET par l'admin. Un favori dont
    // l'épisode/la station a disparu de data.json (podcast supprimé/
    // ré-ingéré, radio retirée par l'admin) est filtré plutôt que planté —
    // data.json est régénéré par l'ingestion RSS, pas une source stable dans
    // le temps.
    if ($action === 'get_favoris') {
        header('Content-Type: application/json; charset=utf-8');
        $favoris = read_favoris();
        $data = read_json_radio($projectRoot . '/web/lecteur/data.json');
        $podcastsById = [];
        foreach ($data['podcasts'] ?? [] as $p) {
            if (isset($p['id'])) $podcastsById[$p['id']] = $p;
        }
        $radiosById = [];
        foreach ($data['radios'] ?? [] as $r) {
            if (isset($r['id'])) $radiosById[$r['id']] = $r;
        }

        $enriched = [];
        foreach ($favoris as $key => $entry) {
            $type = $entry['type'] ?? 'episode';

            if ($type === 'radio') {
                $radio = $radiosById[$entry['radio_id'] ?? ''] ?? null;
                if ($radio === null) continue;
                $enriched[] = [
                    'key'           => $key,
                    'type'          => 'radio',
                    'radio_id'      => $radio['id'],
                    'titre'         => $radio['name'] ?? '',
                    'podcast_titre' => 'Webradio',
                    'image'         => $radio['image'] ?? ($radio['image_url'] ?? ''),
                    'url'           => $radio['url'] ?? '',
                    'added_at'      => $entry['added_at'] ?? '',
                ];
                continue;
            }

            $podcast = $podcastsById[$entry['podcast_id'] ?? ''] ?? null;
            if ($podcast === null) continue;
            $chapter = null;
            foreach (podcast_display_items($podcast) as $ch) {
                if (($ch['id'] ?? null) === ($entry['episode_id'] ?? null)) { $chapter = $ch; break; }
            }
            if ($chapter === null) continue;

            $enriched[] = [
                'key'           => $key,
                'type'          => 'episode',
                'podcast_id'    => $podcast['id'],
                'episode_id'    => $chapter['id'],
                'podcast_titre' => $podcast['titre'] ?? '',
                'titre'         => $chapter['titre'] ?? '',
                'image'         => $chapter['image'] ?? ($podcast['image'] ?? ''),
                'audio'         => $chapter['audio'] ?? '',
                'duree'         => $chapter['duree'] ?? null,
                'added_at'      => $entry['added_at'] ?? '',
            ];
        }

        usort($enriched, fn($a, $b) => strcmp($b['added_at'], $a['added_at']));
        echo json_encode(['ok' => true, 'favoris' => $enriched]);
        exit;
    }

    // Demande d'ouverture d'écran (TICKET-046, appui long bouton favori
    // GPIO16). Écrit seulement — c'est index.html qui consomme via
    // get_ui_request (polling).
    if ($action === 'request_screen' && isset($_GET['screen'])) {
        header('Content-Type: application/json; charset=utf-8');
        write_ui_request((string)$_GET['screen']);
        echo json_encode(['ok' => true]);
        exit;
    }

    if ($action === 'get_ui_request') {
        header('Content-Type: application/json; charset=utf-8');
        $d = read_json_radio(UI_REQUEST_PATH);
        echo json_encode(['screen' => $d['screen'] ?? null, 'ts' => $d['ts'] ?? 0]);
        exit;
    }

    // Battement de cœur du kiosque (TICKET-127). Écriture ATOMIQUE et par
    // ÉCRASEMENT : c'est un état courant, pas un historique — le fichier reste
    // à quelques centaines d'octets pour toujours.
    // ⚠️ Ne déclenche aucune action : ce point d'entrée doit rester purement
    // passif. Il est appelé toutes les 15 s par une page dont on soupçonne
    // qu'elle meurt ; tout effet de bord ici brouillerait la mesure.
    if ($action === 'kiosk_beat') {
        header('Content-Type: application/json; charset=utf-8');
        // ⚠️ PIÈGE D'HORLOGE (constaté le 2026-08-17) : ce PHP tourne en UTC,
        // alors que `data/screen_dpms.log` (shell `date`) et
        // `data/kiosk_freeze.log` (Python `datetime.now()`) écrivent en heure
        // locale. Deux heures d'écart entre les trois journaux qu'on croise
        // justement pendant une panne. `data/sleep_debug.log` est en UTC lui
        // aussi (même `date()` PHP) — c'est pour ça que son « 07:52:48 »
        // correspond à 09:52:48 sur l'horloge de la maison.
        // On expose donc les deux : `ts` en epoch (sans ambiguïté, c'est lui
        // que le guetteur compare), `iso` en UTC, et `local` dans le même
        // format que les autres journaux, pour pouvoir corréler à l'œil.
        // Rien n'est changé globalement ici : toucher au fuseau de radio.php
        // affecterait tous ses horodatages.
        $localNow = (new DateTime('now', new DateTimeZone('Europe/Paris')))->format('Y-m-d H:i:s');
        $payload = [
            'ts'          => (int) round(microtime(true) * 1000),
            'iso'         => date('c'),
            'local'       => $localNow,
            'overlay'     => ($_GET['overlay'] ?? '0') === '1',   // écran de veille affiché ?
            'screen'      => substr((string)($_GET['screen'] ?? '?'), 0, 32),
            'page_age_s'  => (int)($_GET['page_age_s'] ?? -1),    // secondes depuis le chargement de la page
            'beats'       => (int)($_GET['beats'] ?? -1),         // nº de battement depuis le chargement
            'mpd_state'   => substr((string)($_GET['mpd_state'] ?? '?'), 0, 16),
        ];
        $tmp = KIOSK_HEARTBEAT_PATH . '.tmp';
        if (@file_put_contents($tmp, json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . "\n") !== false) {
            @rename($tmp, KIOSK_HEARTBEAT_PATH);
            @chmod(KIOSK_HEARTBEAT_PATH, 0664);
        }
        echo json_encode(['ok' => true]);
        exit;
    }

    // TICKET-114 — signature de data.json, pour savoir si le catalogue a changé
    // sans retransférer les ~700 Ko du fichier. Deux stat() suffisent, donc
    // c'est assez léger pour un polling à 10 s côté kiosque.
    // Pourquoi mtime ET size : mtime seul rate une réécriture dans la même
    // seconde, size seule rate un remplacement de même taille. Ensemble ils
    // couvrent les cas réels de l'ingest.
    if ($action === 'data_version') {
        header('Content-Type: application/json; charset=utf-8');
        $dataPath = __DIR__ . '/data.json';
        clearstatcache(true, $dataPath);
        if (!file_exists($dataPath)) {
            echo json_encode(['mtime' => 0, 'size' => 0]);
            exit;
        }
        echo json_encode([
            'mtime' => (int)@filemtime($dataPath),
            'size'  => (int)@filesize($dataPath),
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
