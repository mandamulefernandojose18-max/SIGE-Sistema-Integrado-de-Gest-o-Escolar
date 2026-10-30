import os

pages_dir = r'd:\SIGE\frontend\pages\painel-escola'
js_dir = r'd:\SIGE\frontend\js\modules\painel-escola'

os.makedirs(pages_dir, exist_ok=True)
os.makedirs(js_dir, exist_ok=True)

# 1. Calendário Escolar
calendario_html = """<section id="view-calendario" class="modulo-view p-3 p-md-4">
  <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 pb-2 border-bottom">
    <div>
      <h3 class="fw-bold mb-1"><i class="bi bi-calendar3 text-primary me-2"></i>Calendário Escolar & Avaliações</h3>
      <p class="text-muted mb-0 small">Controlo oficial de trimestres, prazos de provas, exames, conselhos de turma e feriados lectivos.</p>
    </div>
    <div class="d-flex gap-2">
      <button class="btn btn-primary btn-sm" id="btnNovoEventoCalendario" onclick="modalNovoEventoCalendario()">
        <i class="bi bi-plus-circle me-1"></i> Propor Novo Evento
      </button>
    </div>
  </div>

  <div class="card border-0 shadow-sm mb-4">
    <div class="card-body p-3">
      <div class="row g-2 align-items-center">
        <div class="col-md-4">
          <label class="form-label small fw-semibold text-muted mb-1">Filtrar por Trimestre</label>
          <select id="filtroTrimestreCalendario" class="form-select form-select-sm" onchange="carregarEventosCalendario()">
            <option value="">-- Todos os Períodos --</option>
            <option value="1_TRIMESTRE">1º Trimestre</option>
            <option value="2_TRIMESTRE">2º Trimestre</option>
            <option value="3_TRIMESTRE">3º Trimestre</option>
            <option value="GERAL">Geral / Todo o Ano</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold text-muted mb-1">Tipo de Evento</label>
          <select id="filtroTipoCalendario" class="form-select form-select-sm" onchange="carregarEventosCalendario()">
            <option value="">-- Todos os Tipos --</option>
            <option value="AVALIACAO_TESTE">Avaliação / Teste (ACS / ACP)</option>
            <option value="EXAME">Época de Exames</option>
            <option value="CONSELHO_TURMA">Conselho de Turma</option>
            <option value="FERIADO_PAUSA">Feriado / Pausa Lectiva</option>
            <option value="REUNIAO_ENCARREGADOS">Reunião de Encarregados</option>
            <option value="EVENTO_ESCOLAR">Evento Escolar / Cultural</option>
          </select>
        </div>
        <div class="col-md-4 text-md-end pt-3">
          <button class="btn btn-outline-secondary btn-sm" onclick="carregarEventosCalendario()">
            <i class="bi bi-arrow-clockwise me-1"></i> Atualizar
          </button>
        </div>
      </div>
    </div>
  </div>

  <div class="card border-0 shadow-sm">
    <div class="card-body p-0">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light small text-uppercase text-muted">
            <tr>
              <th class="ps-3">Data / Período</th>
              <th>Título do Evento</th>
              <th>Categoria</th>
              <th>Trimestre</th>
              <th>Estado de Validação</th>
              <th class="text-end pe-3">Acções</th>
            </tr>
          </thead>
          <tbody id="tabelaEventosCalendario">
            <tr><td colspan="6" class="text-center py-4 text-muted"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar eventos...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</section>"""

calendario_js = """async function carregarEventosCalendario() {
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
"""

with open(os.path.join(pages_dir, 'calendario.html'), 'w', encoding='utf-8') as f:
    f.write(calendario_html)
with open(os.path.join(js_dir, 'calendario.js'), 'w', encoding='utf-8') as f:
    f.write(calendario_js)
print('1. Calendario created successfully')

