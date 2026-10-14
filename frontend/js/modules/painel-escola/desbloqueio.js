/**
 * SIGE - PAINEL-ESCOLA | Desbloqueio de Trimestres & Calendarização Oficial
 * Ficheiro de código independente do menu: desbloqueio.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */

function alternarModoCalendarizacaoUI(modo) {
  const painelAuto = document.getElementById('painelCalendarizacaoAutomatica');
  const painelSempre = document.getElementById('painelCalendarizacaoSempre');
  const painelDatas = document.getElementById('painelTrimestresDatas');
  const badgeModo = document.getElementById('badgeModoAtivo');

  if (painelAuto) painelAuto.style.display = modo === 'AUTOMATICO' ? 'block' : 'none';
  if (painelSempre) painelSempre.style.display = modo === 'SEMPRE' ? 'block' : 'none';
  if (painelDatas) painelDatas.style.display = modo === 'SEMPRE' ? 'none' : 'block';

  if (badgeModo) {
    if (modo === 'AUTOMATICO') {
      badgeModo.className = 'badge bg-success';
      badgeModo.textContent = 'Modo: Automático (Duração)';
    } else if (modo === 'SEMPRE') {
      badgeModo.className = 'badge bg-warning text-dark';
      badgeModo.textContent = 'Modo: Permitir Sempre';
    } else {
      badgeModo.className = 'badge bg-primary';
      badgeModo.textContent = 'Modo: Manual (Datas)';
    }
  }
}

function calcularPrazosAutomaticosUI() {
  const dataBaseStr = document.getElementById('prazoDataBase')?.value;
  const valor = parseInt(document.getElementById('prazoValorDuracao')?.value || '4', 10);
  const tipo = document.getElementById('prazoTipoDuracao')?.value || 'SEMANAS';

  let dataBase = dataBaseStr ? new Date(dataBaseStr + 'T00:00:00') : new Date(new Date().getFullYear(), 1, 1);

  const somar = (d, v, t) => {
    const res = new Date(d);
    if (t === 'DIAS') {
      res.setDate(res.getDate() + v);
    } else if (t === 'MESES') {
      res.setMonth(res.getMonth() + v);
    } else {
      res.setDate(res.getDate() + (v * 7));
    }
    return res;
  };

  const fmt = (d) => d.toISOString().substring(0, 10);

  const t1Ini = dataBase;
  const t1Fim = somar(t1Ini, valor, tipo);

  const t2Ini = new Date(t1Fim);
  t2Ini.setDate(t2Ini.getDate() + 1);
  const t2Fim = somar(t2Ini, valor, tipo);

  const t3Ini = new Date(t2Fim);
  t3Ini.setDate(t3Ini.getDate() + 1);
  const t3Fim = somar(t3Ini, valor, tipo);

  const setVal = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.value = val;
  };

  setVal('prazoT1Inicio', fmt(t1Ini));
  setVal('prazoT1Fim', fmt(t1Fim));
  setVal('prazoT2Inicio', fmt(t2Ini));
  setVal('prazoT2Fim', fmt(t2Fim));
  setVal('prazoT3Inicio', fmt(t3Ini));
  setVal('prazoT3Fim', fmt(t3Fim));
}

async function prepararDesbloqueioTrimestre() {
  try {
    const [turmasRes, profsRes] = await Promise.all([
      apiFetch('/api/v1/escola-admin/turmas'),
      apiFetch('/api/v1/professores')
    ]);

    const selectTurma = document.getElementById('desbloqueioTurma');
    if (selectTurma) {
      selectTurma.innerHTML = (turmasRes.data || []).map(t => `<option value="${t.id}">${t.nome} (${t.grau_ano})</option>`).join('');
    }

    const selectProf = document.getElementById('desbloqueioProfessor');
    if (selectProf) {
      selectProf.innerHTML = '<option value="">(Todos os Docentes da Turma)</option>' +
        (profsRes.data || []).map(p => `<option value="${p.id}">${p.nome}</option>`).join('');
    }

    await Promise.all([
      carregarPrazosTrimestrais(),
      carregarAutorizacoesDesbloqueio()
    ]);
  } catch (err) {
    console.warn('Erro ao preparar tela de desbloqueio:', err);
  }
}

