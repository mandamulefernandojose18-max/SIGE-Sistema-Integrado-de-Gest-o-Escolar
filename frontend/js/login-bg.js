/* SIGE — Fundo escolar animado do ecrã de login (canvas 2D, sem dependências).
 * Camadas: céu com aurora → estrelas + estrela cadente → rede de partículas
 * (reage ao rato) → símbolos escolares flutuantes (fórmulas, livros, lápis,
 * capelo, átomo, lâmpada) → colinas + edifício escolar com janelas que acendem.
 * Pausa quando o login está oculto/separador inactivo; respeita
 * prefers-reduced-motion (desenha um quadro estático). Sem dados fictícios.
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
  var W = 0, H = 0, dpr = 1, t = 0, raf = 0, last = 0;
  var mx = 0, my = 0, tx = 0, ty = 0; // parallax (-1..1)
  var pointer = { x: -9999, y: -9999 };
  var stars = [], parts = [], glyphs = [], windows = [], blobs = [], shoot = null;
  var rnd = function (a, b) { return a + Math.random() * (b - a); };

  var TEXTS = ['∑', 'π', '√x', 'E=mc²', 'H₂O', 'ABC', 'a²+b²=c²', 'f(x)', '∫', 'Δ', '7×8', 'α', 'Σn', '1+1=2', 'CO₂', 'x²', '∞', 'θ', 'log', '%'];
  var ICONS = ['book', 'pencil', 'cap', 'atom', 'bulb', 'ruler', 'globe'];

  function build() {
    var area = W * H;
    stars = []; parts = []; glyphs = []; windows = []; blobs = [];
    var ns = Math.min(220, Math.round(area / 6500));
    for (var i = 0; i < ns; i++) stars.push({ x: Math.random(), y: Math.random() * 0.75, r: rnd(0.4, 1.5), p: rnd(0, 6.28), s: rnd(0.6, 2.2), d: rnd(0.2, 1) });
    var np = Math.min(70, Math.round(area / 22000));
    for (i = 0; i < np; i++) parts.push({ x: rnd(0, W), y: rnd(0, H * 0.85), vx: rnd(-0.18, 0.18), vy: rnd(-0.14, 0.14), r: rnd(1, 2.2) });
    var ng = Math.min(34, Math.max(14, Math.round(area / 50000)));
    for (i = 0; i < ng; i++) {
      var isTxt = Math.random() < 0.55;
      glyphs.push({
        x: rnd(0, W), y: rnd(0, H), z: rnd(0.4, 1.4),
        txt: isTxt ? TEXTS[(Math.random() * TEXTS.length) | 0] : null,
        icon: isTxt ? null : ICONS[(Math.random() * ICONS.length) | 0],
        sz: rnd(22, 46), rot: rnd(0, 6.28), vr: rnd(-0.004, 0.004),
        vy: rnd(-0.22, -0.06), ph: rnd(0, 6.28), hue: [38, 200, 265, 160, 330][(Math.random() * 5) | 0]
      });
    }
    for (i = 0; i < 4; i++) blobs.push({ x: rnd(0.1, 0.9), y: rnd(0.1, 0.6), r: rnd(0.35, 0.6), h: [265, 215, 190, 300][i], ph: rnd(0, 6.28), sp: rnd(0.08, 0.2) });
    // Janelas do edifício (grelha) — geradas uma vez por redimensionamento
    var bw = Math.min(W * 0.62, 760), bh = Math.min(H * 0.2, 150);
    var cols = Math.max(8, Math.round(bw / 46)), rows = 3;
    for (var r = 0; r < rows; r++) for (var c = 0; c < cols; c++) windows.push({ c: c, r: r, on: Math.random() < 0.35, nx: rnd(2, 9) });
    windows.cols = cols; windows.rows = rows;
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

  /* ---------- Ícones vectoriais (origem no centro, tamanho s) ---------- */
  function icon(kind, s, col) {
    ctx.save();
    ctx.strokeStyle = col; ctx.fillStyle = col; ctx.lineWidth = Math.max(1.4, s * 0.06);
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    var h = s / 2;
    ctx.beginPath();
    if (kind === 'book') {
      ctx.moveTo(-h, -h * 0.6); ctx.quadraticCurveTo(-h * 0.5, -h * 0.8, 0, -h * 0.5);
      ctx.quadraticCurveTo(h * 0.5, -h * 0.8, h, -h * 0.6); ctx.lineTo(h, h * 0.6);
      ctx.quadraticCurveTo(h * 0.5, h * 0.4, 0, h * 0.7); ctx.quadraticCurveTo(-h * 0.5, h * 0.4, -h, h * 0.6);
      ctx.closePath(); ctx.moveTo(0, -h * 0.5); ctx.lineTo(0, h * 0.7); ctx.stroke();
    } else if (kind === 'pencil') {
      ctx.rotate(-0.78);
      ctx.rect(-h * 0.2, -h, h * 0.4, h * 1.5); ctx.moveTo(-h * 0.2, h * 0.5); ctx.lineTo(0, h); ctx.lineTo(h * 0.2, h * 0.5);
      ctx.moveTo(-h * 0.2, -h * 0.7); ctx.lineTo(h * 0.2, -h * 0.7); ctx.stroke();
    } else if (kind === 'cap') {
      ctx.moveTo(-h, -h * 0.1); ctx.lineTo(0, -h * 0.55); ctx.lineTo(h, -h * 0.1); ctx.lineTo(0, h * 0.35); ctx.closePath();
      ctx.moveTo(-h * 0.5, h * 0.12); ctx.lineTo(-h * 0.5, h * 0.55); ctx.quadraticCurveTo(0, h * 0.85, h * 0.5, h * 0.55); ctx.lineTo(h * 0.5, h * 0.12);
      ctx.moveTo(h, -h * 0.1); ctx.lineTo(h, h * 0.4); ctx.stroke();
    } else if (kind === 'atom') {
      for (var k = 0; k < 3; k++) { ctx.save(); ctx.rotate(k * 1.047); ctx.beginPath(); ctx.ellipse(0, 0, h, h * 0.38, 0, 0, 6.283); ctx.stroke(); ctx.restore(); }
      ctx.beginPath(); ctx.arc(0, 0, s * 0.07, 0, 6.283); ctx.fill();
    } else if (kind === 'bulb') {
      ctx.arc(0, -h * 0.2, h * 0.55, 0.9 * Math.PI, 2.1 * Math.PI); ctx.lineTo(h * 0.22, h * 0.45); ctx.lineTo(-h * 0.22, h * 0.45); ctx.closePath();
      ctx.moveTo(-h * 0.22, h * 0.68); ctx.lineTo(h * 0.22, h * 0.68); ctx.stroke();
    } else if (kind === 'ruler') {
      ctx.rotate(0.5); ctx.rect(-h, -h * 0.25, s, h * 0.5);
      for (var m = -3; m <= 3; m++) { ctx.moveTo(m * h * 0.28, -h * 0.25); ctx.lineTo(m * h * 0.28, -h * (m % 2 ? 0.05 : 0.1)); }
      ctx.stroke();
    } else { // globe
      ctx.arc(0, 0, h * 0.8, 0, 6.283); ctx.moveTo(-h * 0.8, 0); ctx.lineTo(h * 0.8, 0);
      ctx.ellipse(0, 0, h * 0.35, h * 0.8, 0, 0, 6.283); ctx.stroke();
    }
    ctx.restore();
  }

  /* ---------- Camadas ---------- */
  function sky() {
    var g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, '#05031a'); g.addColorStop(0.55, '#0c0a3a'); g.addColorStop(1, '#1d1457');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    ctx.globalCompositeOperation = 'lighter';
    for (var i = 0; i < blobs.length; i++) {
      var b = blobs[i], a = t * b.sp + b.ph;
      var x = (b.x + Math.sin(a) * 0.12 + mx * 0.02) * W, y = (b.y + Math.cos(a * 0.8) * 0.1 + my * 0.02) * H, r = b.r * Math.max(W, H);
      var rg = ctx.createRadialGradient(x, y, 0, x, y, r);
      rg.addColorStop(0, 'hsla(' + b.h + ',85%,55%,0.16)'); rg.addColorStop(1, 'hsla(' + b.h + ',85%,55%,0)');
      ctx.fillStyle = rg; ctx.fillRect(0, 0, W, H);
    }
    ctx.globalCompositeOperation = 'source-over';
  }

  function starfield(dt) {
    for (var i = 0; i < stars.length; i++) {
      var s = stars[i], a = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(t * s.s + s.p));
      ctx.fillStyle = 'rgba(255,255,255,' + (a * s.d).toFixed(3) + ')';
      ctx.beginPath(); ctx.arc(s.x * W + mx * 14 * s.d, s.y * H + my * 8 * s.d, s.r, 0, 6.283); ctx.fill();
    }
    if (!shoot && !reduce && Math.random() < dt * 0.25) shoot = { x: rnd(0.1, 0.9) * W, y: rnd(0, 0.35) * H, vx: rnd(380, 560), vy: rnd(160, 260), l: 0 };
    if (shoot) {
      shoot.x += shoot.vx * dt; shoot.y += shoot.vy * dt; shoot.l += dt;
      var tl = ctx.createLinearGradient(shoot.x, shoot.y, shoot.x - shoot.vx * 0.18, shoot.y - shoot.vy * 0.18);
      tl.addColorStop(0, 'rgba(255,255,255,0.95)'); tl.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.strokeStyle = tl; ctx.lineWidth = 2; ctx.beginPath();
      ctx.moveTo(shoot.x, shoot.y); ctx.lineTo(shoot.x - shoot.vx * 0.18, shoot.y - shoot.vy * 0.18); ctx.stroke();
      if (shoot.l > 1.4 || shoot.x > W + 50 || shoot.y > H) shoot = null;
    }
  }

  function network(dt) {
    var lim = Math.min(150, W * 0.14), i, j, p, q, dx, dy, d;
    for (i = 0; i < parts.length; i++) {
      p = parts[i]; p.x += p.vx * dt * 60; p.y += p.vy * dt * 60;
      if (p.x < 0 || p.x > W) p.vx *= -1; if (p.y < 0 || p.y > H * 0.88) p.vy *= -1;
      dx = p.x - pointer.x; dy = p.y - pointer.y; d = Math.sqrt(dx * dx + dy * dy);
      if (d < 140 && d > 0) { p.x += (dx / d) * (140 - d) * 0.02; p.y += (dy / d) * (140 - d) * 0.02; }
    }
    ctx.lineWidth = 1;
    for (i = 0; i < parts.length; i++) {
      p = parts[i];
      for (j = i + 1; j < parts.length; j++) {
        q = parts[j]; dx = p.x - q.x; dy = p.y - q.y; d = dx * dx + dy * dy;
        if (d < lim * lim) { ctx.strokeStyle = 'rgba(165,180,252,' + (0.22 * (1 - Math.sqrt(d) / lim)).toFixed(3) + ')'; ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke(); }
      }
      dx = p.x - pointer.x; dy = p.y - pointer.y; d = Math.sqrt(dx * dx + dy * dy);
      if (d < 180) { ctx.strokeStyle = 'rgba(223,135,4,' + (0.5 * (1 - d / 180)).toFixed(3) + ')'; ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(pointer.x, pointer.y); ctx.stroke(); }
      ctx.fillStyle = 'rgba(199,210,254,0.8)'; ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, 6.283); ctx.fill();
    }
  }

  function floaters(dt) {
    for (var i = 0; i < glyphs.length; i++) {
      var g = glyphs[i];
      g.y += g.vy * dt * 60 * g.z; g.rot += g.vr * dt * 60;
      if (g.y < -60) { g.y = H * 0.9; g.x = rnd(0, W); }
      var x = g.x + Math.sin(t * 0.5 + g.ph) * 18 * g.z + mx * 28 * g.z, y = g.y + my * 16 * g.z;
      var fade = Math.min(1, Math.max(0, (y + 40) / 120)) * (0.14 + 0.1 * Math.sin(t + g.ph)) * (0.6 + g.z * 0.5);
      var col = 'hsla(' + g.hue + ',90%,75%,' + Math.max(0.03, fade).toFixed(3) + ')';
      ctx.save(); ctx.translate(x, y); ctx.rotate(g.rot * 0.6);
      ctx.shadowColor = 'hsla(' + g.hue + ',90%,65%,0.55)'; ctx.shadowBlur = 14 * g.z;
      if (g.txt) {
        ctx.fillStyle = col; ctx.font = 'italic 600 ' + (g.sz * g.z).toFixed(0) + 'px "Times New Roman", serif';
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(g.txt, 0, 0);
      } else icon(g.icon, g.sz * 1.3 * g.z, col);
      ctx.restore();
    }
  }

  function ground(dt) {
    // colinas em paralaxe
    var layers = [{ c: 'rgba(24,17,79,0.9)', y: 0.80, a: 0.035, f: 1.3, k: 10 }, { c: 'rgba(14,10,54,0.96)', y: 0.88, a: 0.03, f: 2.1, k: 18 }];
    for (var l = 0; l < layers.length; l++) {
      var L = layers[l]; ctx.fillStyle = L.c; ctx.beginPath(); ctx.moveTo(0, H);
      for (var x = 0; x <= W + 20; x += 20) ctx.lineTo(x, H * L.y + Math.sin(x / W * 6.28 * L.f + l * 1.7) * H * L.a + mx * L.k * -1 * 0.5);
      ctx.lineTo(W, H); ctx.closePath(); ctx.fill();
    }
    // edifício escolar (silhueta) com bandeira e janelas
    var bw = Math.min(W * 0.62, 760), bh = Math.min(H * 0.2, 150), bx = (W - bw) / 2 + mx * -8, by = H * 0.93 - bh;
    ctx.fillStyle = '#0a0730'; ctx.strokeStyle = 'rgba(139,92,246,0.35)'; ctx.lineWidth = 1.2;
    ctx.fillRect(bx, by, bw, bh + H);
    var tw = bw * 0.2; // torre central
    ctx.fillRect(bx + bw / 2 - tw / 2, by - bh * 0.55, tw, bh * 0.55 + 2);
    ctx.beginPath(); ctx.moveTo(bx + bw / 2 - tw / 2 - 8, by - bh * 0.55); ctx.lineTo(bx + bw / 2, by - bh * 0.95); ctx.lineTo(bx + bw / 2 + tw / 2 + 8, by - bh * 0.55); ctx.closePath(); ctx.fill(); ctx.stroke();
    // bandeira ondulante
    var px = bx + bw / 2, py = by - bh * 0.95;
    ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(px, py - 34); ctx.stroke();
    ctx.fillStyle = '#df8704'; ctx.beginPath(); ctx.moveTo(px, py - 34);
    for (var f = 0; f <= 24; f += 4) ctx.lineTo(px + f, py - 34 + Math.sin(t * 4 + f * 0.4) * 2.5);
    for (f = 24; f >= 0; f -= 4) ctx.lineTo(px + f, py - 22 + Math.sin(t * 4 + f * 0.4) * 2.5);
    ctx.closePath(); ctx.fill();
    // relógio da torre
    ctx.fillStyle = '#fde68a'; ctx.beginPath(); ctx.arc(px, by - bh * 0.3, tw * 0.22, 0, 6.283); ctx.fill();
    ctx.strokeStyle = '#0a0730'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(px, by - bh * 0.3);
    ctx.lineTo(px + Math.cos(t * 0.5) * tw * 0.16, by - bh * 0.3 + Math.sin(t * 0.5) * tw * 0.16); ctx.stroke();
    // janelas
    var cols = windows.cols, rows = windows.rows, cw = bw / cols;
    for (var i = 0; i < windows.length; i++) {
      var w = windows[i];
      w.nx -= dt; if (w.nx <= 0) { w.on = !w.on || Math.random() < 0.3; w.nx = rnd(3, 12); }
      var wx = bx + w.c * cw + cw * 0.22, wy = by + 12 + w.r * (bh - 20) / rows, ww = cw * 0.56, wh = (bh - 20) / rows * 0.6;
      if (w.on) { ctx.shadowColor = 'rgba(253,224,71,0.7)'; ctx.shadowBlur = 10; ctx.fillStyle = 'rgba(253,224,71,0.85)'; }
      else { ctx.shadowBlur = 0; ctx.fillStyle = 'rgba(99,102,241,0.18)'; }
      ctx.fillRect(wx, wy, ww, wh);
    }
    ctx.shadowBlur = 0;
    // vinheta
    var v = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.3, W / 2, H / 2, Math.max(W, H) * 0.8);
    v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,0.45)');
    ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
  }

  function frame(dt) {
    mx += (tx - mx) * 0.05; my += (ty - my) * 0.05;
    sky(); starfield(dt); network(dt); floaters(dt); ground(dt);
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