# 2. Auditoria
auditoria_html = """<section id="view-auditoria" class="modulo-view p-3 p-md-4">
  <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 pb-2 border-bottom">
    <div>
      <h3 class="fw-bold mb-1"><i class="bi bi-shield-lock-fill text-warning me-2"></i>Auditoria & Trilha de Segurança</h3>
      <p class="text-muted mb-0 small">Registo cronológico rigoroso de quem alterou notas, pagamentos, matrículas e despesas no sistema.</p>
    </div>
    <button class="btn btn-outline-secondary btn-sm" onclick="carregarTrilhaAuditoria()">
      <i class="bi bi-arrow-clockwise me-1"></i> Actualizar Trilha
    </button>
  </div>

  <div class="card border-0 shadow-sm mb-4">
    <div class="card-body p-3">
      <div class="row g-2 align-items-center">
        <div class="col-md-4">
          <label class="form-label small fw-semibold text-muted mb-1">Módulo / Entidade</label>
          <select id="filtroEntidadeAuditoria" class="form-select form-select-sm" onchange="carregarTrilhaAuditoria()">
            <option value="">-- Todos os Módulos --</option>
            <option value="NOTA">Notas & Avaliações</option>
            <option value="PAGAMENTO">Pagamentos & Propinas</option>
            <option value="MATRICULA">Alunos & Matrículas</option>
            <option value="DESPESA">Receitas & Despesas</option>
            <option value="TRANSFERENCIA">Transferências & Anulações</option>
            <option value="CALENDARIO">Calendário Escolar</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold text-muted mb-1">Operação</label>
          <select id="filtroAcaoAuditoria" class="form-select form-select-sm" onchange="carregarTrilhaAuditoria()">
            <option value="">-- Todas as Acções --</option>
            <option value="CRIACAO">Criação / Inserção</option>
            <option value="EDICAO">Edição / Alteração</option>
            <option value="VALIDACAO">Validação Pedagógica</option>
            <option value="APROVACAO">Aprovação da Direcção</option>
            <option value="ELIMINACAO">Eliminação / Cancelamento</option>
          </select>
        </div>
      </div>
    </div>
  </div>

  <div class="card border-0 shadow-sm">
    <div class="card-body p-0">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light small text-uppercase text-muted">
            <tr>
              <th class="ps-3">Data & Hora</th>
              <th>Utilizador</th>
              <th>Perfil / Cargo</th>
              <th>Entidade</th>
              <th>Operação</th>
              <th class="pe-3">Detalhes do Evento</th>
            </tr>
          </thead>
          <tbody id="tabelaTrilhaAuditoria">
            <tr><td colspan="6" class="text-center py-4 text-muted"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar trilha de auditoria...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</section>"""

auditoria_js = """async function carregarTrilhaAuditoria() {
  const tbody = document.getElementById('tabelaTrilhaAuditoria');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar auditoria...</td></tr>';
  const ent = document.getElementById('filtroEntidadeAuditoria')?.value || '';
  const acao = document.getElementById('filtroAcaoAuditoria')?.value || '';
  let url = '/api/v1/auth/auditoria/?';
  if (ent) url += `entidade=${ent}&`;
  if (acao) url += `acao=${acao}&`;
  try {
    const res = await apiFetch(url);
    const lista = res?.data || res || [];
    if (!Array.isArray(lista) || lista.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">Nenhum registo de auditoria encontrado.</td></tr>';
      return;
    }
    let html = '';
    lista.forEach(item => {
      const dt = new Date(item.created_at).toLocaleString('pt-PT');
      const badgeAcao = {
        'CRIACAO': '<span class="badge bg-success">Criação</span>',
        'EDICAO': '<span class="badge bg-primary">Edição</span>',
        'VALIDACAO': '<span class="badge bg-info text-dark">Validação</span>',
        'APROVACAO': '<span class="badge bg-success">Aprovação</span>',
        'ELIMINACAO': '<span class="badge bg-danger">Eliminação</span>',
      }[item.acao] || `<span class="badge bg-secondary">${escapeHtml(item.acao)}</span>`;

      html += `<tr>
        <td class="ps-3 small text-muted">${escapeHtml(dt)}</td>
        <td><strong>${escapeHtml(item.usuario_nome || 'Sistema')}</strong></td>
        <td><span class="badge bg-light text-dark border">${escapeHtml(item.usuario_role || '-')}</span></td>
        <td><span class="fw-semibold text-dark">${escapeHtml(item.entidade)}</span></td>
        <td>${badgeAcao}</td>
        <td class="pe-3 small">${escapeHtml(item.descricao)}</td>
      </tr>`;
    });
    tbody.innerHTML = html;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-danger">Erro ao carregar auditoria.</td></tr>';
  }
}

if (typeof carregarTrilhaAuditoria === 'function') {
  carregarTrilhaAuditoria();
}
"""

with open(os.path.join(pages_dir, 'auditoria.html'), 'w', encoding='utf-8') as f:
    f.write(auditoria_html)
with open(os.path.join(js_dir, 'auditoria.js'), 'w', encoding='utf-8') as f:
    f.write(auditoria_js)
print('2. Auditoria created successfully')

# 3. Presenças & Faltas dos Alunos
presencas_html = """<section id="view-presencas" class="modulo-view p-3 p-md-4">
  <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 pb-2 border-bottom">
    <div>
      <h3 class="fw-bold mb-1"><i class="bi bi-person-check-fill text-success me-2"></i>Presenças & Assiduidade dos Alunos</h3>
      <p class="text-muted mb-0 small">Registo oficial de presenças e faltas justificadas/injustificadas por aula e turma.</p>
    </div>
  </div>

  <div class="card border-0 shadow-sm mb-4">
    <div class="card-body p-3">
      <div class="row g-2 align-items-center">
        <div class="col-md-4">
          <label class="form-label small fw-semibold text-muted mb-1">Selecionar Turma</label>
          <select id="presencaSelectTurma" class="form-select form-select-sm" onchange="carregarAlunosParaPresenca()">
            <option value="">-- Selecione a Turma --</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label small fw-semibold text-muted mb-1">Data da Aula</label>
          <input type="date" id="presencaData" class="form-control form-control-sm" onchange="carregarAlunosParaPresenca()">
        </div>
        <div class="col-md-4 text-md-end pt-3">
          <button class="btn btn-primary btn-sm" onclick="salvarPresencasLote()">
            <i class="bi bi-save me-1"></i> Salvar Assiduidade
          </button>
        </div>
      </div>
    </div>
  </div>

  <div class="card border-0 shadow-sm">
    <div class="card-body p-0">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light small text-uppercase text-muted">
            <tr>
              <th class="ps-3" style="width: 50px;">#</th>
              <th>Matrícula</th>
              <th>Nome Completo do Aluno</th>
              <th class="text-center" style="width: 320px;">Estado de Assiduidade</th>
              <th class="pe-3">Observação</th>
            </tr>
          </thead>
          <tbody id="tabelaListaPresencas">
            <tr><td colspan="5" class="text-center py-4 text-muted">Selecione uma turma para registar presenças.</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</section>"""

