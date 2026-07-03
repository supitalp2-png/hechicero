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

    /* ── Casque dashboard ──────────────────────────────────── */
    @keyframes ear-pulse { 0%,100%{opacity:1} 50%{opacity:.15} }
    .hp-badge {
      display:inline-block; padding:4px 13px;
      border-radius:20px; font-size:13px; font-weight:700;
      border:1px solid transparent;
    }
    /* Graphique capacité restante (barre haute = bien = peu écouté) */
    .hp-bars-wrap {
      position:relative; height:160px; border-bottom:1px solid #334155;
    }
    .hp-bg-gradient {
      position:absolute; inset:0; pointer-events:none; border-radius:3px 3px 0 0;
      background:linear-gradient(to bottom,
        rgba(34,197,94,.07) 0%,
        rgba(234,179,8,.05) 48%,
        rgba(249,115,22,.06) 74%,
        rgba(239,68,68,.09) 100%);
    }
    .hp-thr {
      position:absolute; left:0; right:0;
      height:1px; background:rgba(234,179,8,.3);
    }
    .hp-thr.t25 { background:rgba(249,115,22,.35); }
    .hp-thr.t10 { background:rgba(239,68,68,.42); }
    .hp-bars {
      position:absolute; inset:0;
      display:flex; align-items:stretch; gap:3px; padding:0 2px;
    }
    .hp-bar-col {
      flex:1; position:relative;
    }
    .hp-bar-mark {
      position:absolute; left:0; right:0; height:4px; border-radius:2px;
      transform:translateY(50%);
      transition:bottom .9s cubic-bezier(.22,1,.36,1), background-color .4s;
    }
    .hp-bar-mark.today {
      height:6px;
      box-shadow:0 0 0 2px rgba(255,255,255,.35);
    }
    .hp-day-labels { display:flex; gap:3px; padding:5px 2px 0; }
    .hp-day-label  { flex:1; text-align:center; font-size:9px; color:#475569; }
    .hp-day-label.today { color:#e2e8f0; font-weight:600; }
    /* ─────────────────────────────────────────────────────── */

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

    <section class="ha-panel" style="margin-bottom:18px">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:8px">
        <h2 style="margin:0">🎧 Fatigue auditive — casque</h2>
        <span id="hp-updated" class="muted" style="font-size:11px"></span>
      </div>

      <!-- Layout côte à côte : oreille gauche | graphique droite -->
      <div style="display:flex;gap:0;align-items:flex-start">

        <!-- GAUCHE : icône oreille colorée + jauge verticale + infos du jour -->
        <div style="flex-shrink:0;width:160px;padding-right:20px;border-right:1px solid rgba(100,116,139,.2)">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px">

            <!-- Icône oreille (silhouette solide, couleur = niveau fatigue) — tracée depuis oreille.svg -->
            <svg id="hp-ear-svg" viewBox="300 130 530 930" width="58" height="101" xmlns="http://www.w3.org/2000/svg" style="display:block;flex-shrink:0;transition:filter .5s">
              <path id="hp-ear-color" fill="#22c55e" d="M 594.00,150.42 C 606.61,148.89 622.59,150.94 635.00,153.49 635.00,153.49 643.00,154.70 643.00,154.70 685.77,165.20 723.57,192.63 753.10,224.54 772.69,245.70 787.87,265.50 801.69,291.00 854.63,388.67 855.03,507.88 818.31,611.00 808.37,638.90 795.07,665.29 780.50,691.00 780.50,691.00 763.05,718.42 763.05,718.42 750.47,740.21 739.29,762.88 731.88,787.00 725.21,808.72 720.36,833.37 718.17,856.00 716.39,874.34 715.31,902.02 710.12,919.00 703.99,939.03 686.46,963.86 672.74,979.58 652.00,1003.34 623.68,1028.71 593.00,1037.97 583.46,1040.84 579.33,1042.98 569.00,1043.00 569.00,1043.00 549.00,1043.00 549.00,1043.00 533.69,1042.82 515.11,1033.44 502.85,1024.81 467.31,999.80 445.09,955.42 429.20,916.00 429.20,916.00 417.35,888.00 417.35,888.00 414.69,881.87 411.59,875.81 411.21,869.00 410.74,860.64 415.77,850.67 424.01,847.85 426.71,846.93 430.16,846.94 433.00,847.01 444.30,847.29 448.47,854.57 452.58,864.00 452.58,864.00 469.85,905.00 469.85,905.00 469.85,905.00 479.30,926.00 479.30,926.00 492.08,953.11 515.93,990.66 547.00,998.30 550.73,999.21 558.95,999.19 563.00,999.08 568.03,998.94 571.02,999.12 576.00,997.63 588.20,993.99 599.45,987.59 609.83,980.32 626.21,968.85 646.20,946.59 657.33,930.00 660.86,924.73 668.44,912.64 670.45,907.00 674.78,894.90 676.70,860.63 678.17,846.00 680.80,819.75 686.49,793.06 694.67,768.00 703.59,740.65 714.03,718.84 728.42,694.00 728.42,694.00 739.26,677.00 739.26,677.00 752.40,655.52 764.77,633.52 773.94,610.00 780.27,593.78 786.30,576.90 790.53,560.00 795.28,541.00 801.77,507.17 802.00,488.00 802.00,488.00 803.00,458.00 803.00,458.00 803.00,458.00 802.00,441.00 802.00,441.00 801.86,429.82 797.93,405.33 795.42,394.00 787.59,358.52 776.43,328.70 756.69,298.00 746.36,281.93 735.38,267.70 722.01,254.00 698.69,230.11 670.63,208.30 638.00,198.97 638.00,198.97 631.00,197.56 631.00,197.56 623.04,195.66 615.23,194.01 607.00,194.00 607.00,194.00 598.00,194.00 598.00,194.00 590.40,194.09 582.36,195.81 575.00,197.56 575.00,197.56 566.00,199.37 566.00,199.37 550.19,203.92 534.14,211.45 520.00,219.81 494.08,235.13 468.02,257.32 447.29,279.10 422.44,305.22 405.55,325.81 390.31,359.00 381.70,377.74 374.87,396.99 369.87,417.00 367.71,425.66 365.68,443.78 360.47,449.90 349.23,463.08 324.10,457.04 325.04,433.00 325.28,426.88 329.01,410.47 330.63,404.00 335.58,384.19 342.12,364.61 350.52,346.00 359.65,325.78 369.88,306.17 383.00,288.17 400.48,264.21 421.46,243.23 443.27,223.26 472.27,196.69 506.62,173.19 544.00,160.30 556.30,156.06 570.09,152.83 583.00,151.28 583.00,151.28 594.00,150.42 594.00,150.42 Z"/>
              <!-- Concha / canal auditif -->
              <path fill="#ffffff" opacity=".9" d="M 729.00,569.00 C 722.73,557.94 720.56,545.44 718.73,533.00 718.73,533.00 715.28,510.00 715.28,510.00 713.01,491.30 712.70,479.05 704.69,461.00 699.24,448.71 691.47,435.55 679.91,428.09 656.51,412.99 627.57,425.53 607.00,439.58 601.60,443.27 594.51,448.33 590.06,453.09 581.50,462.25 571.57,487.68 566.81,500.00 553.81,533.66 552.37,571.57 563.02,606.00 563.02,606.00 585.91,660.00 585.91,660.00 592.74,676.69 597.12,694.04 598.83,712.00 599.70,721.08 600.91,738.56 598.15,747.00 596.22,752.91 589.45,762.19 585.41,767.00 573.68,780.98 555.95,792.42 538.00,796.47 538.00,796.47 531.00,797.30 531.00,797.30 525.46,798.11 525.69,798.92 519.00,799.00 519.00,799.00 506.00,799.00 506.00,799.00 499.10,798.92 485.58,796.16 479.00,793.75 470.92,790.79 469.60,790.40 462.00,785.82 459.00,784.01 455.80,781.41 453.32,778.92 451.35,776.94 449.29,774.44 447.99,771.96 439.32,755.38 451.99,744.40 461.12,732.00 473.33,715.41 483.22,697.47 492.24,679.00 494.04,675.33 502.00,657.02 502.09,654.00 502.21,650.40 498.12,645.79 496.00,643.00 496.00,643.00 478.75,620.72 478.75,620.72 469.05,609.07 462.18,587.15 462.18,572.00 462.18,556.59 469.39,545.97 479.32,534.91 491.99,520.82 511.25,505.54 521.43,491.00 535.37,471.08 529.53,448.41 535.74,426.00 544.75,393.52 571.18,382.20 602.00,377.87 607.34,377.12 611.51,376.07 617.00,376.00 641.89,375.71 656.39,375.06 679.96,385.58 710.33,399.13 733.66,430.54 745.05,461.00 748.00,468.89 752.30,480.68 752.91,489.00 753.51,497.16 751.98,504.08 750.40,512.00 747.77,525.17 744.28,540.45 739.68,553.00 737.26,559.61 735.72,565.66 729.00,569.00 Z"/>
            </svg>

            <!-- Jauge verticale : 100% en haut, 0% en bas, dot qui descend -->
            <div style="position:relative;width:28px;height:101px;flex-shrink:0">
              <span style="position:absolute;right:0;top:0;font-size:8px;color:var(--muted);line-height:1">100%</span>
              <span style="position:absolute;right:0;bottom:0;font-size:8px;color:var(--muted);line-height:1">0%</span>
              <div style="position:absolute;left:4px;top:12px;bottom:12px;width:4px;background:rgba(100,116,139,.18);border-radius:2px"></div>
              <div id="hp-gauge-fill" style="position:absolute;left:4px;bottom:12px;width:4px;border-radius:2px;background:#22c55e;height:77px;transition:height .9s cubic-bezier(.22,1,.36,1),background .4s"></div>
              <div id="hp-gauge-dot" style="position:absolute;left:-1px;top:12px;width:14px;height:14px;border-radius:50%;background:#22c55e;border:2px solid #0a1120;transition:top .9s cubic-bezier(.22,1,.36,1),background .4s;transform:translateY(-50%)"></div>
            </div>

          </div>

          <div style="text-align:center">
            <div style="font-size:10px;color:var(--muted);margin-bottom:4px;text-transform:uppercase;letter-spacing:.06em">Aujourd'hui</div>
            <div style="font-size:24px;font-weight:700;line-height:1;margin-bottom:8px" id="hp-time">—</div>
            <span id="hp-badge" class="hp-badge" style="display:inline-block;margin-bottom:8px;font-size:11px">…</span>
            <div style="font-size:11px;color:var(--muted)" id="hp-remain">—</div>
          </div>
        </div>

        <!-- DROITE : graphique 14j -->
        <div style="flex:1;min-width:0;padding-left:20px">
          <div style="font-size:11px;color:var(--muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:.06em">Capacité restante · 14 jours glissants</div>
          <div class="hp-bars-wrap">
            <div class="hp-bg-gradient"></div>
            <div class="hp-thr"     style="bottom:50%"></div>
            <div class="hp-thr t25" style="bottom:25%"></div>
            <div class="hp-thr t10" style="bottom:10%"></div>
            <div id="hp-bars" class="hp-bars">
              <div style="color:var(--muted);font-size:12px;margin:auto">Chargement…</div>
            </div>
          </div>
          <div id="hp-day-labels" class="hp-day-labels"></div>
          <div style="display:flex;gap:12px;margin-top:10px;font-size:11px;flex-wrap:wrap" class="muted">
            <span><span style="color:#22c55e">●</span> Normal (&lt;1h)</span>
            <span><span style="color:#eab308">●</span> Modéré (1h–1h30)</span>
            <span><span style="color:#f97316">●</span> Attention (1h30–1h48)</span>
            <span><span style="color:#ef4444">●</span> Limite (&gt;1h48)</span>
          </div>
        </div>

      </div>
    </section>

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
              <th>Temp              <th>Complétion moyenne</th>
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

    // ── Casque : graphique 14j + thermomètre ─────────────
    function renderHeadphoneBars(days) {
      const barsEl   = qs('hp-bars');
      const labelsEl = qs('hp-day-labels');
      if (!barsEl || !labelsEl) return;

      const DOW = ['Dim','Lun','Mar','Mer','Jeu','Ven','Sam'];
      barsEl.innerHTML   = '';
      labelsEl.innerHTML = '';

      const targets = [];
      days.forEach(d => {
        const pct   = Number(d.pct || 0);
        // Niveau affiché = capacité restante (haut = bien, bas = dégradé) — cohérent
        // avec le titre du graphique et la jauge verticale à gauche.
        const level = Math.max(0, Math.min(100, 100 - pct));
        const color = pct>=90?'#ef4444':pct>=75?'#f97316':pct>=50?'#eab308':'#22c55e';

        const col = document.createElement('div');
        col.className = 'hp-bar-col';
        const mark = document.createElement('div');
        mark.className = 'hp-bar-mark' + (d.is_today ? ' today' : '');
        mark.style.bottom = '0%';
        mark.style.backgroundColor = color;
        col.appendChild(mark);
        barsEl.appendChild(col);
        targets.push({ el: mark, level });

        const lbl       = document.createElement('div');
        lbl.className   = 'hp-day-label' + (d.is_today ? ' today' : '');
        const date      = new Date(d.jour + 'T12:00:00');
        lbl.textContent = d.is_today ? 'auj.' : DOW[date.getDay()];
        labelsEl.appendChild(lbl);
      });

      // Double rAF pour déclencher les transitions CSS
      requestAnimationFrame(() => requestAnimationFrame(() => {
        targets.forEach(({ el, level }) => {
          el.style.bottom = level + '%';
        });
      }));
    }

    async function loadHeadphoneStats() {
      try {
        const r = await fetch('/tracking.php?action=headphone_history', { cache: 'no-store' });
        const d = await r.json();
        if (!d.ok) return;

        renderHeadphoneBars(d.days || []);

        const t     = d.today;
        const pct   = Number(t.pct || 0);
        const min   = Number(t.casque_min || 0);
        const color = pct>=90?'#ef4444':pct>=75?'#f97316':pct>=50?'#eab308':'#22c55e';

        // Icône oreille : couleur pleine selon le niveau de fatigue
        const remain   = Math.max(0, 100 - pct);
        const earColor = qs('hp-ear-color');
        const earSvg   = qs('hp-ear-svg');
        if (earColor) earColor.setAttribute('fill', color);
        if (earSvg)   earSvg.style.filter = pct >= 90 ? `drop-shadow(0 0 6px ${color}90)` : '';

        // Jauge verticale : hauteur du fill = capacité restante, position du point = fatigue
        const gaugeFill = qs('hp-gauge-fill');
        const gaugeDot  = qs('hp-gauge-dot');
        if (gaugeFill) {
          gaugeFill.style.height          = `${(remain * 0.77).toFixed(1)}px`;
          gaugeFill.style.backgroundColor = color;
        }
        if (gaugeDot) {
          gaugeDot.style.top             = `${(12 + (pct / 100) * 77).toFixed(1)}px`;
          gaugeDot.style.backgroundColor = color;
        }

        const h = Math.floor(min / 60), m = Math.round(min % 60);
        qs('hp-time').textContent = min < 1 ? '0 min' : h > 0
          ? `${h}h${String(m).padStart(2,'0')}` : `${Math.round(min)} min`;

        const remainMin = Math.round(120 - min);
        const remainEl  = qs('hp-remain');
        if (remainEl) remainEl.textContent = remainMin > 0 ? `${remainMin} min restantes` : 'Limite atteinte';

        let bg, label;
        if (pct >= 90)      { bg='rgba(239,68,68,.15)';  label='⚠️ Limite !'; }
        else if (pct >= 75) { bg='rgba(249,115,22,.15)'; label='🟠 Attention'; }
        else if (pct >= 50) { bg='rgba(234,179,8,.13)';  label='🟡 Modéré'; }
        else                { bg='rgba(34,197,94,.12)';  label='🟢 Normal'; }
        const badge = qs('hp-badge');
        if (badge) {
          badge.textContent       = label;
          badge.style.background  = bg;
          badge.style.color       = color;
          badge.style.borderColor = color + '55';
        }

        const now = new Date();
        const upd = qs('hp-updated');
        if (upd) upd.textContent = `↻ ${now.getHours()}:${String(now.getMinutes()).padStart(2,'0')}`;

      } catch (e) { console.warn('headphone stats:', e); }
    }

    (async function init() {
      await loadPodcastTitles();
      await loadHeadphoneStats();
      await loadStats();
      setInterval(loadHeadphoneStats, 30_000);
    }());
  </script>
</body>
</html>
