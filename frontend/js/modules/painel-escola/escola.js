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

      // Logótipo da Escola
      const logoVal = e.logo_url || e.logo_base64 || '';
      const finalLogoInput = document.getElementById('confEscolaLogoFinalValue');
      if (finalLogoInput) finalLogoInput.value = logoVal;
      const urlInput = document.getElementById('confEscolaLogoUrl');
      if (urlInput) urlInput.value = logoVal.startsWith('data:') ? '' : logoVal;
      atualizarVisualizacaoLogo(logoVal, e.usar_emblema_nacional);

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

