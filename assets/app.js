/* YAASAP Géostratégie — comportements communs (fond animé, compteurs, graphiques, repères, newsletter) */

/* ---------- Fond réseau animé ---------- */
(function () {
  var c = document.getElementById('bg');
  if (!c) return;
  var x = c.getContext('2d'), W, H, P = [];
  var still = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function init() {
    W = c.width = window.innerWidth; H = c.height = window.innerHeight;
    var n = Math.min(70, Math.floor(W * H / 20000)); P = [];
    for (var i = 0; i < n; i++) P.push({ x: Math.random() * W, y: Math.random() * H, vx: (Math.random() - .5) * .25, vy: (Math.random() - .5) * .25, r: Math.random() * 1.3 + .5 });
  }
  function draw() {
    x.clearRect(0, 0, W, H);
    for (var i = 0; i < P.length; i++) {
      var p = P[i];
      if (!still) { p.x += p.vx; p.y += p.vy; if (p.x < 0 || p.x > W) p.vx *= -1; if (p.y < 0 || p.y > H) p.vy *= -1; }
      x.beginPath(); x.arc(p.x, p.y, p.r, 0, 6.283); x.fillStyle = 'rgba(243,230,196,.55)'; x.fill();
      for (var j = i + 1; j < P.length; j++) {
        var q = P[j], dx = p.x - q.x, dy = p.y - q.y, d = dx * dx + dy * dy;
        if (d < 16000) { x.strokeStyle = 'rgba(217,184,115,' + (0.22 * (1 - d / 16000)).toFixed(3) + ')'; x.lineWidth = .7; x.beginPath(); x.moveTo(p.x, p.y); x.lineTo(q.x, q.y); x.stroke(); }
      }
    }
    if (!still) requestAnimationFrame(draw);
  }
  init(); draw();
  window.addEventListener('resize', function () { init(); if (still) draw(); });
})();

/* ---------- Compteurs KPI ---------- */
(function () {
  function fmt(n, dec, plus) {
    var s = Math.abs(n).toFixed(dec).replace('.', ',');
    if (n < 0 && Math.abs(n) >= Math.pow(10, -dec)) return '−' + s;
    return (plus && n > 0 ? '+' : '') + s;
  }
  var els = document.querySelectorAll('.kpi-v[data-to]');
  if (!('IntersectionObserver' in window) || (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches)) return;
  var io = new IntersectionObserver(function (es) {
    es.forEach(function (e) {
      if (!e.isIntersecting) return; io.unobserve(e.target);
      var el = e.target, to = parseFloat(el.dataset.to), dec = parseInt(el.dataset.dec || '0', 10), pre = el.dataset.pre || '', suf = el.dataset.suf || '', plus = el.dataset.plus === '1';
      var t0 = null;
      function step(ts) {
        if (!t0) t0 = ts; var k = Math.min(1, (ts - t0) / 1100), v = to * (1 - Math.pow(1 - k, 3));
        el.textContent = pre + fmt(v, dec, plus) + suf;
        if (k < 1) requestAnimationFrame(step); else el.textContent = pre + fmt(to, dec, plus) + suf;
      }
      requestAnimationFrame(step);
    });
  }, { threshold: .4 });
  els.forEach(function (el) { io.observe(el); });
})();

/* ---------- Date du masthead + QR ---------- */
(function () {
  var d = document.getElementById('mastDate');
  if (d && window.NOTE_META) d.textContent = window.NOTE_META.dateShort;
  (function tryQR() {
    var el = document.getElementById('qr-mast');
    if (!el) return;
    if (typeof QRCode === 'undefined') { setTimeout(tryQR, 80); return; }
    new QRCode(el, { text: location.href.split('#')[0], width: 32, height: 32, colorDark: '#1d2012', colorLight: '#fff', correctLevel: QRCode.CorrectLevel.M });
  })();
})();

/* ---------- Newsletter ---------- */
function nlSubmit() {
  var el = document.getElementById('nlEmail');
  var email = el ? el.value.trim() : '';
  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { if (el) el.style.borderColor = 'rgba(232,144,106,.8)'; return; }
  var body = new FormData();
  body.append('email', email);
  body.append('source', 'yaasap-geostrategie');
  body.append('_subject', 'Inscription YAASAP Géostratégie');
  body.append('_next', 'false');
  fetch('https://formspree.io/f/meewwqep', { method: 'POST', body: body, headers: { 'Accept': 'application/json' } })
    .then(function (r) {
      if (r.ok) {
        var row = el.parentElement; if (row) row.style.display = 'none';
        var ok = document.getElementById('nlOk'); if (ok) ok.style.display = 'block';
      }
    });
}