presencas_js = """async function initPresencasModulo() {
  const dtInput = document.getElementById('presencaData');
  if (dtInput && !dtInput.value) {
    dtInput.value = new Date().toISOString().split('T')[0];
  }
  const selTurma = document.getElementById('presencaSelectTurma');
  if (selTurma && selTurma.options.length <= 1) {
    const turmas = state.turmasList || state.todasTurmas || [];
    let opts = '<option value="">-- Selecione a Turma --</option>';
    turmas.forEach(t => {
      opts += `<option value="${t.id}">${escapeHtml(t.grau_ano || '')} - ${escapeHtml(t.nome)}</option>`;
    });
    selTurma.innerHTML = opts;
  }
}

async function carregarAlunosParaPresenca() {
  const turmaId = document.getElementById('presencaSelectTurma')?.value;
  const tbody = document.getElementById('tabelaListaPresencas');
  if (!turmaId || !tbody) {
    if (tbody) tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-muted">Selecione uma turma para registar presenças.</td></tr>';
    return;
  }
  tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-muted"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar lista de alunos...</td></tr>';
  const data = document.getElementById('presencaData')?.value || new Date().toISOString().split('T')[0];
  try {
    const [resAlunos, resPres] = await Promise.all([
      apiFetch(`/api/v1/alunos/?turma_id=${turmaId}&status=ATIVO`),
      apiFetch(`/api/v1/alunos/presencas/?turma_id=${turmaId}&data=${data}`)
    ]);
    const alunos = resAlunos?.data || resAlunos?.results || resAlunos || [];
    const presencas = resPres?.data || resPres?.results || resPres || [];
    const mapaPres = {};
    if (Array.isArray(presencas)) {
      presencas.forEach(p => { mapaPres[p.aluno] = p; });
    }
    if (!Array.isArray(alunos) || alunos.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-muted">Nenhum aluno ativo nesta turma.</td></tr>';
      return;
    }
    let html = '';
    alunos.forEach((al, idx) => {
      const pres = mapaPres[al.id];
      const st = pres?.status || 'PRESENTE';
      const obs = pres?.observacao || '';
      html += `<tr>
        <td class="ps-3 text-muted">${idx + 1}</td>
        <td class="font-monospace small">${escapeHtml(al.matricula)}</td>
        <td class="fw-semibold">${escapeHtml(al.nome + ' ' + (al.apelido || ''))}</td>
        <td class="text-center">
          <div class="btn-group btn-group-sm" role="group">
            <input type="radio" class="btn-check" name="pres_${al.id}" id="p_p_${al.id}" value="PRESENTE" ${st === 'PRESENTE' ? 'checked' : ''}>
            <label class="btn btn-outline-success" for="p_p_${al.id}">Presente</label>
            <input type="radio" class="btn-check" name="pres_${al.id}" id="p_fj_${al.id}" value="FALTA_JUSTIFICADA" ${st === 'FALTA_JUSTIFICADA' ? 'checked' : ''}>
            <label class="btn btn-outline-warning" for="p_fj_${al.id}">F. Justif.</label>
            <input type="radio" class="btn-check" name="pres_${al.id}" id="p_fi_${al.id}" value="FALTA_INJUSTIFICADA" ${st === 'FALTA_INJUSTIFICADA' ? 'checked' : ''}>
            <label class="btn btn-outline-danger" for="p_fi_${al.id}">F. Injustif.</label>
          </div>
        </td>
        <td class="pe-3">
          <input type="text" class="form-control form-control-sm" id="obs_${al.id}" value="${escapeHtml(obs)}" placeholder="Nota...">
        </td>
      </tr>`;
    });
    tbody.innerHTML = html;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-danger">Erro ao carregar lista de assiduidade.</td></tr>';
  }
}

async function salvarPresencasLote() {
  const turmaId = document.getElementById('presencaSelectTurma')?.value;
  const data = document.getElementById('presencaData')?.value;
  if (!turmaId || !data) {
    mostrarToast('Selecione a turma e a data.', 'warning');
    return;
  }
  const radios = document.querySelectorAll('#tabelaListaPresencas input[type="radio"]:checked');
  if (!radios.length) {
    mostrarToast('Nenhum aluno na lista para salvar.', 'warning');
    return;
  }
  let salvos = 0;
  for (const r of radios) {
    const alunoId = r.name.replace('pres_', '');
    const status = r.value;
    const obs = document.getElementById(`obs_${alunoId}`)?.value || '';
    try {
      await apiFetch('/api/v1/alunos/presencas/', {
        method: 'POST',
        body: JSON.stringify({ aluno: alunoId, turma: turmaId, data, status, observacao: obs })
      });
      salvos++;
    } catch (_) {}
  }
  mostrarToast(`Assiduidade registada com sucesso (${salvos} registos)!`, 'success');
  carregarAlunosParaPresenca();
}

initPresencasModulo();
"""