async function carregarPrazosTrimestrais() {
  try {
    const res = await apiFetch('/api/v1/notas/prazos-trimestres');
    if (res.success && res.data) {
      const p = res.data;
      const modo = p.modo_calendarizacao || 'MANUAL';

      const selectModo = document.getElementById('prazoModoSelect');
      if (selectModo) selectModo.value = modo;
      alternarModoCalendarizacaoUI(modo);

      const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.value = val ? val.substring(0, 10) : '';
      };
      const setCheck = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.checked = !!val;
      };

      setVal('prazoDataBase', p.data_base_automatica);
      setVal('prazoValorDuracao', p.valor_duracao_automatica || 4);
      if (document.getElementById('prazoTipoDuracao')) {
        document.getElementById('prazoTipoDuracao').value = p.tipo_duracao_automatica || 'SEMANAS';
      }

      setVal('prazoT1Inicio', p.data_inicio_t1);
      setVal('prazoT1Fim', p.data_fim_t1);
      setVal('prazoT2Inicio', p.data_inicio_t2);
      setVal('prazoT2Fim', p.data_fim_t2);
      setVal('prazoT3Inicio', p.data_inicio_t3);
      setVal('prazoT3Fim', p.data_fim_t3);

      setCheck('prazoT1Sempre', p.permitir_sempre_t1);
      setCheck('prazoT2Sempre', p.permitir_sempre_t2);
      setCheck('prazoT3Sempre', p.permitir_sempre_t3);

      // Renderizar badges de status por trimestre
      if (res.prazos) {
        const renderStatusBadge = (idEl, info) => {
          const el = document.getElementById(idEl);
          if (!el || !info) return;
          let badge = '';
          if (info.sempre || modo === 'SEMPRE') {
            badge = '<span class="badge bg-success-subtle text-success border border-success mt-1"><i class="bi bi-unlock me-1"></i>Sempre Permitido</span>';
          } else if (info.motivo === 'FUTURO') {
            badge = `<span class="badge bg-secondary mt-1"><i class="bi bi-clock me-1"></i>Não Iniciado (Disponível a partir de ${info.inicio})</span>`;
          } else if (info.motivo === 'EXPIRADO') {
            badge = `<span class="badge bg-danger mt-1"><i class="bi bi-lock me-1"></i>Prazo Expirado (Fechado em ${info.fim})</span>`;
          } else if (info.aberto) {
            badge = `<span class="badge bg-success mt-1"><i class="bi bi-check-circle me-1"></i>Aberto para Lançamento (Até ${info.fim || 'final'})</span>`;
          } else {
            badge = '<span class="badge bg-light text-muted border mt-1">Datas Não Definidas</span>';
          }
          el.innerHTML = badge;
        };

        renderStatusBadge('statusT1Msg', res.prazos['1_TRIMESTRE']);
        renderStatusBadge('statusT2Msg', res.prazos['2_TRIMESTRE']);
        renderStatusBadge('statusT3Msg', res.prazos['3_TRIMESTRE']);
      }
    }
  } catch (err) {
    console.warn('Erro ao carregar prazos trimestrais:', err);
  }
}

document.getElementById('formPrazosTrimestrais')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const modo = document.getElementById('prazoModoSelect')?.value || 'MANUAL';
    const body = {
      modo_calendarizacao: modo,
      data_base_automatica: document.getElementById('prazoDataBase')?.value || null,
      valor_duracao_automatica: Number(document.getElementById('prazoValorDuracao')?.value || 4),
      tipo_duracao_automatica: document.getElementById('prazoTipoDuracao')?.value || 'SEMANAS',
      data_inicio_t1: document.getElementById('prazoT1Inicio')?.value || null,
      data_fim_t1: document.getElementById('prazoT1Fim')?.value || null,
      data_inicio_t2: document.getElementById('prazoT2Inicio')?.value || null,
      data_fim_t2: document.getElementById('prazoT2Fim')?.value || null,
      data_inicio_t3: document.getElementById('prazoT3Inicio')?.value || null,
      data_fim_t3: document.getElementById('prazoT3Fim')?.value || null,
      permitir_sempre_t1: document.getElementById('prazoT1Sempre')?.checked || false,
      permitir_sempre_t2: document.getElementById('prazoT2Sempre')?.checked || false,
      permitir_sempre_t3: document.getElementById('prazoT3Sempre')?.checked || false,
    };

    const res = await apiFetch('/api/v1/notas/prazos-trimestres', {
      method: 'POST',
      body: JSON.stringify(body)
    });

    if (res.success) {
      alert(res.message || 'Calendário oficial de prazos de lançamento salvo com sucesso!');
      await carregarPrazosTrimestrais();
    } else {
      alert(res.message || 'Erro ao salvar prazos trimestrais');
    }
  } catch (err) {
    alert(err.message || 'Erro ao salvar prazos trimestrais');
  }
});

