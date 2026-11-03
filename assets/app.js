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
    new QRCode(el, { text: location.href.split('#')[0], width: 32, height: 32, colorDark: '#0b1426', colorLight: '#fff', correctLevel: QRCode.CorrectLevel.M });
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
function yaCharts() {
  var list = window.NOTE_CHARTS || [];
  if (!list.length) return;
  if (typeof Chart === 'undefined') { setTimeout(yaCharts, 80); return; }
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
        cx.font = "700 17px 'Playfair Display', Georgia, serif"; cx.fillText(c.center.big || '', a.x, a.y + 4);
        cx.shadowBlur = 0; cx.fillStyle = '#b8b196'; cx.font = "10px 'Source Code Pro', monospace"; cx.fillText(c.center.small || '', a.x, a.y + 24);
        cx.restore();
      } });
    }
    new Chart(cv, { type: kind, data: { labels: c.labels, datasets: datasets }, options: opts, plugins: plugins });
  });
}

/* ---------- Repères chronologiques cliquables ---------- */
function yaTimelines() {
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
}

/* ---------- Sommaire dynamique : surbrillance de la section lue + progression ---------- */
function yaToc() {
  var nav = document.getElementById('toc');
  if (!nav) return;
  var links = [].slice.call(nav.querySelectorAll('a'));
  var targets = links.map(function (a) { return document.getElementById(a.dataset.t); });
  var bar = document.getElementById('tocBar');
  function update() {
    var y = window.scrollY + 130, cur = 0;
    targets.forEach(function (t, i) { if (t && t.getBoundingClientRect().top + window.scrollY <= y) cur = i; });
    var atEnd = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4;
    if (atEnd) cur = targets.length - 1;
    links.forEach(function (a, i) { a.classList.toggle('on', i === cur); });
    if (bar) {
      var h = document.documentElement.scrollHeight - window.innerHeight;
      bar.style.width = (h > 0 ? Math.min(100, Math.max(0, window.scrollY / h * 100)) : 0) + '%';
    }
    var on = links[cur];
    if (on && window.innerWidth <= 900 && on.scrollIntoView) {
      var box = nav.parentElement; box.scrollLeft = on.offsetLeft - 24;
    }
  }
  var tick = false;
  window.addEventListener('scroll', function () { if (!tick) { tick = true; requestAnimationFrame(function () { tick = false; update(); }); } }, { passive: true });
  window.addEventListener('resize', update);
  update();
}

/* ---------- Cartes dynamiques (bloc « map ») ----------
   kind « svg » : fond vectoriel projeté par generate.py (data/cartes/), régions colorées, marqueurs,
   liaisons, calques, zoom et déplacement ; kind « tiles » : fond OpenStreetMap via Leaflet.
   Tous les textes viennent du JSON de la note et sont insérés en texte brut. */