with open(os.path.join(pages_dir, 'presencas.html'), 'w', encoding='utf-8') as f:
    f.write(presencas_html)
with open(os.path.join(js_dir, 'presencas.js'), 'w', encoding='utf-8') as f:
    f.write(presencas_js)
print('3. Presencas created successfully')

# 4. Horários Lectivos
horarios_html = """<section id="view-horarios" class="modulo-view p-3 p-md-4">
  <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 pb-2 border-bottom">
    <div>
      <h3 class="fw-bold mb-1"><i class="bi bi-clock-history text-primary me-2"></i>Horários Lectivos da Turma</h3>
      <p class="text-muted mb-0 small">Distribuição semanal de tempos, disciplinas, docentes e salas de aula.</p>
    </div>
  </div>

  <div class="card border-0 shadow-sm mb-4">
    <div class="card-body p-3">
      <div class="row g-2 align-items-center">
        <div class="col-md-5">
          <label class="form-label small fw-semibold text-muted mb-1">Selecionar Turma</label>
          <select id="horarioSelectTurma" class="form-select form-select-sm" onchange="carregarGradeHorarios()">
            <option value="">-- Selecione a Turma --</option>
          </select>
        </div>
      </div>
    </div>
  </div>

  <div class="card border-0 shadow-sm">
    <div class="card-body p-0">
      <div class="table-responsive">
        <table class="table table-bordered align-middle text-center mb-0">
          <thead class="table-light small text-uppercase">
            <tr>
              <th style="width: 120px;">Tempo / Hora</th>
              <th>Segunda-feira</th>
              <th>Terça-feira</th>
              <th>Quarta-feira</th>
              <th>Quinta-feira</th>
              <th>Sexta-feira</th>
            </tr>
          </thead>
          <tbody id="tabelaGradeHorario">
            <tr><td colspan="6" class="py-4 text-muted">Selecione uma turma para visualizar a grade semanal.</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</section>"""

horarios_js = """async function initHorariosModulo() {
  const selTurma = document.getElementById('horarioSelectTurma');
  if (selTurma && selTurma.options.length <= 1) {
    const turmas = state.turmasList || state.todasTurmas || [];
    let opts = '<option value="">-- Selecione a Turma --</option>';
    turmas.forEach(t => {
      opts += `<option value="${t.id}">${escapeHtml(t.grau_ano || '')} - ${escapeHtml(t.nome)}</option>`;
    });
    selTurma.innerHTML = opts;
  }
}

async function carregarGradeHorarios() {
  const turmaId = document.getElementById('horarioSelectTurma')?.value;
  const tbody = document.getElementById('tabelaGradeHorario');
  if (!turmaId || !tbody) {
    if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="py-4 text-muted">Selecione uma turma para visualizar a grade semanal.</td></tr>';
    return;
  }
  tbody.innerHTML = '<tr><td colspan="6" class="py-4 text-muted"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar horários...</td></tr>';
  try {
    const res = await apiFetch(`/api/v1/turmas/horarios/?turma_id=${turmaId}`);
    const lista = res?.data || res?.results || res || [];
    const tempos = [
      { t: 1, label: '1º Tempo (07:15 - 08:00)' },
      { t: 2, label: '2º Tempo (08:05 - 08:50)' },
      { t: 3, label: '3º Tempo (09:05 - 09:50)' },
      { t: 4, label: '4º Tempo (09:55 - 10:40)' },
      { t: 5, label: '5º Tempo (10:50 - 11:35)' },
      { t: 6, label: '6º Tempo (11:40 - 12:25)' },
    ];
    let html = '';
    tempos.forEach(tempo => {
      html += `<tr><td class="fw-semibold bg-light small text-start ps-3">${tempo.label}</td>`;
      for (let dia = 1; dia <= 5; dia++) {
        const item = Array.isArray(lista) ? lista.find(h => h.dia_semana === dia && h.tempo === tempo.t) : null;
        if (item) {
          html += `<td class="p-2 bg-primary bg-opacity-10 border">
            <strong class="text-primary d-block">${escapeHtml(item.disciplina_nome)}</strong>
            <small class="text-muted d-block">${escapeHtml(item.professor_nome || 'Docente')}</small>
          </td>`;
        } else {
          html += `<td class="text-muted small">-</td>`;
        }
      }
      html += '</tr>';
    });
    tbody.innerHTML = html;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="6" class="py-4 text-danger">Erro ao carregar horário lectivo.</td></tr>';
  }
}

initHorariosModulo();
"""

with open(os.path.join(pages_dir, 'horarios.html'), 'w', encoding='utf-8') as f:
    f.write(horarios_html)
with open(os.path.join(js_dir, 'horarios.js'), 'w', encoding='utf-8') as f:
    f.write(horarios_js)
