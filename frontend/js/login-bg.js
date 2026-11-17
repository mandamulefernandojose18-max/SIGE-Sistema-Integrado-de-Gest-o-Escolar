/* SIGE — Fundo escolar animado do ecrã de login (canvas 2D, sem dependências).
 * Cena de "novo dia na escola": céu de amanhecer com sol e raios de luz, estrelas,
 * átomo gigante em órbita, bokeh, quadros-negros que escrevem fórmulas sozinhos,
 * bandeirolas, aviões de papel, letras e números a cair, ícones escolares
 * coloridos, rede de partículas, edifício escolar com janelas acesas, árvores e
 * pirilampos. Pausa com o separador inactivo ou após autenticação; respeita
 * prefers-reduced-motion (quadro estático). Sem dados reais nem fictícios.
 */
(function () {
  'use strict';
  var host = document.getElementById('loginView');
  if (!host || document.getElementById('loginBgCanvas')) return;

  var cv = document.createElement('canvas');
  cv.id = 'loginBgCanvas';
  cv.setAttribute('aria-hidden', 'true');
  cv.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;z-index:0;pointer-events:none;';
  host.insertBefore(cv, host.firstChild);
  var ctx = cv.getContext('2d');
  if (!ctx) return;

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var W = 0, H = 0, dpr = 1, t = 0, raf = 0, last = 0, sideW = 0;
  var mx = 0, my = 0, tx = 0, ty = 0;
  var pointer = { x: -9999, y: -9999 };
  var stars = [], parts = [], icons = [], letters = [], windows = [], blobs = [], bokeh = [];
  var trees = [], flies = [], planes = [], boards = [], shoot = null;
  var rnd = function (a, b) { return a + Math.random() * (b - a); };
  var ICONS = ['book', 'pencil', 'cap', 'bulb', 'globe', 'atom', 'ruler', 'block', 'star'];
  var CHARS = ['A', 'B', 'C', 'a', 'b', 'c', '1', '2', '3', '4', '5', '+', '=', '÷', '×', 'π', '√', 'Σ', '%', '?'];
  var FLAGS = ['#f97316', '#22d3ee', '#facc15', '#ec4899', '#4ade80', '#a78bfa'];

  function rr(x, y, w, h, r) { ctx.beginPath(); if (ctx.roundRect) ctx.roundRect(x, y, w, h, r); else ctx.rect(x, y, w, h); }
  function zoneX() {
    if (sideW < 90) return rnd(0, W);
    return Math.random() < 0.5 ? rnd(16, sideW - 16) : W - rnd(16, sideW - 16);
  }
  function dims() {
    var bw = Math.min(W * 0.98, 1300), bh = Math.min(H * 0.24, 200);
    return { bw: bw, bh: bh, x0: (W - bw) / 2, base: H * 0.95, wingW: bw * 0.36, wh: bh * 0.72 };
  }

  /* ---------- Quadros-negros que escrevem sozinhos ---------- */
  function makeBoard(title, lines, accent) { return { title: title, lines: lines, accent: accent, li: 0, ci: 0, acc: 0, hold: 0, state: 'type', alpha: 0 }; }
  function boardUpdate(b, dt) {
    if (b.state === 'type') {
      b.alpha = Math.min(1, b.alpha + dt * 3);
      b.acc += dt * 12;
      while (b.acc >= 1 && b.state === 'type') {
        b.acc--; b.ci++;
        if (b.ci > b.lines[b.li].length) { b.li++; b.ci = 0; if (b.li >= b.lines.length) { b.state = 'hold'; b.hold = 4; } }
      }
    } else if (b.state === 'hold') { b.hold -= dt; if (b.hold <= 0) b.state = 'fade'; }
    else { b.alpha -= dt * 1.6; if (b.alpha <= 0) { b.li = 0; b.ci = 0; b.state = 'type'; } }
  }
  function boardFinish(b) { b.li = b.lines.length; b.ci = 0; b.alpha = 1; b.state = 'hold'; b.hold = 1e9; }
  function boardDraw(b, x, y, w) {
    var fs = Math.max(16, Math.min(24, w / 13)), lh = fs * 1.65, h = 64 + b.lines.length * lh + 20;
    ctx.save();
    ctx.translate(x + w / 2, y); ctx.rotate(Math.sin(t * 0.6 + x) * 0.01); ctx.translate(-w / 2, 0);
    ctx.strokeStyle = 'rgba(255,255,255,0.35)'; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(w * 0.18, 0); ctx.lineTo(w * 0.5, -46); ctx.lineTo(w * 0.82, 0); ctx.stroke();
    var g = ctx.createLinearGradient(0, 0, 0, h); g.addColorStop(0, 'rgba(16,72,62,0.9)'); g.addColorStop(1, 'rgba(8,40,44,0.92)');
    ctx.shadowColor = 'rgba(0,0,0,0.5)'; ctx.shadowBlur = 24; ctx.fillStyle = g; rr(0, 0, w, h, 12); ctx.fill();
    ctx.shadowBlur = 0; ctx.strokeStyle = '#b8793f'; ctx.lineWidth = 7; rr(0, 0, w, h, 12); ctx.stroke();
    ctx.fillStyle = b.accent; ctx.font = '700 ' + Math.round(fs * 0.72) + 'px "Segoe UI",sans-serif'; ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left';
    ctx.fillText(b.title.toUpperCase(), 20, 32);
    ctx.fillStyle = 'rgba(255,255,255,0.18)'; ctx.fillRect(20, 40, w - 40, 1.5);
    ctx.font = '600 ' + fs + 'px "Segoe Print","Bradley Hand","Comic Sans MS",cursive';
    var cols = ['rgba(240,248,255,A)', 'rgba(253,224,71,A)', 'rgba(249,168,212,A)', 'rgba(134,239,172,A)', 'rgba(147,197,253,A)'];
    for (var i = 0; i < b.lines.length; i++) {
      if (i > b.li) break;
      var txt = i < b.li ? b.lines[i] : b.lines[i].slice(0, b.ci);
      ctx.fillStyle = cols[i % cols.length].replace('A', (0.92 * b.alpha).toFixed(2));
      var ly = 70 + (i + 0.7) * lh;
      ctx.fillText(txt, 20, ly);
      if (i === b.li && b.state === 'type' && Math.floor(t * 3) % 2 === 0) ctx.fillRect(22 + ctx.measureText(txt).width, ly - fs * 0.8, 2.5, fs);
    }
    ctx.fillStyle = '#8b5a2b'; ctx.fillRect(-6, h, w + 12, 8);
    ctx.fillStyle = '#fafafa'; ctx.fillRect(14, h - 4, 18, 5); ctx.fillStyle = '#fde68a'; ctx.fillRect(40, h - 4, 14, 5);
    ctx.restore();
  }

  /* ---------- Ícones escolares coloridos (origem no centro, tamanho s) ---------- */
  function icon(kind, s) {
    var h = s / 2;
    ctx.save(); ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.lineWidth = Math.max(1.5, s * 0.045);
    if (kind === 'book') {
      ctx.fillStyle = '#2563eb'; rr(-h * 1.05, -h * 0.55, s * 1.05, h * 1.25, 4); ctx.fill();
      ctx.fillStyle = '#fff7e0';
      ctx.beginPath(); ctx.moveTo(0, -h * 0.45); ctx.quadraticCurveTo(-h * 0.5, -h * 0.68, -h * 0.95, -h * 0.5); ctx.lineTo(-h * 0.95, h * 0.5); ctx.quadraticCurveTo(-h * 0.5, h * 0.32, 0, h * 0.55); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.moveTo(0, -h * 0.45); ctx.quadraticCurveTo(h * 0.5, -h * 0.68, h * 0.95, -h * 0.5); ctx.lineTo(h * 0.95, h * 0.5); ctx.quadraticCurveTo(h * 0.5, h * 0.32, 0, h * 0.55); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = '#94a3b8'; ctx.beginPath();
      for (var k = 0; k < 3; k++) { var yy = -h * 0.2 + k * h * 0.22; ctx.moveTo(-h * 0.8, yy); ctx.lineTo(-h * 0.15, yy + 0.04 * h); ctx.moveTo(h * 0.15, yy + 0.04 * h); ctx.lineTo(h * 0.8, yy); }
      ctx.stroke();
    } else if (kind === 'pencil') {
      ctx.rotate(-0.78);
      ctx.fillStyle = '#facc15'; ctx.fillRect(-h * 0.18, -h * 0.9, h * 0.36, h * 1.4);
      ctx.fillStyle = '#f59e0b'; ctx.fillRect(-h * 0.04, -h * 0.9, h * 0.08, h * 1.4);
      ctx.fillStyle = '#f472b6'; rr(-h * 0.18, -h * 1.12, h * 0.36, h * 0.24, 3); ctx.fill();
      ctx.fillStyle = '#cbd5e1'; ctx.fillRect(-h * 0.18, -h * 0.9, h * 0.36, h * 0.12);
      ctx.fillStyle = '#fde68a'; ctx.beginPath(); ctx.moveTo(-h * 0.18, h * 0.5); ctx.lineTo(h * 0.18, h * 0.5); ctx.lineTo(0, h * 0.98); ctx.closePath(); ctx.fill();
      ctx.fillStyle = '#1f2937'; ctx.beginPath(); ctx.moveTo(-h * 0.06, h * 0.82); ctx.lineTo(h * 0.06, h * 0.82); ctx.lineTo(0, h * 0.98); ctx.closePath(); ctx.fill();
    } else if (kind === 'cap') {
      ctx.fillStyle = '#1f2937'; ctx.beginPath(); ctx.moveTo(-h * 0.5, h * 0.05); ctx.lineTo(-h * 0.5, h * 0.55); ctx.quadraticCurveTo(0, h * 0.9, h * 0.5, h * 0.55); ctx.lineTo(h * 0.5, h * 0.05); ctx.closePath(); ctx.fill();
      ctx.fillStyle = '#111827'; ctx.strokeStyle = '#818cf8'; ctx.beginPath(); ctx.moveTo(-h, -h * 0.1); ctx.lineTo(0, -h * 0.6); ctx.lineTo(h, -h * 0.1); ctx.lineTo(0, h * 0.4); ctx.closePath(); ctx.fill(); ctx.stroke();
      ctx.strokeStyle = '#fbbf24'; ctx.lineWidth = Math.max(2, s * 0.05); ctx.beginPath(); ctx.moveTo(0, -h * 0.1); ctx.lineTo(h * 0.9, -h * 0.02); ctx.lineTo(h * 0.9, h * 0.5); ctx.stroke();
      ctx.fillStyle = '#fbbf24'; ctx.beginPath(); ctx.arc(h * 0.9, h * 0.55, h * 0.1, 0, 6.283); ctx.fill();
    } else if (kind === 'bulb') {
      var bg = ctx.createRadialGradient(0, -h * 0.2, 2, 0, -h * 0.2, h * 0.7); bg.addColorStop(0, '#fffbeb'); bg.addColorStop(1, '#fbbf24');
      ctx.fillStyle = bg; ctx.beginPath(); ctx.arc(0, -h * 0.2, h * 0.58, 0.85 * Math.PI, 2.15 * Math.PI); ctx.lineTo(h * 0.24, h * 0.45); ctx.lineTo(-h * 0.24, h * 0.45); ctx.closePath(); ctx.fill();
      ctx.fillStyle = '#94a3b8'; rr(-h * 0.26, h * 0.45, h * 0.52, h * 0.2, 3); ctx.fill(); rr(-h * 0.18, h * 0.68, h * 0.36, h * 0.14, 3); ctx.fill();
      ctx.strokeStyle = '#b45309'; ctx.beginPath(); ctx.moveTo(-h * 0.2, h * 0.4); ctx.lineTo(-h * 0.1, -h * 0.1); ctx.lineTo(0, h * 0.1); ctx.lineTo(h * 0.1, -h * 0.1); ctx.lineTo(h * 0.2, h * 0.4); ctx.stroke();
    } else if (kind === 'globe') {
      ctx.fillStyle = '#38bdf8'; ctx.beginPath(); ctx.arc(0, 0, h * 0.8, 0, 6.283); ctx.fill();
      ctx.fillStyle = '#4ade80'; ctx.beginPath(); ctx.ellipse(-h * 0.25, -h * 0.2, h * 0.28, h * 0.22, 0.5, 0, 6.283); ctx.ellipse(h * 0.3, h * 0.25, h * 0.2, h * 0.3, -0.4, 0, 6.283); ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.55)'; ctx.beginPath(); ctx.ellipse(0, 0, h * 0.35, h * 0.8, 0, 0, 6.283); ctx.moveTo(-h * 0.8, 0); ctx.lineTo(h * 0.8, 0); ctx.stroke();
      ctx.strokeStyle = '#fbbf24'; ctx.lineWidth = Math.max(2, s * 0.06); ctx.beginPath(); ctx.arc(0, 0, h * 0.98, 0.15 * Math.PI, 0.85 * Math.PI); ctx.stroke();
    } else if (kind === 'atom') {
      ctx.strokeStyle = '#22d3ee'; ctx.lineWidth = Math.max(2, s * 0.05);
      for (var q = 0; q < 3; q++) { ctx.save(); ctx.rotate(q * 1.047 + t * 0.4); ctx.beginPath(); ctx.ellipse(0, 0, h, h * 0.36, 0, 0, 6.283); ctx.stroke(); ctx.restore(); }
      ctx.fillStyle = '#f472b6'; ctx.beginPath(); ctx.arc(0, 0, h * 0.2, 0, 6.283); ctx.fill();
    } else if (kind === 'ruler') {
      ctx.rotate(0.5); ctx.fillStyle = '#fbbf24'; rr(-h, -h * 0.26, s, h * 0.52, 4); ctx.fill();
      ctx.strokeStyle = '#78350f'; ctx.beginPath();
      for (var m = -4; m <= 4; m++) { ctx.moveTo(m * h * 0.22, -h * 0.26); ctx.lineTo(m * h * 0.22, -h * (m % 2 ? 0.1 : 0.02)); }
      ctx.stroke();
    } else if (kind === 'star') {
      ctx.fillStyle = '#fde047'; ctx.beginPath();
      for (var p = 0; p < 10; p++) { var rad = p % 2 ? h * 0.42 : h * 0.95, an = -Math.PI / 2 + p * Math.PI / 5; ctx.lineTo(Math.cos(an) * rad, Math.sin(an) * rad); }
      ctx.closePath(); ctx.fill();
    } else { // block (cubo com letra)
      ctx.fillStyle = '#a78bfa'; rr(-h * 0.7, -h * 0.7, h * 1.4, h * 1.4, 8); ctx.fill();
      ctx.fillStyle = '#ede9fe'; ctx.font = '800 ' + Math.round(s * 0.7) + 'px "Segoe UI",sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('A', 0, h * 0.04);
    }
    ctx.restore();
  }

  /* ---------- Construção da cena ---------- */
  function build() {
    var area = W * H, i;
    stars = []; parts = []; icons = []; letters = []; windows = []; blobs = []; bokeh = []; trees = []; flies = []; planes = []; boards = [];
    sideW = Math.max(0, (W - 460) / 2);
    for (i = 0; i < Math.min(240, Math.round(area / 6000)); i++) stars.push({ x: Math.random(), y: Math.random() * 0.6, r: rnd(0.4, 1.6), p: rnd(0, 6.28), s: rnd(0.6, 2.4), d: rnd(0.2, 1) });
    for (i = 0; i < Math.min(60, Math.round(area / 26000)); i++) parts.push({ x: rnd(0, W), y: rnd(0, H * 0.8), vx: rnd(-0.18, 0.18), vy: rnd(-0.14, 0.14), r: rnd(1, 2.2) });
    for (i = 0; i < 14; i++) icons.push({ x: zoneX(), y: rnd(60, H * 0.88), z: rnd(0.7, 1.3), icon: ICONS[i % ICONS.length], sz: rnd(46, 74), rot: rnd(-0.4, 0.4), ph: rnd(0, 6.28), sp: rnd(0.4, 0.9), glow: [48, 199, 262, 330, 150][i % 5] });
    for (i = 0; i < 24; i++) letters.push({ x: zoneX(), y: rnd(-40, H * 0.8), v: rnd(22, 52), ch: CHARS[(Math.random() * CHARS.length) | 0], sz: rnd(22, 40), hue: rnd(0, 360), ph: rnd(0, 6.28) });
    for (i = 0; i < 4; i++) blobs.push({ x: rnd(0.1, 0.9), y: rnd(0.1, 0.5), r: rnd(0.35, 0.6), h: [275, 215, 320, 190][i], ph: rnd(0, 6.28), sp: rnd(0.08, 0.2) });
    for (i = 0; i < 16; i++) bokeh.push({ x: rnd(0, W), y: rnd(0, H), r: rnd(30, 110), h: rnd(180, 340), vx: rnd(-6, 6), vy: rnd(-8, -2), a: rnd(0.04, 0.1) });
    var d = dims(), cols = Math.max(3, Math.round(d.wingW / 46));
    for (var wg = 0; wg < 2; wg++) for (var r = 0; r < 2; r++) for (var c = 0; c < cols; c++) windows.push({ wg: wg, c: c, r: r, on: Math.random() < 0.45, nx: rnd(2, 10) });
    windows.cols = cols;
    for (i = 0; i < Math.max(5, Math.round(W / 150)); i++) trees.push({ x: rnd(0, W), s: rnd(0.7, 1.3), ph: rnd(0, 6.28) });
    for (i = 0; i < 26; i++) flies.push({ x: rnd(0, W), y: rnd(H * 0.7, H * 0.97), ph: rnd(0, 6.28), sp: rnd(0.4, 1.2) });
    for (i = 0; i < 2; i++) planes.push({ x: i ? W + 100 : -100, y0: H * (i ? 0.3 : 0.18), dir: i ? -1 : 1, v: rnd(60, 90), ph: rnd(0, 6) });
    if (sideW >= 250) {
      var bwid = Math.min(330, sideW - 50);
      boards.push({ b: makeBoard('Matemática', ['2x + 6 = 14', 'x = 4', 'a² + b² = c²', '∫ x dx = x²/2', 'sen²θ + cos²θ = 1'], '#fde047'), x: (sideW - bwid) / 2, w: bwid });
      boards.push({ b: makeBoard('Ciências', ['H₂O + CO₂ → O₂', 'E = m · c²', 'F = m · a', 'v = Δs / Δt', 'ρ = m / V'], '#86efac'), x: W - sideW + (sideW - bwid) / 2, w: bwid });
      if (reduce) boards.forEach(function (o) { boardFinish(o.b); });
    }
  }

  function resize() {
    var rc = host.getBoundingClientRect();
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = Math.max(1, rc.width); H = Math.max(1, rc.height);
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    build();
    if (reduce) frame(0);
  }

  /* ---------- Camadas ---------- */
  function sky(dt) {
    var g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, '#050f3a'); g.addColorStop(0.42, '#2a1a7a'); g.addColorStop(0.72, '#8a3a8c'); g.addColorStop(0.9, '#ff7e5f'); g.addColorStop(1, '#ffb36b');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    ctx.globalCompositeOperation = 'lighter';
    var i, b, a;
    for (i = 0; i < blobs.length; i++) {
      b = blobs[i]; a = t * b.sp + b.ph;
      var x = (b.x + Math.sin(a) * 0.12 + mx * 0.02) * W, y = (b.y + Math.cos(a * 0.8) * 0.1 + my * 0.02) * H, r = b.r * Math.max(W, H);
      var rg = ctx.createRadialGradient(x, y, 0, x, y, r);
      rg.addColorStop(0, 'hsla(' + b.h + ',90%,58%,0.12)'); rg.addColorStop(1, 'hsla(' + b.h + ',90%,58%,0)');
      ctx.fillStyle = rg; ctx.fillRect(0, 0, W, H);
    }
    // sol nascente + raios
    var sx = W / 2 + mx * -10, sy = H * 0.9, sr = Math.max(W, H) * 0.7;
    var sg = ctx.createRadialGradient(sx, sy, 0, sx, sy, sr);
    sg.addColorStop(0, 'rgba(255,230,150,0.75)'); sg.addColorStop(0.25, 'rgba(255,150,90,0.3)'); sg.addColorStop(1, 'rgba(255,100,120,0)');
    ctx.fillStyle = sg; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = 'rgba(255,210,140,0.07)';
    for (i = 0; i < 16; i++) {
      a = t * 0.04 + i * 0.3927 - Math.PI * 0.5;
      ctx.beginPath(); ctx.moveTo(sx, sy); ctx.arc(sx, sy, sr * 1.8, a, a + 0.09); ctx.closePath(); ctx.fill();
    }
    // bokeh
    for (i = 0; i < bokeh.length; i++) {
      b = bokeh[i]; b.x += b.vx * dt; b.y += b.vy * dt;
      if (b.y < -120) { b.y = H + 100; b.x = rnd(0, W); } if (b.x < -120) b.x = W + 100; if (b.x > W + 120) b.x = -100;
      var bgd = ctx.createRadialGradient(b.x, b.y, 0, b.x, b.y, b.r);
      bgd.addColorStop(0, 'hsla(' + b.h + ',90%,70%,' + b.a + ')'); bgd.addColorStop(0.8, 'hsla(' + b.h + ',90%,70%,' + (b.a * 0.7) + ')'); bgd.addColorStop(1, 'hsla(' + b.h + ',90%,70%,0)');
      ctx.fillStyle = bgd; ctx.beginPath(); ctx.arc(b.x + mx * 20, b.y + my * 12, b.r, 0, 6.283); ctx.fill();
    }
    ctx.globalCompositeOperation = 'source-over';
  }

  function starfield(dt) {
    for (var i = 0; i < stars.length; i++) {
      var s = stars[i], a = (0.35 + 0.65 * (0.5 + 0.5 * Math.sin(t * s.s + s.p))) * s.d * (1 - s.y * 0.9);
      ctx.fillStyle = 'rgba(255,255,255,' + a.toFixed(3) + ')';
      ctx.beginPath(); ctx.arc(s.x * W + mx * 14 * s.d, s.y * H + my * 8 * s.d, s.r, 0, 6.283); ctx.fill();
    }
    if (!shoot && !reduce && Math.random() < dt * 0.3) shoot = { x: rnd(0.1, 0.9) * W, y: rnd(0, 0.3) * H, vx: rnd(420, 600), vy: rnd(170, 260), l: 0 };
    if (shoot) {
      shoot.x += shoot.vx * dt; shoot.y += shoot.vy * dt; shoot.l += dt;
      var tl = ctx.createLinearGradient(shoot.x, shoot.y, shoot.x - shoot.vx * 0.2, shoot.y - shoot.vy * 0.2);
      tl.addColorStop(0, 'rgba(255,255,255,1)'); tl.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.strokeStyle = tl; ctx.lineWidth = 2.5; ctx.beginPath();
      ctx.moveTo(shoot.x, shoot.y); ctx.lineTo(shoot.x - shoot.vx * 0.2, shoot.y - shoot.vy * 0.2); ctx.stroke();
      if (shoot.l > 1.4 || shoot.x > W + 50 || shoot.y > H) shoot = null;
    }
  }

  function atom() { // átomo gigante em órbita, atrás do cartão
    var cx = W / 2 + mx * 12, cy = H * 0.5 + my * 8, rx = Math.max(W * 0.46, 360), ry = rx * 0.3;
    ctx.globalCompositeOperation = 'lighter';
    for (var o = 0; o < 3; o++) {
      var an = o * 1.0472 + t * 0.06 - 0.3, ca = Math.cos(an), sa = Math.sin(an);
      ctx.strokeStyle = 'rgba(170,200,255,0.22)'; ctx.lineWidth = 1.6; ctx.beginPath();
      for (var k = 0; k <= 80; k++) { var u = k / 80 * 6.2832, ex = rx * Math.cos(u), ey = ry * Math.sin(u); var X = cx + ex * ca - ey * sa, Y = cy + ex * sa + ey * ca; if (k) ctx.lineTo(X, Y); else ctx.moveTo(X, Y); }
      ctx.stroke();
      for (var e = 0; e < 2; e++) {
        var uu = t * (0.5 + o * 0.12) + e * Math.PI + o, exx = rx * Math.cos(uu), eyy = ry * Math.sin(uu), PX = cx + exx * ca - eyy * sa, PY = cy + exx * sa + eyy * ca;
        var eg = ctx.createRadialGradient(PX, PY, 0, PX, PY, 18); eg.addColorStop(0, 'rgba(255,255,255,0.95)'); eg.addColorStop(0.3, 'rgba(120,200,255,0.55)'); eg.addColorStop(1, 'rgba(120,200,255,0)');
        ctx.fillStyle = eg; ctx.beginPath(); ctx.arc(PX, PY, 18, 0, 6.283); ctx.fill();
      }
    }
    ctx.globalCompositeOperation = 'source-over';
  }

  function network(dt) {
    var lim = Math.min(150, W * 0.14), i, j, p, q, dx, dy, d;
    for (i = 0; i < parts.length; i++) {
      p = parts[i]; p.x += p.vx * dt * 60; p.y += p.vy * dt * 60;
      if (p.x < 0 || p.x > W) p.vx *= -1; if (p.y < 0 || p.y > H * 0.82) p.vy *= -1;
      dx = p.x - pointer.x; dy = p.y - pointer.y; d = Math.sqrt(dx * dx + dy * dy);
      if (d < 140 && d > 0) { p.x += (dx / d) * (140 - d) * 0.02; p.y += (dy / d) * (140 - d) * 0.02; }
    }
    ctx.lineWidth = 1;
    for (i = 0; i < parts.length; i++) {
      p = parts[i];
      for (j = i + 1; j < parts.length; j++) {
        q = parts[j]; dx = p.x - q.x; dy = p.y - q.y; d = dx * dx + dy * dy;
        if (d < lim * lim) { ctx.strokeStyle = 'rgba(200,215,255,' + (0.3 * (1 - Math.sqrt(d) / lim)).toFixed(3) + ')'; ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke(); }
      }
      dx = p.x - pointer.x; dy = p.y - pointer.y; d = Math.sqrt(dx * dx + dy * dy);
      if (d < 200) { ctx.strokeStyle = 'rgba(255,200,110,' + (0.65 * (1 - d / 200)).toFixed(3) + ')'; ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(pointer.x, pointer.y); ctx.stroke(); }
      ctx.fillStyle = 'rgba(220,230,255,0.85)'; ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, 6.283); ctx.fill();
    }
  }

  function bunting() {
    var y0 = -6, sag = Math.min(H * 0.07, 60), n = Math.max(8, Math.round(W / 52));
    ctx.strokeStyle = 'rgba(255,255,255,0.55)'; ctx.lineWidth = 1.5; ctx.beginPath();
    for (var i = 0; i <= 60; i++) { var u = i / 60; ctx.lineTo(u * W, y0 + sag * 4 * u * (1 - u)); }
    ctx.stroke();
    for (i = 0; i < n; i++) {
      var uu = (i + 0.5) / n, x = uu * W, y = y0 + sag * 4 * uu * (1 - uu), sw = Math.sin(t * 1.6 + i * 0.7) * 3, fw = 20, fh = 28;
      ctx.fillStyle = FLAGS[i % FLAGS.length]; ctx.globalAlpha = 0.92;
      ctx.beginPath(); ctx.moveTo(x - fw / 2, y); ctx.lineTo(x + fw / 2, y); ctx.lineTo(x + sw, y + fh); ctx.closePath(); ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  function planesDraw(dt) {
    for (var i = 0; i < planes.length; i++) {
      var p = planes[i]; p.x += p.dir * p.v * dt;
      if ((p.dir > 0 && p.x > W + 140) || (p.dir < 0 && p.x < -140)) { p.x = p.dir > 0 ? -120 : W + 120; p.y0 = rnd(0.12, 0.4) * H; p.ph = rnd(0, 6); }
      var fy = function (x) { return p.y0 + Math.sin(x * 0.011 + p.ph) * 38 + (p.dir > 0 ? x * 0.03 : -x * 0.03); };
      for (var k = 1; k <= 16; k++) { var tx2 = p.x - p.dir * k * 16; ctx.fillStyle = 'rgba(255,255,255,' + (0.5 * (1 - k / 17)).toFixed(3) + ')'; ctx.beginPath(); ctx.arc(tx2, fy(tx2), 2.2 - k * 0.08, 0, 6.283); ctx.fill(); }
      var y = fy(p.x), sl = Math.atan2(fy(p.x + p.dir) - y, p.dir);
      ctx.save(); ctx.translate(p.x, y); ctx.rotate(sl); ctx.scale(p.dir, 1);
      ctx.shadowColor = 'rgba(255,255,255,0.6)'; ctx.shadowBlur = 12;
      ctx.fillStyle = '#ffffff'; ctx.beginPath(); ctx.moveTo(26, 0); ctx.lineTo(-18, -13); ctx.lineTo(-8, 0); ctx.closePath(); ctx.fill();
      ctx.shadowBlur = 0; ctx.fillStyle = '#c7d2fe'; ctx.beginPath(); ctx.moveTo(26, 0); ctx.lineTo(-8, 0); ctx.lineTo(-18, 10); ctx.lineTo(-4, 4); ctx.closePath(); ctx.fill();
      ctx.restore();
    }
  }

  function floaters(dt) {
    for (var i = 0; i < icons.length; i++) {
      var g = icons[i], x = g.x + Math.sin(t * g.sp + g.ph) * 14 + mx * 30 * g.z, y = g.y + Math.cos(t * g.sp * 0.8 + g.ph) * 16 + my * 18 * g.z;
      ctx.save(); ctx.translate(x, y); ctx.rotate(g.rot + Math.sin(t * g.sp + g.ph) * 0.12);
      ctx.globalAlpha = 0.78; ctx.shadowColor = 'hsla(' + g.glow + ',95%,65%,0.8)'; ctx.shadowBlur = 22;
      icon(g.icon, g.sz * g.z);
      ctx.restore();
    }
    ctx.globalAlpha = 1;
    for (i = 0; i < letters.length; i++) {
      var l = letters[i]; l.y += l.v * dt;
      if (l.y > H * 0.82) { l.y = -40; l.x = zoneX(); l.ch = CHARS[(Math.random() * CHARS.length) | 0]; l.hue = rnd(0, 360); }
      var a = Math.min(1, (l.y + 40) / 120) * Math.min(1, (H * 0.82 - l.y) / 120) * 0.65;
      ctx.save(); ctx.translate(l.x + Math.sin(t * 0.8 + l.ph) * 16 + mx * 22, l.y); ctx.rotate(Math.sin(t * 0.6 + l.ph) * 0.35);
      ctx.fillStyle = 'hsla(' + l.hue + ',90%,75%,' + a.toFixed(3) + ')'; ctx.shadowColor = 'hsla(' + l.hue + ',95%,65%,0.8)'; ctx.shadowBlur = 14;
      ctx.font = '800 ' + Math.round(l.sz) + 'px "Segoe UI",sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(l.ch, 0, 0);
      ctx.restore();
    }
  }

  function ground(dt) {
    var d = dims(), x0 = d.x0 + mx * -6, base = d.base, bh = d.bh, top = base - bh, bw = d.bw, i;
    var layers = [{ c: '#4a2a9a', y: 0.8, a: 0.035, f: 1.3, k: 10 }, { c: '#2a1a78', y: 0.87, a: 0.03, f: 2.1, k: 18 }];
    for (var l = 0; l < layers.length; l++) {
      var L = layers[l]; ctx.fillStyle = L.c; ctx.globalAlpha = 0.9; ctx.beginPath(); ctx.moveTo(0, H);
      for (var x = 0; x <= W + 20; x += 20) ctx.lineTo(x, H * L.y + Math.sin(x / W * 6.28 * L.f + l * 1.7) * H * L.a - mx * L.k * 0.5);
      ctx.lineTo(W, H); ctx.closePath(); ctx.fill();
    }
    ctx.globalAlpha = 1;
    var bg = ctx.createLinearGradient(0, top, 0, base); bg.addColorStop(0, '#2d2090'); bg.addColorStop(1, '#150f4a');
    ctx.fillStyle = bg;
    var cw = bw * 0.28, cx0 = x0 + bw / 2 - cw / 2, mid = x0 + bw / 2;
    ctx.fillRect(x0, base - d.wh, d.wingW, d.wh); ctx.fillRect(x0 + bw - d.wingW, base - d.wh, d.wingW, d.wh);
    ctx.fillRect(cx0 - 4, top + bh * 0.2, cw + 8, bh * 0.8 + 2);
    ctx.fillStyle = '#3a2cae'; ctx.beginPath(); ctx.moveTo(cx0 - 16, top + bh * 0.2); ctx.lineTo(mid, top - bh * 0.1); ctx.lineTo(cx0 + cw + 16, top + bh * 0.2); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = 'rgba(255,180,100,0.7)'; ctx.lineWidth = 2; ctx.beginPath();
    ctx.moveTo(cx0 - 16, top + bh * 0.2); ctx.lineTo(mid, top - bh * 0.1); ctx.lineTo(cx0 + cw + 16, top + bh * 0.2);
    ctx.moveTo(x0, base - d.wh); ctx.lineTo(x0 + d.wingW, base - d.wh); ctx.moveTo(x0 + bw - d.wingW, base - d.wh); ctx.lineTo(x0 + bw, base - d.wh); ctx.stroke();
    ctx.fillStyle = 'rgba(255,255,255,0.14)';
    for (i = 0; i < 6; i++) ctx.fillRect(cx0 + cw * (0.07 + i * 0.172), top + bh * 0.27, cw * 0.07, bh * 0.66);
    var dg = ctx.createLinearGradient(0, base - bh * 0.4, 0, base - bh * 0.06); dg.addColorStop(0, '#fef08a'); dg.addColorStop(1, '#f59e0b');
    ctx.shadowColor = 'rgba(253,224,71,0.9)'; ctx.shadowBlur = 24; ctx.fillStyle = dg;
    ctx.beginPath(); ctx.moveTo(mid - cw * 0.09, base - bh * 0.06); ctx.lineTo(mid - cw * 0.09, base - bh * 0.3); ctx.arc(mid, base - bh * 0.3, cw * 0.09, Math.PI, 0); ctx.lineTo(mid + cw * 0.09, base - bh * 0.06); ctx.closePath(); ctx.fill();
    ctx.shadowBlur = 0;
    var cly = top + bh * 0.1, clr = bh * 0.075;
    ctx.fillStyle = '#fde68a'; ctx.beginPath(); ctx.arc(mid, cly, clr, 0, 6.283); ctx.fill();
    ctx.strokeStyle = '#2d2090'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(mid, cly); ctx.lineTo(mid + Math.cos(t * 0.5) * clr * 0.75, cly + Math.sin(t * 0.5) * clr * 0.75); ctx.moveTo(mid, cly); ctx.lineTo(mid, cly - clr * 0.6); ctx.stroke();
    var fyp = top - bh * 0.1;
    ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(mid, fyp); ctx.lineTo(mid, fyp - 36); ctx.stroke();
    ctx.fillStyle = '#f97316'; ctx.beginPath(); ctx.moveTo(mid, fyp - 36);
    for (var f = 0; f <= 26; f += 4) ctx.lineTo(mid + f, fyp - 36 + Math.sin(t * 4 + f * 0.4) * 2.5);
    for (f = 26; f >= 0; f -= 4) ctx.lineTo(mid + f, fyp - 22 + Math.sin(t * 4 + f * 0.4) * 2.5);
    ctx.closePath(); ctx.fill();
    ctx.fillStyle = '#4636b8'; ctx.fillRect(cx0 - 8, base - bh * 0.06, cw + 16, bh * 0.03); ctx.fillRect(cx0 - 22, base - bh * 0.03, cw + 44, bh * 0.03);
    var cols = windows.cols, cw2 = d.wingW / cols;
    for (i = 0; i < windows.length; i++) {
      var w = windows[i]; w.nx -= dt;
      if (w.nx <= 0) { w.on = !w.on || Math.random() < 0.3; w.nx = rnd(3, 12); }
      var wx = (w.wg ? x0 + bw - d.wingW : x0) + w.c * cw2 + cw2 * 0.2, wy = base - d.wh + d.wh * 0.14 + w.r * d.wh * 0.42, ww = cw2 * 0.6, wht = d.wh * 0.28;
      if (w.on) { ctx.shadowColor = 'rgba(253,224,71,0.8)'; ctx.shadowBlur = 12; ctx.fillStyle = 'rgba(254,240,138,0.95)'; }
      else { ctx.shadowBlur = 0; ctx.fillStyle = 'rgba(129,140,248,0.25)'; }
      ctx.fillRect(wx, wy, ww, wht);
    }
    ctx.shadowBlur = 0;
    ctx.fillStyle = '#0d0a35'; ctx.fillRect(0, base, W, H - base);
    for (i = 0; i < trees.length; i++) {
      var tr = trees[i], sw = Math.sin(t * 0.9 + tr.ph) * 2, ts = tr.s * Math.min(1, H / 700) * 40;
      ctx.fillStyle = '#1e1b4b'; ctx.fillRect(tr.x - ts * 0.08, base - ts * 0.8, ts * 0.16, ts * 0.9);
      ctx.fillStyle = '#0f4a52';
      ctx.beginPath(); ctx.arc(tr.x + sw, base - ts * 1.1, ts * 0.55, 0, 6.283); ctx.arc(tr.x - ts * 0.4 + sw, base - ts * 0.8, ts * 0.4, 0, 6.283); ctx.arc(tr.x + ts * 0.4 + sw, base - ts * 0.8, ts * 0.4, 0, 6.283); ctx.fill();
      ctx.fillStyle = 'rgba(94,234,212,0.22)'; ctx.beginPath(); ctx.arc(tr.x + sw - ts * 0.15, base - ts * 1.25, ts * 0.25, 0, 6.283); ctx.fill();
    }
    ctx.globalCompositeOperation = 'lighter';
    for (i = 0; i < flies.length; i++) {
      var fl = flies[i], fx = fl.x + Math.sin(t * fl.sp + fl.ph) * 30, fy2 = fl.y + Math.cos(t * fl.sp * 1.3 + fl.ph) * 14, fa = 0.3 + 0.7 * Math.max(0, Math.sin(t * 2 * fl.sp + fl.ph));
      var fg = ctx.createRadialGradient(fx, fy2, 0, fx, fy2, 11); fg.addColorStop(0, 'rgba(255,245,160,' + fa.toFixed(2) + ')'); fg.addColorStop(1, 'rgba(255,220,80,0)');
      ctx.fillStyle = fg; ctx.beginPath(); ctx.arc(fx, fy2, 11, 0, 6.283); ctx.fill();
    }
    ctx.globalCompositeOperation = 'source-over';
    var v = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.35, W / 2, H / 2, Math.max(W, H) * 0.85);
    v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(10,5,40,0.4)');
    ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
  }

  function frame(dt) {
    mx += (tx - mx) * 0.05; my += (ty - my) * 0.05;
    sky(dt); starfield(dt); atom(); network(dt); bunting(); planesDraw(dt);
    for (var i = 0; i < boards.length; i++) { if (!reduce) boardUpdate(boards[i].b, dt); boardDraw(boards[i].b, boards[i].x, Math.max(80, H * 0.14), boards[i].w); }
    floaters(dt); ground(dt);
  }

  function loop(ts) {
    raf = 0;
    if (document.hidden || document.body.classList.contains('authenticated')) { last = 0; return poll(); }
    var dt = last ? Math.min(0.05, (ts - last) / 1000) : 0.016; last = ts; t += dt;
    frame(dt);
    raf = requestAnimationFrame(loop);
  }
  function poll() { if (!raf) setTimeout(function () { if (!raf) raf = requestAnimationFrame(loop); }, 800); }

  host.addEventListener('pointermove', function (e) {
    var rc = host.getBoundingClientRect();
    pointer.x = e.clientX - rc.left; pointer.y = e.clientY - rc.top;
    tx = (pointer.x / W - 0.5) * 2; ty = (pointer.y / H - 0.5) * 2;
  }, { passive: true });
  host.addEventListener('pointerleave', function () { pointer.x = pointer.y = -9999; tx = ty = 0; }, { passive: true });
  window.addEventListener('resize', resize);
  document.addEventListener('visibilitychange', function () { if (!document.hidden && !raf && !reduce) raf = requestAnimationFrame(loop); });

  resize();
  if (!reduce) raf = requestAnimationFrame(loop);
})();
