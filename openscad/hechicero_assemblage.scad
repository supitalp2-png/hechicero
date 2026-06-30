/* ============================================================
   HECHICERO — Modèle d'assemblage 3D
   Grundig Concert Boy 206 + Raspberry Pi 5 + HiFiBerry Amp4
   + Waveshare UPS HAT (D) + Écran 7" + 2× HP
   ============================================================

   AXES :
     X → largeur radio (gauche→droite)  360 mm
     Y → profondeur    (façade→dos)     110 mm
     Z → hauteur       (bas→haut)       210 mm

   Façade = plan Y = 0

   DÉCISIONS FAÇADE (2026-06-28) :
     - Bande vinyle gauche (GRUNDIG) conservée : ~50mm (VINYL_W, à confirmer)
     - Nouveau panneau bouleau 4mm : de X=VINYL_W jusqu'au montant droit
     - HP et écran centrés dans la zone du nouveau panneau
     - Bandes chromées haut/bas conservées

   TRANCHE DU DESSUS :
     - ~10 trous ronds ∅16mm + 1 fente rectangulaire + 1 petit trou
     - Boutons-poussoirs 16mm chrome vissés par dessous (type anti-vandale)
     - 1 bouton déjà installé (bouton RUN, fils rouge+bleu)

   FICHIERS EXTERNES (dans ./components/) :
     - NEW STEP/RASPBERRY_PI_5.STL   ← disponible, utilisé directement
     - hifiberry-amp2-1.0.1.step     ← footprint Amp2 ≈ Amp4, à convertir en STL
     (UPS HAT D et écran : blocs paramétriques)

   SOURCES dimensions :
     - Radio  : radiomuseum.org + mètre ruban Thomas (360×210×110mm confirmé)
     - HP     : mesures photos Thomas (membrane ∅38mm, frame ∅50mm)
     - Pi 5   : officiel raspberrypi.com (85×56mm)
     - UPS D  : waveshare.com (85×56mm)
     - Écran  : waveshare.com 7" HDMI (168×105mm PCB, 155×87mm actif)
     - VINYL_W: estimé ~50mm sur photos — À MESURER et confirmer
   ============================================================ */

$fn = 48;

// ============================================================
// PARAMÈTRES
// ============================================================

// --- Carcasse Grundig Concert Boy 206 ---
R_L  = 360;   // largeur extérieure
R_H  = 210;   // hauteur extérieure
R_P  = 110;   // profondeur extérieure
EP   = 7;     // épaisseur paroi
CH   = 33;    // hauteur bandes chromées haut/bas
RAY  = 6;     // rayon arrondi des coins

// --- Zone utile façade ---
ZU_Z0 = CH;
ZU_Z1 = R_H - CH;
ZU_H  = ZU_Z1 - ZU_Z0;   // ~144mm
ZU_L  = R_L - 2*EP;       // ~346mm

// --- Bande vinyle gauche (conservée) ---
// Largeur estimée sur photos. À CONFIRMER avec mesure avant découpe laser.
VINYL_W = 25;              // mm depuis le bord extérieur gauche (mesuré)

// --- Zone du nouveau panneau (droite de la bande vinyle) ---
PANEL_X0 = VINYL_W;                            // début panneau (X absolu)
PANEL_W  = R_L - VINYL_W - EP;                // ~303mm
PANEL_CX = VINYL_W + PANEL_W / 2;             // centre panneau ~201.5mm

// --- Trous tranche du dessus ---
BTN_D  = 16;    // diamètre trous boutons (∅16mm, à confirmer)
BTN_Y  = R_P - 30; // position Y (vers le dos, zone chrome)
BTN_N  = 10;    // nombre de trous ronds estimé

// --- Écran Waveshare 7" HDMI ---
EC_L   = 168;   // PCB largeur
EC_H   = 105;   // PCB hauteur
EC_EP  = 10;    // épaisseur
EC_AL  = 155;   // zone active largeur
EC_AH  = 87;    // zone active hauteur

