<?php
// ============================================================
// Hechicero — Interface d'administration
// Accès : http://<rpi>/
// Réseau local uniquement — pas d'authentification requise
// ============================================================

define('PROJECT_ROOT',  is_dir('/home/thomas/hechicero') ? '/home/thomas/hechicero' : dirname(__DIR__));
define('PODCASTS_JSON', PROJECT_ROOT . '/data/podcasts.json');
define('DATA_JSON',     PROJECT_ROOT . '/web/lecteur/data.json');
define('CONFIG_JSON',   PROJECT_ROOT . '/web/lecteur/config.json');
define('STATUS_JSON',   PROJECT_ROOT . '/web/status.json');   // servi à /status.json
define('BATTERY_STATS_JSON',   PROJECT_ROOT . '/data/battery_stats.json');
define('BATTERY_HISTORY_JSON', PROJECT_ROOT . '/data/battery_history.json');
define('LAST_SESSION_JSON',    PROJECT_ROOT . '/data/last_session.json');
define('TRACKING_DB',   PROJECT_ROOT . '/data/tracking.db');
define('INGEST_LOG',    '/tmp/hechicero_ingest.log');
define('INGEST_PID',    '/tmp/hechicero_ingest.pid');
define('INGEST_SCRIPT', PROJECT_ROOT . '/scripts/rss_ingest/ingest.py');
define('BACKUP_STATE_JSON', PROJECT_ROOT . '/data/backup_state.json');
define('BACKUP_SCRIPT',     PROJECT_ROOT . '/scripts/backup_manager.py');
define('BACKUP_LOG',        '/tmp/hechicero_backup_validate.log');
define('BACKUP_PID',        '/tmp/hechicero_backup_validate.pid');

// ── Helpers ──────────────────────────────────────────────────

function read_json(string $path): array {
    if (!file_exists($path)) return [];
    $d = json_decode(file_get_contents($path), true);
    return is_array($d) ? $d : [];
}

