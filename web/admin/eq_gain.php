<?php
require_once __DIR__ . '/../bootstrap.php';  // TICKET-129 : fuseau Europe/Paris
// ============================================================
// Hechicero — Gain casque : lecture / écriture partagées
// ============================================================
//
// ── TICKET-119 — pourquoi ce fichier existe ────────────────────────────────
// Le gain casque est réglable depuis DEUX écrans : l'admin complète
// (`audio_eq.php`, depuis le téléphone) et l'écran technique caché
// (`technique.php`, à la dalle, sans réseau). Recopier la logique dans les deux
// aurait été le piège de la zone Z11 : deux IHM sur un même réglage divergent
// dès la première évolution, sans que rien ne plante.
//
// ⚠️ INVARIANT DE SÉCURITÉ AUDITIVE — le gain est borné à 0-6 dB, et il
// n'existe QUE pour le casque. Les haut-parleurs n'en ont pas : `speakers_max`
// ≤ 80 est un invariant du projet, et lui ouvrir un contournement par le gain
// reviendrait à le supprimer. Aucun appelant ne doit pouvoir dépasser ces
// bornes — c'est pourquoi le plafonnement est ICI et pas dans les pages.

define('EQ_CONFIG_PATH', dirname(__DIR__, 2) . '/data/audio_eq.json');
define('EQ_APPLY_SCRIPT', dirname(__DIR__, 2) . '/scripts/audio_eq_apply.py');
const GAIN_CASQUE_MIN = 0;
const GAIN_CASQUE_MAX = 6;


function eq_lire_config(): array
{
    if (!file_exists(EQ_CONFIG_PATH)) return ['profiles' => []];
    $d = json_decode((string)file_get_contents(EQ_CONFIG_PATH), true);
    return is_array($d) ? $d : ['profiles' => []];
}


function lire_gain_casque(): int
{
    $c = eq_lire_config();
    return (int)($c['profiles']['casque']['gain_db'] ?? 0);
}


/**
 * Écrit le gain casque et l'applique immédiatement.
 *
 * ⚠️ N'écrase QUE `gain_db` : la courbe d'égalisation (`bands_db`) et le preset
 * sont relus et réécrits tels quels. C'est la leçon de TICKET-124 — la forme et
 * le niveau ont été séparés précisément pour que régler l'un ne détruise pas
 * l'autre. Un écran qui ne montre que le gain ne doit pas pouvoir remettre les
 * dix bandes à plat.
 *
 * @return array{ok: bool, gain: int, msg: string}
 */
function ecrire_gain_casque(int $gain): array
{
    $gain = max(GAIN_CASQUE_MIN, min(GAIN_CASQUE_MAX, $gain));
    $config = eq_lire_config();
    if (!isset($config['profiles']['casque']) || !is_array($config['profiles']['casque'])) {
        return ['ok' => false, 'gain' => $gain, 'msg' => 'Profil casque absent de audio_eq.json'];
    }
    $config['profiles']['casque']['gain_db'] = $gain;
    $config['updated'] = date('c');

    $json = json_encode($config, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    if (file_put_contents(EQ_CONFIG_PATH, $json) === false) {
        return ['ok' => false, 'gain' => $gain, 'msg' => "Écriture de audio_eq.json refusée (permissions ?)"];
    }

    // Appliquer tout de suite : un réglage qui n'agit qu'au prochain
    // redémarrage est inutilisable en voiture, qui est le cas d'usage visé.
    $cmd = '/usr/bin/python3 ' . escapeshellarg(EQ_APPLY_SCRIPT)
         . ' --profile casque 2>&1';
    exec($cmd, $sortie, $code);
    if ($code !== 0) {
        return ['ok' => false, 'gain' => $gain,
                'msg' => 'Gain enregistré mais non appliqué : ' . implode(' ', array_slice($sortie, 0, 3))];
    }
    return ['ok' => true, 'gain' => $gain, 'msg' => 'Gain casque : ' . $gain . ' dB'];
}