// --- Haut-parleurs (mesurés sur photos + gabarit 2026-06-30) ---
HP_MEM_D      = 38;   // diamètre membrane
HP_FRAME_D    = 50;   // diamètre frame / découpe dans le panneau bois
HP_PROF       = 35;   // profondeur du driver
HP_CHASSIS_SQ = 50;   // chassis CARRÉ (côté) — repose sur la façade, 4 trous de fixation
HP_CHASSIS_EP = 5;    // épaisseur du chassis carré
HP_VIS_OFF    = 5;    // offset des trous de vis depuis le bord du chassis

// --- Raspberry Pi 5 (85×56mm officiel) ---
PI_L  = 85;
PI_W  = 56;
PI_EP = 17;

// --- HiFiBerry Amp4 (même footprint que Amp2 - 85×56mm) ---
HFB_L  = 85;
HFB_W  = 56;
HFB_EP = 14;

// --- Waveshare UPS HAT (D) (85×56mm - waveshare.com) ---
UPS_L  = 85;
UPS_W  = 56;
UPS_EP = 22;   // inclut le porte-batterie 21700

// --- Entretoises M2.5 ---
ENT_H = 11;

// ============================================================
// POSITIONS
// ============================================================

// Écran centré dans la zone panneau (hors bande vinyle)
EC_X = VINYL_W + (PANEL_W - EC_L) / 2;   // ~117.5mm
EC_Z = ZU_Z0 + (ZU_H - EC_H) / 2;
EC_Y = EP;

// HP symétriques par rapport au centre du panneau, hors bande vinyle
HP_Z  = ZU_Z0 + ZU_H / 2;
HP_LX = VINYL_W + HP_FRAME_D / 2 + 8;    // ~83mm (8mm de jeu bord vinyle)
HP_RX = 2 * PANEL_CX - HP_LX;            // ~320mm (symétrique)

// Stack Pi centré en X, au fond, centré en Z
ST_H = PI_EP + ENT_H + UPS_EP + ENT_H + HFB_EP;
ST_X = (R_L - PI_L) / 2;
ST_Y = EP + EC_EP + 22;
ST_Z = ZU_Z0 + (ZU_H - ST_H) / 2;

// ============================================================
// MODULES CARCASSE
// ============================================================

module arrondi_corps() {
    // Corps principal avec coins arrondis (minkowski approx)
    hull() {
        for (x = [RAY, R_L - RAY])
            for (z = [RAY, R_H - RAY])
                translate([x, 0, z])
                    rotate([-90, 0, 0])
                        cylinder(r=RAY, h=R_P);
    }
}

module corps_radio() {
    color([0.13, 0.11, 0.09], 0.22)
    difference() {
        arrondi_corps();
        // Évidement intérieur
        translate([EP, EP, EP])
            cube([R_L - 2*EP, R_P - EP, R_H - 2*EP]);
        // Panneau dos amovible
        translate([EP, R_P - EP - 0.1, EP])
            cube([R_L - 2*EP, EP + 0.2, R_H - 2*EP]);
    }
}

module bandes_chrome() {
    color([0.88, 0.84, 0.70])
    difference() {
        arrondi_corps();
        // Garder seulement les bandes haut et bas
        translate([EP, -1, CH])
            cube([R_L - 2*EP, R_P + 2, R_H - 2*CH]);
        // Évidement intérieur
        translate([EP, EP, EP])
            cube([R_L - 2*EP, R_P - EP, R_H - 2*EP]);
    }
}

module poignee() {
    color([0.76, 0.72, 0.60])
    translate([R_L/2, R_P/2, R_H]) {
        translate([-52, 0, 0]) cylinder(d=7, h=26);
        translate([ 52, 0, 0]) cylinder(d=7, h=26);
        translate([-52, 0, 24]) rotate([0, 90, 0])
            cylinder(d=7, h=104);
    }
}