function write_json_atomic(string $path, array $data): bool {
    $dir = dirname($path);
    if (!is_dir($dir)) mkdir($dir, 0755, true);
    $tmp = $path . '.tmp';
    $ok  = file_put_contents($tmp, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
    if ($ok === false) return false;
    return rename($tmp, $path);
}

function battery_resume_payload(): array {
  $resume = read_json(LAST_SESSION_JSON);
  if (($resume['shutdown_reason'] ?? null) !== 'battery_critical') return [];
  return $resume;
}

function pid_alive(string $f): bool {
    if (!file_exists($f)) return false;
    $pid = (int)file_get_contents($f);
    return $pid > 0 && file_exists('/proc/' . $pid);
}

function slugify(string $s): string {
    $s = mb_strtolower($s, 'UTF-8');
    $s = strtr($s, ['à'=>'a','â'=>'a','é'=>'e','è'=>'e','ê'=>'e','ë'=>'e','î'=>'i','ï'=>'i',
                     'ô'=>'o','ù'=>'u','û'=>'u','ü'=>'u','ç'=>'c','œ'=>'oe','æ'=>'ae',
                     'á'=>'a','í'=>'i','ó'=>'o','ú'=>'u','ñ'=>'n']);
    return substr(preg_replace('/[^a-z0-9]+/', '', $s), 0, 40);
}

// ── MPD ──────────────────────────────────────────────────────

function mpd_cmd(string $cmd): string {
    $s = @fsockopen('unix:///run/mpd/socket', 0, $e1, $e2, 1.5);
    if (!$s) return '';
    stream_set_timeout($s, 2);
    fgets($s);
    fwrite($s, $cmd . "\n");
    $r = '';
    while (!feof($s)) {
        $l = fgets($s);
        if ($l === false) break;
        $r .= $l;
        if (trim($l) === 'OK' || str_starts_with($l, 'ACK')) break;
    }
    fclose($s);
    return $r;
}

function mpd_status(): array {
    $out = [];
    foreach (preg_split('/\r?\n/', mpd_cmd('status')) as $l) {
        if (($p = strpos($l, ': ')) !== false)
            $out[trim(substr($l, 0, $p))] = trim(substr($l, $p + 2));
    }
    return $out;
}

// ── Radios ────────────────────────────────────────────────────

function get_radios(): array {
    $d = read_json(PODCASTS_JSON);
    return $d['radios'] ?? [];
}

function save_radios(array $radios): bool {
    $d = read_json(PODCASTS_JSON);
    $d['radios'] = array_values($radios);
    return write_json_atomic(PODCASTS_JSON, $d);
}

// Variante avec message d'erreur explicite
function save_radios_r(array $radios): array {
    $d = read_json(PODCASTS_JSON);
    $d['radios'] = array_values($radios);
    if (!is_writable(PODCASTS_JSON) && !is_writable(dirname(PODCASTS_JSON))) {
        return ['ok'=>false,'msg'=>
            'Fichier non modifiable par le serveur web. ' .
            'Sur le Pi : sudo chown www-data:www-data ' . PODCASTS_JSON .
            ' && sudo chmod g+w ' . dirname(PODCASTS_JSON)];
    }
    $ok = write_json_atomic(PODCASTS_JSON, $d);
    return ['ok'=>$ok,'msg'=>$ok?'':'Écriture échouée — vérifiez les permissions sur ' . PODCASTS_JSON];
}

// Propage la liste des radios dans data.json immédiatement (sans attendre l'ingest).
// Les radios n'ont pas de RSS ni de téléchargement — elles doivent être instantanées sur le lecteur.
function sync_radios_to_data_json(): void {
    if (!file_exists(DATA_JSON)) return;
    $radios = get_radios();
    $data   = read_json(DATA_JSON);
    $data['radios'] = $radios;
    write_json_atomic(DATA_JSON, $data);
}

// Exécute curl en ligne de commande (évite la dépendance à l'extension PHP curl)
function shell_curl(string $url, array $opts = []): array {
    if (!@shell_exec('which curl 2>/dev/null')) {
        return ['ok'=>false,'code'=>0,'body'=>'','msg'=>"curl n'est pas installé sur le Pi — sudo apt install curl"];
    }
    $timeout  = $opts['timeout']  ?? 15;
    $connect  = $opts['connect']  ?? 6;
    $head     = !empty($opts['head']);
    $range    = $opts['range']    ?? null;   // ex: '0-4095'
    $out_file = $opts['out_file'] ?? null;
    $safe_url = escapeshellarg($url);

    $cmd = "curl -s -L --max-time {$timeout} --connect-timeout {$connect} -A 'Hechicero/1.0'";
    if ($head)      $cmd .= ' -I';
    if ($range)     $cmd .= ' -r ' . escapeshellarg($range);
    if ($out_file)  $cmd .= ' -o ' . escapeshellarg($out_file);
    $cmd .= " -w '\n__META__%{http_code}__%{content_type}__%{size_download}' $safe_url 2>/dev/null";

    $raw  = (string)shell_exec($cmd);
    $sep  = strrpos($raw, "\n__META__");
    $body = $sep !== false ? substr($raw, 0, $sep) : $raw;
    $meta = $sep !== false ? explode('__', substr($raw, $sep + 9)) : [];
    $code  = (int)($meta[0] ?? 0);
    $ctype = strtolower(trim($meta[1] ?? ''));
    $size  = (int)($meta[2] ?? 0);

    return ['ok'=>($code>0 && $code<400),'code'=>$code,'ctype'=>$ctype,'size'=>$size,'body'=>$body];
}

// Télécharge une image depuis une URL distante et la sauvegarde localement
function download_radio_image(string $url, string $id): array {
    $dir  = PROJECT_ROOT . '/web/lecteur/images/radio/';
    $file = $dir . $id . '.jpg';
    $web  = 'images/radio/' . $id . '.jpg';
    if (!is_dir($dir) && !@mkdir($dir, 0755, true)) {
        return ['ok'=>false,'msg'=>"Impossible de créer le dossier images/radio/. Sur le Pi : sudo mkdir -p $dir && sudo chown www-data $dir"];
    }
    if (!is_writable($dir)) {
        return ['ok'=>false,'msg'=>"Dossier images/radio/ non modifiable. Sur le Pi : sudo chown www-data $dir"];
    }
    // Télécharger directement dans le fichier cible via curl
    $r = shell_curl($url, ['timeout'=>20,'connect'=>8,'out_file'=>$file]);
    if (isset($r['msg'])) return ['ok'=>false,'msg'=>$r['msg']];  // curl absent
    if ($r['code'] === 0)  return ['ok'=>false,'msg'=>"L'image est inaccessible depuis le Pi (vérifiez que l'URL est publique)"];
    if ($r['code'] >= 400) return ['ok'=>false,'msg'=>"Le serveur répond HTTP {$r['code']} — l'URL est-elle accessible publiquement ?"];
    if ($r['size'] === 0 || !file_exists($file)) return ['ok'=>false,'msg'=>"Fichier vide reçu — l'URL ne renvoie peut-être pas une image"];
    // Vérifier le type réel du fichier téléchargé
    $finfo = new \finfo(FILEINFO_MIME_TYPE);
    $mime  = $finfo->file($file);
    if (!str_starts_with($mime, 'image/')) {
        @unlink($file);
        return ['ok'=>false,'msg'=>"Ce fichier n'est pas une image (type reçu : $mime). Vérifie l'URL."];
    }
    $kb = round($r['size'] / 1024);
    return ['ok'=>true,'path'=>$web,'msg'=>"Image téléchargée ($kb Ko)"];
}

// ── API ───────────────────────────────────────────────────────

if (isset($_GET['action'])) {
    header('Content-Type: application/json; charset=utf-8');
    $a = $_GET['action'];

    // ── Statut système
    if ($a === 'status') {
        $b     = read_json(STATUS_JSON);
        $mpd   = mpd_status();
        $free  = @disk_free_space(PROJECT_ROOT) ?: 0;
        $total = @disk_total_space(PROJECT_ROOT) ?: 0;
        echo json_encode([
            'battery' => [
                'percent'    => isset($b['percent'])    ? (float)$b['percent']    : null,
                'voltage_v'  => isset($b['voltage_v'])  ? (float)$b['voltage_v']  : null,
                'current_ma' => isset($b['current_ma']) ? (float)$b['current_ma'] : null,
                'state'      => $b['state'] ?? '—',
            ],
            'mpd'  => ['state' => $mpd['state'] ?? 'unknown', 'volume' => $mpd['volume'] ?? '?'],
            'disk' => [
                'free_gb'  => $total > 0 ? round($free  / 1073741824, 1) : 0,
                'total_gb' => $total > 0 ? round($total / 1073741824, 1) : 0,
                'used_pct' => $total > 0 ? round(($total - $free) / $total * 100) : 0,
            ],
            'ingest_running' => pid_alive(INGEST_PID),
            'last_ingest_ts' => file_exists(DATA_JSON) ? filemtime(DATA_JSON) : null,
        ]);
        exit;
    }

      if ($a === 'battery_data') {
        echo json_encode([
          'stats' => read_json(BATTERY_STATS_JSON),
          'history' => read_json(BATTERY_HISTORY_JSON),
          'resume' => battery_resume_payload(),
        ]);
        exit;
      }

      if ($a === 'battery_resume') {
        echo json_encode(battery_resume_payload());
        exit;
      }

      if ($a === 'clear_battery_resume') {
        $ok = true;
        if (file_exists(LAST_SESSION_JSON)) $ok = @unlink(LAST_SESSION_JSON);
        echo json_encode(['ok' => (bool)$ok]);
        exit;
      }

    // ── Podcasts
    if ($a === 'get_podcasts') {
        $cfg    = read_json(PODCASTS_JSON);
        $data   = read_json(DATA_JSON);
        $counts = [];
        foreach ($data['podcasts'] ?? [] as $p) $counts[$p['id']] = count($p['chapitres'] ?? []);
        $list = $cfg['podcasts'] ?? [];
        foreach ($list as &$p) $p['episode_count'] = $counts[$p['id']] ?? 0;
        echo json_encode($list);
        exit;
    }

    if ($a === 'toggle_podcast' && isset($_GET['id'], $_GET['enabled'])) {
        $cfg = read_json(PODCASTS_JSON);
        $en  = $_GET['enabled'] === '1';
        foreach ($cfg['podcasts'] as &$p) if ($p['id'] === $_GET['id']) { $p['enabled'] = $en; break; }
        echo json_encode(['ok' => write_json_atomic(PODCASTS_JSON, $cfg)]);
        exit;
    }

    if ($a === 'add_podcast') {
        $label = trim($_POST['label'] ?? '');
        $rss   = trim($_POST['rss']   ?? '');
        $lang  = in_array($_POST['lang'] ?? 'fr', ['fr','es']) ? $_POST['lang'] : 'fr';
        $max   = (int)($_POST['max_episodes'] ?? 10);
        $max   = $max <= 0 ? 999 : max(1, $max);
        if (!$label || !$rss) { echo json_encode(['ok'=>false,'msg'=>'Titre et RSS requis']); exit; }
        $id  = slugify($label);
        $cfg = read_json(PODCASTS_JSON);
        foreach ($cfg['podcasts'] ?? [] as $p) if ($p['id'] === $id) { echo json_encode(['ok'=>false,'msg'=>'ID déjà existant : '.$id]); exit; }
        $cfg['podcasts'][] = ['id'=>$id,'label'=>$label,'rss'=>$rss,'enabled'=>true,'language'=>$lang,'image'=>'images/'.$id.'.jpg','max_episodes'=>$max];
        $ok = write_json_atomic(PODCASTS_JSON, $cfg);
        // Déclenche immédiatement un ingest ciblé sur ce podcast en arrière-plan
        if ($ok && !pid_alive(INGEST_PID)) {
            // umask 002 (comme le cron thomas, TICKET-027) : sans ça, www-data crée le
            // dossier du podcast en 755 (non group-writable), et toute ingestion
            // ultérieure lancée par thomas (SSH manuel ou cron) échoue en Permission
            // denied sur les .tmp — bug trouvé le 2026-07-18 sur "lesexplorateursdelunivers".
            $cmd = 'umask 002 && python3 ' . escapeshellarg(INGEST_SCRIPT)
                 . ' --podcast ' . escapeshellarg($id)
                 . ' >> ' . escapeshellarg(INGEST_LOG) . ' 2>&1 & echo $!';
            $pid = trim((string)shell_exec($cmd));
            if ($pid) file_put_contents(INGEST_PID, $pid);
        }
        echo json_encode(['ok' => $ok, 'id' => $id]);
        exit;
    }

    if ($a === 'edit_podcast' && isset($_GET['id'])) {
        $cfg = read_json(PODCASTS_JSON);
        foreach ($cfg['podcasts'] as &$p) {
            if ($p['id'] !== $_GET['id']) continue;
            if (isset($_POST['label']) && trim($_POST['label'])) $p['label'] = trim($_POST['label']);
            if (isset($_POST['rss'])   && trim($_POST['rss']))   $p['rss']   = trim($_POST['rss']);
            if (isset($_POST['lang'])  && in_array($_POST['lang'],['fr','es'])) $p['language'] = $_POST['lang'];
            if (isset($_POST['max_episodes'])) {
                $max = (int)$_POST['max_episodes'];
                $p['max_episodes'] = $max <= 0 ? 999 : max(1, $max);
            }
            break;
        }
        echo json_encode(['ok' => write_json_atomic(PODCASTS_JSON, $cfg)]);
        exit;
    }

    if ($a === 'delete_podcast' && isset($_GET['id'])) {
        $del_id = $_GET['id'];
        $cfg = read_json(PODCASTS_JSON);
        $cfg['podcasts'] = array_values(array_filter($cfg['podcasts'] ?? [], fn($p) => $p['id'] !== $del_id));
        $ok = write_json_atomic(PODCASTS_JSON, $cfg);
        // Retrait immédiat de data.json pour que le lecteur ne l'affiche plus sans attendre l'ingest
        if ($ok && file_exists(DATA_JSON)) {
            $data = read_json(DATA_JSON);
            $data['podcasts'] = array_values(array_filter($data['podcasts'] ?? [], fn($p) => $p['id'] !== $del_id));
            write_json_atomic(DATA_JSON, $data);
        }
        echo json_encode(['ok' => $ok]);
        exit;
    }

    // ── Webradios
    if ($a === 'get_radios') { echo json_encode(get_radios()); exit; }

    if ($a === 'add_radio') {
        $name     = trim($_POST['name']  ?? '');
        $url      = trim($_POST['url']   ?? '');
        $desc     = trim($_POST['desc']  ?? '');
        $lang     = in_array($_POST['lang'] ?? 'fr', ['fr','es']) ? $_POST['lang'] : 'fr';
        $image_in = trim($_POST['image'] ?? '');
        if (!$name || !$url) { echo json_encode(['ok'=>false,'msg'=>'Nom et URL requis']); exit; }
        $id = slugify($name);
        $radios = get_radios();
        foreach ($radios as $r) if ($r['id'] === $id) { echo json_encode(['ok'=>false,'msg'=>'ID déjà existant : '.$id]); exit; }
        // Télécharger l'image si une URL distante est fournie
        $image   = 'images/radio/' . $id . '.jpg';
        $img_msg = '';
        if ($image_in && str_starts_with($image_in, 'http')) {
            $dl = download_radio_image($image_in, $id);
            if (!$dl['ok']) { echo json_encode(['ok'=>false,'msg'=>'Image : '.$dl['msg']]); exit; }
            $image   = $dl['path'];
            $img_msg = $dl['msg'];
        }
        $radios[] = ['id'=>$id,'name'=>$name,'desc'=>$desc,'lang'=>$lang,'url'=>$url,'image'=>$image];
        $w = save_radios_r($radios);
        if ($w['ok']) sync_radios_to_data_json();
        echo json_encode(['ok'=>$w['ok'],'id'=>$id,'msg'=>$w['ok']?$img_msg:$w['msg']]);
        exit;
    }

    if ($a === 'edit_radio' && isset($_GET['id'])) {
        $radios  = get_radios();
        $img_msg = '';
        foreach ($radios as &$r) {
            if ($r['id'] !== $_GET['id']) continue;
            if (isset($_POST['name'])  && trim($_POST['name']))  $r['name']  = trim($_POST['name']);
            if (isset($_POST['url'])   && trim($_POST['url']))   $r['url']   = trim($_POST['url']);
            if (isset($_POST['desc']))                           $r['desc']  = trim($_POST['desc']);
            if (isset($_POST['lang'])  && in_array($_POST['lang'],['fr','es'])) $r['lang'] = $_POST['lang'];
            if (isset($_POST['image']) && trim($_POST['image'])) {
                $img_in = trim($_POST['image']);
                if (str_starts_with($img_in, 'http')) {
                    // URL distante → télécharger sur le Pi
                    $dl = download_radio_image($img_in, $_GET['id']);
                    if (!$dl['ok']) { echo json_encode(['ok'=>false,'msg'=>'Image : '.$dl['msg']]); exit; }
                    $r['image'] = $dl['path'];
                    $img_msg    = $dl['msg'];
                } else {
                    $r['image'] = $img_in; // chemin local déjà valide
                }
            }
            break;
        }
        $w = save_radios_r($radios);
        if ($w['ok']) sync_radios_to_data_json();
        echo json_encode(['ok'=>$w['ok'],'msg'=>$w['ok']?$img_msg:$w['msg']]);
        exit;
    }

    if ($a === 'delete_radio' && isset($_GET['id'])) {
        $radios = array_values(array_filter(get_radios(), fn($r) => $r['id'] !== $_GET['id']));
        $ok = save_radios($radios);
        if ($ok) sync_radios_to_data_json();
        echo json_encode(['ok' => $ok]);
        exit;
    }

    // ── Config volume
    if ($a === 'get_config') { echo json_encode(read_json(CONFIG_JSON)); exit; }

    if ($a === 'save_config') {
        $cfg = read_json(CONFIG_JSON);
        if (!isset($cfg['volume'])) $cfg['volume'] = [];
        if (isset($_GET['speakers_max']))   $cfg['volume']['speakers_max']   = max(0, min(100, (int)$_GET['speakers_max']));
        if (isset($_GET['headphones_max'])) $cfg['volume']['headphones_max'] = max(0, min(100, (int)$_GET['headphones_max']));
        // Son de démarrage
        if (isset($_GET['chime_enabled'])) $cfg['chime_enabled'] = (bool)(int)$_GET['chime_enabled'];
        if (isset($_GET['chime_volume']))  $cfg['chime_volume']  = max(0, min(100, (int)$_GET['chime_volume']));
        if (isset($_GET['chime_sound']))   $cfg['chime_sound']   = in_array($_GET['chime_sound'], ['chime.wav','boot_orgue.wav','boot_orgue_v3b.wav']) ? $_GET['chime_sound'] : 'chime.wav';
        // Écran de veille
        if (isset($_GET['sleep_enabled'])) $cfg['sleep_enabled'] = (bool)(int)$_GET['sleep_enabled'];
        if (isset($_GET['sleep_delay']))   $cfg['sleep_delay']   = max(10, min(300, (int)$_GET['sleep_delay']));
        if (isset($_GET['sleep_mode']))    $cfg['sleep_mode']    = in_array($_GET['sleep_mode'], ['classic','classic_clock','retro','retro_clock','modern','modern_clock','clock','brand','both']) ? $_GET['sleep_mode'] : 'retro';
        // Extinction écran
        if (isset($_GET['screen_off_enabled'])) $cfg['screen_off_enabled'] = (bool)(int)$_GET['screen_off_enabled'];
        if (isset($_GET['screen_off_delay']))   $cfg['screen_off_delay']   = in_array((int)$_GET['screen_off_delay'], [600,900,1200,1800]) ? (int)$_GET['screen_off_delay'] : 600;
        echo json_encode(['ok' => write_json_atomic(CONFIG_JSON, $cfg)]);
        exit;
    }

      if ($a === 'get_parental') {
        $p = read_json(PROJECT_ROOT . '/data/parental.json');
        if (empty($p)) {
          $p = ['enabled'=>false,'schedule'=>array_fill_keys(range(0,6),[]),'languages'=>['fr','es']];
        }
        echo json_encode(['ok'=>true,'parental'=>$p]);
        exit;
      }

      if ($a === 'save_parental') {
        $body = json_decode(file_get_contents('php://input'), true);
        if (!is_array($body)) {
          echo json_encode(['ok'=>false,'error'=>'JSON invalide']);
          exit;
        }
        $p = [
          'schedule_enabled' => (bool)($body['schedule_enabled'] ?? false),
          'lang_enabled'     => (bool)($body['lang_enabled']     ?? false),
          'schedule'         => $body['schedule']  ?? array_fill_keys(array_map('strval', range(0,6)), []),
          'languages'        => $body['languages'] ?? ['fr','es'],
        ];
        $ok = write_json_atomic(PROJECT_ROOT . '/data/parental.json', $p);
        echo json_encode(['ok'=>$ok]);
        exit;
      }

      if ($a === 'parental_status') {
        $p = read_json(PROJECT_ROOT . '/data/parental.json');
        $c = read_json(CONFIG_JSON);
        echo json_encode([
          'schedule_enabled' => (bool)($p['schedule_enabled'] ?? $p['enabled'] ?? false),
          'lang_enabled'     => (bool)($p['lang_enabled']     ?? false),
          'schedule'         => $p['schedule']  ?? [],
          'languages'        => $p['languages'] ?? ['fr','es'],
          // veille — config.json uniquement (admin avancée)
          'sleep_enabled'    => (bool)($c['sleep_enabled'] ?? true),
          'sleep_delay'      => (int)($c['sleep_delay']    ?? 15),
          'sleep_mode'       => $c['sleep_mode']            ?? 'retro',
          // son de démarrage
          'chime_enabled'    => (bool)($c['chime_enabled'] ?? true),
          'chime_volume'     => (int)($c['chime_volume']   ?? 15),
        ]);
        exit;
      }

    // ── Sauvegardes (TICKET-085)
    if ($a === 'backup_status') {
        echo json_encode([
            'state'   => read_json(BACKUP_STATE_JSON),
            'running' => pid_alive(BACKUP_PID),
            'log'     => file_exists(BACKUP_LOG) ? implode('', array_slice(file(BACKUP_LOG), -40)) : '',
        ]);
        exit;
    }

    if ($a === 'backup_validate') {
        if (pid_alive(BACKUP_PID)) { echo json_encode(['ok'=>false,'msg'=>'Une sauvegarde est déjà en cours']); exit; }
        $label = trim($_POST['label'] ?? '');
        // Nécessite une règle sudoers dédiée (voir docs/95-RESTAURATION_URGENCE.md) :
        // www-data ALL=(root) NOPASSWD: /usr/bin/python3 .../backup_manager.py validate*
        $cmd = 'sudo /usr/bin/python3 ' . escapeshellarg(BACKUP_SCRIPT)
             . ' validate --label ' . escapeshellarg($label)
             . ' > ' . escapeshellarg(BACKUP_LOG) . ' 2>&1 & echo $!';
        $pid = trim((string)shell_exec($cmd));
        if ($pid) file_put_contents(BACKUP_PID, $pid);
        echo json_encode(['ok' => (bool)$pid, 'pid' => $pid]);
        exit;
    }

    // ── Ingestion
    if ($a === 'run_ingest') {
        if (pid_alive(INGEST_PID)) { echo json_encode(['ok'=>false,'msg'=>'Déjà en cours']); exit; }
        // umask 002 : même raison que add_podcast ci-dessus.
        $cmd = 'umask 002 && python3 ' . escapeshellarg(INGEST_SCRIPT) . ' >> ' . escapeshellarg(INGEST_LOG) . ' 2>&1 & echo $!';
        $pid = trim((string)shell_exec($cmd));
        file_put_contents(INGEST_PID, $pid);
        echo json_encode(['ok'=>true,'pid'=>$pid]);
        exit;
    }

    if ($a === 'ingest_log') {
        $lines = file_exists(INGEST_LOG)
            ? array_slice(file(INGEST_LOG, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) ?: [], -80)
            : [];
        echo json_encode(['lines'=>$lines,'running'=>pid_alive(INGEST_PID)]);
        exit;
    }

    // ── Validation URL avant ajout
    if ($a === 'check_url') {
        $url  = trim($_GET['url']  ?? '');
        $type = trim($_GET['type'] ?? 'rss');  // 'rss' | 'stream'

        if (!filter_var($url, FILTER_VALIDATE_URL) || !preg_match('/^https?:\/\//', $url)) {
            echo json_encode(['ok'=>false,'status'=>'error','msg'=>'URL invalide (doit commencer par http:// ou https://)']);
            exit;
        }

        if ($type === 'stream') {
            $r = shell_curl($url, ['timeout'=>8,'connect'=>5,'head'=>true]);
            if (isset($r['msg'])) { echo json_encode(['ok'=>true,'status'=>'warn','msg'=>'Vérification impossible : '.$r['msg']]); exit; }
            if ($r['code'] === 0) { echo json_encode(['ok'=>false,'status'=>'error','msg'=>'Flux inaccessible depuis le Pi']); exit; }
            if ($r['code'] >= 400) { echo json_encode(['ok'=>false,'status'=>'error','msg'=>"HTTP {$r['code']}"]); exit; }
            $isAudio = str_contains($r['ctype'],'audio') || str_contains($r['ctype'],'mpeg') || str_contains($r['ctype'],'ogg') || str_contains($r['ctype'],'aac');
            echo json_encode($isAudio
                ? ['ok'=>true, 'status'=>'ok',   'msg'=>"✓ Flux audio accessible (HTTP {$r['code']})"]
                : ['ok'=>true, 'status'=>'warn',  'msg'=>"⚠ L'URL répond (HTTP {$r['code']}) mais le type n'est pas reconnu comme audio : {$r['ctype']}"]);
        } else {
            $r = shell_curl($url, ['timeout'=>8,'connect'=>5,'range'=>'0-4095']);
            if (isset($r['msg'])) { echo json_encode(['ok'=>true,'status'=>'warn','msg'=>'Vérification impossible : '.$r['msg']]); exit; }
            if ($r['code'] === 0) { echo json_encode(['ok'=>false,'status'=>'error','msg'=>'Flux RSS inaccessible depuis le Pi']); exit; }
            if ($r['code'] >= 400) { echo json_encode(['ok'=>false,'status'=>'error','msg'=>"HTTP {$r['code']}"]); exit; }
            $isRss = str_contains($r['ctype'],'xml') || str_contains($r['ctype'],'rss')
                  || str_contains($r['body'],'<rss') || str_contains($r['body'],'<channel') || str_contains($r['body'],'<feed');
            echo json_encode($isRss
                ? ['ok'=>true, 'status'=>'ok',   'msg'=>"✓ Flux RSS valide (HTTP {$r['code']})"]
                : ['ok'=>false,'status'=>'warn',  'msg'=>"⚠ L'URL répond (HTTP {$r['code']}) mais ne ressemble pas à un flux RSS"]);
        }
        exit;
    }

    if ($a === 'get_progress') {
        $f = '/tmp/hechicero_progress.json';
        $d = file_exists($f) ? @json_decode(file_get_contents($f), true) : null;
        if (!$d) { echo json_encode(['status'=>'idle']); exit; }
        $d['running'] = pid_alive(INGEST_PID);
        echo json_encode($d);
        exit;
    }

    // ── Téléchargement des images manquantes pour les webradios
    if ($a === 'ensure_radio_images') {
        $radios  = get_radios();
        $img_dir = PROJECT_ROOT . '/web/lecteur/images/radio/';
        $results = [];
        foreach ($radios as $r) {
            $id   = $r['id'];
            $file = $img_dir . $id . '.jpg';
            if (file_exists($file) && filesize($file) > 0) continue;  // déjà présent
            $src  = $r['image_url'] ?? null;
            if (!$src) { $results[$id] = ['ok'=>false,'msg'=>"Pas d'URL image_url pour $id"]; continue; }
            $results[$id] = download_radio_image($src, $id);
        }
        echo json_encode(['ok'=>true,'results'=>$results]);
        exit;
    }

    echo json_encode(['error'=>'action inconnue']);
    exit;
}
?>
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hechicero — Admin</title>
<link rel="stylesheet" href="/css/hechicero-admin.css">
<style>
:root {
  --surf2:   #1c2128;
  --green:   #3fb950;
  --red:     #f85149;
  --blue:    #58a6ff;
}
body { font-size:14px; line-height:1.5; }

/* ── Header */
.mode-switch { display:flex; border:1px solid var(--border); border-radius:6px; overflow:hidden; }
.mode-btn { padding:6px 16px; background:transparent; color:var(--muted); border:none; cursor:pointer;
  font-size:12px; font-weight:600; transition:background .15s,color .15s; }
.mode-btn.active { background:var(--accent); color:#000; }

/* ── Grille système */
.sys-grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:24px; }
@media(max-width:600px){ .sys-grid{ grid-template-columns:1fr; } }

/* ── Cards */
.card { background:var(--surface); border:1px solid var(--border); border-radius:18px; padding:16px; box-shadow:0 18px 60px rgba(0,0,0,.22); }
.card-title { font-size:0.72rem; font-weight:700; color:var(--muted); text-transform:uppercase; letter-spacing:.08em; margin-bottom:10px; }

/* ── Stats */
.stat { display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px solid var(--border); }
.stat:last-child { border-bottom:none; }
.stat-l { color:var(--muted); font-size:13px; }
.stat-v { font-weight:600; font-size:13px; }
.ok   { color:var(--green); }
.warn { color:var(--accent); }
.err  { color:var(--red); }
.bar-wrap { background:var(--border); border-radius:3px; height:6px; margin-top:10px; overflow:hidden; }
.bar-fill  { height:100%; border-radius:3px; background:var(--green); transition:width .4s; }

/* ── Section */
section { margin-bottom:24px; }
.sec-hdr { display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; }
.sec-hdr h2 { font-size:0.95rem; font-weight:700; color:var(--text); letter-spacing:.02em; }
.sec-count { font-size:11px; color:var(--muted); font-weight:400; margin-left:6px; }

/* ── Colonnes FR / ES */
.lang-cols { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
/* Chaque colonne est un flex-col → la card s'étire jusqu'en bas */
.lang-cols > div { display:flex; flex-direction:column; }
.lang-cols > div .card { flex:1; }
/* Grille "Ajouter" (expert) */
.add-grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
/* ── Administration avancée (cards + mode veille) */
.adv-grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
.sleep-mode-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; font-size:13px; }
/* ── Responsive mobile (≤900 px) */
@media(max-width:900px){
  .lang-cols  { grid-template-columns:1fr; }
  .add-grid   { grid-template-columns:1fr; }
  .sys-grid   { grid-template-columns:1fr; }
  .adv-grid   { grid-template-columns:1fr; }
  .sleep-mode-grid { grid-template-columns:1fr; }
  .card       { padding:12px; }
  /* Sur mobile l'URL brute n'est pas lisible — on la masque même en mode expert */
  .item-url   { display:none !important; }
  /* Boutons d'action : on les descend sous l'info sur mobile */
  .item-row   { flex-wrap:wrap; }
  .item-info  { width:100%; }
  .item-row .btn-ghost, .item-row .btn-danger { margin-top:4px; }
}
.lang-col-hdr { display:flex; align-items:center; gap:8px; margin-bottom:8px; height:24px;
  font-size:12px; font-weight:700; color:var(--muted); text-transform:uppercase; letter-spacing:.06em; }
.lang-dot { width:8px; height:8px; border-radius:50%; background:var(--border); flex-shrink:0; }
.lang-dot-fr { background:#0055A4; }
.lang-dot-es { background:#c8a050; }

/* ── Items */
.item-row { display:flex; align-items:center; gap:10px; padding:9px 0; border-bottom:1px solid var(--border); }
.item-row:last-child { border-bottom:none; }
.item-info { flex:1; min-width:0; }
.item-name { font-weight:600; font-size:13px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.item-meta { font-size:11px; color:var(--muted); margin-top:2px; }
.item-url  { font-size:10px; color:var(--muted); font-family:monospace; white-space:nowrap; overflow:hidden;
  text-overflow:ellipsis; margin-top:2px; }

/* ── Toggle */
.toggle { position:relative; width:36px; height:20px; flex-shrink:0; }
.toggle input { opacity:0; width:0; height:0; position:absolute; }
.tgl-sl { position:absolute; inset:0; background:var(--border); border-radius:20px; cursor:pointer; transition:background .2s; }
.tgl-sl::before { content:''; position:absolute; width:14px; height:14px; border-radius:50%;
  left:3px; top:3px; background:var(--muted); transition:transform .2s,background .2s; }
.toggle input:checked + .tgl-sl { background:var(--green); }
.toggle input:checked + .tgl-sl::before { transform:translateX(16px); background:#fff; }
.toggle input:disabled + .tgl-sl { opacity:.5; cursor:default; }

/* ── Boutons */
.btn { display:inline-flex; align-items:center; gap:5px; padding:6px 12px; border-radius:6px;
  border:1px solid var(--border); background:var(--surface-2); color:var(--text);
  cursor:pointer; font-size:12px; font-weight:600; transition:background .15s,border-color .15s; white-space:nowrap; }
.btn:hover    { background:rgba(240,190,79,.08); border-color:var(--accent); }
.btn:disabled { opacity:.4; cursor:not-allowed; }
.btn-primary  { background:var(--accent); color:#000; border-color:var(--accent); }
.btn-primary:hover { background:#b8903c; }
.btn-danger   { color:var(--red); border-color:var(--red); }
.btn-danger:hover  { background:#2d0f0e; }
.btn-ghost    { background:transparent; border-color:transparent; color:var(--muted); padding:4px 6px; }
.btn-ghost:hover { background:var(--surf2); border-color:var(--border); color:var(--text); }
.btn-sm { padding:4px 9px; font-size:11px; }
.btn-xs { padding:3px 7px; font-size:10px; }

/* ── Formulaires */
.form-card { background:var(--surface); border:1px solid var(--border); border-radius:18px; padding:16px; margin-bottom:14px; box-shadow:0 18px 60px rgba(0,0,0,.22); }
.form-card h3 { font-size:12px; font-weight:700; color:var(--accent); margin-bottom:12px; }
.form-row { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
@media(max-width:500px){ .form-row{ grid-template-columns:1fr; } }
.fg { display:flex; flex-direction:column; gap:4px; }
.fg.full { grid-column:1/-1; }
.fg label { font-size:10px; color:var(--muted); font-weight:700; text-transform:uppercase; letter-spacing:.05em; }
.fg input, .fg select, .fg textarea {
  background:var(--bg); border:1px solid var(--border); border-radius:5px;
  color:var(--text); padding:7px 10px; font-size:13px; outline:none;
  transition:border-color .15s; font-family:inherit; }
.fg input:focus,.fg select:focus { border-color:var(--accent); }
.fg select option { background:var(--bg); }
.form-actions { grid-column:1/-1; display:flex; gap:8px; align-items:center; padding-top:4px; }
.form-msg { font-size:11px; }

/* ── Inline edit */
.edit-panel { display:none; background:var(--surf2); border:1px solid var(--border); border-radius:6px;
  padding:14px; margin:6px 0 6px 0; }
.edit-panel.open { display:block; }
.edit-panel .form-row { margin-top:0; }

/* ── Volume */
.vol-row { display:flex; align-items:center; gap:10px; margin-bottom:12px; }
.vol-row:last-of-type { margin-bottom:0; }
.vol-lbl { width:140px; color:var(--muted); font-size:13px; flex-shrink:0; }
.vol-row input[type=range] { flex:1; accent-color:var(--accent); cursor:pointer; }
.vol-val { width:38px; text-align:right; font-weight:700; color:var(--accent); font-size:13px; }

/* ── Progression */
.prog-row   { display:flex; align-items:center; gap:10px; margin-bottom:10px; }
.prog-label { width:130px; font-size:12px; color:var(--muted); flex-shrink:0;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.prog-track { flex:1; background:var(--border); border-radius:4px; height:8px; overflow:hidden; }
.prog-fill  { height:100%; border-radius:4px; transition:width .4s ease; }
.prog-fill-pod { background:var(--accent); }
.prog-fill-ep  { background:var(--blue); }
.prog-nums  { width:44px; text-align:right; font-size:11px; color:var(--muted); flex-shrink:0; }
.sync-status { font-size:13px; font-weight:600; margin-bottom:14px; }

/* ── Log technique (expert) */
#log-box { background:#010409; border:1px solid var(--border); border-radius:6px;
  padding:12px; font-family:'Courier New',monospace; font-size:11px;
  color:#c9d1d9; height:200px; overflow-y:auto; white-space:pre-wrap; word-break:break-all; }
.log-ok   { color:var(--green); }
.log-err  { color:var(--red); }
.log-warn { color:var(--accent); }

/* ── Expert visibility */
.expert-only  { display:none !important; }
body.expert .expert-only  { display:block !important; }
body.expert .expert-flex  { display:inline-flex !important; }
.expert-flex  { display:none !important; }
body.expert .expert-chk   { cursor:pointer !important; }
body.expert input[disabled] { cursor:not-allowed !important; }

/* ── Max episodes select (expert) */
.max-sel { background:var(--bg); border:1px solid var(--border); border-radius:4px;
  color:var(--text); font-size:11px; padding:2px 4px; cursor:pointer; }

.toggle-switch { position:relative; display:inline-block; width:44px; height:24px; }
.toggle-switch input { opacity:0; width:0; height:0; }
.slider { position:absolute; cursor:pointer; inset:0; background:#2d3f55;
  border-radius:12px; transition:.3s; }
.slider:before { content:''; position:absolute; height:18px; width:18px; left:3px; bottom:3px;
  background:#fff; border-radius:50%; transition:.3s; }
input:checked + .slider { background:var(--accent); }
input:checked + .slider:before { transform:translateX(20px); }

#schedule-grid { display:grid; grid-template-columns:40px repeat(7,1fr); gap:2px; }
.sg-corner,.sg-day-head { font-size:10px; color:var(--muted); text-align:center; padding:4px 2px; }
.sg-slot-label { font-size:9px; color:var(--muted); text-align:right; padding-right:4px;
  display:flex; align-items:center; justify-content:flex-end; }
.sg-cell { height:28px; border-radius:3px; cursor:pointer; transition:background .12s; }
.sg-cell.sg-on  { background:#16a34a50; border:1px solid #16a34a90; }
.sg-cell.sg-off { background:#dc262640; border:1px solid #dc262680; }
.sg-cell.sg-locked { background:#0a0f1a; border:1px dashed #1e293b; cursor:not-allowed; opacity:0.4; }
.sg-cell.sg-on:hover  { background:#16a34a70; }
.sg-cell.sg-off:hover { background:#dc262660; }
</style>
</head>
<body>

<div class="ha-page">

<!-- ── Header ──────────────────────────────────────────────── -->
<div class="ha-header">
  <div>
    <h1>Hechicero</h1>
    <div class="ha-subtitle">Administration principale, contrôle parental et synchronisation.</div>
  </div>
  <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
    <div class="mode-switch">
      <button class="mode-btn active" id="btn-normal" onclick="setMode('normal')">Normal</button>
      <button class="mode-btn"        id="btn-expert" onclick="setMode('expert')">Expert</button>
    </div>
    <nav class="ha-nav">
      <a class="ha-btn active" href="/">
        <span class="ha-btn-icon">⚙</span> Admin
      </a>
      <a class="ha-btn" href="/dashboard.php">
        <span class="ha-btn-icon">📊</span> Écoute
      </a>
      <a class="ha-btn" href="/admin/battery_dashboard.php">
        <span class="ha-btn-icon">🔋</span> Batterie
      </a>
      <a class="ha-btn expert-only" href="/admin/backup_dashboard.php" title="Visible seulement en mode Expert">
        <span class="ha-btn-icon">💾</span> Sauvegardes
      </a>
      <a class="ha-btn" href="/lecteur/" target="_blank" title="Ouvrir le lecteur enfant">
        <span class="ha-btn-icon">📻</span> Lecteur
      </a>
    </nav>
  </div>
</div>

<!-- ── État système (expert) ───────────────────────────────── -->
<section class="expert-only">
  <div class="sec-hdr"><h2>État du système</h2></div>
  <div class="sys-grid">
    <div class="card">
      <div class="card-title">Batterie</div>
      <div class="stat"><span class="stat-l">Niveau</span><span class="stat-v" id="bat-pct">…</span></div>
      <div class="stat"><span class="stat-l">État</span><span class="stat-v" id="bat-state">…</span></div>
      <div class="stat"><span class="stat-l">Tension</span><span class="stat-v" id="bat-volt">…</span></div>
      <div class="stat"><span class="stat-l">Courant</span><span class="stat-v" id="bat-amp">…</span></div>
      <div class="bar-wrap"><div class="bar-fill" id="bat-bar" style="width:0%"></div></div>
    </div>
    <div class="card">
      <div class="card-title">Système</div>
      <div class="stat"><span class="stat-l">MPD</span><span class="stat-v" id="mpd-state">…</span></div>
      <div class="stat"><span class="stat-l">Volume MPD</span><span class="stat-v" id="mpd-vol">…</span></div>
      <div class="stat"><span class="stat-l">Disque libre</span><span class="stat-v" id="disk-free">…</span></div>
      <div class="stat"><span class="stat-l">Disque utilisé</span><span class="stat-v" id="disk-pct">…</span></div>
      <div class="stat"><span class="stat-l">Dernière ingestion</span><span class="stat-v" id="last-ingest">…</span></div>
      <div class="bar-wrap"><div class="bar-fill" id="disk-bar" style="width:0%;background:var(--accent)"></div></div>
    </div>
  </div>
</section>

<section>
  <div class="sec-hdr"><h2>Contrôle parental</h2></div>
  <div class="card" id="parental-card">

    <!-- Interrupteur horaires -->
    <div class="stat" style="margin-bottom:8px">
      <span class="stat-l" style="font-size:14px;font-weight:600">🕐 Contrôle des horaires</span>
      <label class="toggle-switch">
        <input type="checkbox" id="schedule-enabled">
        <span class="slider"></span>
      </label>
    </div>
    <p id="schedule-status-text" style="font-size:12px;color:var(--muted);margin-bottom:16px">Chargement...</p>

    <div id="parental-schedule-wrap">
      <div id="schedule-grid"></div>
      <p style="font-size:11px;color:var(--muted);margin-top:6px">
        Gris = toujours bloqué · <span style="color:#4ade80">■</span> Vert = autorisé · <span style="color:#f87171">■</span> Rouge = bloqué
      </p>
    </div>

    <hr style="border:none;border-top:1px solid #1e293b;margin:20px 0">

    <!-- Interrupteur langues -->
    <div class="stat" style="margin-bottom:8px">
      <span class="stat-l" style="font-size:14px;font-weight:600">🌐 Contrôle des langues</span>
      <label class="toggle-switch">
        <input type="checkbox" id="lang-enabled">
        <span class="slider"></span>
      </label>
    </div>
    <p id="lang-status-text" style="font-size:12px;color:var(--muted);margin-bottom:12px">Chargement...</p>

    <div id="lang-toggles" style="display:flex;gap:16px;flex-wrap:wrap">
      <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
        <input type="checkbox" id="lang-fr" value="fr" checked>
        <span>🇫🇷 Français</span>
      </label>
      <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
        <input type="checkbox" id="lang-es" value="es" checked>
        <span>🇪🇸 Español</span>
      </label>
    </div>

    <button class="btn btn-primary" id="btn-save-parental" style="margin-top:16px">Enregistrer</button>
    <span id="parental-save-msg" style="font-size:12px;margin-left:10px;color:var(--muted)"></span>
  </div>
</section>

<!-- ── Administration avancée ──────────────────────────────── -->
<section class="expert-only">
  <div class="sec-hdr">
    <h2>Administration avancée</h2>
    <button class="btn btn-primary btn-sm" id="btn-save-adv" onclick="saveConfig()">Enregistrer</button>
  </div>
  <div class="adv-grid">

    <!-- Volume max -->
    <div class="card">
      <div class="card-title">🔊 Volume maximum</div>
      <div class="vol-row">
        <span class="vol-lbl">Haut-parleurs</span>
        <input type="range" id="vol-speakers" min="0" max="100" value="40"
               oninput="document.getElementById('val-speakers').textContent=this.value+'%'">
        <span class="vol-val" id="val-speakers">40%</span>
      </div>
      <div class="vol-row">
        <span class="vol-lbl">Casque</span>
        <input type="range" id="vol-headphones" min="0" max="100" value="60"
               oninput="document.getElementById('val-headphones').textContent=this.value+'%'">
        <span class="vol-val" id="val-headphones">60%</span>
      </div>
      <p style="font-size:11px;color:var(--muted);margin-top:10px">100 % dans l'IHM enfant = cette valeur dans MPD.</p>
    </div>

    <!-- Son de démarrage -->
    <div class="card">
      <div class="card-title">🔔 Son de démarrage</div>
      <div class="stat" style="margin-bottom:12px">
        <span class="stat-l">Activé</span>
        <label class="toggle-switch">
          <input type="checkbox" id="chime-enabled" checked>
          <span class="slider"></span>
        </label>
      </div>
      <div class="vol-row">
        <span class="vol-lbl">Volume</span>
        <input type="range" id="chime-volume" min="0" max="40" value="15"
               oninput="document.getElementById('val-chime').textContent=this.value+'%'">
        <span class="vol-val" id="val-chime">15%</span>
      </div>
      <div class="vol-row" style="margin-top:10px">
        <span class="vol-lbl">Son</span>
        <select id="chime-sound" style="flex:1;padding:4px 8px;border-radius:6px;border:1px solid var(--border,#ccc);font-size:13px">
          <option value="chime.wav">Accord classique</option>
          <option value="boot_orgue.wav">Orgue magique</option>
          <option value="boot_orgue_v3b.wav">Orgue grave</option>
        </select>
      </div>
      <p style="font-size:11px;color:var(--muted);margin-top:10px">Son joué au démarrage du lecteur.</p>
    </div>

    <!-- Écran de veille -->
    <div class="card" style="grid-column:1/-1">
      <div class="card-title">🌙 Écran de veille</div>
      <div style="display:flex;gap:32px;flex-wrap:wrap;align-items:center;margin-bottom:14px">
        <div class="stat" style="margin:0">
          <span class="stat-l">Activé</span>
          <label class="toggle-switch">
            <input type="checkbox" id="sleep-enabled" checked>
            <span class="slider"></span>
          </label>
        </div>
        <label style="font-size:13px;color:var(--muted)">
          Délai :
          <select id="sleep-delay" style="margin-left:6px;background:#0b1220;color:var(--text);border:1px solid #1e293b;border-radius:4px;padding:3px 8px">
            <option value="15">15 s</option>
            <option value="30">30 s</option>
            <option value="60">1 min</option>
            <option value="120">2 min</option>
            <option value="300">5 min</option>
            <option value="600">10 min</option>
          </select>
        </label>
      </div>
      <div class="sleep-mode-grid">
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer"><input type="radio" name="sleep-mode" value="classic"> Classique</label>
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer"><input type="radio" name="sleep-mode" value="classic_clock"> Classique + horloge</label>
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer"><input type="radio" name="sleep-mode" value="retro" checked> Rétro Or</label>
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer"><input type="radio" name="sleep-mode" value="retro_clock"> Rétro Or + horloge</label>
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer"><input type="radio" name="sleep-mode" value="modern"> Chrome</label>
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer"><input type="radio" name="sleep-mode" value="modern_clock"> Chrome + horloge</label>
      </div>
      <hr style="border:none;border-top:1px solid #1e293b;margin:16px 0">
      <div class="card-title">💤 Extinction écran</div>
      <div style="display:flex;gap:32px;flex-wrap:wrap;align-items:center">
        <div class="stat" style="margin:0">
          <span class="stat-l">Activée</span>
          <label class="toggle-switch">
            <input type="checkbox" id="screen-off-enabled" checked>
            <span class="slider"></span>
          </label>
        </div>
        <label style="font-size:13px;color:var(--muted)">
          Délai :
          <select id="screen-off-delay" style="margin-left:6px;background:#0b1220;color:var(--text);border:1px solid #1e293b;border-radius:4px;padding:3px 8px">
            <option value="600">10 min</option>
            <option value="900">15 min</option>
            <option value="1200">20 min</option>
            <option value="1800">30 min</option>
          </select>
        </label>
      </div>
      <p style="font-size:11px;color:var(--muted);margin-top:10px">Coupe le rétroéclairage après inactivité. Premier toucher = rallumage. Géré par <code>hechicero-idle.service</code>.</p>
    </div>

  </div>
</section>

<!-- ── Volume (expert) — LEGACY, remplacé par Admin avancée ── -->
<!-- section supprimée, contenu fusionné dans Admin avancée -->

<!-- ── Ajouter (expert) ────────────────────────────────────── -->
<section class="expert-only">
  <div class="sec-hdr"><h2>Ajouter</h2></div>
  <div class="add-grid">

    <!-- Ajouter podcast -->
    <div class="form-card">
      <h3>➕ Podcast RSS</h3>
      <div class="form-row">
        <div class="fg"><label>Titre *</label><input type="text" id="pod-label" placeholder="Les Odyssées"></div>
        <div class="fg">
          <label>Langue</label>
          <select id="pod-lang"><option value="fr">🇫🇷 Français</option><option value="es">🇪🇸 Español</option></select>
        </div>
        <div class="fg full"><label>URL RSS *</label><input type="url" id="pod-rss" placeholder="https://…"></div>
        <div class="fg">
          <label>Épisodes max</label>
          <select id="pod-max">
            <option value="5">5</option>
            <option value="10" selected>10</option>
            <option value="20">20</option>
            <option value="50">50</option>
            <option value="0">∞ Tous</option>
          </select>
        </div>
        <div class="form-actions">
          <button class="btn btn-primary btn-sm" onclick="addPodcast()">Ajouter</button>
          <span class="form-msg" id="pod-msg"></span>
        </div>
      </div>
    </div>

    <!-- Ajouter webradio -->
    <div class="form-card">
      <h3>➕ Webradio</h3>
      <div class="form-row">
        <div class="fg"><label>Nom *</label><input type="text" id="rad-name" placeholder="Mon Petit France Inter"></div>
        <div class="fg">
          <label>Langue</label>
          <select id="rad-lang"><option value="fr">🇫🇷 Français</option><option value="es">🇪🇸 Español</option></select>
        </div>
        <div class="fg full"><label>URL du flux (stream) *</label><input type="url" id="rad-url" placeholder="https://icecast.…/flux.mp3"></div>
        <div class="fg"><label>Description</label><input type="text" id="rad-desc" placeholder="Généraliste · Radio France"></div>
        <div class="fg"><label>URL image (optionnel)</label><input type="url" id="rad-image" placeholder="https://…/cover.jpg"></div>
        <div class="form-actions">
          <button class="btn btn-primary btn-sm" onclick="addRadio()">Ajouter</button>
          <span class="form-msg" id="rad-msg"></span>
        </div>
      </div>
    </div>

  </div>
</section>

<!-- ── Podcasts ────────────────────────────────────────────── -->
<section>
  <div class="sec-hdr">
    <h2>Podcasts <span class="sec-count" id="pod-count"></span></h2>
  </div>
  <div class="lang-cols">
    <div>
      <div class="lang-col-hdr"><span class="lang-dot lang-dot-fr"></span> Français</div>
      <div class="card" id="pod-fr"><p style="color:var(--muted);font-size:13px">Chargement…</p></div>
    </div>
    <div>
      <div class="lang-col-hdr"><span class="lang-dot lang-dot-es"></span> Español</div>
      <div class="card" id="pod-es"><p style="color:var(--muted);font-size:13px">Chargement…</p></div>
    </div>
  </div>
</section>

<!-- ── Webradios ───────────────────────────────────────────── -->
<section>
  <div class="sec-hdr">
    <h2>Webradios <span class="sec-count" id="radio-count"></span></h2>
  </div>
  <div class="lang-cols">
    <div>
      <div class="lang-col-hdr"><span class="lang-dot lang-dot-fr"></span> Français</div>
      <div class="card" id="radio-fr"><p style="color:var(--muted);font-size:13px">Chargement…</p></div>
    </div>
    <div>
      <div class="lang-col-hdr"><span class="lang-dot lang-dot-es"></span> Español</div>
      <div class="card" id="radio-es"><p style="color:var(--muted);font-size:13px">Chargement…</p></div>
    </div>
  </div>
</section>

<!-- ── Synchronisation ──────────────────────────────────────── -->
<section>
  <div class="sec-hdr">
    <h2>Synchronisation des podcasts</h2>
    <button class="btn btn-primary btn-sm" id="btn-ingest" onclick="runIngest()">▶ Mettre à jour</button>
  </div>

  <!-- État repos : message simple -->
  <div id="sync-idle" style="font-size:12px;color:var(--muted);margin-bottom:8px">
    Cliquez sur « Mettre à jour » pour télécharger les derniers épisodes.
  </div>

  <!-- Progression (visible pendant et après la synchro) -->
  <div id="sync-progress" style="display:none" class="card">
    <div class="sync-status" id="sync-status-text">Démarrage…</div>

    <div class="prog-row">
      <div class="prog-label">Podcasts</div>
      <div class="prog-track"><div class="prog-fill prog-fill-pod" id="prog-pod-fill" style="width:0%"></div></div>
      <div class="prog-nums" id="prog-pod-nums">0 / 0</div>
    </div>

    <div class="prog-row">
      <div class="prog-label" id="prog-ep-label">Épisodes</div>
      <div class="prog-track"><div class="prog-fill prog-fill-ep" id="prog-ep-fill" style="width:0%"></div></div>
      <div class="prog-nums" id="prog-ep-nums">0 / 0</div>
    </div>

    <!-- Logs techniques, expert seulement -->
    <details class="expert-only" style="margin-top:14px">
      <summary style="cursor:pointer;font-size:11px;color:var(--muted);user-select:none;list-style:none">
        ▸ Logs techniques
      </summary>
      <div id="log-box" style="margin-top:8px">…</div>
    </details>
  </div>
</section>

</div>

<script>
// ── API ────────────────────────────────────────────────────
const api = (params, body) => {
  const url = 'index.php?' + new URLSearchParams(params);
  if (body) return fetch(url, {method:'POST', body:new URLSearchParams(body)}).then(r=>r.json());
  return fetch(url).then(r=>r.json());
};

const esc = s => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const fmtTs = ts => ts ? new Date(ts*1000).toLocaleDateString('fr-FR') + ' ' + new Date(ts*1000).toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'}) : '—';
const maxLabel = m => m >= 999 ? '∞' : m;

// ── Mode ───────────────────────────────────────────────────
let currentMode = 'normal';
function setMode(mode) {
  currentMode = mode;
  document.body.className = mode === 'expert' ? 'expert' : '';
  document.getElementById('btn-normal').classList.toggle('active', mode === 'normal');
  document.getElementById('btn-expert').classList.toggle('active', mode === 'expert');
  localStorage.setItem('hechicero_mode', mode);
  // Refresh les listes pour activer/désactiver les contrôles
  loadPodcasts();
  loadRadios();
}

// ── Statut ────────────────────────────────────────────────
async function loadStatus() {
  const s = await api({action:'status'}).catch(()=>null);
  if (!s) return;
  const b = s.battery, pct = b.percent ?? 0;
  document.getElementById('bat-pct').textContent   = b.percent  !== null ? b.percent  + ' %'  : '—';
  document.getElementById('bat-state').textContent = b.state    ?? '—';
  document.getElementById('bat-volt').textContent  = b.voltage_v  !== null ? b.voltage_v  + ' V'  : '—';
  document.getElementById('bat-amp').textContent   = b.current_ma !== null ? b.current_ma + ' mA' : '—';
  const bb = document.getElementById('bat-bar');
  bb.style.width = pct + '%';
  bb.style.background = pct > 50 ? 'var(--green)' : pct > 20 ? 'var(--accent)' : 'var(--red)';

  const ms = document.getElementById('mpd-state');
  ms.textContent = s.mpd.state;
  ms.className   = 'stat-v ' + (s.mpd.state==='play'?'ok':s.mpd.state==='pause'?'warn':'');
  document.getElementById('mpd-vol').textContent   = s.mpd.volume !== '?' ? s.mpd.volume + ' %' : '—';
  document.getElementById('disk-free').textContent = s.disk.free_gb + ' Go / ' + s.disk.total_gb + ' Go';
  document.getElementById('disk-pct').textContent  = s.disk.used_pct + ' %';
  const db = document.getElementById('disk-bar');
  db.style.width      = s.disk.used_pct + '%';
  db.style.background = s.disk.used_pct>85?'var(--red)':s.disk.used_pct>65?'var(--accent)':'var(--green)';
  document.getElementById('last-ingest').textContent = fmtTs(s.last_ingest_ts);

  // Bouton synchro : verrouillé si déjà en cours
  if (s.ingest_running) {
    document.getElementById('btn-ingest').disabled    = true;
    document.getElementById('btn-ingest').textContent = '⏳ En cours…';
    document.getElementById('sync-idle').style.display     = 'none';
    document.getElementById('sync-progress').style.display = 'block';
  }
}

// ── Config avancée ────────────────────────────────────────
async function loadConfig() {
  const c = await api({action:'get_config'}).catch(()=>({}));
  const sv = c.volume?.speakers_max   ?? 40;
  const hv = c.volume?.headphones_max ?? 60;
  document.getElementById('vol-speakers').value         = sv;
  document.getElementById('val-speakers').textContent   = sv + '%';
  document.getElementById('vol-headphones').value       = hv;
  document.getElementById('val-headphones').textContent = hv + '%';
  // Son de démarrage
  const ce = !!(c.chime_enabled ?? true);
  const cv = c.chime_volume ?? 15;
  document.getElementById('chime-enabled').checked      = ce;
  document.getElementById('chime-volume').value         = cv;
  document.getElementById('val-chime').textContent      = cv + '%';
  document.getElementById('chime-sound').value          = c.chime_sound ?? 'chime.wav';
  // Écran de veille (lire depuis config.json — admin avancée)
  document.getElementById('sleep-enabled').checked      = !!(c.sleep_enabled ?? true);
  document.getElementById('sleep-delay').value          = String(c.sleep_delay ?? 15);
  const modeVal = c.sleep_mode ?? 'retro';
  const modeInput = document.querySelector(`input[name="sleep-mode"][value="${modeVal}"]`);
  if (modeInput) modeInput.checked = true;
  // Extinction écran
  document.getElementById('screen-off-enabled').checked = !!(c.screen_off_enabled ?? true);
  document.getElementById('screen-off-delay').value     = String(c.screen_off_delay ?? 600);
}
async function saveConfig() {
  const r = await api({
    action:         'save_config',
    speakers_max:   document.getElementById('vol-speakers').value,
    headphones_max: document.getElementById('vol-headphones').value,
    chime_enabled:  document.getElementById('chime-enabled').checked ? 1 : 0,
    chime_volume:   document.getElementById('chime-volume').value,
    chime_sound:    document.getElementById('chime-sound').value,
    sleep_enabled:       document.getElementById('sleep-enabled').checked ? 1 : 0,
    sleep_delay:         document.getElementById('sleep-delay').value,
    sleep_mode:          (document.querySelector('input[name="sleep-mode"]:checked') || {value:'retro'}).value,
    screen_off_enabled:  document.getElementById('screen-off-enabled').checked ? 1 : 0,
    screen_off_delay:    document.getElementById('screen-off-delay').value,
  });
  const btn = document.getElementById('btn-save-adv');
  btn.textContent = r.ok ? '✓ Enregistré' : '✗ Erreur';
  setTimeout(()=>btn.textContent='Enregistrer', 2000);
}

const DAYS_LABELS = ['Dim','Lun','Mar','Mer','Jeu','Ven','Sam'];
const SLOTS = [
  { key:'0-7',   label:'0h-7h',   locked:false },
  { key:'7-12',  label:'7h-12h',  locked:false },
  { key:'12-14', label:'12h-14h', locked:false },
  { key:'14-17', label:'14h-17h', locked:false },
  { key:'17-20', label:'17h-20h', locked:false },
  { key:'20-22', label:'20h-22h', locked:false },
  { key:'22-24', label:'22h-24h', locked:false },
];

// Défaut : toutes les plages autorisées (vert)
const DEFAULT_SLOTS_ON = SLOTS.filter(s => !s.locked).map(s => s.key);

let parentalConfig = {
  schedule_enabled: false,
  lang_enabled: false,
  schedule: {},
  languages: ['fr','es']
};

function normalizeParentalSchedule(schedule) {
  const out = {};
  for (let day = 0; day <= 6; day++) {
    const key = String(day);
    // Si le jour existe dans le JSON sauvegardé, on le conserve
    // Sinon : défaut = tout autorisé (toutes les plages non-locked en vert)
    out[key] = Array.isArray(schedule?.[key]) ? schedule[key].slice() : DEFAULT_SLOTS_ON.slice();
  }
  return out;
}

async function loadParental() {
  const r = await api({action:'get_parental'}).catch(()=>null);
  if (!r || !r.ok) return;
  const p = r.parental || {};
  parentalConfig = {
    schedule_enabled: !!(p.schedule_enabled ?? p.enabled ?? false),
    lang_enabled:     !!(p.lang_enabled ?? false),
    schedule:         normalizeParentalSchedule(p.schedule || {}),
    languages:        Array.isArray(p.languages) ? p.languages : ['fr','es'],
  };
  renderParentalUI();
}

function renderParentalUI() {
  const p = parentalConfig;
  document.getElementById('schedule-enabled').checked = !!p.schedule_enabled;
  document.getElementById('schedule-status-text').textContent =
    p.schedule_enabled ? 'Actif — les plages rouges sont bloquées.' :
                         'Inactif — aucune restriction horaire.';

  document.getElementById('lang-enabled').checked = !!p.lang_enabled;
  document.getElementById('lang-status-text').textContent =
    p.lang_enabled ? 'Actif — seules les langues cochées sont accessibles.' :
                     'Inactif — les deux langues sont toujours disponibles.';

  document.getElementById('lang-fr').checked = (p.languages || []).includes('fr');
  document.getElementById('lang-es').checked = (p.languages || []).includes('es');
  // sleep & chime sont dans la section Admin avancée → chargés par loadConfig()

  const grid = document.getElementById('schedule-grid');
  grid.innerHTML = '';
  grid.insertAdjacentHTML('beforeend', '<div class="sg-corner"></div>');
  DAYS_LABELS.forEach(d => grid.insertAdjacentHTML('beforeend', `<div class="sg-day-head">${d}</div>`));

  SLOTS.forEach(slot => {
    grid.insertAdjacentHTML('beforeend', `<div class="sg-slot-label">${slot.label}</div>`);
    for (let day = 0; day <= 6; day++) {
      const dayKey = String(day);
      const active = (p.schedule[dayKey] || []).includes(slot.key);
      const cls = slot.locked ? 'sg-locked' : (active ? 'sg-on' : 'sg-off');
      const cell = document.createElement('div');
      cell.className = `sg-cell ${cls}`;
      cell.dataset.day = dayKey;
      cell.dataset.slot = slot.key;
      if (!slot.locked) cell.addEventListener('click', toggleCell);
      grid.appendChild(cell);
    }
  });
}

function toggleCell(e) {
  const cell = e.currentTarget;
  const day  = String(cell.dataset.day);
  const slot = cell.dataset.slot;
  const sch  = parentalConfig.schedule;
  if (!sch[day]) sch[day] = [];
  const idx = sch[day].indexOf(slot);
  if (idx >= 0) { sch[day].splice(idx, 1); cell.className = 'sg-cell sg-off'; }
  else          { sch[day].push(slot);      cell.className = 'sg-cell sg-on'; }
}

async function saveParental() {
  // sleep_enabled / sleep_delay / sleep_mode → sauvegardés dans saveConfig() (admin avancée)
  parentalConfig.schedule_enabled = document.getElementById('schedule-enabled').checked;
  parentalConfig.lang_enabled     = document.getElementById('lang-enabled').checked;
  parentalConfig.languages = [];
  if (document.getElementById('lang-fr').checked) parentalConfig.languages.push('fr');
  if (document.getElementById('lang-es').checked) parentalConfig.languages.push('es');

  if (parentalConfig.lang_enabled && parentalConfig.languages.length === 0) {
    document.getElementById('parental-save-msg').textContent = '⚠ Sélectionnez au moins une langue';
    return;
  }

  document.getElementById('parental-save-msg').textContent = 'Enregistrement…';
  try {
    const r = await fetch('/?action=save_parental', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(parentalConfig),
    });
    const d = await r.json();
    document.getElementById('parental-save-msg').textContent = d.ok ? '✓ Enregistré' : '✗ Erreur';
    renderParentalUI();
  } catch(e) {
    document.getElementById('parental-save-msg').textContent = '✗ Erreur réseau';
  }
  setTimeout(() => document.getElementById('parental-save-msg').textContent = '', 3000);
}

// ── Copier dans le presse-papiers ─────────────────────────
async function copyUrl(url) {
  try { await navigator.clipboard.writeText(url); } catch { prompt('Copiez l\'URL :', url); }
}

// ── Podcasts ──────────────────────────────────────────────
let _podcasts = [];

async function loadPodcasts() {
  _podcasts = await api({action:'get_podcasts'}).catch(()=>[]);
  const fr  = _podcasts.filter(p=>(p.language||'fr')==='fr');
  const es  = _podcasts.filter(p=>(p.language||'fr')==='es');
  document.getElementById('pod-count').textContent = '· ' + _podcasts.length + '  (' + fr.length + ' FR · ' + es.length + ' ES)';
  renderPodcastCol('pod-fr', fr);
  renderPodcastCol('pod-es', es);
}

function renderPodcastCol(containerId, list) {
  const expert = currentMode === 'expert';
  document.getElementById(containerId).innerHTML = list.length ? list.map(p => {
    const eps = p.episode_count || 0;
    const en  = p.enabled !== false;
    const maxOpts = [5,10,20,50].map(v=>`<option value="${v}" ${p.max_episodes==v?'selected':''}>${v}</option>`).join('');
    return `
    <div class="item-row" id="row-${p.id}">
      <label class="toggle">
        <input type="checkbox" ${en?'checked':''} ${expert?'':'disabled'}
               onchange="togglePodcast('${p.id}',this.checked)">
        <span class="tgl-sl"></span>
      </label>
      <div class="item-info">
        <div class="item-name">${esc(p.label)}</div>
        <div class="item-meta">
          ${eps} épisode${eps!==1?'s':''} ·
          ${expert
            ? `<select class="max-sel" title="Épisodes max" onchange="setMaxEp('${p.id}',this.value)">${maxOpts}<option value="0" ${p.max_episodes>=999?'selected':''}>∞</option></select>`
            : `max ${maxLabel(p.max_episodes)}`
          }
        </div>
        ${expert ? `<div class="item-url" title="${esc(p.rss)}">${esc(p.rss)}</div>` : ''}
      </div>
      ${expert ? `
        <button class="btn btn-ghost btn-xs" title="Copier le flux RSS" onclick="copyUrl('${esc(p.rss)}')">📋</button>
        <button class="btn btn-ghost btn-xs" onclick="toggleEditPodcast('${p.id}')">✏️</button>
        <button class="btn btn-danger btn-xs" onclick="deletePodcast('${p.id}','${esc(p.label)}')">🗑</button>
      ` : ''}
    </div>
    ${expert ? `
    <div class="edit-panel" id="edit-pod-${p.id}">
      <div class="form-row">
        <div class="fg"><label>Titre</label><input type="text" id="ep-label-${p.id}" value="${esc(p.label)}"></div>
        <div class="fg"><label>Langue</label>
          <select id="ep-lang-${p.id}">
            <option value="fr" ${(p.language||'fr')==='fr'?'selected':''}>🇫🇷 Français</option>
            <option value="es" ${(p.language||'fr')==='es'?'selected':''}>🇪🇸 Español</option>
          </select>
        </div>
        <div class="fg full"><label>URL RSS</label><input type="url" id="ep-rss-${p.id}" value="${esc(p.rss)}"></div>
        <div class="form-actions">
          <button class="btn btn-primary btn-sm" onclick="savePodcast('${p.id}')">Enregistrer</button>
          <button class="btn btn-sm" onclick="toggleEditPodcast('${p.id}')">Annuler</button>
          <span class="form-msg" id="ep-msg-${p.id}"></span>
        </div>
      </div>
    </div>` : ''}`;
  }).join('') : `<p style="color:var(--muted);font-size:13px">Aucun podcast</p>`;
}

function toggleEditPodcast(id) { document.getElementById('edit-pod-' + id)?.classList.toggle('open'); }

async function togglePodcast(id, enabled) { await api({action:'toggle_podcast', id, enabled:enabled?'1':'0'}); }

async function setMaxEp(id, val) {
  await api({action:'edit_podcast', id}, {max_episodes: val});
}

async function savePodcast(id) {
  const label = document.getElementById('ep-label-' + id)?.value;
  const rss   = document.getElementById('ep-rss-'   + id)?.value;
  const lang  = document.getElementById('ep-lang-'  + id)?.value;
  const msg   = document.getElementById('ep-msg-'   + id);
  const r = await api({action:'edit_podcast', id}, {label, rss, lang});
  if (r.ok) { msg.textContent='✓ Enregistré'; msg.style.color='var(--green)'; setTimeout(()=>loadPodcasts(), 800); }
  else { msg.textContent='✗ Erreur'; msg.style.color='var(--red)'; }
}

async function addPodcast() {
  const label = document.getElementById('pod-label').value.trim();
  const rss   = document.getElementById('pod-rss').value.trim();
  const lang  = document.getElementById('pod-lang').value;
  const max   = document.getElementById('pod-max').value;
  const msg   = document.getElementById('pod-msg');
  if (!label || !rss) { msg.textContent='Titre et RSS requis'; msg.style.color='var(--red)'; return; }

  // ── Validation du flux RSS avant ajout
  msg.textContent='⏳ Vérification du flux…'; msg.style.color='var(--muted)';
  const chk = await api({action:'check_url', url:rss, type:'rss'}).catch(()=>({ok:false,status:'error',msg:'Erreur réseau'}));
  if (chk.status === 'error') {
    msg.textContent = '✗ ' + (chk.msg || 'Flux inaccessible'); msg.style.color='var(--red)';
    return;
  }
  if (chk.status === 'warn') {
    msg.textContent = chk.msg + ' — Continuer quand même ?'; msg.style.color='var(--accent)';
    if (!confirm(chk.msg + '\n\nAjouter quand même ?')) return;
  }

  msg.textContent='…'; msg.style.color='var(--muted)';
  const r = await api({action:'add_podcast'}, {label, rss, lang, max_episodes:max});
  if (r.ok) {
    msg.textContent='✓ Ajouté (id: '+r.id+')'; msg.style.color='var(--green)';
    document.getElementById('pod-label').value = '';
    document.getElementById('pod-rss').value   = '';
    loadPodcasts();
  } else { msg.textContent=r.msg||'Erreur'; msg.style.color='var(--red)'; }
}

async function deletePodcast(id, label) {
  if (!confirm('Supprimer "'+label+'" ? (les fichiers audio ne sont pas supprimés)')) return;
  if ((await api({action:'delete_podcast', id})).ok) loadPodcasts();
}

// ── Webradios ─────────────────────────────────────────────
async function loadRadios() {
  const radios = await api({action:'get_radios'}).catch(()=>[]);
  const fr = radios.filter(r=>r.lang==='fr');
  const es = radios.filter(r=>r.lang==='es');
  document.getElementById('radio-count').textContent = '· ' + radios.length + ' (' + fr.length + ' FR · ' + es.length + ' ES)';
  renderRadioCol('radio-fr', fr);
  renderRadioCol('radio-es', es);
}

function renderRadioCol(containerId, list) {
  const expert = currentMode === 'expert';
  document.getElementById(containerId).innerHTML = list.length ? list.map(r => `
    <div class="item-row" id="row-rad-${r.id}">
      <div class="item-info">
        <div class="item-name">${esc(r.name)}</div>
        <div class="item-meta">${esc(r.desc||'')}</div>
        ${expert ? `<div class="item-url" title="${esc(r.url)}">${esc(r.url)}</div>` : ''}
      </div>
      ${expert ? `
        <button class="btn btn-ghost btn-xs" title="Copier le flux" onclick="copyUrl('${esc(r.url)}')">📋</button>
        <button class="btn btn-ghost btn-xs" onclick="toggleEditRadio('${r.id}')">✏️</button>
        <button class="btn btn-danger btn-xs" onclick="deleteRadio('${r.id}','${esc(r.name)}')">🗑</button>
      ` : ''}
    </div>
    ${expert ? `
    <div class="edit-panel" id="edit-rad-${r.id}">
      <div class="form-row">
        <div class="fg"><label>Nom</label><input type="text" id="er-name-${r.id}" value="${esc(r.name)}"></div>
        <div class="fg"><label>Langue</label>
          <select id="er-lang-${r.id}">
            <option value="fr" ${r.lang==='fr'?'selected':''}>🇫🇷 Français</option>
            <option value="es" ${r.lang==='es'?'selected':''}>🇪🇸 Español</option>
          </select>
        </div>
        <div class="fg full"><label>URL du flux</label><input type="url" id="er-url-${r.id}" value="${esc(r.url)}"></div>
        <div class="fg"><label>Description</label><input type="text" id="er-desc-${r.id}" value="${esc(r.desc||'')}"></div>
        <div class="fg"><label>URL image (sera téléchargée sur le Pi)</label><input type="url" id="er-img-${r.id}" value="${esc(r.image||'')}" placeholder="https://…/cover.jpg"></div>
        <div class="form-actions">
          <button class="btn btn-primary btn-sm" onclick="saveRadio('${r.id}')">Enregistrer</button>
          <button class="btn btn-sm" onclick="toggleEditRadio('${r.id}')">Annuler</button>
          <span class="form-msg" id="er-msg-${r.id}"></span>
        </div>
      </div>
    </div>` : ''}
  `).join('') : `<p style="color:var(--muted);font-size:13px">Aucune webradio</p>`;
}

function toggleEditRadio(id) { document.getElementById('edit-rad-' + id)?.classList.toggle('open'); }

async function saveRadio(id) {
  const name  = document.getElementById('er-name-' + id)?.value;
  const url   = document.getElementById('er-url-'  + id)?.value;
  const desc  = document.getElementById('er-desc-' + id)?.value;
  const lang  = document.getElementById('er-lang-' + id)?.value;
  const image = document.getElementById('er-img-'  + id)?.value;
  const msg   = document.getElementById('er-msg-'  + id);
  // Prévenir si l'image est une URL distante
  if (image && image.startsWith('http')) {
    msg.textContent = '⏳ Téléchargement de l\'image…'; msg.style.color = 'var(--muted)';
  }
  const r = await api({action:'edit_radio', id}, {name, url, desc, lang, image});
  if (r.ok) {
    msg.textContent = '✓ ' + (r.msg || 'Enregistré');
    msg.style.color = 'var(--green)';
    setTimeout(()=>loadRadios(), 1200);
  } else {
    msg.textContent = '✗ ' + (r.msg || 'Erreur inconnue');
    msg.style.color = 'var(--red)';
  }
}

async function addRadio() {
  const name  = document.getElementById('rad-name').value.trim();
  const url   = document.getElementById('rad-url').value.trim();
  const desc  = document.getElementById('rad-desc').value.trim();
  const lang  = document.getElementById('rad-lang').value;
  const image = document.getElementById('rad-image').value.trim();
  const msg   = document.getElementById('rad-msg');
  if (!name || !url) { msg.textContent='Nom et URL requis'; msg.style.color='var(--red)'; return; }

  // ── Validation du flux stream avant ajout
  msg.textContent='⏳ Vérification du flux…'; msg.style.color='var(--muted)';
  const chk = await api({action:'check_url', url, type:'stream'}).catch(()=>({ok:false,status:'error',msg:'Erreur réseau'}));
  if (chk.status === 'error') {
    msg.textContent = '✗ ' + (chk.msg || 'Flux inaccessible'); msg.style.color='var(--red)';
    return;
  }
  if (chk.status === 'warn') {
    msg.textContent = chk.msg; msg.style.color='var(--accent)';
    if (!confirm(chk.msg + '\n\nAjouter quand même ?')) return;
  }

  msg.textContent='…'; msg.style.color='var(--muted)';
  const r = await api({action:'add_radio'}, {name, url, desc, lang, image});
  if (r.ok) {
    msg.textContent='✓ Ajouté'; msg.style.color='var(--green)';
    ['rad-name','rad-url','rad-desc','rad-image'].forEach(id=>document.getElementById(id).value='');
    loadRadios();
  } else { msg.textContent=r.msg||'Erreur'; msg.style.color='var(--red)'; }
}

async function deleteRadio(id, name) {
  if (!confirm('Supprimer "'+name+'" ?')) return;
  if ((await api({action:'delete_radio', id})).ok) loadRadios();
}

// ── Synchronisation ────────────────────────────────────────
async function runIngest() {
  const r = await api({action:'run_ingest'});
  if (!r.ok) { alert(r.msg || 'Impossible de démarrer la synchronisation'); return; }
  document.getElementById('btn-ingest').disabled    = true;
  document.getElementById('btn-ingest').textContent = '⏳ En cours…';
  document.getElementById('sync-idle').style.display    = 'none';
  document.getElementById('sync-progress').style.display = 'block';
  document.getElementById('sync-status-text').textContent = 'Démarrage…';
  document.getElementById('sync-status-text').style.color = 'var(--text)';
  pollProgress();
}

async function pollProgress() {
  const p = await api({action:'get_progress'}).catch(()=>null);
  if (p && p.status !== 'idle') {
    updateProgressUI(p);
    if (p.running || p.status === 'running') {
      if (currentMode === 'expert') pollLog();
      setTimeout(pollProgress, 2000);
      return;
    }
    // Terminé
    document.getElementById('btn-ingest').disabled    = false;
    document.getElementById('btn-ingest').textContent = '▶ Mettre à jour';
    loadStatus(); loadPodcasts();
    if (currentMode === 'expert') pollLog();
  }
}

function updateProgressUI(p) {
  const statusEl = document.getElementById('sync-status-text');
  const errCount = (p.errors || []).length;

  if (p.status === 'running') {
    statusEl.textContent = `📡 ${p.current_label || '…'}`;
    statusEl.style.color = 'var(--text)';
  } else if (p.status === 'done') {
    if (errCount > 0) {
      statusEl.textContent = `✓ Terminé — ${p.done_podcasts} podcasts mis à jour · ${errCount} épisode${errCount>1?'s':''} non téléchargé${errCount>1?'s':''}`;
      statusEl.style.color = 'var(--accent)';
    } else {
      statusEl.textContent = `✓ ${p.done_podcasts} podcast${p.done_podcasts>1?'s':''} synchronisé${p.done_podcasts>1?'s':''}`;
      statusEl.style.color = 'var(--green)';
    }
  } else if (p.status === 'error') {
    statusEl.textContent = '✗ La synchronisation a rencontré un problème inattendu';
    statusEl.style.color = 'var(--red)';
  }

  // Barre podcasts
  const podPct = p.total_podcasts > 0 ? Math.round(p.done_podcasts / p.total_podcasts * 100) : 0;
  document.getElementById('prog-pod-fill').style.width = podPct + '%';
  document.getElementById('prog-pod-nums').textContent = `${p.done_podcasts} / ${p.total_podcasts}`;

  // Barre épisodes
  const epPct = p.total_episodes > 0 ? Math.round(p.done_episodes / p.total_episodes * 100) : 0;
  document.getElementById('prog-ep-fill').style.width  = epPct + '%';
  document.getElementById('prog-ep-nums').textContent  = `${p.done_episodes} / ${p.total_episodes}`;
  document.getElementById('prog-ep-label').textContent = p.current_label && p.status==='running' ? p.current_label : 'Épisodes';
}

function colorLine(line) {
  const e = document.createElement('span');
  e.textContent = line;
  if (/[Ee]rror|fail|ERR|PermissionError/.test(line)) e.className='log-err';
  else if (/[Ww]arn/.test(line))                      e.className='log-warn';
  else if (/Downloaded|Terminé|OK|Already/.test(line)) e.className='log-ok';
  return e.outerHTML;
}

async function pollLog() {
  const r   = await api({action:'ingest_log'}).catch(()=>({lines:[],running:false}));
  const box = document.getElementById('log-box');
  if (r.lines?.length) { box.innerHTML = r.lines.map(colorLine).join('\n'); box.scrollTop = box.scrollHeight; }
}

// ── Init ──────────────────────────────────────────────────
setMode(localStorage.getItem('hechicero_mode') || 'normal');
api({action:'ensure_radio_images'}).catch(()=>{});  // télécharge les images radio manquantes
loadStatus();
loadConfig();
loadParental();
loadPodcasts();
loadRadios();
document.getElementById('btn-save-parental').addEventListener('click', saveParental);
// Si une synchro était en cours (ex: rechargement de page), afficher la progression
api({action:'get_progress'}).then(p => {
  if (p && p.status !== 'idle') {
    document.getElementById('sync-idle').style.display     = 'none';
    document.getElementById('sync-progress').style.display = 'block';
    updateProgressUI(p);
    if (p.running || p.status === 'running') pollProgress();
  }
}).catch(()=>{});
setInterval(loadStatus, 15000);
</script>
</body>
</html>
