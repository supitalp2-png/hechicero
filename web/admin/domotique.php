<?php
// ============================================================
// Hechicero — Admin domotique Chambre (TICKET-113)
// Reprend le look de l'écran Chambre de l'IHM enfant (TICKET-112) pour un
// pilotage/consultation depuis l'admin (téléphone). Parle à la passerelle
// domotique — AUCUN secret ici : seulement l'IP LAN et les 2 routes
// génériques /lampe /volet (la passerelle détient seule tokens et IDs Netatmo).
// Extensible plus tard avec des règles d'admin (ex. volet 8h-19h, veilleuse
// nuit auto-extinction 10 min) — cf. bloc "Règles (à venir)" en bas.
// ============================================================
$currentPage = basename($_SERVER['PHP_SELF'] ?? 'domotique.php');
?><!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Hechicero · Domotique</title>
  <link rel="stylesheet" href="/css/hechicero-admin.css">
  <style>
    :root { --ch-cyan:#00c8ff; }
    .ch-status { font-size:.95rem; color:var(--muted,#8a97a3); }
    .ch-status.off { color:#ff6b6b; }
    .ch-wrap { display:flex; gap:22px; flex-wrap:wrap; align-items:stretch; }
    .ch-card {
      flex:1 1 340px; max-width:470px;
      background:var(--surface,#131c2b); border:1.5px solid var(--border,#22304a);
      border-radius:18px; padding:18px 20px; display:flex; flex-direction:column;
    }
    .ch-head { display:flex; align-items:center; gap:12px; margin-bottom:10px; }
    .ch-title { font-size:1.5rem; font-weight:600; margin-right:auto; color:var(--text,#e6edf3); }
    .ch-val { font-size:2.4rem; font-weight:700; color:var(--ch-cyan); font-variant-numeric:tabular-nums; }
    .ch-badge {
      font-size:.85rem; padding:4px 14px; border-radius:20px;
      background:rgba(0,200,255,.15); color:var(--ch-cyan); visibility:hidden; white-space:nowrap;
    }
    .ch-row { display:flex; gap:18px; align-items:center; justify-content:center; flex:1; }
    .ch-col { display:flex; flex-direction:column; align-items:center; gap:10px; }
    .ch-tap { cursor:pointer; -webkit-tap-highlight-color:transparent; }
    .ch-tap:active { transform:scale(.94); }
    .ch-icon-bulb { width:150px; height:auto; display:block; }
    .ch-icon-volet { width:178px; height:auto; display:block; }
    .ch-hint { font-size:.95rem; color:var(--muted,#8a97a3); }
    .ch-end { font-size:.95rem; color:var(--muted,#8a97a3); }
    .ch-sun { display:block; color:#e0b878; }
    .ch-sun-lg { width:36px; height:36px; }
    .ch-sun-sm { width:24px; height:24px; color:#b89968; }
    .ch-slider-col { justify-content:center; gap:8px; }
    .ch-vbox { width:64px; height:186px; display:flex; align-items:center; justify-content:center; }
    .ch-vbox input {
      -webkit-appearance:none; appearance:none;
      width:186px; height:14px; margin:0; border-radius:8px;
      background:var(--border,#22304a); transform:rotate(-90deg); cursor:pointer;
    }
    .ch-vbox input::-webkit-slider-thumb {
      -webkit-appearance:none; appearance:none;
      width:46px; height:46px; border-radius:50%;
      background:var(--ch-cyan); border:3px solid #0c1014; box-shadow:0 2px 8px rgba(0,0,0,.4);
    }
    .ch-vbox input::-moz-range-thumb {
      width:46px; height:46px; border:3px solid #0c1014; border-radius:50%; background:var(--ch-cyan);
    }
  </style>
</head>
<body>
  <div class="ha-page">
    <div class="ha-header">
      <div>
        <h1>🏠 Domotique — Chambre</h1>
        <div class="ha-subtitle">Lumière et volet de la chambre</div>
      </div>
      <nav class="ha-nav">
        <a class="ha-btn" href="/"><span class="ha-btn-icon">‹</span> Bureau</a>
        <a class="ha-btn" href="/lecteur/" target="_blank"><span class="ha-btn-icon">📻</span> Lecteur</a>
      </nav>
    </div>

    <div style="margin-bottom:12px"><span class="ch-status" id="ch-status">Connexion…</span></div>

    <div class="ch-wrap">
      <!-- Lumière -->
      <div class="ch-card">
        <div class="ch-head">
          <span class="ch-title">Lumière</span>
          <span class="ch-val" id="ch-lumOut">–</span>
        </div>
        <div class="ch-row">
          <div class="ch-col">
            <svg class="ch-tap ch-icon-bulb" id="ch-bulbBtn" viewBox="0 0 120 130" role="button" aria-label="Allumer ou éteindre">
              <circle id="ch-halo" cx="60" cy="52" r="40" fill="#ffd873" opacity="0.4"/>
              <path id="ch-bulb" d="M60 16 a30 30 0 0 1 30 30 c0 14 -9 22 -15 30 l-30 0 c-6 -8 -15 -16 -15 -30 a30 30 0 0 1 30 -30 z" fill="#3a3f45" stroke="#5a6068" stroke-width="1.5"/>
              <rect x="47" y="90" width="26" height="8" rx="2" fill="#5a6068"/>
              <rect x="49" y="100" width="22" height="7" rx="2" fill="#5a6068"/>
              <rect x="52" y="109" width="16" height="7" rx="2" fill="#5a6068"/>
            </svg>
            <div class="ch-hint">appuyer = on / off</div>
          </div>
          <div class="ch-col ch-slider-col">
            <svg class="ch-sun ch-sun-lg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-label="Plus fort">
              <circle cx="12" cy="12" r="5"/>
              <path d="M12 1v3M12 20v3M1 12h3M20 12h3"/>
            </svg>
            <div class="ch-vbox"><input type="range" id="ch-lum" min="1" max="100" step="1" value="50" aria-label="Intensité"></div>
            <svg class="ch-sun ch-sun-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-label="Plus doux">
              <circle cx="12" cy="12" r="3.6"/>
              <path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3"/>
            </svg>
          </div>
        </div>
      </div>

      <!-- Volet -->
      <div class="ch-card">
        <div class="ch-head">
          <span class="ch-title">Volet</span>
          <span class="ch-badge" id="ch-moving">en mouvement</span>
          <span class="ch-val" id="ch-posOut">–</span>
        </div>
        <div class="ch-row">
          <div class="ch-col">
            <svg class="ch-tap ch-icon-volet" id="ch-voletBtn" viewBox="0 0 260 300" role="button" aria-label="Ouvrir ou fermer">
              <rect x="20" y="20" width="220" height="240" rx="6" fill="#123a4f"/>
              <rect x="20" y="20" width="220" height="240" rx="6" fill="none" stroke="#2b556b" stroke-width="2"/>
              <line x1="130" y1="20" x2="130" y2="260" stroke="#2b556b" stroke-width="3"/>
              <line x1="20" y1="140" x2="240" y2="140" stroke="#2b556b" stroke-width="3"/>
              <g id="ch-slats"></g>
              <rect x="14" y="14" width="232" height="252" rx="8" fill="none" stroke="#3a3f45" stroke-width="6"/>
              <rect x="30" y="262" width="200" height="14" rx="3" fill="#3a3f45"/>
            </svg>
            <div class="ch-hint">appuyer = ouvre / ferme</div>
          </div>
          <div class="ch-col ch-slider-col">
            <span class="ch-end">↑ ouvert</span>
            <div class="ch-vbox"><input type="range" id="ch-pos" min="0" max="100" step="1" value="0" aria-label="Position"></div>
            <span class="ch-end">↓ fermé</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Règles (à venir, TICKET-113) — placeholder pour de futures fonctions
         d'administration domotique : volet ouvrable seulement 8h-19h,
         veilleuse nuit avec extinction auto 10 min, etc. Rien d'actif pour
         l'instant, on garde juste la place et l'intention. -->
  </div>

<script>
// Logique reprise de l'écran Chambre du lecteur (TICKET-112). Aucun secret :
// seulement l'IP LAN de la passerelle et les routes génériques.
const CH_GW = 'http://192.168.1.3:8000';
const $ = id => document.getElementById(id);
let chLampOn = false, chLastLum = 100;
let chDispP = 0, chSrvP = 0, chTargetP = 0, chSrvMoving = false;
let chAnim = null, chFastPoll = null, chReconcile = null, chLumTimer = null, chPosTimer = null;

function chSetStatus(txt, off){ const s=$('ch-status'); s.textContent=txt; s.classList.toggle('off', !!off); }

async function chApi(path, method='GET', body){
  const opt={ method, headers:{} };
  if(body){ opt.headers['Content-Type']='application/json'; opt.body=JSON.stringify(body); }
  const ctrl=new AbortController(); const t=setTimeout(()=>ctrl.abort(),6000); opt.signal=ctrl.signal;
  try{
    const r=await fetch(CH_GW+path,opt); clearTimeout(t);
    if(!r.ok) throw new Error('HTTP '+r.status);
    chSetStatus('Passerelle connectée'); return await r.json();
  }catch(e){ clearTimeout(t); chSetStatus('Passerelle hors ligne', true); throw e; }
}

// Éteinte = ampoule grise, pas de halo. Allumée = ampoule jaune + halo dont
// la taille/opacité suit l'intensité (spec Thomas 2026-07-24). Lit l'état
// (chLampOn) et la valeur du curseur.
function chDrawLum(){
  const v=+$('ch-lum').value, halo=$('ch-halo'), bulb=$('ch-bulb');
  if(chLampOn){
    $('ch-lumOut').textContent=v+' %';
    bulb.setAttribute('fill','#ffd34d');
    halo.setAttribute('opacity',(0.15+v/100*0.75).toFixed(2));
    halo.setAttribute('r',(28+v/100*26).toFixed(0));
  }else{
    $('ch-lumOut').textContent='éteinte';
    bulb.setAttribute('fill','#3a3f45');
    halo.setAttribute('opacity','0');
  }
}

const CH_topY=22, CH_fullH=236, CH_left=22, CH_right=238, CH_nSlats=14, CH_gap=236/14;
function chDrawVolet(){
  $('ch-posOut').textContent=Math.round(chDispP)+' %';
  const closedFrac=(100-chDispP)/100, coverH=CH_fullH*closedFrac;
  let s='';
  if(coverH>1){
    const covered=Math.max(1,Math.round(CH_nSlats*closedFrac)), openness=chDispP/100;
    const sy=Math.max(2.5, CH_gap*(1-openness*0.7));
    const lg=Math.round(40+openness*110);
    const col='rgb('+lg+','+(lg+14)+','+(lg+24)+')';
    for(let i=0;i<covered;i++){
      const cy=CH_topY+CH_gap*i+CH_gap/2;
      s+='<rect x="'+CH_left+'" y="'+(cy-sy/2)+'" width="'+(CH_right-CH_left)+'" height="'+sy.toFixed(1)+'" rx="1.5" fill="'+col+'" stroke="#0f1a22" stroke-width="0.6"/>';
    }
  }
  $('ch-slats').innerHTML=s;
  $('ch-moving').style.visibility=chSrvMoving?'visible':'hidden';
}

async function chPollOnce(){
  try{ const d=await chApi('/volet'); chSrvP=d.position; chSrvMoving=!!d.moving; if(!chSrvMoving) chDrawVolet(); }catch(e){}
}
function chStartTracking(){
  clearInterval(chFastPoll); clearTimeout(chReconcile);
  chSrvMoving=true; chDrawVolet();
  const started=Date.now();
  chFastPoll=setInterval(async ()=>{
    await chPollOnce();
    const nearTarget=Math.abs(chSrvP-chTargetP)<=3, timedOut=Date.now()-started>40000;
    if((!chSrvMoving && nearTarget) || timedOut){
      clearInterval(chFastPoll);
      chReconcile=setTimeout(chPollOnce, 20000);
    }
  }, 700);
}
function chCommandVolet(pos){
  chTargetP=pos; $('ch-pos').value=pos; chSrvMoving=true; chDrawVolet();
  chApi('/volet','POST',{position:pos}).then(chStartTracking).catch(()=>{});
}

const L=$('ch-lum');
// Bouger le curseur allume TOUJOURS la lampe à la valeur choisie (même si
// elle était éteinte) ; au plus bas = intensité minimale, pas éteinte.
L.addEventListener('input',()=>{
  const v=+L.value; chLampOn=true; chLastLum=v; chDrawLum();
  clearTimeout(chLumTimer);
  chLumTimer=setTimeout(()=>chApi('/lampe','POST',{on:true, brightness:v}).catch(()=>{}), 350);
});
// Appui sur l'ampoule = allume/éteint. À l'allumage, on reprend la dernière
// intensité connue.
$('ch-bulbBtn').addEventListener('click', async ()=>{
  chLampOn=!chLampOn;
  if(chLampOn){
    const v=chLastLum>0?chLastLum:100; L.value=v; chDrawLum();
    chApi('/lampe','POST',{on:true, brightness:v}).catch(()=>{});
  }else{
    chDrawLum();
    chApi('/lampe','POST',{on:false}).catch(()=>{});
  }
});
const P=$('ch-pos');
P.addEventListener('input',()=>{
  chTargetP=+P.value; chSrvMoving=true; chDrawVolet();
  clearTimeout(chPosTimer);
  chPosTimer=setTimeout(()=>chCommandVolet(chTargetP), 300);
});
// Toggle volet = consigne : ouvert (100) -> 0 ; sinon -> 100 (cf. TICKET-112).
$('ch-voletBtn').addEventListener('click', ()=> chCommandVolet(chTargetP>=100?0:100));

// Animation continue : la position affichée glisse vers la position serveur.
chAnim=setInterval(()=>{
  if(Math.abs(chDispP-chSrvP)>0.3){
    chDispP += (chSrvP>chDispP?1:-1)*Math.min(1.5,Math.abs(chSrvP-chDispP));
    chDrawVolet();
  }
}, 40);

(async function init(){
  try{
    const l=await chApi('/lampe'); chLampOn=!!l.on;
    chLastLum=(l.brightness>0)?l.brightness:100;
    L.value=chLampOn?(l.brightness>0?l.brightness:chLastLum):chLastLum;
    chDrawLum();
  }
  catch(e){ chLampOn=false; chDrawLum(); }
  try{ const d=await chApi('/volet'); chSrvP=chDispP=chTargetP=d.position; chSrvMoving=!!d.moving; $('ch-pos').value=d.position; chDrawVolet(); if(chSrvMoving) chStartTracking(); }
  catch(e){ chDrawVolet(); }
})();
</script>
</body>
</html>
