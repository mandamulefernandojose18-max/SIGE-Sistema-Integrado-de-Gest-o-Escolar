/* SIGE — Cena escolar ilustrada e animada do ecrã de login (SVG + CSS, sem dependências).
 * Ilustração vectorial plana nas cores da marca: sol com raios, nuvens, pássaros,
 * avião de papel, objectos escolares a flutuar (livro, lápis, globo, capelo, lâmpada,
 * bloco ABC), colinas, edifício escolar com relógio e bandeira a ondular, árvores a
 * balançar, autocarro escolar em andamento e crianças a caminhar com mochilas.
 * Paralaxe suave com o rato. Respeita prefers-reduced-motion. Sem dados reais/fictícios.
 */
(function () {
  'use strict';
  var host = document.getElementById('loginView');
  if (!host || document.getElementById('loginBgScene')) return;

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Peças reutilizáveis ---------- */
  function cloud(x, y, s, d, dl, op) {
    return '<g class="lb-drift" style="--d:' + d + 's;--dl:' + dl + 's"><g transform="translate(' + x + ' ' + y + ') scale(' + s + ')" opacity="' + op + '">' +
      '<ellipse cx="85" cy="68" rx="64" ry="7" fill="#b9dcff" opacity=".55"/>' +
      '<circle cx="40" cy="40" r="30" fill="#fff"/><circle cx="82" cy="26" r="38" fill="#fff"/><circle cx="128" cy="40" r="32" fill="#fff"/>' +
      '<rect x="28" y="40" width="112" height="30" rx="15" fill="#fff"/></g></g>';
  }
  function bird(x, y, dl) {
    return '<g transform="translate(' + x + ' ' + y + ')"><path class="lb-flap" style="animation-delay:' + dl + 's" d="M0 0 q9 -11 18 0 q9 -11 18 0" fill="none" stroke="#1e3a8a" stroke-width="3" stroke-linecap="round"/></g>';
  }
  function win(x, y, i) {
    return '<g><rect x="' + x + '" y="' + y + '" width="44" height="52" rx="3" fill="url(#lbGlass)" stroke="#fffaf0" stroke-width="4"/>' +
      '<path d="M' + (x + 22) + ' ' + y + 'V' + (y + 52) + 'M' + x + ' ' + (y + 26) + 'H' + (x + 44) + '" stroke="#fffaf0" stroke-width="3"/>' +
      '<path class="lb-shine" style="animation-delay:' + (-i * 0.9) + 's" d="M' + (x + 8) + ' ' + (y + 52) + 'L' + (x + 22) + ' ' + y + 'L' + (x + 32) + ' ' + y + 'L' + (x + 18) + ' ' + (y + 52) + 'Z" fill="#fff"/></g>';
  }
  function tree(x, y, s, c1, c2) {
    return '<g transform="translate(' + x + ' ' + y + ') scale(' + s + ')"><g class="lb-sway">' +
      '<rect x="-9" y="-72" width="18" height="72" rx="6" fill="#8b5e3c"/>' +
      '<circle cx="-38" cy="-86" r="36" fill="' + c1 + '"/><circle cx="38" cy="-86" r="36" fill="' + c1 + '"/><circle cx="0" cy="-112" r="52" fill="' + c1 + '"/>' +
      '<circle cx="-14" cy="-130" r="28" fill="' + c2 + '" opacity=".65"/><circle cx="34" cy="-96" r="14" fill="' + c2 + '" opacity=".5"/></g></g>';
  }
  function bush(x, y, s) {
    return '<g transform="translate(' + x + ' ' + y + ') scale(' + s + ')"><g class="lb-sway" style="animation-duration:3.6s">' +
      '<circle cx="-22" cy="-16" r="22" fill="#2f9e5f"/><circle cx="20" cy="-16" r="24" fill="#2f9e5f"/><circle cx="0" cy="-28" r="28" fill="#3fb374"/>' +
      '<circle cx="-14" cy="-30" r="4" fill="#fb7185"/><circle cx="12" cy="-18" r="4" fill="#fde047"/><circle cx="-26" cy="-10" r="4" fill="#fff"/><circle cx="26" cy="-30" r="4" fill="#f472b6"/></g></g>';
  }
  function kid(shirt, skin, hair, pack, y, dir, dur, dl, sc) {
    var flip = dir < 0 ? -sc : sc;
    return '<g transform="translate(0 ' + y + ')"><g class="' + (dir < 0 ? 'lb-walkL' : 'lb-walkR') + '" style="--d:' + dur + 's;animation-delay:' + dl + 's">' +
      '<g transform="scale(' + flip + ' ' + sc + ')"><ellipse cx="0" cy="2" rx="16" ry="4" fill="#000" opacity=".15"/><g class="lb-kid">' +
      '<g transform="translate(0 -34)"><g class="lb-leg b"><path d="M0 0V32" stroke="#334155" stroke-width="6" stroke-linecap="round"/><path d="M-1 34h8" stroke="#0f172a" stroke-width="6" stroke-linecap="round"/></g></g>' +
      '<g transform="translate(0 -34)"><g class="lb-leg"><path d="M0 0V32" stroke="#1e293b" stroke-width="6" stroke-linecap="round"/><path d="M-1 34h8" stroke="#0f172a" stroke-width="6" stroke-linecap="round"/></g></g>' +
      '<rect x="-19" y="-62" width="11" height="22" rx="4" fill="' + pack + '"/>' +
      '<rect x="-11" y="-64" width="22" height="32" rx="9" fill="' + shirt + '"/>' +
      '<g transform="translate(0 -58)"><g class="lb-leg b" style="animation-duration:.5s"><path d="M0 0V22" stroke="' + skin + '" stroke-width="5" stroke-linecap="round"/></g></g>' +
      '<circle cx="0" cy="-76" r="12" fill="' + skin + '"/><path d="M-12 -78a12 12 0 0 1 24 0z" fill="' + hair + '"/>' +
      '<circle cx="5" cy="-75" r="1.8" fill="#1e293b"/><path d="M3 -70q3 3 6 0" stroke="#7c2d12" stroke-width="1.5" fill="none" stroke-linecap="round"/>' +
      '</g></g></g></g>';
  }
  function spark(x, y, dl, c) {
    return '<path class="lb-spark" style="animation-delay:' + dl + 's" transform="translate(' + x + ' ' + y + ')" d="M0 -12 Q2 -2 12 0 Q2 2 0 12 Q-2 2 -12 0 Q-2 -2 0 -12Z" fill="' + c + '"/>';
  }
  function floatObj(x, y, dur, dl, inner) {
    return '<g transform="translate(' + x + ' ' + y + ')"><g class="lb-bob" style="animation-duration:' + dur + 's;animation-delay:' + dl + 's">' + inner + '</g></g>';
  }
  var OBJ_BOOK = '<rect x="-48" y="-34" width="96" height="68" rx="7" fill="#2563eb"/><path d="M0 -27Q-22 -36 -42 -27V27Q-22 18 0 29Q22 18 42 27V-27Q22 -36 0 -27Z" fill="#fff7e0"/><path d="M0 -27V29" stroke="#cbd5e1" stroke-width="2"/><path d="M-34 -14Q-18 -19 -7 -13M-34 0Q-18 -5 -7 1M-34 14Q-18 9 -7 15M34 -14Q18 -19 7 -13M34 0Q18 -5 7 1" stroke="#94a3b8" stroke-width="2.4" fill="none" stroke-linecap="round"/>';
  var OBJ_PENCIL = '<g transform="rotate(35)"><rect x="-10" y="-50" width="20" height="74" rx="2" fill="#facc15"/><rect x="-2" y="-50" width="4" height="74" fill="#f59e0b"/><rect x="-10" y="-64" width="20" height="16" rx="4" fill="#f472b6"/><rect x="-10" y="-50" width="20" height="8" fill="#cbd5e1"/><path d="M-10 24H10L0 50Z" fill="#fde68a"/><path d="M-3.5 40H3.5L0 50Z" fill="#1f2937"/></g>';
  var OBJ_GLOBE = '<circle r="40" fill="#38bdf8"/><ellipse cx="-12" cy="-12" rx="14" ry="11" transform="rotate(25 -12 -12)" fill="#4ade80"/><ellipse cx="16" cy="14" rx="10" ry="15" transform="rotate(-20 16 14)" fill="#4ade80"/><ellipse rx="15" ry="40" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width="2"/><path d="M-40 0H40" stroke="#fff" stroke-opacity=".5" stroke-width="2"/><path d="M-46 12A48 48 0 0 0 46 12" fill="none" stroke="#fbbf24" stroke-width="5" stroke-linecap="round" transform="translate(0 14)"/><rect x="-14" y="56" width="28" height="7" rx="3" fill="#fbbf24"/>';
  var OBJ_BLOCK = '<rect x="-36" y="-36" width="72" height="72" rx="10" fill="#7c3aed"/><rect x="-36" y="-36" width="72" height="30" rx="10" fill="#a78bfa"/><text x="0" y="22" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-weight="800" font-size="56" fill="#fff">A</text>';
  var OBJ_CAP = '<path d="M-26 6V34Q0 50 26 34V6Z" fill="#1f2937"/><path d="M-52 -4L0 -30L52 -4L0 22Z" fill="#111827" stroke="#6366f1" stroke-width="3" stroke-linejoin="round"/><path d="M0 -4L46 0V30" stroke="#fbbf24" stroke-width="4" fill="none" stroke-linecap="round"/><circle cx="46" cy="34" r="6" fill="#fbbf24"/>';
  var OBJ_BULB = '<circle cy="-8" r="34" fill="#fde047"/><circle cy="-8" r="48" fill="#fde047" opacity=".25"/><path d="M-20 14H20L14 34H-14Z" fill="#fde047"/><rect x="-16" y="34" width="32" height="10" rx="4" fill="#94a3b8"/><rect x="-11" y="46" width="22" height="8" rx="4" fill="#64748b"/><path d="M-12 24L-6 -10L0 8L6 -10L12 24" stroke="#d97706" stroke-width="3" fill="none" stroke-linejoin="round"/>';

  /* ---------- Cena ---------- */
  var ray = '';
  for (var r = 0; r < 12; r++) ray += '<rect x="-7" y="-128" width="14" height="44" rx="7" fill="#fff2a8" opacity=".8" transform="rotate(' + (r * 30) + ')"/>';
  var winsL = '', winsR = '', i, c, rw;
  for (rw = 0; rw < 2; rw++) for (c = 0; c < 5; c++) { winsL += win(266 + c * 72, 548 + rw * 70, c + rw * 5); winsR += win(1006 + c * 72, 548 + rw * 70, c * 2 + rw * 3); }
  var cols = '';
  for (i = 0; i < 6; i++) cols += '<rect x="' + (628 + i * 62) + '" y="470" width="22" height="206" rx="3" fill="#fffaf0"/><rect x="' + (624 + i * 62) + '" y="466" width="30" height="8" rx="2" fill="#f1d9a6"/><rect x="' + (624 + i * 62) + '" y="672" width="30" height="8" rx="2" fill="#f1d9a6"/>';

  var svg =
    '<svg id="loginBgScene" class="lb" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMax slice" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" style="position:absolute;inset:0;width:100%;height:100%;z-index:0;pointer-events:none;">' +
    '<defs>' +
    '<linearGradient id="lbSky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1d6fe0"/><stop offset=".5" stop-color="#5fb2fb"/><stop offset="1" stop-color="#d4f0ff"/></linearGradient>' +
    '<radialGradient id="lbSun"><stop offset="0" stop-color="#fff7c2"/><stop offset=".45" stop-color="#ffe27a" stop-opacity=".55"/><stop offset="1" stop-color="#ffd24d" stop-opacity="0"/></radialGradient>' +
    '<linearGradient id="lbH1" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9be3b0"/><stop offset="1" stop-color="#63c993"/></linearGradient>' +
    '<linearGradient id="lbH2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4fbb83"/><stop offset="1" stop-color="#2f9a6b"/></linearGradient>' +
    '<linearGradient id="lbGrass" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#43b777"/><stop offset="1" stop-color="#1f7a53"/></linearGradient>' +
    '<linearGradient id="lbWall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff7e2"/><stop offset="1" stop-color="#f1d9a6"/></linearGradient>' +
    '<linearGradient id="lbRoof" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2f2791"/><stop offset="1" stop-color="#18114f"/></linearGradient>' +
    '<linearGradient id="lbGlass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#cfeeff"/><stop offset="1" stop-color="#5aa9e6"/></linearGradient>' +
    '<linearGradient id="lbHaze" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity=".55"/></linearGradient>' +
    '</defs>' +
    '<style>' +
    '.lb *{transform-box:view-box}' +
    '.lb-drift{animation:lbDrift var(--d,120s) linear infinite;animation-delay:var(--dl,0s)}' +
    '@keyframes lbDrift{from{transform:translateX(-520px)}to{transform:translateX(2000px)}}' +
    '.lb-rays{animation:lbSpin 70s linear infinite}' +
    '@keyframes lbSpin{to{transform:rotate(360deg)}}' +
    '.lb-sway{animation:lbSway 5s ease-in-out infinite alternate}' +
    '@keyframes lbSway{from{transform:rotate(-1.6deg)}to{transform:rotate(1.6deg)}}' +
    '.lb-bob{animation:lbBob 6s ease-in-out infinite alternate;filter:drop-shadow(0 10px 8px rgba(10,30,80,.22))}' +
    '@keyframes lbBob{from{transform:translate(0,0) rotate(-4deg)}to{transform:translate(0,-18px) rotate(4deg)}}' +
    '.lb-bus{animation:lbBus 26s linear infinite}' +
    '@keyframes lbBus{from{transform:translateX(-420px)}to{transform:translateX(2000px)}}' +
    '.lb-busb{animation:lbBounce .45s ease-in-out infinite alternate}' +
    '@keyframes lbBounce{to{transform:translateY(-2.5px)}}' +
    '.lb-wheel{animation:lbSpin .7s linear infinite}' +
    '.lb-road{stroke-dasharray:46 34;animation:lbDash 1.2s linear infinite}' +
    '@keyframes lbDash{to{stroke-dashoffset:80}}' +
    '.lb-leg{animation:lbLeg .5s ease-in-out infinite alternate}.lb-leg.b{animation-direction:alternate-reverse}' +
    '@keyframes lbLeg{from{transform:rotate(28deg)}to{transform:rotate(-28deg)}}' +
    '.lb-kid{animation:lbKid .5s ease-in-out infinite alternate}' +
    '@keyframes lbKid{to{transform:translateY(-3px)}}' +
    '.lb-walkR{animation:lbWR var(--d,40s) linear infinite}.lb-walkL{animation:lbWL var(--d,40s) linear infinite}' +
    '@keyframes lbWR{from{transform:translateX(-220px)}to{transform:translateX(1820px)}}' +
    '@keyframes lbWL{from{transform:translateX(1820px)}to{transform:translateX(-220px)}}' +
    '.lb-shine{opacity:0;animation:lbShine 7s ease-in-out infinite}' +
    '@keyframes lbShine{0%,70%,100%{opacity:0}82%{opacity:.85}}' +
    '.lb-spark{transform-box:fill-box!important;transform-origin:center;animation:lbSpark 2.6s ease-in-out infinite}' +
    '@keyframes lbSpark{0%,100%{transform:scale(0);opacity:0}50%{transform:scale(1);opacity:1}}' +
    '.lb-flock{animation:lbFlock 40s linear infinite}' +
    '@keyframes lbFlock{from{transform:translate(-200px,0)}50%{transform:translate(800px,-40px)}to{transform:translate(1800px,10px)}}' +
    '.lb-flap{transform-box:fill-box!important;transform-origin:center;animation:lbFlap .45s ease-in-out infinite alternate}' +
    '@keyframes lbFlap{to{transform:scaleY(.25)}}' +
    '.lb-plane{animation:lbPlane 28s ease-in-out infinite}' +
    '@keyframes lbPlane{0%{transform:translate(-120px,430px) rotate(-14deg)}35%{transform:translate(520px,260px) rotate(-6deg)}70%{transform:translate(1120px,320px) rotate(9deg)}100%{transform:translate(1760px,130px) rotate(-12deg)}}' +
    '.lb-min{animation:lbSpin 30s linear infinite}.lb-hr{animation:lbSpin 360s linear infinite}' +
    '@media (prefers-reduced-motion:reduce){.lb *{animation:none!important}}' +
    '</style>' +
    '<rect x="-200" y="-200" width="2000" height="1300" fill="url(#lbSky)"/>' +

    '<g id="lbP1"><g transform="translate(1230 190)"><circle r="200" fill="url(#lbSun)"/><g class="lb-rays">' + ray + '</g><circle r="64" fill="#ffd84d"/><circle r="52" fill="#ffe680"/></g></g>' +

    '<g id="lbP2">' +
    cloud(100, 90, 1.3, 150, -20, 0.95) + cloud(520, 210, 0.9, 190, -90, 0.85) + cloud(300, 40, 0.7, 220, -150, 0.8) + cloud(900, 120, 1.1, 170, -60, 0.9) + cloud(40, 330, 0.8, 200, -120, 0.75) +
    '<g class="lb-flock">' + bird(0, 200, 0) + bird(40, 224, .1) + bird(78, 196, .2) + bird(112, 232, .05) + bird(150, 208, .15) + '</g>' +
    '<g class="lb-plane"><path d="M0 0L-52 -12L-34 4Z" fill="#fff"/><path d="M0 0L-34 4L-42 24Z" fill="#c7d2fe"/><path d="M-52 -12L-34 4" stroke="#a5b4fc" stroke-width="1.5"/></g>' +
    floatObj(170, 300, 6.2, 0, OBJ_BOOK) + floatObj(380, 170, 5.4, -1.2, OBJ_PENCIL) + floatObj(300, 440, 7, -2.4, OBJ_GLOBE) +
    floatObj(1440, 320, 6.6, -.6, OBJ_BLOCK) + floatObj(1220, 400, 5.8, -1.8, OBJ_CAP) + floatObj(1500, 140, 6.9, -3, OBJ_BULB) +
    spark(260, 250, 0, '#fff') + spark(430, 280, 1.1, '#fde047') + spark(120, 430, .6, '#fff') + spark(1330, 250, 1.4, '#fff') + spark(1500, 440, .3, '#fde047') + spark(1180, 300, 2, '#fff') +
    '</g>' +

    '<g id="lbP3">' +
    '<path d="M-100 570C100 500 280 520 460 556S780 490 1020 530 1380 500 1700 540V900H-100Z" fill="url(#lbH1)"/>' +
    '<path d="M-100 620C140 570 400 610 620 618S1000 566 1260 606 1500 596 1700 610V900H-100Z" fill="url(#lbH2)"/>' +
    '<rect x="-100" y="540" width="1800" height="160" fill="url(#lbHaze)" opacity=".6"/>' +
    '</g>' +

    '<g id="lbP4">' +
    '<ellipse cx="800" cy="702" rx="720" ry="16" fill="#000" opacity=".15"/>' +
    '<rect x="240" y="520" width="380" height="172" fill="url(#lbWall)"/><rect x="980" y="520" width="380" height="172" fill="url(#lbWall)"/>' +
    '<rect x="228" y="504" width="404" height="20" rx="4" fill="url(#lbRoof)"/><rect x="968" y="504" width="404" height="20" rx="4" fill="url(#lbRoof)"/>' +
    '<rect x="240" y="676" width="380" height="16" fill="#e7cd96"/><rect x="980" y="676" width="380" height="16" fill="#e7cd96"/>' +
    winsL + winsR +
    '<rect x="600" y="440" width="400" height="252" fill="url(#lbWall)"/>' +
    '<path d="M570 444L800 336L1030 444Z" fill="url(#lbRoof)"/><path d="M620 440L800 356L980 440Z" fill="#fff7e2" opacity=".12"/>' +
    '<circle cx="800" cy="410" r="28" fill="#fff"/><circle cx="800" cy="410" r="28" fill="none" stroke="#df8704" stroke-width="5"/>' +
    '<g transform="translate(800 410)"><g class="lb-min"><path d="M0 0V-20" stroke="#18114f" stroke-width="3" stroke-linecap="round"/></g><g class="lb-hr"><path d="M0 0V-13" stroke="#18114f" stroke-width="4" stroke-linecap="round"/></g></g>' +
    cols +
    '<rect x="722" y="540" width="156" height="34" rx="8" fill="#18114f"/><text x="800" y="565" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-weight="800" font-size="22" letter-spacing="4" fill="#df8704">SIGE</text>' +
    '<path d="M768 692V632a32 32 0 0 1 64 0V692Z" fill="#18114f"/><circle cx="800" cy="650" r="3" fill="#df8704"/><path d="M800 620V692" stroke="#2f2791" stroke-width="2"/>' +
    '<rect x="586" y="692" width="428" height="10" rx="2" fill="#e7cd96"/><rect x="566" y="702" width="468" height="10" rx="2" fill="#d9bd80"/>' +
    '<path d="M800 336V286" stroke="#cbd5e1" stroke-width="4" stroke-linecap="round"/>' +
    '<path fill="#df8704"><animate attributeName="d" dur="1.7s" repeatCount="indefinite" values="M802 288q18 -9 36 0t36 0v26q-18 -9 -36 0t-36 0z;M802 288q18 9 36 0t36 0v26q-18 9 -36 0t-36 0z;M802 288q18 -9 36 0t36 0v26q-18 -9 -36 0t-36 0z"/></path>' +
    '</g>' +

    '<g id="lbP5">' +
    '<path d="M-100 700C260 680 640 712 960 690S1500 700 1700 690V960H-100Z" fill="url(#lbGrass)"/>' +
    bush(180, 760, 1.2) + bush(560, 742, 0.9) + bush(1050, 742, 0.9) + bush(1430, 762, 1.2) +
    tree(70, 770, 1.35, '#2f9e5f', '#8ae0a5') + tree(1530, 772, 1.4, '#2a9d6c', '#8ae0a5') + tree(400, 748, 0.8, '#3fb374', '#a7f0c0') + tree(1230, 750, 0.85, '#37a96c', '#a7f0c0') +
    '<rect x="-100" y="786" width="1800" height="10" fill="#d5dbe4"/>' +
    '<rect x="-100" y="796" width="1800" height="76" fill="#4b5563"/><rect x="-100" y="796" width="1800" height="6" fill="#374151"/>' +
    '<path class="lb-road" d="M-100 836H1700" stroke="#fde68a" stroke-width="5" fill="none"/>' +
    kid('#ef4444', '#f2c29b', '#3b2a20', '#2563eb', 764, 1, 46, -8, 1.15) + kid('#22c55e', '#8d5a3b', '#111827', '#f59e0b', 772, -1, 54, -30, 1.3) +
    kid('#8b5cf6', '#e8b48a', '#7c4a1d', '#ec4899', 758, 1, 62, -40, 1.05) + kid('#0ea5e9', '#6b4423', '#0f172a', '#ef4444', 770, -1, 40, -12, 1.25) +
    '<g class="lb-bus"><g class="lb-busb" transform="translate(0 0)">' +
    '<rect x="0" y="772" width="226" height="64" rx="14" fill="#fbbf24"/><rect x="0" y="772" width="226" height="16" rx="10" fill="#fcd34d"/>' +
    '<rect x="14" y="780" width="30" height="26" rx="4" fill="#bfe6ff"/><rect x="52" y="780" width="30" height="26" rx="4" fill="#bfe6ff"/><rect x="90" y="780" width="30" height="26" rx="4" fill="#bfe6ff"/><rect x="128" y="780" width="30" height="26" rx="4" fill="#bfe6ff"/><rect x="170" y="780" width="42" height="34" rx="5" fill="#bfe6ff"/>' +
    '<rect x="0" y="812" width="226" height="6" fill="#1f2937"/><text x="14" y="831" font-family="Segoe UI,Arial,sans-serif" font-weight="800" font-size="11" fill="#1f2937" letter-spacing="2">ESCOLAR</text>' +
    '<circle cx="221" cy="822" r="5" fill="#fef08a"/><rect x="0" y="826" width="226" height="8" rx="3" fill="#92400e" opacity=".5"/>' +
    '<g transform="translate(52 838)"><g class="lb-wheel"><circle r="16" fill="#111827"/><circle r="7" fill="#9ca3af"/><path d="M-7 0H7M0 -7V7" stroke="#4b5563" stroke-width="2"/></g></g>' +
    '<g transform="translate(176 838)"><g class="lb-wheel"><circle r="16" fill="#111827"/><circle r="7" fill="#9ca3af"/><path d="M-7 0H7M0 -7V7" stroke="#4b5563" stroke-width="2"/></g></g>' +
    '</g></g>' +
    '</g>' +
    '</svg>';

  host.insertAdjacentHTML('afterbegin', svg);
  var scene = document.getElementById('loginBgScene');
  if (!scene || reduce) return;

  /* ---------- Paralaxe suave com o rato ---------- */
  var layers = [['lbP1', 5], ['lbP2', 12], ['lbP3', 18], ['lbP4', 26], ['lbP5', 40]].map(function (a) { return { el: document.getElementById(a[0]), k: a[1], x: 0, y: 0 }; });
  var tx = 0, ty = 0, raf = 0;
  function loop() {
    raf = 0;
    if (document.hidden || document.body.classList.contains('authenticated')) return;
    var moving = false;
    layers.forEach(function (L) {
      var nx = L.x + (tx * L.k - L.x) * 0.06, ny = L.y + (ty * L.k * 0.4 - L.y) * 0.06;
      if (Math.abs(nx - L.x) > 0.01 || Math.abs(ny - L.y) > 0.01) { moving = true; L.x = nx; L.y = ny; L.el.setAttribute('transform', 'translate(' + nx.toFixed(2) + ' ' + ny.toFixed(2) + ')'); }
    });
    if (moving) raf = requestAnimationFrame(loop);
  }
  host.addEventListener('pointermove', function (e) {
    var rc = host.getBoundingClientRect();
    tx = -((e.clientX - rc.left) / rc.width - 0.5) * 2; ty = -((e.clientY - rc.top) / rc.height - 0.5) * 2;
    if (!raf) raf = requestAnimationFrame(loop);
  }, { passive: true });
  host.addEventListener('pointerleave', function () { tx = ty = 0; if (!raf) raf = requestAnimationFrame(loop); }, { passive: true });
})();