print('4. Horarios created successfully')

# 5. Planos de Aula & Sumários
sumarios_html = """<section id="view-sumarios" class="modulo-view p-3 p-md-4">
  <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 pb-2 border-bottom">
    <div>
      <h3 class="fw-bold mb-1"><i class="bi bi-journal-text text-primary me-2"></i>Planos de Aula & Sumários</h3>
      <p class="text-muted mb-0 small">Supervisão pedagógica de planos de aula, sumários diários e conteúdos lecionados.</p>
    </div>
  </div>

  <div class="card border-0 shadow-sm mb-4">
    <div class="card-body p-3">
      <div class="row g-2 align-items-center">
        <div class="col-md-4">
          <label class="form-label small fw-semibold text-muted mb-1">Filtrar por Turma</label>
          <select id="sumarioSelectTurma" class="form-select form-select-sm" onchange="carregarListaSumarios()">
            <option value="">-- Todas as Turmas --</option>
          </select>
        </div>
      </div>
    </div>
  </div>

  <div class="card border-0 shadow-sm">
    <div class="card-body p-0">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light small text-uppercase text-muted">
            <tr>
              <th class="ps-3">Aula # / Data</th>
              <th>Turma & Disciplina</th>
              <th>Tema / Unidade Temática</th>
              <th>Sumário da Aula</th>
              <th>Estado Pedagógico</th>
              <th class="text-end pe-3">Validação DAP</th>
            </tr>
          </thead>
          <tbody id="tabelaListaSumarios">
            <tr><td colspan="6" class="text-center py-4 text-muted"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar sumários...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</section>"""

sumarios_js = """async function initSumariosModulo() {
  const selTurma = document.getElementById('sumarioSelectTurma');
  if (selTurma && selTurma.options.length <= 1) {
    const turmas = state.turmasList || state.todasTurmas || [];
    let opts = '<option value="">-- Todas as Turmas --</option>';
    turmas.forEach(t => {
      opts += `<option value="${t.id}">${escapeHtml(t.grau_ano || '')} - ${escapeHtml(t.nome)}</option>`;
    });
    selTurma.innerHTML = opts;
  }
  carregarListaSumarios();
}

async function carregarListaSumarios() {
  const tbody = document.getElementById('tabelaListaSumarios');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar sumários...</td></tr>';
  const turmaId = document.getElementById('sumarioSelectTurma')?.value || '';
  let url = '/api/v1/notas/planos-sumarios/?';
  if (turmaId) url += `turma_id=${turmaId}&`;
  try {
    const res = await apiFetch(url);
    const lista = res?.data || res?.results || res || [];
    if (!Array.isArray(lista) || lista.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">Nenhum sumário ou plano de aula registado.</td></tr>';
      return;
    }
    const role = state.user?.role || '';
    const isDap = ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'].includes(role);
    let html = '';
    lista.forEach(s => {
      const badgeVal = s.status_validacao === 'VALIDADO_DAP'
        ? '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Validado pelo DAP</span>'
        : '<span class="badge bg-warning text-dark"><i class="bi bi-clock me-1"></i>Pendente de Validação</span>';
      let btnValidar = '';
      if (isDap && s.status_validacao !== 'VALIDADO_DAP') {
        btnValidar = `<button class="btn btn-sm btn-outline-success py-0 px-2" onclick="validarSumarioDap('${s.id}')"><i class="bi bi-check2"></i> Validar</button>`;
      }
      html += `<tr>
        <td class="ps-3"><strong>Aula ${s.numero_aula}</strong><br><small class="text-muted">${s.data}</small></td>
        <td><strong>${escapeHtml(s.turma_nome || '')}</strong><br><span class="badge bg-light text-dark border">${escapeHtml(s.disciplina_nome || '')}</span></td>
        <td><strong>${escapeHtml(s.tema)}</strong><br><small class="text-muted">${escapeHtml(s.unidade_tematica || '')}</small></td>
        <td class="small text-truncate" style="max-width: 250px;">${escapeHtml(s.sumario)}</td>
        <td>${badgeVal}</td>
        <td class="text-end pe-3">${btnValidar}</td>
      </tr>`;
    });
    tbody.innerHTML = html;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-danger">Erro ao carregar sumários.</td></tr>';
  }
}

async function validarSumarioDap(id) {
  try {
    const res = await apiFetch(`/api/v1/notas/planos-sumarios/${id}/validar/`, { method: 'POST' });
    if (res && res.success !== false) {
      mostrarToast('Sumário validado pedagogicamente com sucesso!', 'success');
      carregarListaSumarios();
    }
  } catch (e) {
    mostrarToast('Erro ao validar sumário: ' + e.message, 'danger');
  }
}

initSumariosModulo();
"""

with open(os.path.join(pages_dir, 'sumarios.html'), 'w', encoding='utf-8') as f:
    f.write(sumarios_html)
with open(os.path.join(js_dir, 'sumarios.js'), 'w', encoding='utf-8') as f:
    f.write(sumarios_js)
print('5. Sumarios created successfully')