module bande_vinyle() {
    // Bande vinyle/simili-cuir gauche conservée (avec logo GRUNDIG)
    color([0.10, 0.09, 0.09], 0.95)
    translate([0, 0, CH])
        cube([VINYL_W, EP + 1, R_H - 2*CH]);
}

module panneau_bois() {
    // Nouveau panneau contreplaqué bouleau 4mm (zone à découper laser)
    color([0.76, 0.60, 0.38], 0.5)
    translate([VINYL_W, -1, CH])
        cube([PANEL_W, 5, R_H - 2*CH]);
}

module trous_dessus() {
    // Visualisation des trous ∅16mm sur la tranche du dessus
    // (boutons-poussoirs chrome à visser)
    color([0.75, 0.75, 0.75])
    for (i = [0 : BTN_N - 1])
        translate([
            VINYL_W + 15 + i * ((PANEL_W - 30) / (BTN_N - 1)),
            BTN_Y,
            R_H + 1
        ])
            cylinder(d = BTN_D, h = 8);
    // Bouton déjà installé (RUN) — chrome, en bas à gauche du panneau
    color([0.90, 0.88, 0.85])
    translate([VINYL_W + 15, BTN_Y, R_H + 1])
        cylinder(d = BTN_D, h = 12);
}

module decoupes_facade() {
    // Ouverture écran
    translate([EC_X + (EC_L - EC_AL)/2 - 3, -1, EC_Z + (EC_H - EC_AH)/2 - 3])
        cube([EC_AL + 6, EP + 2, EC_AH + 6]);
    // Ouverture HP gauche
    translate([HP_LX, -1, HP_Z])
        rotate([-90, 0, 0])
            cylinder(d = HP_FRAME_D + 4, h = EP + 2);
    // Ouverture HP droit
    translate([HP_RX, -1, HP_Z])
        rotate([-90, 0, 0])
            cylinder(d = HP_FRAME_D + 4, h = EP + 2);
}

// ============================================================
// MODULES COMPOSANTS
// ============================================================

module ecran() {
    // PCB
    color([0.06, 0.08, 0.20])
    translate([EC_X, EC_Y, EC_Z])
        cube([EC_L, EC_EP, EC_H]);
    // Zone active
    color([0.12, 0.52, 0.88], 0.4)
    translate([EC_X + (EC_L - EC_AL)/2, EC_Y - 1, EC_Z + (EC_H - EC_AH)/2])
        cube([EC_AL, 2, EC_AH]);
    // Trous de fixation M3
    color([0.75, 0.75, 0.75])
    for (dx = [5.5, EC_L - 5.5])
        for (dz = [5.5, EC_H - 5.5])
            translate([EC_X + dx, EC_Y + EC_EP, EC_Z + dz])
                rotate([-90, 0, 0])
                    cylinder(d=3.2, h=5);
}

module hp_driver(cx) {
    // Chassis CARRÉ (constaté sur gabarit 2026-06-30)
    // Le chassis repose sur le panneau bois, la découpe est circulaire ∅46mm
    translate([cx, EP, HP_Z]) {
        rotate([-90, 0, 0]) {
            // Chassis carré plastique
            color([0.20, 0.18, 0.15])
            difference() {
                translate([-HP_CHASSIS_SQ/2, -HP_CHASSIS_SQ/2, 0])
                    cube([HP_CHASSIS_SQ, HP_CHASSIS_SQ, HP_CHASSIS_EP]);
                // Découpe centrale pour le driver
                translate([0, 0, -1]) cylinder(d = HP_FRAME_D - 2, h = HP_CHASSIS_EP + 2);
            }
            // 4 trous de vis aux coins du chassis
            color([0.55, 0.55, 0.55])
            for (sx = [-1, 1]) for (sy = [-1, 1])
                translate([sx * (HP_CHASSIS_SQ/2 - HP_VIS_OFF),
                           sy * (HP_CHASSIS_SQ/2 - HP_VIS_OFF), -1])
                    cylinder(d = 3.2, h = HP_CHASSIS_EP + 2);
            // Corps / aimant
            color([0.15, 0.14, 0.12])
            translate([0, 0, HP_CHASSIS_EP])
                cylinder(d = HP_MEM_D + 6, h = HP_PROF - HP_CHASSIS_EP);
            // Membrane
            color([0.22, 0.20, 0.17])
            translate([0, 0, HP_CHASSIS_EP - 2])
                cylinder(d = HP_MEM_D, h = 3);
        }
    }
}

