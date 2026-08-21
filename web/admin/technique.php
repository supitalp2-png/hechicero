<?php
require_once __DIR__ . '/../bootstrap.php';   // TICKET-129 : fuseau Europe/Paris
require_once __DIR__ . '/eq_gain.php';
// ============================================================
// Hechicero — Écran technique caché (TICKET-119)
// Ouvert par un appui simultané de 3 s sur casque (GPIO25) + antenne (GPIO23)
// ============================================================
//
// ── À QUOI ÇA SERT ────────────────────────────────────────────────────────
// Cet écran est fait pour les moments où RIEN D'AUTRE n'est disponible : en
// mobilité, sans savoir l'IP du Pi, sans téléphone connecté au même réseau.
// D'où trois contenus et pas plus : les adresses IP, l'état de la batterie, et
// le gain casque — le seul réglage qu'on veuille vraiment ajuster en voiture.
//
// ⚠️ ÉCRAN PARENT. Il n'expose aucun secret (pas de jeton, pas d'identifiant de
// la passerelle domotique) et n'offre aucun contournement du contrôle parental.
// Il est protégé par l'obscurité de la combinaison, rien de plus : ne jamais y
// mettre quoi que ce soit dont la divulgation poserait problème.

// ── Sortie du kiosque ─────────────────────────────────────────────────────
// Traité AVANT toute sortie HTML : c'est une API, pas une page.
//
// ⚠️ Apache tourne en `www-data`, Chromium en `thomas` : la fermeture demande
// donc un droit explicite. Règle sudoers à poser à la main (volontairement
// étroite — pas de `ALL`, une seule commande, un seul motif) :
//
//   www-data ALL=(root) NOPASSWD: /usr/bin/pkill -u thomas -x chromium
//
// dans /etc/sudoers.d/hechicero-kiosque, en 0440.
//
// ⚠️ Décision de Thomas (2026-08-21) : PAS de relance automatique, et le
// redémarrage est sa porte de sortie assumée. Ce code s'arrête à la fermeture
// de Chromium — ce qui se passe ensuite sur le bureau ne le concerne pas.
if (($_GET['action'] ?? '') === 'quitter_kiosque' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    header('Content-Type: application/json; charset=utf-8');
    exec('sudo -n /usr/bin/pkill -u thomas -x chromium 2>&1', $sortie, $code);
    // pkill renvoie 1 quand aucun processus ne correspond : ce n'est pas une
    // erreur de droits, c'est que le kiosque n'était déjà plus là.
    if ($code === 0) {
        echo json_encode(['ok' => true]);
    } elseif ($code === 1) {
        echo json_encode(['ok' => true, 'msg' => 'Chromium ne tournait pas']);
    } else {
        echo json_encode(['ok' => false,
            'msg' => "Droit refusé — la règle sudoers /etc/sudoers.d/hechicero-kiosque manque. "
                   . implode(' ', array_slice($sortie, 0, 2))]);
    }
    exit;
}

$message = '';
$erreur  = false;

if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'gain') {
    $r = ecrire_gain_casque((int)($_POST['gain'] ?? 0));
    $message = $r['msg'];
    $erreur  = !$r['ok'];
}

$gain = lire_gain_casque();

/**
 * Adresses IPv4 de CHAQUE interface active.
 *
 * ⚠️ Toutes, pas seulement la première trouvée : c'est précisément quand elles
 * changent — bascule Wi-Fi domicile / partage de connexion / câble
 * USB-Ethernet — qu'on a besoin de cet écran. N'en montrer qu'une reviendrait à
 * être muet dans le seul cas qui justifie son existence.
 */
function adresses_ip(): array
{
    $out = [];
    exec('ip -4 -o addr show scope global 2>/dev/null', $lignes);
    foreach ($lignes as $l) {
        $c = preg_split('/\s+/', trim($l));
        if (count($c) >= 4) $out[$c[1]] = explode('/', $c[3])[0];
    }
    return $out;
}

/**
 * SSID du réseau Wi-Fi associé, et sa force de signal.
 *
 * Demandé par Thomas le 2026-08-21 : en mobilité, savoir SUR QUEL réseau on est
 * compte autant que l'adresse. Entre le Wi-Fi de la maison, le répéteur et le
 * partage de connexion du téléphone, une IP seule ne dit pas laquelle des trois
 * a été retenue — et c'est justement la question qu'on se pose.
 *
 * ⚠️ `iw` plutôt que `nmcli` : instantané, aucun accès au démon, et surtout
 * **aucun risque d'exposer un mot de passe** — `nmcli` sait les afficher.
 * Cet écran ne doit montrer que des informations sans conséquence
 * (cf. l'avertissement en tête de fichier).
 */