# 6. Ocorrências Disciplinares
ocorrencias_html = """<section id="view-ocorrencias" class="modulo-view p-3 p-md-4">
  <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 pb-2 border-bottom">
    <div>
      <h3 class="fw-bold mb-1"><i class="bi bi-exclamation-octagon-fill text-warning me-2"></i>Ocorrências Disciplinares</h3>
      <p class="text-muted mb-0 small">Registo disciplinar, acompanhamento de faltas graves e mediação pedagógica.</p>
    </div>
  </div>

  <div class="card border-0 shadow-sm">
    <div class="card-body p-0">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light small text-uppercase text-muted">
            <tr>
              <th class="ps-3">Data</th>
              <th>Aluno</th>
              <th>Gravidade</th>
              <th>Descrição do Facto</th>
              <th>Medida Tomada</th>
              <th>Estado</th>
              <th class="text-end pe-3">Homologação</th>
            </tr>
          </thead>
          <tbody id="tabelaListaOcorrencias">
            <tr><td colspan="7" class="text-center py-4 text-muted"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar ocorrências...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</section>"""

ocorrencias_js = """async function carregarListaOcorrencias() {
  const tbody = document.getElementById('tabelaListaOcorrencias');
  if (!tbody) return;
  try {
    const res = await apiFetch('/api/v1/notas/ocorrencias/');
    const lista = res?.data || res?.results || res || [];
    if (!Array.isArray(lista) || lista.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-muted">Nenhuma ocorrência disciplinar registada.</td></tr>';
      return;
    }
    const role = state.user?.role || '';
    const isDap = ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP'].includes(role);
    let html = '';
    lista.forEach(oc => {
      const badgeGrav = {
        'LEVE': '<span class="badge bg-info text-dark">Leve</span>',
        'GRAVE': '<span class="badge bg-warning text-dark">Grave</span>',
        'MUITO_GRAVE': '<span class="badge bg-danger">Muito Grave</span>',
      }[oc.gravidade] || oc.gravidade;
      const badgeSt = oc.status_validacao === 'HOMOLOGADA_DAP'
        ? '<span class="badge bg-success">Homologada pelo DAP</span>'
        : '<span class="badge bg-secondary">Aguardando Parecer</span>';
      let btnHomologar = '';
      if (isDap && oc.status_validacao !== 'HOMOLOGADA_DAP') {
        btnHomologar = `<button class="btn btn-sm btn-outline-success py-0 px-2" onclick="homologarOcorrencia('${oc.id}')"><i class="bi bi-check2"></i> Homologar</button>`;
      }
      html += `<tr>
        <td class="ps-3 small text-muted">${oc.data}</td>
        <td><strong>${escapeHtml(oc.aluno_nome)}</strong><br><small class="text-muted">${escapeHtml(oc.aluno_matricula)}</small></td>
        <td>${badgeGrav}</td>
        <td class="small" style="max-width: 250px;">${escapeHtml(oc.descricao)}</td>
        <td class="small">${escapeHtml(oc.medida_tomada || '-')}</td>
        <td>${badgeSt}</td>
        <td class="text-end pe-3">${btnHomologar}</td>
      </tr>`;
    });
    tbody.innerHTML = html;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-danger">Erro ao carregar ocorrências.</td></tr>';
  }
}

async function homologarOcorrencia(id) {
  try {
    const res = await apiFetch(`/api/v1/notas/ocorrencias/${id}/homologar/`, { method: 'POST' });
    if (res && res.success !== false) {
      mostrarToast('Ocorrência homologada pelo DAP com sucesso!', 'success');
      carregarListaOcorrencias();
    }
  } catch (e) {
    mostrarToast('Erro ao homologar ocorrência: ' + e.message, 'danger');
  }
}

carregarListaOcorrencias();
"""

with open(os.path.join(pages_dir, 'ocorrencias.html'), 'w', encoding='utf-8') as f:
    f.write(ocorrencias_html)
with open(os.path.join(js_dir, 'ocorrencias.js'), 'w', encoding='utf-8') as f:
    f.write(ocorrencias_js)
print('6. Ocorrencias created successfully')

# 7. Transferências & Anulações
transferencias_html = """<section id="view-transferencias" class="modulo-view p-3 p-md-4">
  <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 pb-2 border-bottom">
    <div>
      <h3 class="fw-bold mb-1"><i class="bi bi-arrow-left-right text-primary me-2"></i>Transferências & Anulações de Matrícula</h3>
      <p class="text-muted mb-0 small">Processamento pela Secretaria e validação/aprovação oficial exclusiva do Director da Escola.</p>
    </div>
  </div>

  <div class="card border-0 shadow-sm">
    <div class="card-body p-0">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light small text-uppercase text-muted">
            <tr>
              <th class="ps-3">Data</th>
              <th>Aluno</th>
              <th>Tipo de Processo</th>
              <th>Escola Destino / Origem</th>
              <th>Motivo</th>
              <th>Estado Oficial</th>
              <th class="text-end pe-3">Aprovação Director</th>
            </tr>
          </thead>
          <tbody id="tabelaListaTransferencias">
            <tr><td colspan="7" class="text-center py-4 text-muted"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar transferências...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</section>"""

