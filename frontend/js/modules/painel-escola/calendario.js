async function carregarEventosCalendario() {
  const tbody = document.getElementById('tabelaEventosCalendario');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar calendário...</td></tr>';
  const tri = document.getElementById('filtroTrimestreCalendario')?.value || '';
  const tipo = document.getElementById('filtroTipoCalendario')?.value || '';
  let url = '/api/v1/documentos/calendario/?';
  if (tri) url += `trimestre=${tri}&`;
  if (tipo) url += `tipo=${tipo}&`;
  try {
    const res = await apiFetch(url);
    const lista = res?.results || res?.data || res || [];
    if (!Array.isArray(lista) || lista.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">Nenhum evento registado no calendário lectivo.</td></tr>';
      return;
    }
    const role = state.user?.role || '';
    const podeAprovar = ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'].includes(role);
    let html = '';
    lista.forEach(ev => {
      const dt = ev.data_inicio + (ev.data_fim ? ' até ' + ev.data_fim : '');
      const badgeStatus = ev.status_aprovacao === 'APROVADO_DIRECTOR'
        ? '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Aprovado pela Direcção</span>'
        : '<span class="badge bg-warning text-dark"><i class="bi bi-hourglass-split me-1"></i>Proposto pelo DAP</span>';
      let btnAprovar = '';
      if (podeAprovar && ev.status_aprovacao !== 'APROVADO_DIRECTOR') {
        btnAprovar = `<button class="btn btn-sm btn-outline-success py-0 px-2" onclick="aprovarEventoCalendario('${ev.id}')"><i class="bi bi-check2"></i> Aprovar</button>`;
      }
      html += `<tr>
        <td class="ps-3 fw-semibold">${escapeHtml(dt)}</td>
        <td><strong>${escapeHtml(ev.titulo)}</strong><br><small class="text-muted">${escapeHtml(ev.descricao || '')}</small></td>
        <td><span class="badge bg-light text-dark border">${escapeHtml(ev.tipo_display || ev.tipo)}</span></td>
        <td>${escapeHtml(ev.trimestre || 'Geral')}</td>
        <td>${badgeStatus}</td>
        <td class="text-end pe-3">${btnAprovar}</td>
      </tr>`;
    });
    tbody.innerHTML = html;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-danger">Erro ao carregar calendário.</td></tr>';
  }
}

async function aprovarEventoCalendario(id) {
  try {
    const res = await apiFetch(`/api/v1/documentos/calendario/${id}/aprovar/`, { method: 'POST' });
    if (res && res.success !== false) {
      mostrarToast('Evento do calendário aprovado oficialmente com sucesso!', 'success');
      carregarEventosCalendario();
    }
  } catch (e) {
    mostrarToast('Falha ao aprovar evento: ' + e.message, 'danger');
  }
}

function modalNovoEventoCalendario() {
  const modalHtml = `
    <div class="modal fade" id="modalAddCalendario" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header bg-primary text-white">
            <h5 class="modal-title"><i class="bi bi-calendar-plus me-2"></i>Propor Evento no Calendário</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label fw-semibold">Título do Evento</label>
              <input type="text" id="calTitulo" class="form-control" placeholder="Ex: Provas Trimestrais de ACS">
            </div>
            <div class="row g-2 mb-3">
              <div class="col-6">
                <label class="form-label fw-semibold">Tipo</label>
                <select id="calTipo" class="form-select">
                  <option value="AVALIACAO_TESTE">Avaliação / Teste</option>
                  <option value="EXAME">Exame</option>
                  <option value="CONSELHO_TURMA">Conselho de Turma</option>
                  <option value="FERIADO_PAUSA">Feriado / Pausa</option>
                  <option value="REUNIAO_ENCARREGADOS">Reunião de Encarregados</option>
                  <option value="EVENTO_ESCOLAR">Evento Cultural</option>
                </select>
              </div>
              <div class="col-6">
                <label class="form-label fw-semibold">Trimestre</label>
                <select id="calTrimestre" class="form-select">
                  <option value="1_TRIMESTRE">1º Trimestre</option>
                  <option value="2_TRIMESTRE">2º Trimestre</option>
                  <option value="3_TRIMESTRE">3º Trimestre</option>
                  <option value="GERAL">Geral</option>
                </select>
              </div>
            </div>
            <div class="row g-2 mb-3">
              <div class="col-6">
                <label class="form-label fw-semibold">Data de Início</label>
                <input type="date" id="calDataInicio" class="form-control">
              </div>
              <div class="col-6">
                <label class="form-label fw-semibold">Data de Fim (Opcional)</label>
                <input type="date" id="calDataFim" class="form-control">
              </div>
            </div>
            <div class="mb-3">
              <label class="form-label fw-semibold">Descrição / Orientações</label>
              <textarea id="calDescricao" class="form-control" rows="2" placeholder="Notas explicativas..."></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
            <button type="button" class="btn btn-primary" onclick="salvarEventoCalendario()">Salvar Evento</button>
          </div>
        </div>
      </div>
    </div>
  `;
  const el = document.getElementById('modalAddCalendario');
  if (el) el.remove();
  document.body.insertAdjacentHTML('beforeend', modalHtml);
  const modal = new bootstrap.Modal(document.getElementById('modalAddCalendario'));
  modal.show();
}

async function salvarEventoCalendario() {
  const titulo = document.getElementById('calTitulo')?.value;
  const tipo = document.getElementById('calTipo')?.value;
  const trimestre = document.getElementById('calTrimestre')?.value;
  const data_inicio = document.getElementById('calDataInicio')?.value;
  const data_fim = document.getElementById('calDataFim')?.value || null;
  const descricao = document.getElementById('calDescricao')?.value || '';
  if (!titulo || !data_inicio) {
    mostrarToast('Preencha o título e a data de início.', 'warning');
    return;
  }
  try {
    const res = await apiFetch('/api/v1/documentos/calendario/', {
      method: 'POST',
      body: JSON.stringify({ titulo, tipo, trimestre, data_inicio, data_fim, descricao })
    });
    if (res && res.success !== false) {
      mostrarToast('Evento adicionado ao calendário!', 'success');
      bootstrap.Modal.getInstance(document.getElementById('modalAddCalendario'))?.hide();
      carregarEventosCalendario();
    }
  } catch (e) {
    mostrarToast('Erro ao salvar evento: ' + e.message, 'danger');
  }
}

if (typeof carregarEventosCalendario === 'function') {
  carregarEventosCalendario();
}
