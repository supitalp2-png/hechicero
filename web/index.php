<?php
// index.php - Hechicero battery dashboard (minimal, copy/paste)
header('Content-Type: text/html; charset=utf-8');
?>
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Hechicero - Batterie</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{font-family:Arial,Helvetica,sans-serif;padding:18px;max-width:720px;margin:auto}
h2{margin-bottom:6px}
.bar{width:100%;max-width:420px;height:28px;border:1px solid #ccc;border-radius:6px;overflow:hidden;background:#f3f3f3}
.fill{height:100%;background:linear-gradient(90deg,#6cc644,#2ea44f);width:0%;transition:width .6s}
.status{margin-top:10px;font-weight:600}
.alert{color:#b22222;font-weight:700}
.small{font-size:0.9em;color:#666;margin-top:6px}
.meta{margin-top:12px;font-size:0.85em;color:#444}
.refresh{margin-top:10px}
button{padding:6px 10px;border-radius:6px;border:1px solid #bbb;background:#fff;cursor:pointer}
</style>
</head>
<body>
<h2>Hechicero — État batterie</h2>
<div id="content">
  <div class="bar"><div id="fill" class="fill"></div></div>
  <div class="status" id="etat">Chargement…</div>
  <div class="small" id="detail">—</div>
  <div id="alert" class="alert" style="display:none;margin-top:8px"></div>
  <div class="meta" id="meta">Dernière mise à jour : —</div>
  <div class="refresh"><button id="btnRefresh">Rafraîchir</button></div>
</div>

<script>
const STATUS_URL = '/status.json';
async function refresh(){
  try{
    const r = await fetch(STATUS_URL + '?_=' + Date.now());
    if(!r.ok) throw new Error('no status');
    const s = await r.json();
    const pct = Number.isFinite(s.percent) ? s.percent : 0;
    document.getElementById('fill').style.width = pct + '%';
    document.getElementById('etat').textContent = (s.state||'—') + ' (' + (Number.isFinite(s.percent)? s.percent + '%' : '?') + ')';
    document.getElementById('detail').textContent = 'Courant: ' + (s.current_ma!==undefined? s.current_ma + ' mA' : '?') + ' • Tension: ' + (s.voltage_v!==undefined? s.voltage_v + ' V' : '?');
    document.getElementById('meta').textContent = 'Dernière mise à jour : ' + (s.ts? new Date(s.ts*1000).toLocaleString() : '—');
    if(s.alert){
      const a = document.getElementById('alert');
      a.style.display='block';
      a.textContent = s.alert;
    } else {
      document.getElementById('alert').style.display='none';
    }
  }catch(e){
    document.getElementById('etat').textContent = 'Données indisponibles';
    document.getElementById('detail').textContent = '';
    document.getElementById('meta').textContent = '';
    document.getElementById('alert').style.display='none';
  }
}
document.getElementById('btnRefresh').addEventListener('click', refresh);
refresh();
setInterval(refresh, 10000);
</script>
</body>
</html>
