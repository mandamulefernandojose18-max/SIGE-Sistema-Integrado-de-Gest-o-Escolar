/* SIGE — Camada de efeitos do login (canvas 2D por cima da ilustração SVG).
 * Estrelas cintilantes e constelações, estrelas cadentes, equações em cápsulas de
 * vidro a subir, símbolos gigantes translúcidos, símbolos em órbita à volta do sol
 * e pó de estrelas que segue o rato (explosão ao clicar). Pausa com o separador
 * inactivo ou após autenticação; respeita prefers-reduced-motion (quadro estático).
 * Sem dados reais nem fictícios.
 */
(function () {
  'use strict';
  var host = document.getElementById('loginView');
  if (!host || document.getElementById('loginFxCanvas')) return;
  var cv = document.createElement('canvas');
  cv.id = 'loginFxCanvas';
  cv.setAttribute('aria-hidden', 'true');
  cv.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;z-index:0;pointer-events:none;';
  var scene = document.getElementById('loginBgScene');
  if (scene && scene.nextSibling) host.insertBefore(cv, scene.nextSibling); else host.insertBefore(cv, host.firstChild);
  var ctx = cv.getContext('2d');
  if (!ctx) return;

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var W = 0, H = 0, dpr = 1, t = 0, raf = 0, last = 0, S = 1, offX = 0, offY = 0, skyB = 0;
  var mx = 0, my = 0, tx = 0, ty = 0, pointer = { x: -9999, y: -9999 }, lastSpawn = 0;
  var stars = [], consts = [], chips = [], glyphs = [], orbit = [], shoots = [], dust = [], nextShoot = 1.5;
  var rnd = function (a, b) { return a + Math.random() * (b - a); };
  var pick = function (a) { return a[(Math.random() * a.length) | 0]; };
  var EQ = ['E = mc²', 'a² + b² = c²', 'π ≈ 3,14', '∑ n = n(n+1)/2', '∫ x dx', '√x', 'sen²θ + cos²θ = 1', 'log₂ 8 = 3', 'Δ = b² − 4ac', 'H₂O', 'F = m·a', 'f(x) = x²', '2 + 2 = 4', '7 × 8 = 56', 'A B C', '1 2 3', 'α β γ', '∞', 'CO₂', 'v = d / t', 'x² − 9 = 0'];
  var GLY = ['∑', 'π', '∞', '√', '∫', 'Δ', 'θ', '±', '÷', '×', '%', 'α'];
  var CHIP = [['rgba(24,17,79,0.55)', 'rgba(255,255,255,0.45)'], ['rgba(223,135,4,0.6)', 'rgba(255,230,170,0.7)'], ['rgba(109,40,217,0.5)', 'rgba(221,214,254,0.6)'], ['rgba(8,120,170,0.5)', 'rgba(186,230,253,0.65)']];
  var STAR_C = ['255,255,255', '253,230,138', '191,227,255'];

  function sparkle(x, y, r, rot, a, c) {
    ctx.save(); ctx.translate(x, y); ctx.rotate(rot);
    ctx.fillStyle = 'rgba(' + c + ',' + a.toFixed(3) + ')'; ctx.shadowColor = 'rgba(' + c + ',0.9)'; ctx.shadowBlur = r * 1.6;
    ctx.beginPath(); ctx.moveTo(0, -r); ctx.quadraticCurveTo(0, 0, r, 0); ctx.quadraticCurveTo(0, 0, 0, r); ctx.quadraticCurveTo(0, 0, -r, 0); ctx.quadraticCurveTo(0, 0, 0, -r); ctx.fill();
    ctx.shadowBlur = 0; ctx.beginPath(); ctx.arc(0, 0, r * 0.16, 0, 6.283); ctx.fill();
    ctx.restore();
  }
  function rr(x, y, w, h, r) { ctx.beginPath(); if (ctx.roundRect) ctx.roundRect(x, y, w, h, r); else ctx.rect(x, y, w, h); }

  function newChip(init) {
    var txt = pick(EQ), z = rnd(0.75, 1.3), col = pick(CHIP);
    ctx.font = '700 ' + Math.round(17 * z) + 'px "Cascadia Code","Consolas","Segoe UI",monospace';
    var w = ctx.measureText(txt).width + 30 * z, h = 36 * z;
    return { txt: txt, z: z, col: col, w: w, h: h, x: rnd(0, W), y: init ? rnd(-40, H) : H + 60, v: rnd(14, 34) * z, ph: rnd(0, 6.28), sw: rnd(10, 26), rot: rnd(-0.12, 0.12), life: 0, span: H + 120 };
  }

  function build() {
    stars = []; consts = []; chips = []; glyphs = []; orbit = []; shoots = [];
    S = Math.max(W / 1600, H / 900); offX = (W - 1600 * S) / 2; offY = H - 900 * S; skyB = Math.max(H * 0.3, offY + 560 * S);
    var ns = Math.min(110, Math.round(W * skyB / 9000)), i;
    for (i = 0; i < ns; i++) stars.push({ x: rnd(0, W), y: rnd(0, skyB * 0.98), r: rnd(2.5, 8), p: rnd(0, 6.28), s: rnd(0.8, 2.6), c: pick(STAR_C), d: rnd(0.3, 1), rs: rnd(-0.3, 0.3) });
    for (var k = 0; k < 4; k++) {
      var cx = rnd(0.08, 0.92) * W, cy = rnd(0.05, 0.4) * skyB, pts = [], n = 5 + ((Math.random() * 3) | 0);
      for (i = 0; i < n; i++) pts.push({ x: cx + rnd(-90, 90) + i * 22, y: cy + rnd(-50, 50), r: rnd(3.5, 6.5), p: rnd(0, 6.28) });
      consts.push({ pts: pts, ph: rnd(0, 6.28) });
    }
    var nc = Math.min(22, Math.max(9, Math.round(W / 85)));
    for (i = 0; i < nc; i++) chips.push(newChip(true));
    for (i = 0; i < 8; i++) glyphs.push({ ch: GLY[i % GLY.length], x: rnd(0, W), y: rnd(0.04, 0.55) * H, sz: rnd(70, 130), rot: rnd(0, 6.28), vr: rnd(-0.12, 0.12), ph: rnd(0, 6.28), v: rnd(4, 10), a: rnd(0.14, 0.26) });
    for (i = 0; i < 8; i++) orbit.push({ ch: GLY[(i * 3) % GLY.length], u: i / 8 * 6.2832, v: rnd(0.22, 0.3) });
  }

  function resize() {
    var rc = host.getBoundingClientRect(); dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = Math.max(1, rc.width); H = Math.max(1, rc.height);
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    build(); if (reduce) frame(0);
  }

  function drawStars() {
    var i, s, a;
    for (i = 0; i < consts.length; i++) {
      var c = consts[i], pulse = 0.3 + 0.25 * Math.sin(t * 0.9 + c.ph);
      ctx.strokeStyle = 'rgba(255,255,255,' + pulse.toFixed(2) + ')'; ctx.lineWidth = 1.2; ctx.beginPath();
      for (var j = 0; j < c.pts.length; j++) { var p = c.pts[j], px = p.x + mx * 8, py = p.y + my * 5; if (j) ctx.lineTo(px, py); else ctx.moveTo(px, py); }
      ctx.stroke();
      for (j = 0; j < c.pts.length; j++) { p = c.pts[j]; sparkle(p.x + mx * 8, p.y + my * 5, p.r * (1 + 0.25 * Math.sin(t * 2 + p.p)), t * 0.2 + p.p, 0.95, '255,255,255'); }
    }
    for (i = 0; i < stars.length; i++) {
      s = stars[i]; a = (0.25 + 0.75 * (0.5 + 0.5 * Math.sin(t * s.s + s.p))) * s.d;
      sparkle(s.x + mx * 14 * s.d, s.y + my * 8 * s.d, s.r * (0.7 + 0.4 * a), t * s.rs + s.p, a, s.c);
    }
  }

  function drawShoots(dt) {
    nextShoot -= dt;
    if (nextShoot <= 0 && !reduce) { nextShoot = rnd(2, 4.5); var dir = Math.random() < 0.5 ? 1 : -1; shoots.push({ x: dir > 0 ? rnd(-0.05, 0.5) * W : rnd(0.5, 1.05) * W, y: rnd(0.02, 0.35) * skyB, vx: dir * rnd(520, 760), vy: rnd(180, 320), l: 0 }); }
    for (var i = shoots.length - 1; i >= 0; i--) {
      var s = shoots[i]; s.x += s.vx * dt; s.y += s.vy * dt; s.l += dt;
      var tl = 0.22, g = ctx.createLinearGradient(s.x, s.y, s.x - s.vx * tl, s.y - s.vy * tl);
      g.addColorStop(0, 'rgba(255,255,255,0.95)'); g.addColorStop(0.3, 'rgba(253,230,138,0.6)'); g.addColorStop(1, 'rgba(253,230,138,0)');
      ctx.strokeStyle = g; ctx.lineWidth = 3; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(s.x, s.y); ctx.lineTo(s.x - s.vx * tl, s.y - s.vy * tl); ctx.stroke();
      sparkle(s.x, s.y, 8, s.l * 6, 1, '255,255,255');
      if (s.l > 1.6 || s.x < -80 || s.x > W + 80 || s.y > skyB) shoots.splice(i, 1);
    }
  }

  function drawGlyphs(dt) {
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    for (var i = 0; i < glyphs.length; i++) {
      var g = glyphs[i]; g.y -= g.v * dt; g.rot += g.vr * dt;
      if (g.y < -100) { g.y = H * 0.7; g.x = rnd(0, W); }
      ctx.save(); ctx.translate(g.x + Math.sin(t * 0.3 + g.ph) * 30 + mx * 30, g.y + my * 18); ctx.rotate(g.rot);
      ctx.font = '800 ' + g.sz + 'px "Times New Roman",serif'; ctx.fillStyle = 'rgba(255,255,255,' + (g.a * (0.7 + 0.3 * Math.sin(t + g.ph))).toFixed(3) + ')';
      ctx.shadowColor = 'rgba(255,255,255,0.7)'; ctx.shadowBlur = 24; ctx.fillText(g.ch, 0, 0); ctx.restore();
    }
  }

  function drawOrbit() {
    var sx = offX + 1230 * S, sy = offY + 190 * S, rx = 230 * S, ry = rx * 0.42;
    ctx.strokeStyle = 'rgba(255,255,255,0.28)'; ctx.lineWidth = 1.4; ctx.setLineDash([4, 8]); ctx.beginPath(); ctx.ellipse(sx, sy, rx, ry, -0.25, 0, 6.2832); ctx.stroke(); ctx.setLineDash([]);
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    for (var i = 0; i < orbit.length; i++) {
      var o = orbit[i], u = o.u + t * o.v, ex = Math.cos(u) * rx, ey = Math.sin(u) * ry, ca = Math.cos(-0.25), sa = Math.sin(-0.25);
      var X = sx + ex * ca - ey * sa, Y = sy + ex * sa + ey * ca, depth = 0.7 + 0.3 * Math.sin(u);
      ctx.save(); ctx.translate(X, Y); ctx.font = '800 ' + Math.round(34 * S * depth) + 'px "Times New Roman",serif';
      ctx.fillStyle = 'rgba(255,255,255,' + (0.55 + 0.4 * depth).toFixed(2) + ')'; ctx.shadowColor = 'rgba(255,200,60,0.95)'; ctx.shadowBlur = 16; ctx.fillText(o.ch, 0, 0); ctx.restore();
    }
  }

  function drawChips(dt) {
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    for (var i = 0; i < chips.length; i++) {
      var c = chips[i]; c.y -= c.v * dt; c.life += c.v * dt;
      if (c.y < -60) { chips[i] = c = newChip(false); }
      var p = Math.min(1, Math.max(0, (H + 60 - c.y) / (H + 120))), a = Math.min(1, p / 0.1) * Math.min(1, (1 - p) / 0.25);
      var x = c.x + Math.sin(t * 0.6 + c.ph) * c.sw + mx * 24 * c.z, y = c.y + my * 14 * c.z;
      ctx.save(); ctx.translate(x, y); ctx.rotate(c.rot + Math.sin(t * 0.5 + c.ph) * 0.06); ctx.globalAlpha = a * 0.95;
      ctx.shadowColor = 'rgba(10,20,70,0.35)'; ctx.shadowBlur = 18; ctx.shadowOffsetY = 6;
      var g = ctx.createLinearGradient(0, -c.h / 2, 0, c.h / 2); g.addColorStop(0, c.col[0]); g.addColorStop(1, c.col[0]);
      ctx.fillStyle = g; rr(-c.w / 2, -c.h / 2, c.w, c.h, c.h / 2); ctx.fill();
      ctx.shadowColor = 'transparent'; ctx.shadowBlur = 0; ctx.shadowOffsetY = 0;
      ctx.strokeStyle = c.col[1]; ctx.lineWidth = 1.3; rr(-c.w / 2, -c.h / 2, c.w, c.h, c.h / 2); ctx.stroke();
      ctx.fillStyle = 'rgba(255,255,255,0.18)'; rr(-c.w / 2 + 6, -c.h / 2 + 3, c.w - 12, c.h * 0.32, c.h * 0.16); ctx.fill();
      ctx.font = '700 ' + Math.round(17 * c.z) + 'px "Cascadia Code","Consolas","Segoe UI",monospace'; ctx.fillStyle = '#fff'; ctx.fillText(c.txt, 0, 1);
      ctx.restore();
    }
  }

  function spawnDust(x, y, n, burst) {
    for (var i = 0; i < n; i++) { var an = rnd(0, 6.283), sp = burst ? rnd(60, 260) : rnd(10, 60); dust.push({ x: x, y: y, vx: Math.cos(an) * sp, vy: Math.sin(an) * sp - (burst ? 0 : 20), l: 0, life: rnd(0.7, 1.3), r: rnd(3, burst ? 9 : 6), c: pick(['255,255,255', '253,224,71', '255,190,90']) }); }
    if (dust.length > 260) dust.splice(0, dust.length - 260);
  }
  function drawDust(dt) {
    for (var i = dust.length - 1; i >= 0; i--) {
      var d = dust[i]; d.l += dt; d.x += d.vx * dt; d.y += d.vy * dt; d.vy += 40 * dt; d.vx *= 0.985;
      var a = 1 - d.l / d.life; if (a <= 0) { dust.splice(i, 1); continue; }
      sparkle(d.x, d.y, d.r * (0.5 + a * 0.6), d.l * 4, a, d.c);
    }
  }

  function frame(dt) {
    mx += (tx - mx) * 0.05; my += (ty - my) * 0.05;
    ctx.clearRect(0, 0, W, H);
    drawStars(); drawShoots(dt); drawGlyphs(dt); drawOrbit(); drawChips(dt); drawDust(dt);
  }

  function loop(ts) {
    raf = 0;
    if (document.hidden || document.body.classList.contains('authenticated')) { last = 0; return poll(); }
    var dt = last ? Math.min(0.05, (ts - last) / 1000) : 0.016; last = ts; t += dt;
    frame(dt); raf = requestAnimationFrame(loop);
  }
  function poll() { if (!raf) setTimeout(function () { if (!raf) raf = requestAnimationFrame(loop); }, 800); }

  host.addEventListener('pointermove', function (e) {
    var rc = host.getBoundingClientRect(); pointer.x = e.clientX - rc.left; pointer.y = e.clientY - rc.top;
    tx = (pointer.x / W - 0.5) * 2; ty = (pointer.y / H - 0.5) * 2;
    if (!reduce && t - lastSpawn > 0.04) { lastSpawn = t; spawnDust(pointer.x, pointer.y, 1, false); }
  }, { passive: true });
  host.addEventListener('pointerdown', function (e) { if (reduce) return; var rc = host.getBoundingClientRect(); spawnDust(e.clientX - rc.left, e.clientY - rc.top, 16, true); }, { passive: true });
  host.addEventListener('pointerleave', function () { pointer.x = pointer.y = -9999; tx = ty = 0; }, { passive: true });
  window.addEventListener('resize', resize);
  document.addEventListener('visibilitychange', function () { if (!document.hidden && !raf && !reduce) raf = requestAnimationFrame(loop); });
  resize();
  if (!reduce) raf = requestAnimationFrame(loop);
})();
