/**
 * SIGE - PAINEL-ESCOLA | Desbloqueio de Trimestres
 * Ficheiro de código independente do menu: desbloqueio.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
// ==================== 12. DESBLOQUEIO DE TRIMESTRE & CALENDÁRIO DE PRAZOS ====================
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

    // Carregar calendário oficial de prazos e lista de autorizações activas
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
      const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.value = val ? val.substring(0, 10) : '';
      };
      setVal('prazoT1Inicio', p.data_inicio_t1);
      setVal('prazoT1Fim', p.data_fim_t1);
      setVal('prazoT2Inicio', p.data_inicio_t2);
      setVal('prazoT2Fim', p.data_fim_t2);
      setVal('prazoT3Inicio', p.data_inicio_t3);
      setVal('prazoT3Fim', p.data_fim_t3);
    }
  } catch (err) {
    console.warn('Erro ao carregar prazos trimestrais:', err);
  }
}

document.getElementById('formPrazosTrimestrais')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const body = {
      data_inicio_t1: document.getElementById('prazoT1Inicio')?.value || null,
      data_fim_t1: document.getElementById('prazoT1Fim')?.value || null,
      data_inicio_t2: document.getElementById('prazoT2Inicio')?.value || null,
      data_fim_t2: document.getElementById('prazoT2Fim')?.value || null,
      data_inicio_t3: document.getElementById('prazoT3Inicio')?.value || null,
      data_fim_t3: document.getElementById('prazoT3Fim')?.value || null
    };

    const res = await apiFetch('/api/v1/notas/prazos-trimestres', {
      method: 'POST',
      body: JSON.stringify(body)
    });

    if (res.success) {
      alert('Calendário oficial de prazos de lançamento salvo com sucesso!');
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
        const profNome = a.professor ? (a.professor.usuario?.nome || a.professor.nome || 'Docente') : '<em class="text-muted">(Toda a Turma)</em>';
        const autorNome = a.autorizado_por || a.autorizador?.nome || 'Direcção / DAP';
        const turmaNome = a.turma?.nome ? `${a.turma.nome} (${a.turma.grau_ano || ''})` : 'Turma';
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