function yaMaps() {
  var M = window.NOTE_MAPS || [];
  var NS = 'http://www.w3.org/2000/svg';
  function el(tag, attrs, parent) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs) if (attrs[k] !== undefined && attrs[k] !== null) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }
  function btn(txt, on, parent) {
    var b = document.createElement('button'); b.type = 'button'; b.textContent = txt; if (on) b.classList.add('on');
    parent.appendChild(b); return b;
  }
  function detail(td, name, note, meta) {
    if (!td) return;
    td.innerHTML = '';
    var h = document.createElement('div'); h.className = 'd-name'; h.textContent = name; td.appendChild(h);
    if (meta) { var m = document.createElement('div'); m.className = 'd-meta'; m.textContent = meta; td.appendChild(m); }
    var p = document.createElement('div'); p.className = 'd-note'; p.style.marginTop = '0'; p.textContent = note || ''; td.appendChild(p);
  }
  function legend(lg, items) {
    if (!lg) return;
    lg.innerHTML = '';
    (items || []).forEach(function (it) {
      var s = document.createElement('span'); var i = document.createElement('i'); i.className = 'lg ' + (it.cls || '');
      if (it.color) i.style.background = it.color;
      s.appendChild(i); s.appendChild(document.createTextNode(it.label)); lg.appendChild(s);
    });
  }

  function svgMap(c, idx, box, ctl, lg, td) {
    var W = c.w || 1000, H = c.h || 640;
    box.style.aspectRatio = W + '/' + H;
    var hl = c.hl || [];
    var svg = el('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'vmap' }, box);
    var root = el('g', { class: 'vroot' }, svg);
    var gl = el('g', { class: 'shapes' }, root), gr = el('g', { class: 'regions' }, root), gk = el('g', { class: 'links' }, root), gm = el('g', { class: 'marks' }, root);
    var byId = {};
    (c.shapes || []).forEach(function (s) {
      var p = el('path', { d: s.d, class: 'land' + (s.cls ? ' ' + s.cls : '') + (hl.indexOf(s.id) >= 0 ? ' hl' : ''), 'data-id': s.id }, gl);
      byId[s.id] = { shape: s, path: p };
      if (s.name) { var t = el('title', {}, p); t.textContent = s.name; }
    });
    var items = []; // éléments cliquables : {node, name, note, meta, layer}
    function pick(node, name, note, meta) {
      items.forEach(function (x) { x.node.classList.remove('on'); });
      node.classList.add('on'); detail(td, name, note, meta);
    }
    function clickable(node, name, note, meta, layer) {
      node.setAttribute('tabindex', '0'); if (layer) node.setAttribute('data-layer', layer);
      node.addEventListener('click', function () { pick(node, name, note, meta); });
      node.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); pick(node, name, note, meta); } });
      items.push({ node: node, name: name, note: note, meta: meta, layer: layer });
    }
    // Régions colorées (choroplèthe) : {id, cls, alpha, label, sub, info, meta}
    (c.regions || []).forEach(function (r) {
      var b = byId[r.id]; if (!b) return;
      b.path.classList.add('region'); if (r.cls) b.path.classList.add(r.cls);
      if (r.alpha !== undefined) b.path.style.fillOpacity = r.alpha;
      if (r.color) b.path.style.fill = r.color;
      gr.appendChild(b.path);
      var cx = (r.c && r.c[0]) || (b.shape.c && b.shape.c[0]), cy = (r.c && r.c[1]) || (b.shape.c && b.shape.c[1]);
      if (r.shift && cx !== undefined) { cx += r.shift[0]; cy += r.shift[1]; }
      if (cx !== undefined && (r.label || r.sub)) {
        var g = el('g', { class: 'rlab', 'pointer-events': 'none' }, gr);
        if (r.label) { var t1 = el('text', { x: cx, y: cy - (r.sub ? 4 : 0), 'text-anchor': 'middle' }, g); t1.textContent = r.label; }
        if (r.sub) { var t2 = el('text', { x: cx, y: cy + 12, 'text-anchor': 'middle', class: 'sub' }, g); t2.textContent = r.sub; }
      }
      clickable(b.path, r.name || b.shape.name || r.id, r.info, r.meta, r.layer);
    });
    // Liaisons : {from:[x,y], to:[x,y], cls, layer, curve}
    (c.links || []).forEach(function (l) {
      var a = l.from, b = l.to, k = l.curve === undefined ? .18 : l.curve;
      var mx = (a[0] + b[0]) / 2 - (b[1] - a[1]) * k, my = (a[1] + b[1]) / 2 + (b[0] - a[0]) * k;
      var p = el('path', { d: 'M' + a[0] + ' ' + a[1] + ' Q' + mx + ' ' + my + ' ' + b[0] + ' ' + b[1], class: 'link ' + (l.cls || '') }, gk);
      if (l.layer) p.setAttribute('data-layer', l.layer);
    });
    // Marqueurs : {x, y, label, cls, t, info, meta, layer, r, out:'l|r|t|b', dx, dy}
    (c.markers || []).forEach(function (m) {
      var g = el('g', { class: 'mk ' + (m.cls || '') }, gm);
      var x = m.x, y = m.y;
      if (m.out) { // point hors cadre : marqueur en bordure, flèche vers l'extérieur
        x = Math.max(14, Math.min(W - 14, x)); y = Math.max(14, Math.min(H - 14, y));
        g.classList.add('out');
      }
      el('circle', { class: 'halo', cx: x, cy: y, r: m.r ? m.r * 2.2 : 13 }, g);
      el('circle', { class: 'dot', cx: x, cy: y, r: m.r || 5 }, g);
      if (m.out) {
        var ax = m.out === 'l' ? -1 : m.out === 'r' ? 1 : 0, ay = m.out === 't' ? -1 : m.out === 'b' ? 1 : 0;
        el('path', { class: 'arrow', d: 'M' + (x + ax * 9) + ' ' + (y + ay * 9) + ' l' + (ax * 10 + ay * -4) + ' ' + (ay * 10 + ax * -4) + ' M' + (x + ax * 9) + ' ' + (y + ay * 9) + ' l' + (ax * 10 + ay * 4) + ' ' + (ay * 10 + ax * 4) }, g);
      }
      var t = el('text', { x: x + (m.dx !== undefined ? m.dx : 9), y: y + (m.dy !== undefined ? m.dy : 4), 'text-anchor': m.anchor || 'start' }, g);
      t.textContent = m.label;
      var tt = el('title', {}, g); tt.textContent = m.t || m.label;
      clickable(g, m.t || m.label, m.info, m.meta, m.layer);
    });
    // Calques
    var layers = c.layers || [];
    var active = {};
    function applyLayers() {
      root.querySelectorAll('[data-layer]').forEach(function (n) { n.style.display = active[n.getAttribute('data-layer')] === false ? 'none' : ''; });
    }
    if (layers.length) {
      var all = btn('Tout', true, ctl);
      var bl = layers.map(function (L) {
        active[L.id] = L.on !== false;
        var b = btn(L.label, active[L.id], ctl);
        b.addEventListener('click', function () {
          active[L.id] = !active[L.id]; b.classList.toggle('on', active[L.id]);
          all.classList.toggle('on', layers.every(function (x) { return active[x.id]; })); applyLayers();
        });
        return b;
      });
      all.addEventListener('click', function () {
        var allOn = layers.every(function (x) { return active[x.id]; });
        layers.forEach(function (x, i) { active[x.id] = !allOn; bl[i].classList.toggle('on', !allOn); });
        all.classList.toggle('on', !allOn); applyLayers();
      });
      applyLayers();
    }
    // Zoom et déplacement (viewBox)
    var vb = { x: 0, y: 0, w: W, h: H };
    function setVB() { svg.setAttribute('viewBox', vb.x + ' ' + vb.y + ' ' + vb.w + ' ' + vb.h); svg.style.setProperty('--zk', (W / vb.w).toFixed(3)); }
    function zoom(f) {
      var nw = Math.max(W / 8, Math.min(W, vb.w / f)), nh = nw * H / W;
      vb.x += (vb.w - nw) / 2; vb.y += (vb.h - nh) / 2; vb.w = nw; vb.h = nh;
      vb.x = Math.max(0, Math.min(W - vb.w, vb.x)); vb.y = Math.max(0, Math.min(H - vb.h, vb.y)); setVB();
    }
    var z = document.createElement('span'); z.className = 'map-zoom'; ctl.appendChild(z);
    btn('+', false, z).addEventListener('click', function () { zoom(1.6); });
    btn('−', false, z).addEventListener('click', function () { zoom(1 / 1.6); });
    btn('⟲', false, z).addEventListener('click', function () { vb = { x: 0, y: 0, w: W, h: H }; setVB(); });
    var drag = null;
    svg.addEventListener('pointerdown', function (ev) { if (vb.w >= W) return; drag = { x: ev.clientX, y: ev.clientY, vx: vb.x, vy: vb.y }; svg.setPointerCapture(ev.pointerId); svg.classList.add('grab'); });
    svg.addEventListener('pointermove', function (ev) {
      if (!drag) return; var r = svg.getBoundingClientRect(), k = vb.w / r.width;
      vb.x = Math.max(0, Math.min(W - vb.w, drag.vx - (ev.clientX - drag.x) * k)); vb.y = Math.max(0, Math.min(H - vb.h, drag.vy - (ev.clientY - drag.y) * k)); setVB();
    });
    svg.addEventListener('pointerup', function () { drag = null; svg.classList.remove('grab'); });
    svg.addEventListener('pointercancel', function () { drag = null; svg.classList.remove('grab'); });
    setVB();
    legend(lg, c.legend);
    if (c.detail) detail(td, c.detail.name || '', c.detail.note || c.detail, c.detail.meta);
  }

  function tileMap(c, idx, box, ctl, lg, td) {
    if (typeof L === 'undefined' || !L.map) {
      box.classList.add('nomap');
      var ul = document.createElement('ul'); ul.className = 'map-list';
      (c.markers || []).forEach(function (m) { var li = document.createElement('li'); li.textContent = m.label + (m.t ? ' · ' + m.t : ''); ul.appendChild(li); });
      box.appendChild(ul); legend(lg, c.legend);
      if (c.detail) detail(td, c.detail.name || '', c.detail.note || c.detail, c.detail.meta);
      return;
    }
    var map = L.map(box, { scrollWheelZoom: false, attributionControl: true, zoomControl: true });
    map.setView(c.center || [52.23, 21.01], c.zoom || 14);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' }).addTo(map);
    var groups = {}, all = [];
    var colors = { crisis: '#e8664a', inst: '#d9b25e', gov: '#8fb3e8', pres: '#f3e2b3', other: '#b9d37a' };
    (c.markers || []).forEach(function (m) {
      var col = m.color || colors[m.cls] || '#d9b25e';
      var mk = L.circleMarker([m.lat, m.lon], { radius: m.r || 8, color: col, weight: 2, fillColor: col, fillOpacity: .45 });
      mk.bindTooltip(m.label, { direction: 'top', offset: [0, -8], className: 'ymap-tip' });
      mk.on('click', function () { all.forEach(function (x) { x.setStyle({ weight: 2 }); }); mk.setStyle({ weight: 4 }); detail(td, m.t || m.label, m.info, m.meta); });
      var g = m.layer || 'all'; (groups[g] = groups[g] || L.layerGroup().addTo(map)).addLayer(mk); all.push(mk);
    });
    (c.links || []).forEach(function (l) {
      var pl = L.polyline([l.from, l.to], { color: l.color || '#d9b25e', weight: 2, dashArray: l.dash || '6 6', opacity: .8 });
      var g = l.layer || 'all'; (groups[g] = groups[g] || L.layerGroup().addTo(map)).addLayer(pl);
    });
    var layers = c.layers || [];
    if (layers.length) {
      layers.forEach(function (Ly) {
        var on = Ly.on !== false; if (!on && groups[Ly.id]) map.removeLayer(groups[Ly.id]);
        var b = btn(Ly.label, on, ctl);
        b.addEventListener('click', function () {
          on = !on; b.classList.toggle('on', on);
          if (groups[Ly.id]) { if (on) groups[Ly.id].addTo(map); else map.removeLayer(groups[Ly.id]); }
        });
      });
    }
    legend(lg, c.legend);
    if (c.detail) detail(td, c.detail.name || '', c.detail.note || c.detail, c.detail.meta);
    setTimeout(function () { map.invalidateSize(); }, 50);
  }

  M.forEach(function (c, idx) {
    var box = document.getElementById('map' + idx);
    if (!box || box.dataset.ready) return;
    box.dataset.ready = '1';
    var ctl = document.getElementById('mapCtl' + idx), lg = document.getElementById('mapLg' + idx), td = document.getElementById('mapDetail' + idx);
    try { (c.kind === 'tiles' ? tileMap : svgMap)(c, idx, box, ctl, lg, td); }
    catch (e) { box.textContent = 'Carte indisponible.'; if (window.console) console.error(e); }
  });
}

/* Initialisation (rappelée après le déverrouillage d'une analyse archivée) */
window.yaInit = function () { yaCharts(); yaTimelines(); yaMaps(); yaToc(); };
window.yaInit();