transferencias_js = """async function carregarListaTransferencias() {
  const tbody = document.getElementById('tabelaListaTransferencias');
  if (!tbody) return;
  try {
    const res = await apiFetch('/api/v1/alunos/transferencias/');
    const lista = res?.data || res?.results || res || [];
    if (!Array.isArray(lista) || lista.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-muted">Nenhum processo de transferência ou anulação registado.</td></tr>';
      return;
    }
    const role = state.user?.role || '';
    const isDirector = ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'].includes(role);
    let html = '';
    lista.forEach(tr => {
      const badgeSt = tr.status === 'APROVADO'
        ? '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Aprovado pelo Director</span>'
        : '<span class="badge bg-warning text-dark"><i class="bi bi-hourglass-split me-1"></i>Pendente de Parecer</span>';
      let btnAprovar = '';
      if (isDirector && tr.status !== 'APROVADO') {
        btnAprovar = `<button class="btn btn-sm btn-outline-success py-0 px-2" onclick="aprovarTransferencia('${tr.id}')"><i class="bi bi-check2"></i> Homologar</button>`;
      }
      html += `<tr>
        <td class="ps-3 small text-muted">${tr.data_solicitacao}</td>
        <td><strong>${escapeHtml(tr.aluno_nome)}</strong><br><small class="text-muted">${escapeHtml(tr.aluno_matricula)}</small></td>
        <td><span class="badge bg-light text-dark border">${escapeHtml(tr.tipo)}</span></td>
        <td>${escapeHtml(tr.escola_origem_destino || '-')}</td>
        <td class="small">${escapeHtml(tr.motivo)}</td>
        <td>${badgeSt}</td>
        <td class="text-end pe-3">${btnAprovar}</td>
      </tr>`;
    });
    tbody.innerHTML = html;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-danger">Erro ao carregar processos.</td></tr>';
  }
}

async function aprovarTransferencia(id) {
  try {
    const res = await apiFetch(`/api/v1/alunos/transferencias/${id}/aprovar/`, { method: 'POST' });
    if (res && res.success !== false) {
      mostrarToast('Transferência homologada oficialmente pelo Director!', 'success');
      carregarListaTransferencias();
    }
  } catch (e) {
    mostrarToast('Erro ao homologar transferência: ' + e.message, 'danger');
  }
}

carregarListaTransferencias();
"""

with open(os.path.join(pages_dir, 'transferencias.html'), 'w', encoding='utf-8') as f:
    f.write(transferencias_html)
with open(os.path.join(js_dir, 'transferencias.js'), 'w', encoding='utf-8') as f:
    f.write(transferencias_js)
print('7. Transferencias created successfully')

# 8. Receitas & Despesas
despesas_html = """<section id="view-despesas" class="modulo-view p-3 p-md-4">
  <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 pb-2 border-bottom">
    <div>
      <h3 class="fw-bold mb-1"><i class="bi bi-wallet-fill text-danger me-2"></i>Receitas & Despesas Operacionais</h3>
      <p class="text-muted mb-0 small">Separação estrita de funções: quem regista no Finanças NÃO aprova a despesa. Aprovação exclusiva do Director.</p>
    </div>
  </div>

  <div class="card border-0 shadow-sm">
    <div class="card-body p-0">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light small text-uppercase text-muted">
            <tr>
              <th class="ps-3">Data</th>
              <th>Tipo</th>
              <th>Categoria & Descrição</th>
              <th>Valor (MZN)</th>
              <th>Forma Pagamento</th>
              <th>Estado de Aprovação</th>
              <th class="text-end pe-3">Aprovação do Director</th>
            </tr>
          </thead>
          <tbody id="tabelaListaDespesas">
            <tr><td colspan="7" class="text-center py-4 text-muted"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar transacções...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</section>"""

despesas_js = """async function carregarListaDespesas() {
  const tbody = document.getElementById('tabelaListaDespesas');
  if (!tbody) return;
  try {
    const res = await apiFetch('/api/v1/pagamentos/transacoes/');
    const lista = res?.data || res?.results || res || [];
    if (!Array.isArray(lista) || lista.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-muted">Nenhuma despesa ou receita registada.</td></tr>';
      return;
    }
    const role = state.user?.role || '';
    const isDirector = ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'].includes(role);
    let html = '';
    lista.forEach(item => {
      const badgeTipo = item.tipo === 'RECEITA'
        ? '<span class="badge bg-success">Receita</span>'
        : '<span class="badge bg-danger">Despesa</span>';
      const badgeSt = item.status_aprovacao === 'APROVADO_DIRECTOR'
        ? '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Aprovado pelo Director</span>'
        : '<span class="badge bg-warning text-dark"><i class="bi bi-hourglass-split me-1"></i>Pendente Aprovação</span>';
      let btnAprovar = '';
      if (isDirector && item.status_aprovacao !== 'APROVADO_DIRECTOR') {
        btnAprovar = `<button class="btn btn-sm btn-outline-success py-0 px-2" onclick="aprovarDespesa('${item.id}')"><i class="bi bi-check2"></i> Aprovar</button>`;
      }
      html += `<tr>
        <td class="ps-3 small text-muted">${item.data}</td>
        <td>${badgeTipo}</td>
        <td><strong>${escapeHtml(item.categoria)}</strong><br><small class="text-muted">${escapeHtml(item.descricao)}</small></td>
        <td class="fw-bold">${Number(item.valor).toLocaleString('pt-MZ', { minimumFractionDigits: 2 })} MT</td>
        <td><span class="badge bg-light text-dark border">${escapeHtml(item.forma_pagamento)}</span></td>
        <td>${badgeSt}</td>
        <td class="text-end pe-3">${btnAprovar}</td>
      </tr>`;
    });
    tbody.innerHTML = html;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-danger">Erro ao carregar despesas.</td></tr>';
  }
}

async function aprovarDespesa(id) {
  try {
    const res = await apiFetch(`/api/v1/pagamentos/transacoes/${id}/aprovar/`, { method: 'POST' });
    if (res && res.success !== false) {
      mostrarToast('Despesa aprovada oficialmente com sucesso!', 'success');
      carregarListaDespesas();
    }
  } catch (e) {
    mostrarToast('Erro ao aprovar despesa: ' + e.message, 'danger');
  }
}

carregarListaDespesas();
"""

