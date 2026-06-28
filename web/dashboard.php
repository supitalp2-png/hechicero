<?php
$currentPage = basename($_SERVER['PHP_SELF'] ?? 'dashboard.php');
?><!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Hechicero Dashboard</title>
  <link rel="stylesheet" href="/css/hechicero-admin.css">
  <style>
    .logo { font-size: 20px; font-weight: 700; letter-spacing: 0.04em; }
    .period-select {
      border: 1px solid var(--border);
      background: var(--surface-2);
      border-radius: 12px;
      color: var(--text);
      padding: 10px 14px;
      font-size: 14px;
    }

    h1 {
      margin: 0 0 16px;
      font-size: clamp(30px, 4vw, 44px);
      line-height: 1.06;
    }
    h2 { margin: 0 0 14px; font-size: 20px; }

    .toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 18px;
    }
    .muted { color: var(--muted); }

    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }
    .card {
      border: 1px solid var(--border);
      border-radius: 16px;
      background: linear-gradient(180deg, rgba(30, 41, 59, 0.68), rgba(17, 24, 39, 0.94));
      padding: 16px;
      min-height: 110px;
    }
    .card-label {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      margin-bottom: 8px;
    }
    .card-value {
      font-size: clamp(24px, 3vw, 34px);
      font-weight: 700;
      line-height: 1.1;
    }

    .chart-legend {
      display: flex;
      gap: 16px;
      margin-top: 8px;
      font-size: 12px;
      color: var(--muted);
    }
    .legend-dot {
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 2px;
      vertical-align: middle;
      margin-right: 4px;
    }
    .bar-track {
      height: 14px;
      border-radius: 999px;
      background: #0b1220;
      border: 1px solid rgba(100, 116, 139, 0.22);
      overflow: hidden;
    }
    .bar-fill { height: 100%; border-radius: 999px; }
    .bar-fill.fr { background: linear-gradient(90deg, rgba(74, 158, 255, 0.45), var(--fr)); }
    .bar-fill.es { background: linear-gradient(90deg, rgba(201, 162, 39, 0.45), var(--es)); }
    .bar-minutes {
      color: var(--muted);
      font-variant-numeric: tabular-nums;
      min-width: 66px;
      text-align: right;
    }

    .funnel-wrap { display: grid; gap: 10px; }
    .funnel-row {
      display: grid;
      grid-template-columns: 220px 1fr 52px;
      gap: 10px;
      align-items: center;
    }
    .funnel-label { font-size: 13px; }
    .funnel-bar-track {
      height: 18px;
      border-radius: 999px;
      background: #0b1220;
      border: 1px solid rgba(100, 116, 139, 0.22);
      overflow: hidden;
      position: relative;
    }
    .funnel-bar {
      height: 100%;
      border-radius: 999px;
      transition: width .2s;
    }
    .funnel-pct {
      text-align: right;
      font-variant-numeric: tabular-nums;
      font-weight: 700;
    }
    .funnel-count {
      color: var(--muted);
      font-size: 12px;
      margin-top: 3px;
    }

    .heatmap-box {
      background: var(--kibana-bg);
      border: 1px solid rgba(30, 41, 59, 0.9);
      border-radius: 12px;
      padding: 10px;
      overflow-x: auto;
    }
    #heatmap-grid {
      display: grid;
      grid-template-columns: 42px repeat(7, 28px);
      gap: 3px;
      align-items: center;
      width: max-content;
      min-width: 100%;
    }
    .hm-head, .hm-hour {
      color: var(--muted);
      font-size: 10px;
      text-align: center;
    }
    .hm-hour { text-align: right; padding-right: 4px; }
    .hm-cell {
      width: 28px;
      height: 20px;
      border-radius: 3px;
      border: 1px solid rgba(30, 41, 59, 0.45);
      background: rgba(201, 162, 39, 0);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }
    th, td {
      border-bottom: 1px solid rgba(30, 41, 59, 0.8);
      padding: 10px;
      text-align: left;
      vertical-align: top;
    }
    th {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .06em;
    }
    tbody tr:hover { background: rgba(30, 41, 59, 0.24); }

    .lang-pill {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 40px;
      padding: 4px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      color: #08111f;
    }
    .lang-pill.fr { background: var(--fr); }
    .lang-pill.es { background: var(--es); }

    .status-ok { color: var(--ok); font-weight: 700; }
    .status-warn { color: var(--warn); font-weight: 700; }
    .error {
      border-color: rgba(239, 68, 68, 0.45);
      background: rgba(127, 29, 29, 0.15);
      color: #fecaca;
      margin-bottom: 18px;
    }

    @media (max-width: 980px) {
      .funnel-row { grid-template-columns: 1fr; }
      .funnel-pct { text-align: left; }
    }
    @media (max-width: 640px) {
      .ha-header, .toolbar { align-items: stretch; }
      .day-row { grid-template-columns: 1fr; }
      .lang-row { grid-template-columns: 24px 1fr auto; }
      table, thead, tbody, tr, th, td { display: block; }
      thead { display: none; }
      tbody tr { padding: 8px 0; border-bottom: 1px solid rgba(30, 41, 59, 0.8); }
      tbody td { border: 0; padding: 4px 0; }
    }
  </style>