module rpi5() {
    translate([ST_X, ST_Y, ST_Z]) {
        stl_path = "components/NEW STEP/RASPBERRY_PI_5.STL";
        color([0.15, 0.28, 0.65])
        import(stl_path, convexity=10);
    }
}

module rpi5_fallback() {
    // Utilisé si le STL ne charge pas
    color([0.15, 0.28, 0.65])
    translate([ST_X, ST_Y, ST_Z]) {
        cube([PI_L, PI_W, PI_EP]);
        color([0.50, 0.50, 0.50]) {
            translate([PI_L - 2, 8,  2]) cube([12, 16, 7]);
            translate([PI_L - 2, 28, 2]) cube([12, 16, 7]);
            translate([22, -4, 2]) cube([10, 5, 6]);
        }
    }
}

module ups_hat() {
    color([0.25, 0.45, 0.25])
    translate([ST_X, ST_Y, ST_Z + PI_EP + ENT_H]) {
        cube([UPS_L, UPS_W, UPS_EP]);
        // Porte-batterie 21700
        color([0.18, 0.18, 0.18])
        translate([10, 5, UPS_EP])
            cube([65, 25, 12]);
        // USB-C charge
        color([0.55, 0.55, 0.55])
        translate([8, -4, 2]) cube([9, 5, 6]);
    }
}

module hifiberry() {
    translate([ST_X, ST_Y, ST_Z + PI_EP + ENT_H + UPS_EP + ENT_H]) {
        // Utilise le STEP Amp2 si converti, sinon fallback
        color([0.25, 0.48, 0.25])
        cube([HFB_L, HFB_W, HFB_EP]);
        // Bornier HP (spécifique Amp4)
        color([0.60, 0.55, 0.10])
        translate([2, HFB_W, 2]) cube([28, 10, 10]);
    }
}

module entretoises(z_base) {
    color([0.80, 0.80, 0.80])
    for (dx = [3.5, PI_L - 3.5])
        for (dy = [3.5, PI_W - 3.5])
            translate([ST_X + dx, ST_Y + dy, z_base])
                cylinder(d=4, h=ENT_H);
}

// ============================================================
// ASSEMBLAGE
// ============================================================

// Carcasse
difference() {
    union() {
        corps_radio();
        bandes_chrome();
        poignee();
    }
    decoupes_facade();
}

// Façade
bande_vinyle();       // bande simili-cuir gauche conservée
panneau_bois();       // nouveau panneau bouleau (semi-transparent)
trous_dessus();       // boutons-poussoirs tranche du dessus

// Composants internes
ecran();
hp_driver(HP_LX);
hp_driver(HP_RX);

// Stack Pi — utilise le STL si disponible, sinon fallback
rpi5();
// rpi5_fallback();   // ← décommenter si le STL ne charge pas

entretoises(ST_Z + PI_EP);
ups_hat();
entretoises(ST_Z + PI_EP + ENT_H + UPS_EP);
hifiberry();

// ============================================================
// DEBUG
// ============================================================
// echo("Zone utile façade : ", ZU_L, "x", ZU_H, "mm");
// echo("Panneau bois      : ", PANEL_W, "x", ZU_H, "mm  (X0=", PANEL_X0, ")");
// echo("Stack Pi total H  : ", ST_H, "mm");
// echo("HP gauche X=", HP_LX, "  droit X=", HP_RX);
// echo("Écran X=", EC_X, "  Z=", EC_Z);
// echo("VINYL_W=", VINYL_W, "  — À CONFIRMER par mesure physique");
// %translate([0, 0, 0]) cube([R_L, R_P, R_H]); // boîte englobante