with open(os.path.join(pages_dir, 'despesas.html'), 'w', encoding='utf-8') as f:
    f.write(despesas_html)
with open(os.path.join(js_dir, 'despesas.js'), 'w', encoding='utf-8') as f:
    f.write(despesas_js)
print('8. Despesas created successfully')

# 9. Comunicados Escolares
comunicados_html = """<section id="view-comunicados" class="modulo-view p-3 p-md-4">
  <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 pb-2 border-bottom">
    <div>
      <h3 class="fw-bold mb-1"><i class="bi bi-megaphone-fill text-primary me-2"></i>Comunicados & Avisos Oficiais</h3>
      <p class="text-muted mb-0 small">Circulares, convocações e avisos para docentes, alunos e encarregados de educação.</p>
    </div>
  </div>

  <div class="card border-0 shadow-sm">
    <div class="card-body p-0">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light small text-uppercase text-muted">
            <tr>
              <th class="ps-3">Data</th>
              <th>Título do Comunicado</th>
              <th>Público-Alvo</th>
              <th>Prioridade</th>
              <th>Estado</th>
              <th class="text-end pe-3">Validação</th>
            </tr>
          </thead>
          <tbody id="tabelaListaComunicados">
            <tr><td colspan="6" class="text-center py-4 text-muted"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar comunicados...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</section>"""

comunicados_js = """async function carregarListaComunicados() {
  const tbody = document.getElementById('tabelaListaComunicados');
  if (!tbody) return;
  try {
    const res = await apiFetch('/api/v1/documentos/comunicados/');
    const lista = res?.data || res?.results || res || [];
    if (!Array.isArray(lista) || lista.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">Nenhum comunicado escolar publicado.</td></tr>';
      return;
    }
    const role = state.user?.role || '';
    const isDirector = ['SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA'].includes(role);
    let html = '';
    lista.forEach(com => {
      const badgePrio = com.prioridade === 'URGENTE'
        ? '<span class="badge bg-danger">Urgente</span>'
        : (com.prioridade === 'IMPORTANTE' ? '<span class="badge bg-warning text-dark">Importante</span>' : '<span class="badge bg-secondary">Normal</span>');
      let btnAprovar = '';
      if (isDirector && !com.aprovado_pelo_director) {
        btnAprovar = `<button class="btn btn-sm btn-outline-success py-0 px-2" onclick="aprovarComunicado('${com.id}')"><i class="bi bi-check2"></i> Publicar</button>`;
      }
      html += `<tr>
        <td class="ps-3 small text-muted">${new Date(com.data_publicacao).toLocaleDateString('pt-PT')}</td>
        <td><strong>${escapeHtml(com.titulo)}</strong><br><small class="text-muted">${escapeHtml(com.conteudo.substring(0, 80))}...</small></td>
        <td><span class="badge bg-light text-dark border">${escapeHtml(com.publico_alvo_display || com.publico_alvo)}</span></td>
        <td>${badgePrio}</td>
        <td><span class="badge bg-success">Activo</span></td>
        <td class="text-end pe-3">${btnAprovar}</td>
      </tr>`;
    });
    tbody.innerHTML = html;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-danger">Erro ao carregar comunicados.</td></tr>';
  }
}

async function aprovarComunicado(id) {
  try {
    const res = await apiFetch(`/api/v1/documentos/comunicados/${id}/aprovar/`, { method: 'POST' });
    if (res && res.success !== false) {
      mostrarToast('Comunicado homologado e publicado com sucesso!', 'success');
      carregarListaComunicados();
    }
  } catch (e) {
    mostrarToast('Erro ao publicar comunicado: ' + e.message, 'danger');
  }
}

carregarListaComunicados();
"""

with open(os.path.join(pages_dir, 'comunicados.html'), 'w', encoding='utf-8') as f:
    f.write(comunicados_html)
with open(os.path.join(js_dir, 'comunicados.js'), 'w', encoding='utf-8') as f:
    f.write(comunicados_js)
print('9. Comunicados created successfully')

print('All 9 frontend modules generated with complete perfection!')
