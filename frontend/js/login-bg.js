/* SIGE — Fundo animado do ecrã de login (canvas 2D, sem dependências).
 * Estética moderna "edu-tech": malha de gradientes fluidos (índigo/ciano/violeta),
 * grelha de pontos com ondas e foco no rato, grafo de conhecimento com pulsos de
 * luz, átomo orbital, ilustrações escolares em linha luminosa que se desenham
 * sozinhas dentro de bolhas de vidro, painéis holográficos que escrevem fórmulas,
 * edifício escolar em traço de néon e feixe de luz. Pausa com o separador inactivo
 * ou após autenticação; respeita prefers-reduced-motion. Sem dados reais nem fictícios.
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
  var blobs = [], nodes = [], bubbles = [], dust = [], windows = [], panels = [];
  var rnd = function (a, b) { return a + Math.random() * (b - a); };
  var KINDS = ['cap', 'book', 'atom', 'bulb', 'flask', 'globe', 'pencil', 'bars'];
  var PAL = [['#22d3ee', '#818cf8'], ['#a78bfa', '#f0abfc'], ['#fbbf24', '#fb7185'], ['#34d399', '#22d3ee']];

  function rr(x, y, w, h, r) { ctx.beginPath(); if (ctx.roundRect) ctx.roundRect(x, y, w, h, r); else ctx.rect(x, y, w, h); }
  function dims() {
    var bw = Math.min(W * 0.98, 1300), bh = Math.min(H * 0.22, 190);
    return { bw: bw, bh: bh, x0: (W - bw) / 2, base: H * 0.955, wingW: bw * 0.36, wh: bh * 0.7 };
  }

  /* ---------- Painéis holográficos que escrevem fórmulas ---------- */
  function makePanel(title, lines, c1, c2) { return { title: title, lines: lines, c1: c1, c2: c2, li: 0, ci: 0, acc: 0, hold: 0, state: 'type', alpha: 0 }; }
  function panelUpdate(b, dt) {
    if (b.state === 'type') {
      b.alpha = Math.min(1, b.alpha + dt * 3); b.acc += dt * 13;
      while (b.acc >= 1 && b.state === 'type') {
        b.acc--; b.ci++;
        if (b.ci > b.lines[b.li].length) { b.li++; b.ci = 0; if (b.li >= b.lines.length) { b.state = 'hold'; b.hold = 4.5; } }
      }
    } else if (b.state === 'hold') { b.hold -= dt; if (b.hold <= 0) b.state = 'fade'; }
    else { b.alpha -= dt * 1.5; if (b.alpha <= 0) { b.li = 0; b.ci = 0; b.state = 'type'; } }
  }
  function panelFinish(b) { b.li = b.lines.length; b.ci = 0; b.alpha = 1; b.state = 'hold'; b.hold = 1e9; }
  function panelDraw(b, x, y, w) {
    var fs = Math.max(15, Math.min(20, w / 16)), lh = fs * 1.9, h = 48 + b.lines.length * lh + 14;
    ctx.save(); ctx.translate(x, y + Math.sin(t * 0.7 + x) * 5);
    var fill = ctx.createLinearGradient(0, 0, w, h); fill.addColorStop(0, 'rgba(255,255,255,0.09)'); fill.addColorStop(1, 'rgba(255,255,255,0.02)');
    ctx.shadowColor = 'rgba(34,211,238,0.25)'; ctx.shadowBlur = 30; ctx.fillStyle = fill; rr(0, 0, w, h, 16); ctx.fill(); ctx.shadowBlur = 0;
    var st = ctx.createLinearGradient(0, 0, w, h); st.addColorStop(0, b.c1); st.addColorStop(1, b.c2);
    ctx.globalAlpha = 0.55; ctx.strokeStyle = st; ctx.lineWidth = 1.4; rr(0, 0, w, h, 16); ctx.stroke(); ctx.globalAlpha = 1;
    var dots = ['#fb7185', '#fbbf24', '#34d399'];
    for (var d = 0; d < 3; d++) { ctx.fillStyle = dots[d]; ctx.globalAlpha = 0.85; ctx.beginPath(); ctx.arc(18 + d * 14, 20, 4, 0, 6.283); ctx.fill(); }
    ctx.globalAlpha = 1; ctx.fillStyle = 'rgba(255,255,255,0.55)'; ctx.font = '600 ' + Math.round(fs * 0.7) + 'px "Segoe UI",sans-serif'; ctx.textAlign = 'right'; ctx.textBaseline = 'alphabetic';
    ctx.fillText(b.title.toUpperCase(), w - 18, 24);
    ctx.fillStyle = 'rgba(255,255,255,0.1)'; ctx.fillRect(14, 34, w - 28, 1);
    ctx.textAlign = 'left'; ctx.font = '600 ' + fs + 'px "Cascadia Code","Consolas","Courier New",monospace';
    for (var i = 0; i < b.lines.length && i <= b.li; i++) {
      var txt = i < b.li ? b.lines[i] : b.lines[i].slice(0, b.ci), ly = 50 + (i + 0.75) * lh;
      ctx.fillStyle = 'rgba(251,191,36,' + (0.9 * b.alpha).toFixed(2) + ')'; ctx.fillText('›', 16, ly);
      ctx.fillStyle = 'rgba(226,240,255,' + (0.95 * b.alpha).toFixed(2) + ')'; ctx.fillText(txt, 34, ly);
      if (i === b.li && b.state === 'type' && Math.floor(t * 3) % 2 === 0) { ctx.fillStyle = b.c1; ctx.fillRect(36 + ctx.measureText(txt).width, ly - fs * 0.85, 2, fs); }
    }
    ctx.restore();
  }

  /* ---------- Ilustrações escolares em linha (só o contorno; origem no centro) ---------- */
  function iconPath(kind, h) {
    ctx.beginPath();
    if (kind === 'cap') {
      ctx.moveTo(-h, -h * 0.1); ctx.lineTo(0, -h * 0.6); ctx.lineTo(h, -h * 0.1); ctx.lineTo(0, h * 0.4); ctx.closePath();
      ctx.moveTo(-h * 0.5, h * 0.12); ctx.lineTo(-h * 0.5, h * 0.55); ctx.quadraticCurveTo(0, h * 0.88, h * 0.5, h * 0.55); ctx.lineTo(h * 0.5, h * 0.12);
      ctx.moveTo(h, -h * 0.1); ctx.lineTo(h, h * 0.45);
    } else if (kind === 'book') {
      ctx.moveTo(0, -h * 0.45); ctx.quadraticCurveTo(-h * 0.5, -h * 0.7, -h, -h * 0.5); ctx.lineTo(-h, h * 0.5); ctx.quadraticCurveTo(-h * 0.5, h * 0.3, 0, h * 0.55);
      ctx.quadraticCurveTo(h * 0.5, h * 0.3, h, h * 0.5); ctx.lineTo(h, -h * 0.5); ctx.quadraticCurveTo(h * 0.5, -h * 0.7, 0, -h * 0.45); ctx.lineTo(0, h * 0.55);
      ctx.moveTo(-h * 0.75, -h * 0.15); ctx.lineTo(-h * 0.2, -h * 0.02); ctx.moveTo(-h * 0.75, h * 0.12); ctx.lineTo(-h * 0.2, h * 0.25);
      ctx.moveTo(h * 0.75, -h * 0.15); ctx.lineTo(h * 0.2, -h * 0.02); ctx.moveTo(h * 0.75, h * 0.12); ctx.lineTo(h * 0.2, h * 0.25);
    } else if (kind === 'atom') {
      for (var q = 0; q < 3; q++) { ctx.moveTo(h, 0); ctx.ellipse(0, 0, h, h * 0.36, q * 1.0472 + t * 0.35, 0, 6.2832); }
      ctx.moveTo(h * 0.14, 0); ctx.arc(0, 0, h * 0.14, 0, 6.2832);
    } else if (kind === 'bulb') {
      ctx.arc(0, -h * 0.2, h * 0.58, 0.85 * Math.PI, 2.15 * Math.PI); ctx.lineTo(h * 0.24, h * 0.45); ctx.lineTo(-h * 0.24, h * 0.45); ctx.closePath();
      ctx.moveTo(-h * 0.24, h * 0.62); ctx.lineTo(h * 0.24, h * 0.62); ctx.moveTo(-h * 0.16, h * 0.8); ctx.lineTo(h * 0.16, h * 0.8);
      ctx.moveTo(-h * 0.2, h * 0.4); ctx.lineTo(-h * 0.1, -h * 0.1); ctx.lineTo(0, h * 0.1); ctx.lineTo(h * 0.1, -h * 0.1); ctx.lineTo(h * 0.2, h * 0.4);
    } else if (kind === 'flask') {
      ctx.moveTo(-h * 0.2, -h * 0.8); ctx.lineTo(-h * 0.2, -h * 0.2); ctx.lineTo(-h * 0.75, h * 0.65); ctx.quadraticCurveTo(-h * 0.82, h * 0.88, -h * 0.55, h * 0.88);
      ctx.lineTo(h * 0.55, h * 0.88); ctx.quadraticCurveTo(h * 0.82, h * 0.88, h * 0.75, h * 0.65); ctx.lineTo(h * 0.2, -h * 0.2); ctx.lineTo(h * 0.2, -h * 0.8);
      ctx.moveTo(-h * 0.32, -h * 0.8); ctx.lineTo(h * 0.32, -h * 0.8); ctx.moveTo(-h * 0.5, h * 0.3); ctx.lineTo(h * 0.5, h * 0.3);
    } else if (kind === 'globe') {
      ctx.arc(0, 0, h * 0.82, 0, 6.2832); ctx.moveTo(-h * 0.82, 0); ctx.lineTo(h * 0.82, 0);
      ctx.moveTo(h * 0.36, 0); ctx.ellipse(0, 0, h * 0.36, h * 0.82, 0, 0, 6.2832);
      ctx.moveTo(-h * 0.7, -h * 0.4); ctx.quadraticCurveTo(0, -h * 0.3, h * 0.7, -h * 0.4); ctx.moveTo(-h * 0.7, h * 0.4); ctx.quadraticCurveTo(0, h * 0.3, h * 0.7, h * 0.4);
    } else if (kind === 'pencil') {
      ctx.moveTo(-h * 0.8, h * 0.8); ctx.lineTo(-h * 0.7, h * 0.35); ctx.lineTo(h * 0.35, -h * 0.7); ctx.lineTo(h * 0.7, -h * 0.35); ctx.lineTo(-h * 0.35, h * 0.7); ctx.closePath();
      ctx.moveTo(-h * 0.7, h * 0.35); ctx.lineTo(-h * 0.35, h * 0.7); ctx.moveTo(h * 0.15, -h * 0.5); ctx.lineTo(h * 0.5, -h * 0.15);
    } else { // bars (gráfico decorativo, sem valores)
      ctx.moveTo(-h * 0.8, -h * 0.8); ctx.lineTo(-h * 0.8, h * 0.8); ctx.lineTo(h * 0.8, h * 0.8);
      ctx.rect(-h * 0.5, h * 0.2, h * 0.28, h * 0.6); ctx.rect(-h * 0.1, -h * 0.2, h * 0.28, h * 1.0); ctx.rect(h * 0.3, -h * 0.55, h * 0.28, h * 1.35);
    }
  }
  function drawBubble(b) {
    var s = b.sz, h = s / 2, x = b.x + Math.sin(t * b.sp + b.ph) * 10 + mx * 26 * b.z, y = b.y + Math.cos(t * b.sp * 0.8 + b.ph) * 12 + my * 16 * b.z;
    var u = ((t + b.ph * 2) % 9) / 9, prog = u < 0.32 ? u / 0.32 : (u < 0.82 ? 1 : 1 - (u - 0.82) / 0.18);
    prog = prog * prog * (3 - 2 * prog);
    ctx.save(); ctx.translate(x, y);
    var br = h * 1.25, bg = ctx.createRadialGradient(-br * 0.3, -br * 0.4, 2, 0, 0, br);
    bg.addColorStop(0, 'rgba(255,255,255,0.14)'); bg.addColorStop(1, 'rgba(255,255,255,0.02)');
    ctx.fillStyle = bg; ctx.strokeStyle = 'rgba(255,255,255,0.18)'; ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.arc(0, 0, br, 0, 6.2832); ctx.fill(); ctx.stroke();
    var oa = t * 0.8 + b.ph; ctx.fillStyle = b.pal[0]; ctx.shadowColor = b.pal[0]; ctx.shadowBlur = 10;
    ctx.beginPath(); ctx.arc(Math.cos(oa) * br, Math.sin(oa) * br, 2.4, 0, 6.2832); ctx.fill();
    var gr = ctx.createLinearGradient(-h, -h, h, h); gr.addColorStop(0, b.pal[0]); gr.addColorStop(1, b.pal[1]);
    ctx.strokeStyle = gr; ctx.lineWidth = Math.max(1.8, s * 0.05); ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    ctx.shadowColor = b.pal[0]; ctx.shadowBlur = 14;
    iconPath(b.kind, h * 0.92);
    var L = s * 3.2; ctx.setLineDash([Math.max(0.01, L * prog), L * 3]); ctx.stroke(); ctx.setLineDash([]);
    ctx.restore();
  }

  /* ---------- Construção da cena ---------- */
  function build() {
    var area = W * H, i;
    blobs = []; nodes = []; bubbles = []; dust = []; windows = []; panels = [];
    sideW = Math.max(0, (W - 460) / 2);
    var cols = [[79, 70, 229], [6, 182, 212], [139, 92, 246], [14, 165, 233], [236, 72, 153]];
    for (i = 0; i < cols.length; i++) blobs.push({ c: cols[i], x: rnd(0.1, 0.9), y: rnd(0.1, 0.9), r: rnd(0.38, 0.6), a: i === 4 ? 0.1 : 0.22, ax: rnd(0.1, 0.3), ay: rnd(0.1, 0.25), sx: rnd(0.07, 0.16), sy: rnd(0.06, 0.14), p: rnd(0, 6.28) });
    for (i = 0; i < Math.min(64, Math.round(area / 24000)); i++) nodes.push({ x: rnd(0, W), y: rnd(0, H * 0.85), vx: rnd(-0.16, 0.16), vy: rnd(-0.12, 0.12), r: rnd(1.2, 2.4), c: i % 3 === 0 ? '#a78bfa' : '#67e8f9' });
    for (i = 0; i < 44; i++) dust.push({ x: rnd(0, W), y: rnd(0, H), v: rnd(6, 20), r: rnd(0.8, 2), ph: rnd(0, 6.28), h: i % 4 ? 190 : 42 });
    var hasPanels = sideW >= 250, n = 0;
    for (var sd = 0; sd < 2; sd++) for (var k = 0; k < 4; k++) {
      var col = k % 2, row = k >> 1, zx = sideW < 150 ? rnd(0.1, 0.9) * W : (sd ? W - sideW * (col ? 0.28 : 0.72) : sideW * (col ? 0.72 : 0.28));
      var yy = hasPanels ? H * (0.58 + row * 0.17) : H * (0.2 + k * 0.17);
      bubbles.push({ kind: KINDS[n % KINDS.length], pal: PAL[n % PAL.length], x: zx, y: yy + (col ? 18 : -10), z: rnd(0.7, 1.2), sz: rnd(54, 74), ph: rnd(0, 9), sp: rnd(0.4, 0.8) }); n++;
    }
    var d = dims(), wc = Math.max(3, Math.round(d.wingW / 46));
    for (var wg = 0; wg < 2; wg++) for (var r = 0; r < 2; r++) for (var c = 0; c < wc; c++) windows.push({ wg: wg, c: c, r: r, on: Math.random() < 0.45, nx: rnd(2, 10) });
    windows.cols = wc;
    if (hasPanels) {
      var pw = Math.min(320, sideW - 50);
      panels.push({ b: makePanel('Matemática', ['2x + 6 = 14', 'x = 4', 'a² + b² = c²', '∫ x dx = x²/2', 'sen²θ + cos²θ = 1'], '#22d3ee', '#818cf8'), x: (sideW - pw) / 2, w: pw });
      panels.push({ b: makePanel('Ciências', ['H₂O + CO₂ → O₂', 'E = m · c²', 'F = m · a', 'v = Δs / Δt', 'ρ = m / V'], '#a78bfa', '#f0abfc'), x: W - sideW + (sideW - pw) / 2, w: pw });
      if (reduce) panels.forEach(function (o) { panelFinish(o.b); });
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
  function mesh() {
    var g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, '#040816'); g.addColorStop(0.6, '#070e2e'); g.addColorStop(1, '#0a1238');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    ctx.globalCompositeOperation = 'lighter';
    var R = Math.max(W, H);
    for (var i = 0; i < blobs.length; i++) {
      var b = blobs[i], x = (b.x + Math.sin(t * b.sx + b.p) * b.ax) * W + mx * 24, y = (b.y + Math.cos(t * b.sy + b.p) * b.ay) * H + my * 16, r = b.r * R;
      var rg = ctx.createRadialGradient(x, y, 0, x, y, r), c = b.c.join(',');
      rg.addColorStop(0, 'rgba(' + c + ',' + b.a + ')'); rg.addColorStop(0.55, 'rgba(' + c + ',' + (b.a * 0.35) + ')'); rg.addColorStop(1, 'rgba(' + c + ',0)');
      ctx.fillStyle = rg; ctx.fillRect(0, 0, W, H);
    }
    ctx.globalCompositeOperation = 'source-over';
  }

  function grid() {
    var step = W < 600 ? 30 : 38, cx = W / 2, cy = H * 0.55, wave = t * 1.1;
    for (var gx = step / 2; gx < W; gx += step) for (var gy = step / 2; gy < H; gy += step) {
      var dx = gx - cx, dy = gy - cy, dist = Math.sqrt(dx * dx + dy * dy);
      var a = 0.1 + 0.1 * Math.sin(dist / 85 - wave) * Math.exp(-dist / 900);
      var px = gx - pointer.x, py = gy - pointer.y, pd = px * px + py * py;
      if (pd < 52900) a += 0.5 * (1 - Math.sqrt(pd) / 230);
      if (a < 0.04) continue;
      ctx.fillStyle = 'rgba(165,200,255,' + a.toFixed(3) + ')';
      ctx.fillRect(gx + mx * 6 - 0.8, gy + my * 4 - 0.8, 1.6, 1.6);
    }
  }

  function atom() {
    var cx = W / 2 + mx * 12, cy = H * 0.5 + my * 8, rx = Math.max(W * 0.46, 360), ry = rx * 0.3;
    ctx.globalCompositeOperation = 'lighter';
    for (var o = 0; o < 3; o++) {
      var an = o * 1.0472 + t * 0.05 - 0.3, ca = Math.cos(an), sa = Math.sin(an);
      ctx.strokeStyle = 'rgba(140,190,255,0.16)'; ctx.lineWidth = 1.3; ctx.beginPath();
      for (var k = 0; k <= 90; k++) { var u = k / 90 * 6.2832, ex = rx * Math.cos(u), ey = ry * Math.sin(u), X = cx + ex * ca - ey * sa, Y = cy + ex * sa + ey * ca; if (k) ctx.lineTo(X, Y); else ctx.moveTo(X, Y); }
      ctx.stroke();
      for (var e = 0; e < 2; e++) {
        var uu = t * (0.45 + o * 0.1) + e * Math.PI + o, exx = rx * Math.cos(uu), eyy = ry * Math.sin(uu), PX = cx + exx * ca - eyy * sa, PY = cy + exx * sa + eyy * ca;
        var eg = ctx.createRadialGradient(PX, PY, 0, PX, PY, 16); eg.addColorStop(0, 'rgba(255,255,255,0.95)'); eg.addColorStop(0.3, 'rgba(103,232,249,0.5)'); eg.addColorStop(1, 'rgba(103,232,249,0)');
        ctx.fillStyle = eg; ctx.beginPath(); ctx.arc(PX, PY, 16, 0, 6.283); ctx.fill();
      }
    }
    ctx.globalCompositeOperation = 'source-over';
  }

  function graph(dt) {
    var lim = Math.min(160, W * 0.14), i, j, p, q, dx, dy, d;
    for (i = 0; i < nodes.length; i++) {
      p = nodes[i]; p.x += p.vx * dt * 60; p.y += p.vy * dt * 60;
      if (p.x < 0 || p.x > W) p.vx *= -1; if (p.y < 0 || p.y > H * 0.84) p.vy *= -1;
      dx = p.x - pointer.x; dy = p.y - pointer.y; d = Math.sqrt(dx * dx + dy * dy);
      if (d < 150 && d > 0) { p.x += (dx / d) * (150 - d) * 0.02; p.y += (dy / d) * (150 - d) * 0.02; }
    }
    ctx.lineWidth = 1;
    for (i = 0; i < nodes.length; i++) {
      p = nodes[i];
      for (j = i + 1; j < nodes.length; j++) {
        q = nodes[j]; dx = p.x - q.x; dy = p.y - q.y; d = dx * dx + dy * dy;
        if (d < lim * lim) {
          var f = 1 - Math.sqrt(d) / lim;
          ctx.strokeStyle = 'rgba(150,200,255,' + (0.28 * f).toFixed(3) + ')'; ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke();
          if ((i * 7 + j * 13) % 4 === 0) {
            var u = (t * 0.45 + ((i * 31 + j * 17) % 10) / 10) % 1, pxx = p.x + (q.x - p.x) * u, pyy = p.y + (q.y - p.y) * u;
            ctx.fillStyle = 'rgba(255,255,255,' + (0.9 * f).toFixed(2) + ')'; ctx.shadowColor = '#22d3ee'; ctx.shadowBlur = 8;
            ctx.beginPath(); ctx.arc(pxx, pyy, 1.7, 0, 6.283); ctx.fill(); ctx.shadowBlur = 0;
          }
        }
      }
      dx = p.x - pointer.x; dy = p.y - pointer.y; d = Math.sqrt(dx * dx + dy * dy);
      if (d < 210) { ctx.strokeStyle = 'rgba(251,191,36,' + (0.6 * (1 - d / 210)).toFixed(3) + ')'; ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(pointer.x, pointer.y); ctx.stroke(); }
      ctx.fillStyle = p.c; ctx.shadowColor = p.c; ctx.shadowBlur = 8; ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, 6.283); ctx.fill(); ctx.shadowBlur = 0;
    }
  }

  function school(dt) {
    var d = dims(), x0 = d.x0 + mx * -6, base = d.base, bh = d.bh, top = base - bh, bw = d.bw, i;
    var hg = ctx.createRadialGradient(W / 2, base, 0, W / 2, base, W * 0.55);
    hg.addColorStop(0, 'rgba(34,211,238,0.28)'); hg.addColorStop(0.5, 'rgba(99,102,241,0.12)'); hg.addColorStop(1, 'rgba(99,102,241,0)');
    ctx.fillStyle = hg; ctx.fillRect(0, base - H * 0.4, W, H * 0.4 + (H - base));
    var cw = bw * 0.28, cx0 = x0 + bw / 2 - cw / 2, mid = x0 + bw / 2;
    var fill = ctx.createLinearGradient(0, top, 0, base); fill.addColorStop(0, 'rgba(99,102,241,0.30)'); fill.addColorStop(1, 'rgba(6,10,40,0.85)');
    ctx.fillStyle = fill;
    ctx.fillRect(x0, base - d.wh, d.wingW, d.wh); ctx.fillRect(x0 + bw - d.wingW, base - d.wh, d.wingW, d.wh); ctx.fillRect(cx0 - 4, top + bh * 0.2, cw + 8, bh * 0.8);
    ctx.beginPath(); ctx.moveTo(cx0 - 16, top + bh * 0.2); ctx.lineTo(mid, top - bh * 0.1); ctx.lineTo(cx0 + cw + 16, top + bh * 0.2); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = 'rgba(125,211,252,0.75)'; ctx.lineWidth = 1.6; ctx.shadowColor = '#22d3ee'; ctx.shadowBlur = 12; ctx.lineJoin = 'round';
    ctx.beginPath();
    ctx.moveTo(x0, base); ctx.lineTo(x0, base - d.wh); ctx.lineTo(cx0 - 4, base - d.wh); ctx.lineTo(cx0 - 4, top + bh * 0.2); ctx.lineTo(cx0 - 16, top + bh * 0.2); ctx.lineTo(mid, top - bh * 0.1);
    ctx.lineTo(cx0 + cw + 16, top + bh * 0.2); ctx.lineTo(cx0 + cw + 4, top + bh * 0.2); ctx.lineTo(cx0 + cw + 4, base - d.wh); ctx.lineTo(x0 + bw, base - d.wh); ctx.lineTo(x0 + bw, base);
    ctx.stroke();
    ctx.strokeStyle = 'rgba(125,211,252,0.35)'; ctx.lineWidth = 1.2; ctx.beginPath();
    for (i = 0; i < 6; i++) { var cxx = cx0 + cw * (0.08 + i * 0.168); ctx.moveTo(cxx, top + bh * 0.27); ctx.lineTo(cxx, base - bh * 0.07); }
    ctx.stroke();
    var cly = top + bh * 0.1, clr = bh * 0.075;
    ctx.strokeStyle = 'rgba(251,191,36,0.95)'; ctx.shadowColor = '#fbbf24'; ctx.beginPath(); ctx.arc(mid, cly, clr, 0, 6.283);
    ctx.moveTo(mid, cly); ctx.lineTo(mid + Math.cos(t * 0.5) * clr * 0.75, cly + Math.sin(t * 0.5) * clr * 0.75); ctx.moveTo(mid, cly); ctx.lineTo(mid, cly - clr * 0.6); ctx.stroke();
    var dg = ctx.createLinearGradient(0, base - bh * 0.4, 0, base); dg.addColorStop(0, 'rgba(254,240,138,0.95)'); dg.addColorStop(1, 'rgba(251,146,60,0.9)');
    ctx.fillStyle = dg; ctx.shadowColor = '#fbbf24'; ctx.shadowBlur = 22;
    ctx.beginPath(); ctx.moveTo(mid - cw * 0.09, base - bh * 0.05); ctx.lineTo(mid - cw * 0.09, base - bh * 0.3); ctx.arc(mid, base - bh * 0.3, cw * 0.09, Math.PI, 0); ctx.lineTo(mid + cw * 0.09, base - bh * 0.05); ctx.closePath(); ctx.fill();
    var wc = windows.cols, cw2 = d.wingW / wc;
    for (i = 0; i < windows.length; i++) {
      var w = windows[i]; w.nx -= dt;
      if (w.nx <= 0) { w.on = !w.on || Math.random() < 0.3; w.nx = rnd(3, 12); }
      var wx = (w.wg ? x0 + bw - d.wingW : x0) + w.c * cw2 + cw2 * 0.22, wy = base - d.wh + d.wh * 0.16 + w.r * d.wh * 0.42, ww = cw2 * 0.56, wht = d.wh * 0.26;
      if (w.on) { ctx.shadowColor = '#fbbf24'; ctx.shadowBlur = 10; ctx.fillStyle = 'rgba(253,224,130,0.6)'; }
      else { ctx.shadowBlur = 0; ctx.fillStyle = 'rgba(125,211,252,0.1)'; }
      ctx.fillRect(wx, wy, ww, wht);
    }
    ctx.shadowBlur = 0;
    var lg = ctx.createLinearGradient(0, 0, W, 0), sh = (t * 0.12) % 1;
    lg.addColorStop(0, 'rgba(34,211,238,0)'); lg.addColorStop(Math.max(0.001, sh - 0.15), 'rgba(34,211,238,0.15)'); lg.addColorStop(Math.min(0.999, sh), 'rgba(255,255,255,0.9)'); lg.addColorStop(Math.min(0.999, sh + 0.15), 'rgba(167,139,250,0.15)'); lg.addColorStop(1, 'rgba(167,139,250,0)');
    ctx.fillStyle = '#050a26'; ctx.fillRect(0, base, W, H - base);
    ctx.fillStyle = lg; ctx.fillRect(0, base, W, 2);
  }

  function beam() {
    var x = ((t * 0.07) % 1.7 - 0.35) * W;
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.transform(1, 0, -0.45, 1, x, 0);
    var g = ctx.createLinearGradient(0, 0, 220, 0); g.addColorStop(0, 'rgba(160,200,255,0)'); g.addColorStop(0.5, 'rgba(160,200,255,0.07)'); g.addColorStop(1, 'rgba(160,200,255,0)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, 220, H); ctx.restore();
  }

  function dustDraw(dt) {
    ctx.globalCompositeOperation = 'lighter';
    for (var i = 0; i < dust.length; i++) {
      var p = dust[i]; p.y -= p.v * dt; if (p.y < -10) { p.y = H + 10; p.x = rnd(0, W); }
      var a = 0.25 + 0.5 * Math.max(0, Math.sin(t * 1.4 + p.ph));
      ctx.fillStyle = 'hsla(' + p.h + ',95%,75%,' + a.toFixed(2) + ')'; ctx.shadowColor = 'hsl(' + p.h + ',95%,65%)'; ctx.shadowBlur = 8;
      ctx.beginPath(); ctx.arc(p.x + Math.sin(t * 0.6 + p.ph) * 12 + mx * 10, p.y, p.r, 0, 6.283); ctx.fill();
    }
    ctx.shadowBlur = 0; ctx.globalCompositeOperation = 'source-over';
  }

  function frame(dt) {
    mx += (tx - mx) * 0.05; my += (ty - my) * 0.05;
    mesh(); grid(); atom(); graph(dt); beam();
    for (var i = 0; i < panels.length; i++) { if (!reduce) panelUpdate(panels[i].b, dt); panelDraw(panels[i].b, panels[i].x, Math.max(56, H * 0.1), panels[i].w); }
    for (i = 0; i < bubbles.length; i++) drawBubble(bubbles[i]);
    school(dt); dustDraw(dt);
    var v = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.4, W / 2, H / 2, Math.max(W, H) * 0.85);
    v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(2,4,20,0.5)'); ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
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