function reseau_wifi(): array
{
    $out = [];
    exec('iw dev wlan0 link 2>/dev/null', $lignes);
    foreach ($lignes as $l) {
        if (preg_match('/^\s*SSID:\s*(.+)$/', $l, $m))   $out['ssid'] = trim($m[1]);
        if (preg_match('/signal:\s*(-?\d+)/', $l, $m))    $out['signal'] = (int)$m[1];
        if (preg_match('/freq:\s*(\d+)/', $l, $m))        $out['freq'] = (int)$m[1];
    }
    return $out;
}

function etat_batterie(): array
{
    $p = dirname(__DIR__, 2) . '/data/battery_stats.json';
    if (!file_exists($p)) return [];
    $d = json_decode((string)file_get_contents($p), true);
    return is_array($d) ? $d : [];
}

$ips  = adresses_ip();
$wifi = reseau_wifi();
$bat = etat_batterie();
$age = null;
if (!empty($bat['last_updated'])) {
    try {
        $t = new DateTime($bat['last_updated']);
        $age = max(0, (new DateTime())->getTimestamp() - $t->getTimestamp());
    } catch (Exception $e) { $age = null; }
}
?><!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hechicero — technique</title>
<style>
  /* Dimensionné pour le DOIGT sur une dalle de 7 pouces (1024x600), pas pour
     une souris : cibles de 56 px minimum, pas de survol, pas de menu. */
  :root { --fond:#0b1017; --carte:#141c26; --trait:#243244; --texte:#e6edf5;
          --doux:#8ea3bb; --or:#d2a24c; --alerte:#e05c5c; }
  * { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
  body { margin:0; background:var(--fond); color:var(--texte);
         font-family:system-ui,-apple-system,"Segoe UI",sans-serif; padding:14px 16px 90px; }
  h1 { font-size:20px; margin:0 0 12px; color:var(--or); letter-spacing:.04em; }
  .carte { background:var(--carte); border:1px solid var(--trait); border-radius:12px;
           padding:14px 16px; margin-bottom:12px; }
  .carte h2 { font-size:13px; margin:0 0 10px; color:var(--doux);
              text-transform:uppercase; letter-spacing:.09em; font-weight:600; }
  .ligne { display:flex; justify-content:space-between; align-items:baseline;
           padding:7px 0; border-bottom:1px solid rgba(255,255,255,.05); font-size:17px; }
  .ligne:last-child { border-bottom:0; }
  .ligne .k { color:var(--doux); }
  .ligne .v { font-family:ui-monospace,monospace; font-size:19px; }
  .vide { color:var(--doux); font-style:italic; }
  input[type=range] { width:100%; height:56px; accent-color:var(--or); }
  .val { font-size:30px; font-weight:700; color:var(--or); text-align:center; margin:2px 0 6px; }
  button { width:100%; min-height:60px; font-size:18px; border-radius:12px;
           border:1px solid var(--trait); background:#1d2836; color:var(--texte); }
  button.primaire { background:var(--or); color:#1a1206; border-color:var(--or); font-weight:700; }
  button.danger  { background:transparent; color:var(--alerte); border-color:var(--alerte); }
  .msg { padding:10px 12px; border-radius:10px; margin-bottom:12px; font-size:15px;
         background:rgba(210,162,76,.13); border:1px solid rgba(210,162,76,.4); }
  .msg.err { background:rgba(224,92,92,.13); border-color:rgba(224,92,92,.45); }
  .barre { position:fixed; left:0; right:0; bottom:0; padding:12px 16px;
           background:linear-gradient(transparent,var(--fond) 30%); }
  .note { font-size:13px; color:var(--doux); margin-top:8px; line-height:1.45; }
</style>
</head>
<body>

<h1>Écran technique</h1>

<?php if ($message): ?>
  <div class="msg <?php echo $erreur ? 'err' : ''; ?>"><?php echo htmlspecialchars($message); ?></div>
<?php endif; ?>

<div class="carte">
  <h2>Adresses réseau</h2>
  <?php if (!empty($wifi['ssid'])): ?>
    <div class="ligne"><span class="k">Wi-Fi</span>
      <span class="v"><?php echo htmlspecialchars($wifi['ssid']); ?></span></div>
    <?php if (isset($wifi['signal'])): ?>
    <div class="ligne"><span class="k">Signal</span>
      <span class="v"><?php echo (int)$wifi['signal']; ?> dBm<?php
        // Repère de lecture : au-delà de −70 dBm le débit s'effondre, et c'est
        // la zone où les coupures de TICKET-109/110 se produisaient.
        echo $wifi['signal'] < -70 ? ' ⚠️' : '';
        echo isset($wifi['freq']) ? ' · ' . round($wifi['freq'] / 1000, 1) . ' GHz' : '';
      ?></span></div>
    <?php endif; ?>
  <?php else: ?>
    <div class="ligne"><span class="k">Wi-Fi</span>
      <span class="v vide">non associé</span></div>
  <?php endif; ?>
  <?php if (!$ips): ?>
    <div class="vide">Aucune interface active — l'appareil est hors réseau.</div>
  <?php else: foreach ($ips as $iface => $ip): ?>
    <div class="ligne"><span class="k"><?php echo htmlspecialchars($iface); ?></span>
      <span class="v"><?php echo htmlspecialchars($ip); ?></span></div>
  <?php endforeach; endif; ?>
</div>

<div class="carte">
  <h2>Alimentation</h2>
  <?php if (!$bat): ?>
    <div class="vide">Mesure indisponible.</div>
  <?php else: ?>
    <div class="ligne"><span class="k">Niveau</span>
      <span class="v"><?php echo (int)($bat['current_level'] ?? 0); ?> %</span></div>
    <?php if (isset($bat['level_table'])): ?>
    <div class="ligne"><span class="k">Table seule</span>
      <span class="v"><?php echo (int)$bat['level_table']; ?> %</span></div>
    <?php endif; ?>
    <div class="ligne"><span class="k">État</span>
      <span class="v"><?php echo !empty($bat['charging']) ? 'en charge' : 'sur batterie'; ?></span></div>
    <div class="ligne"><span class="k">Tension</span>
      <span class="v"><?php echo htmlspecialchars((string)($bat['voltage_v'] ?? '?')); ?> V</span></div>
    <div class="ligne"><span class="k">Courant</span>
      <span class="v"><?php echo sprintf('%+d', (int)($bat['current_ma'] ?? 0)); ?> mA</span></div>
    <?php if ($age !== null && $age > 180): ?>
    <div class="ligne"><span class="k">⚠️ Mesure figée</span>
      <span class="v"><?php echo (int)round($age / 60); ?> min</span></div>
    <?php endif; ?>
  <?php endif; ?>
</div>

<form method="post" class="carte">
  <h2>Gain casque</h2>
  <input type="hidden" name="action" value="gain">
  <div class="val" id="val"><?php echo $gain; ?> dB</div>
  <input type="range" name="gain" id="gain" min="<?php echo GAIN_CASQUE_MIN; ?>"
         max="<?php echo GAIN_CASQUE_MAX; ?>" step="1" value="<?php echo $gain; ?>"
         oninput="document.getElementById('val').textContent = this.value + ' dB'">
  <button type="submit" class="primaire">Appliquer</button>
  <div class="note">Ne concerne que le casque, et jamais les haut-parleurs :
    leur limite est un garde-fou auditif. À n'augmenter que si le volume MPD
    est déjà au maximum et que le son reste faible.</div>
</form>

<div class="carte">
  <h2>Kiosque</h2>
  <button class="danger" onclick="quitterKiosque()">Quitter le kiosque</button>
  <div class="note">Ferme Chromium et rend la main au bureau.
    <strong>Seul un redémarrage ramène la radio.</strong></div>
</div>

<div class="barre">
  <button class="primaire" onclick="location.href='/lecteur/'">← Retour à la radio</button>
</div>

<script>
// ── Retour automatique à la radio (TICKET-119) ────────────────────────────
// Demande de Thomas : « le passage en écran de veille fait ressortir de cette
// page ». Comme on a quitté le lecteur, son minuteur de veille ne tourne plus —
// cette page porte donc le sien, calé sur le MÊME délai (screen_off_delay).
// Sans ça, l'appareil resterait bloqué sur un écran d'administration, et
// l'enfant retrouverait des réglages au lieu de ses podcasts.
let minuteur = null;
async function armerRetour() {
  let delai = 600;
  try {
    const r = await fetch('/lecteur/config.json', { cache: 'no-store' });
    const c = await r.json();
    delai = Number(c.screen_off_delay ?? 600);
  } catch (_) {}
  const reArmer = () => {
    clearTimeout(minuteur);
    minuteur = setTimeout(() => { location.href = '/lecteur/'; }, delai * 1000);
  };
  ['click', 'keydown', 'input'].forEach(e =>
    document.addEventListener(e, reArmer, { capture: true, passive: true }));
  reArmer();
}
armerRetour();

async function quitterKiosque() {
  if (!confirm("Fermer Chromium ?\n\nSeul un redémarrage ramènera la radio.")) return;
  try {
    const r = await fetch('?action=quitter_kiosque', { method: 'POST' });
    const d = await r.json();
    if (!d.ok) alert("Échec : " + (d.msg || 'inconnu'));
  } catch (e) { alert("Échec : " + e); }
}
</script>
</body>
</html>