</head>
<body>
  <div class="ha-page">
    <div class="ha-header">
      <div class="logo">⚙ Hechicero</div>
      <nav class="ha-nav">
        <a class="ha-btn <?php echo $currentPage === 'index.php' ? 'active' : ''; ?>" href="/">
          <span class="ha-btn-icon">⚙</span> Admin
        </a>
        <a class="ha-btn <?php echo $currentPage === 'dashboard.php' ? 'active' : ''; ?>" href="/dashboard.php">
          <span class="ha-btn-icon">📊</span> Écoute
        </a>
        <a class="ha-btn <?php echo $currentPage === 'battery_dashboard.php' ? 'active' : ''; ?>" href="/admin/battery_dashboard.php">
          <span class="ha-btn-icon">🔋</span> Batterie
        </a>
        <a class="ha-btn" href="/lecteur/" target="_blank">
          <span class="ha-btn-icon">📻</span> Lecteur
        </a>
      </nav>
    </div>

    <h1>📊 Dashboard d'écoute</h1>

    <div class="toolbar">
      <div class="muted">Audimat podcast: langues, complétion, moments d'écoute et fidélité.</div>
      <label>
        <select id="period" class="period-select">
          <option value="7">7 derniers jours</option>
          <option value="30">30 derniers jours</option>
          <option value="90">90 derniers jours</option>
        </select>
      </label>
    </div>

    <div id="error-box" class="ha-panel error" style="display:none"></div>

    <div class="ha-grid ha-cols-auto cards">
      <div class="card">
        <div class="card-label">Total écouté</div>
        <div id="card-total-heures" class="card-value">…</div>
      </div>
      <div class="card">
        <div class="card-label">Épisodes lancés</div>
        <div id="card-total-episodes" class="card-value">…</div>
      </div>
      <div class="card">
        <div class="card-label">Terminés</div>
        <div id="card-completed" class="card-value">…</div>
      </div>
      <div class="card">
        <div class="card-label">Part espagnol</div>
        <div id="card-pct-es" class="card-value">…</div>
      </div>
      <div class="card">
        <div class="card-label">🔥 Série en cours</div>
        <div id="card-streak" class="card-value">…</div>
      </div>
    </div>

    <div class="ha-grid ha-cols-2" style="margin-bottom:18px;">
      <section class="ha-panel">
        <h2>Temps par langue par jour</h2>
        <div id="chart" class="ha-chart"></div>
      </section>

      <section class="ha-panel">
        <h2>Moyenne par jour de la semaine</h2>
        <div id="dow-wrap" class="ha-chart"></div>
      </section>
    </div>

    <div class="ha-grid ha-cols-2" style="margin-bottom:18px">
      <section class="ha-panel">
        <h2>📻 Webradio — écoute par langue</h2>
        <div id="radio-cards" class="ha-grid ha-cols-auto cards" style="grid-template-columns:repeat(3,1fr);margin-bottom:14px"></div>
        <div id="radio-chart"></div>
      </section>
      <section class="ha-panel">
        <h2>📻 Top stations</h2>
        <div id="radio-stations-wrap"></div>
      </section>
    </div>

    <div class="ha-grid ha-cols-2" style="margin-bottom:18px;">
      <section class="ha-panel" style="grid-column:1/-1">
        <h2>Top podcasts</h2>
        <div id="top-pods-wrap"></div>
      </section>
    </div>

    <div class="ha-grid ha-cols-2" style="margin-bottom:18px;">
      <section class="ha-panel">
        <h2>Jusqu'où écoute-t-il ?</h2>
        <div id="funnel-wrap" class="funnel-wrap"></div>
      </section>

      <section class="ha-panel">
        <h2>Quand écoute-t-il ?</h2>
        <div class="heatmap-box">
          <div id="heatmap-grid"></div>
        </div>
      </section>
    </div>

    <section class="ha-panel" style="margin-bottom:18px">
      <h2>Épisodes favoris</h2>
      <div id="top-episodes-wrap"></div>
    </section>

    <section class="ha-panel">
      <h2>Épisodes récents</h2>
      <div id="recent-wrap"></div>
    </section>
  </div>

  <script>
    const podcastTitles = Object.create(null);
    const episodeTitles = Object.create(null);

    function qs(id) { return document.getElementById(id); }

    function showError(message) {
      const box = qs('error-box');
      box.textContent = message;
      box.style.display = message ? 'block' : 'none';
    }

    function formatMinutes(minutes) {
      const m = Number(minutes || 0);
      if (m >= 60) {
        const h = Math.floor(m / 60);
        const rem = Math.round(m % 60);
        return rem > 0 ? `${h}h${String(rem).padStart(2,'0')}` : `${h}h`;
      }
      return `${m.toFixed(0)} min`;
    }

    function formatSeconds(seconds) {
      const total = Math.max(0, Math.round(Number(seconds || 0)));
      const h = Math.floor(total / 3600);
      const m = Math.floor((total % 3600) / 60);
      const s = total % 60;
      if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
      return `${m}:${String(s).padStart(2, '0')}`;
    }

    function formatDateLabel(day) {
      const parts = String(day || '').split('-');
      if (parts.length !== 3) return day || '—';
      return `${parts[2]}/${parts[1]}`;
    }

    function podcastLabel(id) {
      return podcastTitles[id] || id || '—';
    }

    function episodeLabel(podcastId, episodeId) {
      if (episodeTitles[podcastId] && episodeTitles[podcastId][episodeId]) {
        return episodeTitles[podcastId][episodeId];
      }
      return episodeId || '—';
    }

    async function loadPodcastTitles() {
      try {
        const response = await fetch('/lecteur/data.json', { cache: 'no-store' });
        if (!response.ok) return;
        const data = await response.json();
        for (const pod of data.podcasts || []) {
          podcastTitles[pod.id] = pod.titre || pod.id;
          episodeTitles[pod.id] = Object.create(null);
          for (const ep of pod.chapitres || []) {
            episodeTitles[pod.id][ep.id] = ep.titre || ep.id;
          }
        }
      } catch (_) {}
    }

    function renderSummary(summary, streak) {
      const totalEpisodes = Number(summary.total_episodes || 0);
      const completed = Number(summary.episodes_termines || 0);
      const pctCompleted = totalEpisodes > 0 ? Math.round((completed * 100) / totalEpisodes) : 0;
      qs('card-total-heures').textContent = `${Number(summary.total_heures || 0).toFixed(1)} h`;
      qs('card-total-episodes').textContent = String(totalEpisodes);
      qs('card-completed').textContent = `${pctCompleted} %`;
      qs('card-pct-es').textContent = `${Math.round(Number(summary.pct_es || 0))} %`;
      qs('card-streak').textContent = `${Number(streak || 0)} jour(s)`;
    }

    // Constantes de couleur (hardcodées pour SVG, coherent avec les CSS vars)
    const COLOR_FR = '#4a9eff';
    const COLOR_ES = '#c9a227';

    function makeBarChartSVG(rows) {
      if (!rows || !rows.length) return '<div class="ha-empty">Aucune écoute sur la période.</div>';

      const grouped = new Map();
      for (const row of rows) {
        const day = row.jour || '—';
        if (!grouped.has(day)) grouped.set(day, { fr: 0, es: 0 });
        const t = grouped.get(day);
        const lang = String(row.langue || 'fr').toLowerCase();
        if (lang === 'es') t.es = Number(row.minutes || 0);
        else t.fr = Number(row.minutes || 0);
      }

      const days = [...grouped.keys()].sort();
      const n = days.length;

      const maxVal = Math.max(...days.map(d => (grouped.get(d).fr || 0) + (grouped.get(d).es || 0)), 1);
      const axisMax = (Math.ceil(maxVal / 10) * 10) || 10;

      // Dimensions
      const ML = 42, MR = 10, MT = 10, MB = 40;
      const chartH = 180;
      const totalH = chartH + MT + MB;
      const barGap = 3;
      const barW = Math.min(32, Math.max(7, Math.floor((860 - ML - MR) / n) - barGap));
      const slotW = barW + barGap;
      const totalW = ML + n * slotW + MR;

      const parts = [];

      // Grille Y
      const yTicks = 4;
      for (let i = 0; i <= yTicks; i++) {
        const v = Math.round(axisMax * i / yTicks);
        const y = +(MT + chartH - (v / axisMax) * chartH).toFixed(1);
        parts.push(`<line x1="${ML}" y1="${y}" x2="${(totalW - MR)}" y2="${y}" stroke="rgba(100,116,139,0.15)" stroke-width="1"/>`);
        parts.push(`<text x="${ML - 5}" y="${y + 3.5}" text-anchor="end" font-size="9" fill="rgba(100,116,139,0.7)">${v}</text>`);
      }

      // Barres + labels X
      const labelEvery = n <= 10 ? 1 : n <= 21 ? 2 : n <= 35 ? 5 : 7;
      const baseY = MT + chartH;

      days.forEach((day, i) => {
        const x = +(ML + i * slotW).toFixed(1);
        const { fr, es } = grouped.get(day);
        const frH = +((fr / axisMax) * chartH).toFixed(1);
        const esH = +((es / axisMax) * chartH).toFixed(1);

        if (fr > 0) {
          parts.push(`<rect x="${x}" y="${+(baseY - frH).toFixed(1)}" width="${barW}" height="${frH}" fill="${COLOR_FR}" opacity="0.88" rx="2"><title>${formatDateLabel(day)} FR : ${formatMinutes(fr)}</title></rect>`);
        }
        if (es > 0) {
          parts.push(`<rect x="${x}" y="${+(baseY - frH - esH).toFixed(1)}" width="${barW}" height="${esH}" fill="${COLOR_ES}" opacity="0.88" rx="2"><title>${formatDateLabel(day)} ES : ${formatMinutes(es)}</title></rect>`);
        }

        if (i % labelEvery === 0) {
          const lx = +(x + barW / 2).toFixed(1);
          const ly = baseY + 5;
          parts.push(`<text transform="rotate(-40 ${lx} ${ly})" x="${lx}" y="${ly}" text-anchor="end" font-size="9" fill="rgba(100,116,139,0.75)">${formatDateLabel(day)}</text>`);
        }
      });

      const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${totalW} ${totalH}" style="width:100%;min-width:min(100%,${totalW}px);height:${totalH}px">${parts.join('')}</svg>`;
      const legend = `<div class="chart-legend">
        <span><span class="legend-dot" style="background:${COLOR_FR}"></span>FR</span>
        <span><span class="legend-dot" style="background:${COLOR_ES}"></span>ES</span>
      </div>`;
      return `<div style="overflow-x:auto">${svg}</div>${legend}`;
    }

    function renderChart(rows) {
      qs('chart').innerHTML = makeBarChartSVG(rows);
    }

    function renderRadio(radioByDay, radioSummary, radioTopStations) {
      // Cards résumé
      const totalH = Number(radioSummary.total_heures || 0);
      const totalS = Number(radioSummary.total_sessions || 0);
      const pctEs  = Math.round(Number(radioSummary.pct_es || 0));
      qs('radio-cards').innerHTML = `
        <div class="card">
          <div class="card-label">Heures radio</div>
          <div class="card-value">${totalH.toFixed(1)} h</div>
        </div>
        <div class="card">
          <div class="card-label">Sessions</div>
          <div class="card-value">${totalS}</div>
        </div>
        <div class="card">
          <div class="card-label">Part espagnol</div>
          <div class="card-value">${pctEs} %</div>
        </div>`;

      // Chart par jour
      qs('radio-chart').innerHTML = makeBarChartSVG(radioByDay);

      // Top stations
      const wrap = qs('radio-stations-wrap');
      if (!radioTopStations || !radioTopStations.length) {
        wrap.innerHTML = '<div class="ha-empty">Aucune écoute radio.</div>';
        return;
      }
      const body = radioTopStations.map(row => {
        const lang = String(row.langue || 'fr').toLowerCase();
        return `
          <tr>
            <td>${row.station || '—'}</td>
            <td><span class="lang-pill ${lang === 'es' ? 'es' : 'fr'}">${lang.toUpperCase()}</span></td>
            <td>${Number(row.nb_sessions || 0)}</td>
            <td>${formatMinutes(row.minutes)}</td>
          </tr>`;
      }).join('');
      wrap.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Station</th><th>Langue</th><th>Sessions</th><th>Temps total</th>
            </tr>
          </thead>
          <tbody>${body}</tbody>
        </table>`;
    }

    function renderDow(rows) {
      const wrap = document.getElementById('dow-wrap');
      if (!rows || !rows.length) {
        wrap.innerHTML = '<div class="ha-empty">Pas assez de données.</div>';
        return;
      }
      const DOW_LABELS = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'];
      const DOW_WEEKEND = [0, 6];

      const map = {};
      for (const r of rows) map[r.dow] = r;

      const maxAvg = Math.max(...rows.map(r => Number(r.avg_minutes || 0)), 1);
      // Arrondir le max à la dizaine supérieure pour l'axe
      const axisMax = Math.ceil(maxAvg / 10) * 10;

      // En-tête axe X
      const tickCount = 4;
      const ticks = Array.from({length: tickCount + 1}, (_, i) => Math.round(axisMax * i / tickCount));
      const header = `<div style="display:grid;grid-template-columns:40px 1fr auto;gap:10px;margin-bottom:6px">
        <div></div>
        <div style="position:relative;height:14px">
          ${ticks.map((v, i) => `<span style="position:absolute;left:${i * 25}%;transform:translateX(-50%);font-size:10px;color:var(--muted)">${v}</span>`).join('')}
        </div>
        <div style="min-width:80px"></div>
      </div>`;

      const rows_html = Array.from({length: 7}, (_, dow) => {
        const r = map[dow];
        const avg  = r ? Number(r.avg_minutes || 0) : 0;
        const pct  = Math.max(0, Math.min(100, (avg / axisMax) * 100));
        const isWe = DOW_WEEKEND.includes(dow);
        const color = isWe ? COLOR_ES : COLOR_FR;
        const hasData = r !== undefined;
        return `
          <div style="display:grid;grid-template-columns:40px 1fr auto;gap:10px;align-items:center;margin-bottom:7px">
            <div style="color:var(--muted);font-weight:700;font-size:13px">${DOW_LABELS[dow]}</div>
            <div class="bar-track">
              <div class="bar-fill" style="width:${pct}%;background:linear-gradient(90deg,${color}55,${color})"></div>
            </div>
            <div class="bar-minutes" style="min-width:80px">${hasData && avg > 0 ? formatMinutes(avg) + ' moy.' : '<span style="color:var(--muted)">—</span>'}</div>
          </div>`;
      }).join('');

      wrap.innerHTML = header + rows_html;
    }

    function renderTopPods(rows) {
      const wrap = qs('top-pods-wrap');
      if (!rows.length) {
        wrap.innerHTML = '<div class="ha-empty">Aucune donnée podcast.</div>';
        return;
      }

      const body = rows.map(row => {
        const lang = String(row.langue || 'fr').toLowerCase();
        const pct = row.pct_completion == null ? '—' : `${Math.round(Number(row.pct_completion || 0))} %`;
        return `
          <tr>
            <td>${podcastLabel(row.podcast_id)}</td>
            <td><span class="lang-pill ${lang === 'es' ? 'es' : 'fr'}">${lang.toUpperCase()}</span></td>
            <td>${Number(row.nb_ecoutes || 0)}</td>
            <td>${formatMinutes(row.minutes_totales)}</td>
            <td>${pct}</td>
          </tr>`;
      }).join('');

      wrap.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Titre du podcast</th>
              <th>Langue</th>
              <th>Écoutes</th>
              <th>Temps total</th>
              <th>Complétion moyenne</th>
            </tr>
          </thead>
          <tbody>${body}</tbody>
        </table>`;
    }

    function renderFunnel(funnel) {
      const wrap = qs('funnel-wrap');
      const q0 = Number(funnel.q0 || 0);
      const q1 = Number(funnel.q1 || 0);
      const q2 = Number(funnel.q2 || 0);
      const q3 = Number(funnel.q3 || 0);
      const q4 = Number(funnel.q4 || 0);
      const total = Math.max(1, q0 + q1 + q2 + q3 + q4);
      const rows = [
        { label: 'Abandon rapide (< 25%)', count: q0, color: '#e74c3c' },
        { label: 'Début écouté (25-50%)', count: q1, color: '#e67e22' },
        { label: 'Moitié atteinte (50-75%)', count: q2, color: '#f1c40f' },
        { label: 'Presque terminé (75-90%)', count: q3, color: '#27ae60' },
        { label: 'Épisode terminé ✓', count: q4, color: '#2ecc71' },
      ];

      wrap.innerHTML = rows.map(item => {
        const pct = Math.round((item.count * 100) / total);
        return `
          <div>
            <div class="funnel-row">
              <div class="funnel-label">${item.label}</div>
              <div class="funnel-bar-track"><div class="funnel-bar" style="width:${pct}%;background:${item.color}"></div></div>
              <div class="funnel-pct">${pct}%</div>
            </div>
            <div class="funnel-count">${item.count} épisodes</div>
          </div>`;
      }).join('');
    }

    function renderHeatmap(rows) {
      const grid = qs('heatmap-grid');
      const days = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'];
      const minHour = 6;
      const maxHour = 22;
      const matrix = Array.from({ length: 7 }, () => Array(24).fill(0));
      for (const row of rows) {
        const dow = Number(row.dow);
        const hour = Number(row.hour);
        if (dow >= 0 && dow <= 6 && hour >= 0 && hour <= 23) {
          matrix[dow][hour] = Number(row.minutes || 0);
        }
      }
      let max = 0;
      for (let d = 0; d < 7; d++) {
        for (let h = minHour; h <= maxHour; h++) {
          max = Math.max(max, matrix[d][h]);
        }
      }
      max = Math.max(max, 1);

      grid.innerHTML = '<div></div>' + days.map(d => `<div class="hm-head">${d}</div>`).join('');
      for (let h = minHour; h <= maxHour; h++) {
        grid.insertAdjacentHTML('beforeend', `<div class="hm-hour">${h}h</div>`);
        for (let d = 0; d < 7; d++) {
          const value = matrix[d][h] || 0;
          const alpha = Math.min(0.9, Math.max(0, value / max * 0.9));
          grid.insertAdjacentHTML(
            'beforeend',
            `<div class="hm-cell" title="${days[d]} ${h}h: ${formatMinutes(value)}" style="background:rgba(201,162,39,${alpha.toFixed(3)})"></div>`
          );
        }
      }
    }

    function renderTopEpisodes(rows) {
      const wrap = qs('top-episodes-wrap');
      const topFive = (rows || []).slice(0, 5);
      if (!topFive.length) {
        wrap.innerHTML = '<div class="ha-empty">Aucune donnée de replay.</div>';
        return;
      }

      const body = topFive.map(row => `
        <tr>
          <td>${podcastLabel(row.podcast_id)}</td>
          <td>${episodeLabel(row.podcast_id, row.episode_id)}</td>
          <td>${Number(row.replays || 0)}</td>
          <td>${formatMinutes(row.avg_minutes)}</td>
        </tr>`).join('');

      wrap.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Podcast</th>
              <th>Épisode</th>
              <th>Écoutes</th>
              <th>Durée moy.</th>
            </tr>
          </thead>
          <tbody>${body}</tbody>
        </table>`;
    }

    function renderRecent(rows) {
      const wrap = qs('recent-wrap');
      if (!rows.length) {
        wrap.innerHTML = '<div class="ha-empty">Aucun épisode récent.</div>';
        return;
      }

      const body = rows.map(row => {
        const listened = Number(row.listened_s || 0);
        const duration = Number(row.duration_s || 0);
        const pct = duration > 0 ? Math.round((listened * 100) / duration) : 0;
        const status = Number(row.completed || 0) === 1
          ? '<span class="status-ok">✅ Terminé</span>'
          : `<span class="status-warn">⏳ ${pct}%</span>`;

        return `
          <tr>
            <td>${row.started_at || '—'}</td>
            <td>${podcastLabel(row.podcast_id)}</td>
            <td>${formatSeconds(listened)}</td>
            <td>${formatSeconds(duration)}</td>
            <td>${status}</td>
          </tr>`;
      }).join('');

      wrap.innerHTML = `
        <table>
          <thead>
            <tr>
              <th>Date/heure</th>
              <th>Podcast</th>
              <th>Écouté</th>
              <th>Durée</th>
              <th>Statut</th>
            </tr>
          </thead>
          <tbody>${body}</tbody>
        </table>`;
    }

    async function loadStats() {
      showError('');
      const days = qs('period').value;
      try {
        const response = await fetch(`/tracking.php?action=stats&days=${encodeURIComponent(days)}`, { cache: 'no-store' });
        const payload = await response.json();
        if (!response.ok || !payload.ok) {
          throw new Error(payload.error || 'Réponse invalide du dashboard');
        }
        renderSummary(payload.summary || {}, payload.streak || 0);
        renderChart(payload.by_day || []);
        renderDow(payload.by_dow || []);
        renderRadio(payload.radio_by_day || [], payload.radio_summary || {}, payload.radio_top_stations || []);
        renderTopPods(payload.top_pods || []);
        renderFunnel(payload.funnel || {});
        renderHeatmap(payload.heatmap || []);
        renderTopEpisodes(payload.top_episodes || []);
        renderRecent(payload.recent || []);
      } catch (error) {
        showError(`Impossible de charger les statistiques: ${error.message || error}`);
        renderSummary({}, 0);
        renderChart([]);
        renderDow([]);
        renderRadio([], {}, []);
        renderTopPods([]);
        renderFunnel({});
        renderHeatmap([]);
        renderTopEpisodes([]);
        renderRecent([]);
      }
    }

    qs('period').addEventListener('change', loadStats);

    (async function init() {
      await loadPodcastTitles();
      await loadStats();
    }());
  </script>
</body>
</html>