/* ---------- Graphiques ---------- */
(function tryCharts() {
  var list = window.NOTE_CHARTS || [];
  if (!list.length) return;
  if (typeof Chart === 'undefined') { setTimeout(tryCharts, 80); return; }
  var tf = { size: 10, family: "'Source Code Pro','Courier New',monospace" };
  Chart.defaults.color = '#b8b196'; Chart.defaults.font = tf;
  var tt = { backgroundColor: 'rgba(24,24,14,.92)', titleColor: '#fbf5e4', bodyColor: '#f1e4c3', borderColor: 'rgba(214,190,130,.45)', borderWidth: 1, padding: 10, cornerRadius: 8, displayColors: false };
  var FILL = ['rgba(217,184,115,.55)', 'rgba(232,144,106,.6)', 'rgba(185,211,122,.5)', 'rgba(184,177,150,.4)', 'rgba(122,122,70,.6)', 'rgba(241,228,195,.4)'];
  var EDGE = ['rgba(233,214,160,1)', 'rgba(232,144,106,1)', 'rgba(185,211,122,1)', 'rgba(216,203,160,.9)', 'rgba(160,160,100,1)', 'rgba(241,228,195,.9)'];

  list.forEach(function (c, idx) {
    var cv = document.getElementById('ch' + idx);
    if (!cv) return;
    var kind = c.kind || 'bar';
    var multi = kind === 'doughnut' ? false : true;
    var datasets = c.datasets.map(function (d, i) {
      if (kind === 'doughnut') {
        return { label: d.label || '', data: d.data, backgroundColor: c.labels.map(function (_, k) { return FILL[k % FILL.length]; }), borderColor: c.labels.map(function (_, k) { return EDGE[k % EDGE.length]; }), borderWidth: 1.5, hoverOffset: 10 };
      }
      if (kind === 'line') {
        return { label: d.label || '', data: d.data, borderColor: EDGE[i % EDGE.length], backgroundColor: FILL[i % FILL.length], borderWidth: 2, pointRadius: 3, pointHoverRadius: 6, tension: .25, fill: false };
      }
      return { label: d.label || '', data: d.data, backgroundColor: FILL[i % FILL.length], borderColor: EDGE[i % EDGE.length], borderWidth: 1.2, borderRadius: 4 };
    });
    var opts = {
      responsive: true, maintainAspectRatio: false, animation: { duration: 800, easing: 'easeOutQuart' },
      plugins: {
        legend: { display: kind === 'doughnut' || datasets.length > 1, position: 'bottom', labels: { color: '#b8b196', font: tf, boxWidth: 10, padding: 14 } },
        tooltip: Object.assign({}, tt, { callbacks: { label: function (ctx) { var v = ctx.raw; return (ctx.dataset.label ? ctx.dataset.label + ' : ' : ctx.label + ' : ') + String(v).replace('.', ',') + (c.unit ? ' ' + c.unit : ''); } } })
      }
    };
    if (kind === 'doughnut') { opts.cutout = '66%'; }
    else {
      opts.scales = {
        x: { grid: { color: 'rgba(214,190,130,.08)' }, ticks: { color: '#b8b196', font: tf } },
        y: { grid: { color: 'rgba(214,190,130,.1)' }, ticks: { color: '#b8b196', font: tf }, title: { display: !!c.unit, text: c.unit || '', color: '#9a937a', font: tf } }
      };
    }
    var plugins = [];
    if (kind === 'doughnut' && c.center) {
      plugins.push({ id: 'ctr', afterDraw: function (ch) {
        var a = ch.getDatasetMeta(0).data[0], cx = ch.ctx; if (!a) return;
        cx.save(); cx.textAlign = 'center'; cx.fillStyle = '#fbf5e4'; cx.shadowColor = 'rgba(217,184,115,.9)'; cx.shadowBlur = 14;
        cx.font = "700 17px Orbitron, 'Source Sans 3', sans-serif"; cx.fillText(c.center.big || '', a.x, a.y + 4);
        cx.shadowBlur = 0; cx.fillStyle = '#b8b196'; cx.font = "10px 'Source Code Pro', monospace"; cx.fillText(c.center.small || '', a.x, a.y + 24);
        cx.restore();
      } });
    }
    new Chart(cv, { type: kind, data: { labels: c.labels, datasets: datasets }, options: opts, plugins: plugins });
  });
})();

/* ---------- Repères chronologiques cliquables ---------- */
(function () {
  var T = window.NOTE_TIMELINES || [];
  T.forEach(function (events, idx) {
    var tl = document.getElementById('tl' + idx), td = document.getElementById('tlDetail' + idx);
    if (!tl || !td || !events.length) return;
    function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;'); }
    function show(i) {
      [].forEach.call(tl.children, function (b, j) { b.classList.toggle('on', j === i); });
      td.innerHTML = '<div class="d-name">' + esc(events[i][0]) + ' · ' + esc(events[i][1]) + '</div><div class="d-note" style="margin-top:0">' + esc(events[i][2]) + '</div>';
    }
    events.forEach(function (e, i) {
      var b = document.createElement('button'); b.type = 'button'; b.textContent = e[0];
      b.addEventListener('click', function () { show(i); }); tl.appendChild(b);
    });
    show(events.length - 1);
  });
})();