async function carregarAutorizacoesDesbloqueio() {
  const tbody = document.getElementById('tabelaAutorizacoesDesbloqueio');
  if (!tbody) return;
  try {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center py-3 text-muted"><div class="spinner-border spinner-border-sm me-2"></div>A carregar autorizações...</td></tr>';
    const res = await apiFetch('/api/v1/notas/autorizacoes');
    if (res.success && Array.isArray(res.data) && res.data.length > 0) {
      tbody.innerHTML = res.data.map(a => {
        const agora = new Date();
        const expiraEm = a.data_expiracao ? new Date(a.data_expiracao) : null;
        const expirada = a.expirada || (expiraEm && expiraEm < agora);

        const statusBadge = expirada
          ? '<span class="badge bg-secondary">Expirada</span>'
          : '<span class="badge bg-success">Activa</span>';
        
        const dataCriacao = a.created_at ? new Date(a.created_at).toLocaleString('pt-MZ') : '-';
        const dataExp = expiraEm ? expiraEm.toLocaleString('pt-MZ') : '-';
        const profNome = a.professor_nome || (a.professor ? (a.professor.usuario?.nome || a.professor.nome) : '(Todos os Docentes da Turma)');
        const autorNome = a.autorizado_por || 'Direcção / Secretaria';
        const turmaNome = a.turma_nome || (a.turma?.nome ? `${a.turma.nome} (${a.turma.grau_ano || ''})` : 'Turma');
        const trimLabel = a.periodo === '1_TRIMESTRE' ? '1º Trimestre' : (a.periodo === '2_TRIMESTRE' ? '2º Trimestre' : (a.periodo === '3_TRIMESTRE' ? '3º Trimestre' : a.periodo));

        return `
          <tr>
            <td><strong class="text-primary">${turmaNome}</strong></td>
            <td>${profNome}</td>
            <td><span class="badge bg-light text-dark border">${trimLabel}</span></td>
            <td>${autorNome}</td>
            <td>${dataCriacao}</td>
            <td>
              <div>${a.motivo || 'Autorizado'}</div>
              <small class="text-muted">Expira em: ${dataExp}</small>
            </td>
            <td>${statusBadge}</td>
            <td class="text-end">
              <button class="btn btn-outline-danger btn-sm" onclick="revogarAutorizacaoDesbloqueio('${a.id}')" title="Revogar autorização">
                <i class="bi bi-trash"></i>
              </button>
            </td>
          </tr>
        `;
      }).join('');
    } else {
      tbody.innerHTML = '<tr><td colspan="8" class="text-center py-3 text-muted">Nenhuma autorização de desbloqueio registada de momento.</td></tr>';
    }
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center py-3 text-danger">Erro ao carregar autorizações de desbloqueio.</td></tr>';
  }
}

async function revogarAutorizacaoDesbloqueio(id) {
  if (!confirm('Deseja realmente revogar esta autorização de desbloqueio?')) return;
  try {
    const res = await apiFetch(`/api/v1/notas/autorizacoes/${id}`, { method: 'DELETE' });
    if (res.success) {
      alert('Autorização revogada com sucesso!');
      carregarAutorizacoesDesbloqueio();
    } else {
      alert(res.message || 'Erro ao revogar autorização');
    }
  } catch (err) {
    alert(err.message || 'Erro ao revogar autorização');
  }
}

document.getElementById('formAutorizarDesbloqueio')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const body = {
      turma_id: document.getElementById('desbloqueioTurma').value,
      professor_id: document.getElementById('desbloqueioProfessor').value || undefined,
      periodo: document.getElementById('desbloqueioTrimestre').value,
      duracao_horas: Number(document.getElementById('desbloqueioHoras').value),
      motivo: document.getElementById('desbloqueioMotivo').value
    };

    const res = await apiFetch('/api/v1/notas/autorizar-desbloqueio', {
      method: 'POST',
      body: JSON.stringify(body)
    });

    if (res.success) {
      alert('Autorização de desbloqueio concedida com sucesso!');
      document.getElementById('desbloqueioMotivo').value = '';
      carregarAutorizacoesDesbloqueio();
    }
  } catch (err) {
    alert(err.message || 'Erro ao autorizar desbloqueio');
  }
});

// Exposição global
window.alternarModoCalendarizacaoUI = alternarModoCalendarizacaoUI;
window.calcularPrazosAutomaticosUI = calcularPrazosAutomaticosUI;
window.carregarPrazosTrimestrais = carregarPrazosTrimestrais;
window.carregarAutorizacoesDesbloqueio = carregarAutorizacoesDesbloqueio;
window.revogarAutorizacaoDesbloqueio = revogarAutorizacaoDesbloqueio;
window.prepararDesbloqueioTrimestre = prepararDesbloqueioTrimestre;
