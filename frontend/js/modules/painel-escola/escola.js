/**
 * SIGE - PAINEL-ESCOLA | Definições & Logótipo da Escola
 * Ficheiro de código independente do menu: escola.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
// ==================== 3. ESCOLA & TURMAS ====================
window.atualizarPreviewCodigoEscolaConfig = function() {
  const prov = document.getElementById('confEscolaProvincia')?.value || state.escolaAtual?.provincia || 'Maputo Cidade';
  const dist = document.getElementById('confEscolaDistrito')?.value || state.escolaAtual?.distrito || '';
  const tipo = document.getElementById('confEscolaTipo')?.value || state.escolaAtual?.tipo_escola || 'S';
  const nome = document.getElementById('confEscolaNome')?.value || state.escolaAtual?.nome || '';

  const codExistente = state.escolaAtual?.codigo_escola || '';
  let seqNum = 1;
  if (codExistente && codExistente.length >= 9) {
    const parsedSeq = parseInt(codExistente.slice(5), 10);
    if (!isNaN(parsedSeq) && parsedSeq > 0) seqNum = parsedSeq;
  }

  const prev = window.gerarPreviewCodigoEscola(prov, dist, tipo, nome, seqNum);
  const setTxt = (id, txt) => {
    const el = document.getElementById(id);
    if (el) el.textContent = txt;
  };
  setTxt('confEscolaCodigoBadge', prev.codigo_escola);
  setTxt('confCodigoGD', prev.codigo_gd);
  setTxt('confCodigoDP', prev.codigo_dp);
  setTxt('confCodigoSECR', prev.codigo_secr);
  setTxt('labelBadgeGD', prev.codigo_gd);
  setTxt('labelBadgeDP', prev.codigo_dp);
  setTxt('labelBadgeSECR', prev.codigo_secr);
};

async function carregarEscolaETurmas() {
  try {
    const resInfo = await apiFetch('/api/v1/escola-admin/info');
    if (resInfo.success) {
      const e = resInfo.data;
      state.escolaAtual = e;
      if (state.tenant) {
        state.tenant.codigo_escola = e.codigo_escola;
        state.tenant.tipo_escola = e.tipo_escola;
      }
      document.getElementById('confEscolaNome').value = e.nome;
      document.getElementById('confEscolaAnoLetivo').value = e.ano_letivo_ativo;
      document.getElementById('confEscolaTrimestreAtivo').value = e.trimestre_ativo || '1_TRIMESTRE';
      if (document.getElementById('confEscolaPublicacaoNotas')) {
        document.getElementById('confEscolaPublicacaoNotas').value = e.publicacao_notas_trimestre || 'TODOS';
      }
      document.getElementById('confEscolaTelefone').value = e.telefone || '';
      document.getElementById('confEscolaEmail').value = e.email;
      document.getElementById('confEscolaDirector').value = e.director_nome || '';
      document.getElementById('confEscolaDAP').value = e.dap_nome || '';
      document.getElementById('confEscolaChefeSec').value = e.chefe_secretaria_nome || '';
      document.getElementById('confEscolaEmblema').checked = !!e.usar_emblema_nacional;

      const selTipo = document.getElementById('confEscolaTipo');
      if (selTipo) selTipo.value = e.tipo_escola || 'S';

      const codEscola = e.codigo_escola || '0101S0001';
      const codGD = e.codigo_gabinete_director || `GD${codEscola}`;
      const codDP = e.codigo_direccao_pedagogica || `DP${codEscola}`;
      const codSECR = e.codigo_secretaria || `SECR${codEscola}`;
      const setTxt = (id, txt) => {
        const el = document.getElementById(id);
        if (el) el.textContent = txt;
      };
      setTxt('confEscolaCodigoBadge', codEscola);
      setTxt('confCodigoGD', codGD);
      setTxt('confCodigoDP', codDP);
      setTxt('confCodigoSECR', codSECR);
      setTxt('labelBadgeGD', codGD);
      setTxt('labelBadgeDP', codDP);
      setTxt('labelBadgeSECR', codSECR);

      // Logótipo da Escola & Catálogo de Identidade Visual
      if (e.galeria_logos && Array.isArray(e.galeria_logos)) {
        state.escolaAtual.galeria_logos = e.galeria_logos;
        if (state.tenant) state.tenant.galeria_logos = e.galeria_logos;
      }
      const logoVal = e.logo_url || e.logo_base64 || '';
      const finalLogoInput = document.getElementById('confEscolaLogoFinalValue');
      if (finalLogoInput) finalLogoInput.value = logoVal;
      const urlInput = document.getElementById('confEscolaLogoUrl');
      if (urlInput) urlInput.value = '';
      window.atualizarVisualizacaoLogo(logoVal, e.usar_emblema_nacional);
      window.renderizarGaleriaLogos();

      // Províncias
      const selectProv = document.getElementById('confEscolaProvincia');
      selectProv.innerHTML = (state.geografia.provincias || []).map(p => 
        `<option value="${p}" ${p === e.provincia ? 'selected' : ''}>${p}</option>`
      ).join('');
      atualizarDistritosEscola(e.provincia || 'Maputo Cidade', e.distrito);
    }

    // Carregar turmas no painel integrado e dedicado
    await carregarTurmas();
  } catch (err) {
    console.error('Erro ao carregar dados da escola:', err);
  }
}

// ==================== GALERIA DE LOGÓTIPOS & PERMUTAÇÃO INSTANTÂNEA ====================
window.obterGaleriaLogosEscola = function() {
  const e = state.escolaAtual || state.tenant || {};
  let galeria = Array.isArray(e.galeria_logos) ? [...e.galeria_logos] : [];

  const chaveLocal = `sige_galeria_logos_${e.id || 'default'}`;
  try {
    const salvoLocal = JSON.parse(localStorage.getItem(chaveLocal) || '[]');
    if (Array.isArray(salvoLocal)) {
      salvoLocal.forEach(item => {
        if (item && item.url && !galeria.some(g => g.id === item.id || g.url === item.url)) {
          galeria.push(item);
        }
      });
    }
  } catch (_) {}

  const logoAtual = e.logo_url || e.logo_base64;
  if (logoAtual && !logoAtual.includes('emblema-mocambique.png')) {
    if (!galeria.some(g => g.url === logoAtual)) {
      galeria.unshift({
        id: 'logo_anterior_' + Date.now(),
        nome: 'Logótipo da Escola',
        url: logoAtual,
        tipo: 'SALVO',
        criado_em: new Date().toISOString()
      });
    }
  }

  const mapa = new Map();
  galeria.forEach(item => {
    if (item && item.url && !mapa.has(item.url)) {
      mapa.set(item.url, item);
    }
  });

  return Array.from(mapa.values());
};

window.renderizarGaleriaLogos = function() {
  const container = document.getElementById('galeriaLogosContainer');
  if (!container) return;

  const galeria = window.obterGaleriaLogosEscola();
  const e = state.escolaAtual || state.tenant || {};
  const logoAtivoAtual = document.getElementById('confEscolaLogoFinalValue')?.value ?? (e.logo_url || e.logo_base64 || '');
  const checkEmblema = document.getElementById('confEscolaEmblema');
  const usarEmblema = checkEmblema ? checkEmblema.checked : (e.usar_emblema_nacional !== false);

  const contadorEl = document.getElementById('contadorGaleriaLogos');
  if (contadorEl) {
    const total = galeria.length + 1;
    contadorEl.textContent = `${total} disponível${total > 1 ? 'is' : ''}`;
  }

  const isEmblemaAtivo = Boolean(usarEmblema || !logoAtivoAtual || logoAtivoAtual === 'img/emblema-mocambique.png');

  let html = `
    <!-- 1. Emblema Nacional Oficial (Permanente e sempre disponível) -->
    <div class="col-6 col-sm-6 col-md-6 col-lg-6">
      <div class="card h-100 p-2 text-center logo-card-item cursor-pointer ${isEmblemaAtivo ? 'border-primary border-2 bg-primary-subtle shadow-sm' : 'border-secondary-subtle bg-white'}"
           onclick="selecionarLogotipoGaleria('emblema_nacional')"
           title="Clique para usar o Emblema Nacional Oficial"
           style="cursor: pointer; transition: all 0.2s; min-height: 120px;">
        <div class="d-flex align-items-center justify-content-center bg-light rounded p-1 mb-1" style="height: 60px;">
          <img src="img/emblema-mocambique.png" alt="Emblema Nacional" style="max-height: 100%; max-width: 100%; object-fit: contain;">
        </div>
        <div class="small fw-bold text-truncate text-dark" style="font-size: 0.74rem;" title="Emblema Nacional (Padrão Oficial)">
          Emblema Nacional
        </div>
        <div class="mt-1">
          ${isEmblemaAtivo 
            ? '<span class="badge bg-primary text-white" style="font-size: 0.68rem;"><i class="bi bi-check-circle-fill me-1"></i>Activo</span>' 
            : '<span class="badge bg-light text-secondary border" style="font-size: 0.68rem;"><i class="bi bi-hand-index-thumb me-1"></i>Usar este</span>'}
        </div>
      </div>
    </div>
  `;

  galeria.forEach((item, idx) => {
    const isAtivo = !isEmblemaAtivo && (logoAtivoAtual === item.url);
    const nomeExibicao = item.nome || `Logótipo ${idx + 1}`;
    html += `
      <div class="col-6 col-sm-6 col-md-6 col-lg-6">
        <div class="card h-100 p-2 text-center logo-card-item cursor-pointer position-relative ${isAtivo ? 'border-primary border-2 bg-primary-subtle shadow-sm' : 'border-secondary-subtle bg-white'}"
             onclick="selecionarLogotipoGaleria('${item.id}')"
             title="Clique para alternar para este logótipo"
             style="cursor: pointer; transition: all 0.2s; min-height: 120px;">
          <button type="button" class="btn btn-sm btn-danger py-0 px-1 position-absolute top-0 end-0 m-1 rounded-circle shadow-sm"
                  style="font-size: 0.65rem; width: 22px; height: 22px; line-height: 1; padding: 0; z-index: 2;"
                  onclick="event.stopPropagation(); removerLogotipoDaGaleria('${item.id}')"
                  title="Eliminar este logótipo da galeria">
            <i class="bi bi-trash"></i>
          </button>
          <div class="d-flex align-items-center justify-content-center bg-light rounded p-1 mb-1" style="height: 60px;">
            <img src="${item.url}" alt="${nomeExibicao}" style="max-height: 100%; max-width: 100%; object-fit: contain;">
          </div>
          <div class="small fw-bold text-truncate text-dark" style="font-size: 0.74rem;" title="${nomeExibicao}">
            ${nomeExibicao}
          </div>
          <div class="mt-1">
            ${isAtivo 
              ? '<span class="badge bg-primary text-white" style="font-size: 0.68rem;"><i class="bi bi-check-circle-fill me-1"></i>Activo</span>' 
              : '<span class="badge bg-light text-secondary border" style="font-size: 0.68rem;"><i class="bi bi-hand-index-thumb me-1"></i>Usar este</span>'}
          </div>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
};

window.selecionarLogotipoGaleria = async function(id) {
  const finalInput = document.getElementById('confEscolaLogoFinalValue');
  const checkEmblema = document.getElementById('confEscolaEmblema');
  const e = state.escolaAtual || state.tenant || {};

  let logoUrlParaSalvar = '';
  let usarEmblemaParaSalvar = false;

  if (id === 'emblema_nacional') {
    if (finalInput) finalInput.value = '';
    if (checkEmblema) checkEmblema.checked = true;
    logoUrlParaSalvar = '';
    usarEmblemaParaSalvar = true;
    window.atualizarVisualizacaoLogo('', true);
  } else {
    const galeria = window.obterGaleriaLogosEscola();
    const item = galeria.find(g => g.id === id);
    if (!item) return;

    if (finalInput) finalInput.value = item.url;
    if (checkEmblema) checkEmblema.checked = false;
    logoUrlParaSalvar = item.url;
    usarEmblemaParaSalvar = false;
    window.atualizarVisualizacaoLogo(item.url, false);
  }

  window.renderizarGaleriaLogos();

  if (state.escolaAtual) {
    state.escolaAtual.logo_url = logoUrlParaSalvar || null;
    state.escolaAtual.usar_emblema_nacional = usarEmblemaParaSalvar;
  }
  if (state.tenant) {
    state.tenant.logo_url = logoUrlParaSalvar || null;
    state.tenant.usar_emblema_nacional = usarEmblemaParaSalvar;
  }

  // Auto-salvar no backend de forma transparente para permitir permuta instantânea com um só clique
  try {
    const galeria = window.obterGaleriaLogosEscola();
    const body = {
      usar_emblema_nacional: usarEmblemaParaSalvar,
      logo_url: logoUrlParaSalvar,
      galeria_logos: galeria
    };
    await apiFetch('/api/v1/escola-admin/info', {
      method: 'PUT',
      body: JSON.stringify(body)
    });
    if (typeof mostrarToast === 'function') {
      mostrarToast(
        usarEmblemaParaSalvar 
          ? 'Emblema Nacional oficial activado com sucesso!' 
          : 'Logótipo alterado e activado com sucesso!',
        'success'
      );
    }
  } catch (err) {
    console.warn('Erro ao auto-salvar permuta de logótipo:', err);
  }
};

window.adicionarLogotipoAGaleria = async function(url, nome = '') {
  if (!url || !url.trim()) return;
  const urlLimpo = url.trim();
  const galeria = window.obterGaleriaLogosEscola();
  const e = state.escolaAtual || state.tenant || {};

  const existente = galeria.find(g => g.url === urlLimpo);
  if (existente) {
    await window.selecionarLogotipoGaleria(existente.id);
    return;
  }

  const novoId = 'logo_' + Date.now();
  const novoItem = {
    id: novoId,
    nome: nome || `Logótipo ${galeria.length + 1}`,
    url: urlLimpo,
    tipo: 'UPLOAD',
    criado_em: new Date().toISOString()
  };

  galeria.push(novoItem);

  const chaveLocal = `sige_galeria_logos_${e.id || 'default'}`;
  try {
    localStorage.setItem(chaveLocal, JSON.stringify(galeria));
  } catch (_) {}

  if (state.escolaAtual) state.escolaAtual.galeria_logos = galeria;
  if (state.tenant) state.tenant.galeria_logos = galeria;

  await window.selecionarLogotipoGaleria(novoId);
};

window.removerLogotipoDaGaleria = async function(id) {
  if (id === 'emblema_nacional') {
    alert('O Emblema Nacional Oficial é padrão do sistema e não pode ser eliminado.');
    return;
  }
  if (!confirm('Deseja realmente eliminar este logótipo da galeria?')) {
    return;
  }

  let galeria = window.obterGaleriaLogosEscola();
  const itemRemovido = galeria.find(g => g.id === id);
  galeria = galeria.filter(g => g.id !== id);

  const e = state.escolaAtual || state.tenant || {};
  const chaveLocal = `sige_galeria_logos_${e.id || 'default'}`;
  try {
    localStorage.setItem(chaveLocal, JSON.stringify(galeria));
  } catch (_) {}

  if (state.escolaAtual) state.escolaAtual.galeria_logos = galeria;
  if (state.tenant) state.tenant.galeria_logos = galeria;

  const finalInput = document.getElementById('confEscolaLogoFinalValue');
  if (itemRemovido && finalInput && finalInput.value === itemRemovido.url) {
    await window.selecionarLogotipoGaleria('emblema_nacional');
  } else {
    window.renderizarGaleriaLogos();
    try {
      await apiFetch('/api/v1/escola-admin/info', {
        method: 'PUT',
        body: JSON.stringify({ galeria_logos: galeria })
      });
      if (typeof mostrarToast === 'function') {
        mostrarToast('Logótipo removido da galeria.', 'info');
      }
    } catch (_) {}
  }
};

window.processarUploadLogoLocal = function(input) {
  const file = input.files?.[0];
  if (!file) return;

  if (!file.type.startsWith('image/')) {
    alert('Por favor, seleccione um ficheiro de imagem válido (PNG, JPG, WebP).');
    return;
  }

  if (file.size > 5 * 1024 * 1024) {
    alert('A imagem seleccionada é muito pesada (máximo 5MB).');
    return;
  }

  const reader = new FileReader();
  reader.onload = async function(e) {
    const dataUrl = e.target.result;
    const nomeFicheiro = file.name ? file.name.replace(/\.[^/.]+$/, "") : `Logótipo`;
    await window.adicionarLogotipoAGaleria(dataUrl, nomeFicheiro);
    input.value = '';
  };
  reader.readAsDataURL(file);
};

window.processarUrlLogo = async function(url) {
  if (!url || !url.trim()) {
    alert('Por favor, insira um link / URL válido da imagem.');
    return;
  }
  const urlLimpo = url.trim();
  await window.adicionarLogotipoAGaleria(urlLimpo, 'Logótipo Web');
  const inputEl = document.getElementById('confEscolaLogoUrl');
  if (inputEl) inputEl.value = '';
};

window.removerLogotipoEscola = async function() {
  await window.selecionarLogotipoGaleria('emblema_nacional');
};

window.alternarEmblemaCheck = async function(checked) {
  if (checked) {
    await window.selecionarLogotipoGaleria('emblema_nacional');
  } else {
    const galeria = window.obterGaleriaLogosEscola();
    if (galeria.length > 0) {
      await window.selecionarLogotipoGaleria(galeria[0].id);
    }
  }
};

window.atualizarVisualizacaoLogo = function(logoSrc, usarEmblema = true) {
  const img = document.getElementById('confEscolaLogoPreview');
  const statusEl = document.getElementById('confEscolaLogoStatus');
  const btnRemover = document.getElementById('btnRemoverLogo');

  if (!usarEmblema && logoSrc && logoSrc.trim() && !logoSrc.includes('emblema-mocambique.png')) {
    if (img) img.src = logoSrc;
    const galeria = (typeof window.obterGaleriaLogosEscola === 'function') ? window.obterGaleriaLogosEscola() : [];
    const item = galeria.find(g => g.url === logoSrc);
    if (statusEl) statusEl.textContent = item?.nome ? `Logótipo: ${item.nome}` : 'Logótipo Próprio Activo';
    if (btnRemover) btnRemover.style.display = 'inline-block';
  } else {
    if (img) img.src = 'img/emblema-mocambique.png';
    if (statusEl) statusEl.textContent = 'Emblema Nacional (Padrão Oficial)';
    if (btnRemover) btnRemover.style.display = 'none';
  }
};

document.getElementById('formEscolaInfo')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const body = {
      nome: document.getElementById('confEscolaNome').value,
      tipo_escola: document.getElementById('confEscolaTipo')?.value || 'S',
      ano_letivo_ativo: document.getElementById('confEscolaAnoLetivo').value,
      trimestre_ativo: document.getElementById('confEscolaTrimestreAtivo').value,
      publicacao_notas_trimestre: document.getElementById('confEscolaPublicacaoNotas')?.value || 'TODOS',
      telefone: document.getElementById('confEscolaTelefone').value,
      email: document.getElementById('confEscolaEmail').value,
      director_nome: document.getElementById('confEscolaDirector').value,
      dap_nome: document.getElementById('confEscolaDAP').value,
      chefe_secretaria_nome: document.getElementById('confEscolaChefeSec').value,
      provincia: document.getElementById('confEscolaProvincia').value,
      distrito: document.getElementById('confEscolaDistrito').value,
      usar_emblema_nacional: document.getElementById('confEscolaEmblema').checked,
      logo_url: document.getElementById('confEscolaLogoFinalValue')?.value || '',
      galeria_logos: window.obterGaleriaLogosEscola()
    };
    const res = await apiFetch('/api/v1/escola-admin/info', {
      method: 'PUT',
      body: JSON.stringify(body)
    });
    if (res.success) {
      if (state.tenant) {
        state.tenant.publicacao_notas_trimestre = body.publicacao_notas_trimestre;
        state.tenant.permitir_visualizacao_notas = body.publicacao_notas_trimestre !== 'NENHUM';
        if (typeof atualizarBotaoToggleNotasDap === 'function') {
          atualizarBotaoToggleNotasDap(body.publicacao_notas_trimestre, state.tenant.permitir_visualizacao_notas);
        }
      }
      await carregarEscolaETurmas();
      alert('Configurações da escola e logótipo oficial actualizados com sucesso!');
    }
  } catch (err) {
    alert('Erro ao actualizar dados da escola');
  }
});


