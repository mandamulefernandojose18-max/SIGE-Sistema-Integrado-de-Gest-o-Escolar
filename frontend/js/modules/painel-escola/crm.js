// CRM Escolar — alertas de evasão, atendimentos e ficha 360º. API: /api/v1/crm/
// Filtros em cascata (Classe → Turma); resultados paginados (altura constante para qualquer n).
const crmState = { turmas: [], alertasOffset: 0, atendPagina: 1 };
const CRM_PAGINA = 25;

function crmLista(res) { return res?.data || res?.results || (Array.isArray(res) ? res : []); }
function crmModal(id) { return bootstrap.Modal.getOrCreateInstance(document.getElementById(id)); }
function crmOpcoes(sel, itens, vazio) {
  if (!sel) return;
  sel.innerHTML = itens.length
    ? itens.map(i => `<option value="${escapeHtml(i.valor)}">${escapeHtml(i.texto)}</option>`).join('')
    : `<option value="">${vazio}</option>`;
  sel.disabled = itens.length === 0;
}

window.crmMostrarTab = function (tab) {
  const alertas = tab === 'alertas';
  document.getElementById('crmPainelAlertas').style.display = alertas ? '' : 'none';
  document.getElementById('crmPainelAtend').style.display = alertas ? 'none' : '';
  document.getElementById('crmTabAlertas').classList.toggle('active', alertas);
  document.getElementById('crmTabAtend').classList.toggle('active', !alertas);
  if (!alertas) crmCarregarAtendimentos(true);
};

async function crmIniciar() {
  try {
    const res = await apiFetch('/api/v1/escola-admin/turmas');
    crmState.turmas = crmLista(res).map(t => ({ id: String(t.id), nome: t.nome || '', classe: t.grau_ano || '' }));
  } catch (e) {
    crmState.turmas = [];
  }
  const classes = [...new Set(crmState.turmas.map(t => t.classe))].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  crmOpcoes(document.getElementById('crmClasse'), classes.map(c => ({ valor: c, texto: c })), 'Sem turmas registadas');
  crmAoMudarClasse();
}

window.crmAoMudarClasse = function () {
  const classe = document.getElementById('crmClasse')?.value;
  const turmas = crmState.turmas.filter(t => t.classe === classe)
    .sort((a, b) => a.nome.localeCompare(b.nome, undefined, { numeric: true }));
  const sel = document.getElementById('crmTurma');
  crmOpcoes(sel, turmas.map(t => ({ valor: t.id, texto: t.nome })), '—');
  if (turmas.length) sel.insertAdjacentHTML('afterbegin', '<option value="">Todas as turmas da classe</option>'), sel.value = '';
};

window.crmCarregarAlertas = async function (reiniciar) {
  if (reiniciar) crmState.alertasOffset = 0;
  const tbody = document.getElementById('crmTabelaAlertas');
  const q = new URLSearchParams({
    min_faltas: document.getElementById('crmMinFaltas').value || 0,
    min_propinas_atraso: document.getElementById('crmMinPropinas').value || 0,
    limite: CRM_PAGINA, offset: crmState.alertasOffset
  });
  const classe = document.getElementById('crmClasse').value;
  const turma = document.getElementById('crmTurma').value;
  if (classe) q.set('classe', classe);
  if (turma) q.set('turma_id', turma);
  try {
    const res = await apiFetch('/api/v1/crm/alertas-evasao/?' + q.toString());
    const itens = res?.resultados || [];
    if (reiniciar) tbody.innerHTML = '';
    if (reiniciar && !itens.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">Nenhum aluno atinge os limites definidos para este filtro.</td></tr>';
    }
    itens.forEach(a => {
      const motivos = (a.motivos || []).map(m => m === 'FALTAS'
        ? '<span class="badge bg-danger">Faltas</span>' : '<span class="badge bg-warning text-dark">Propinas</span>').join(' ');
      tbody.insertAdjacentHTML('beforeend', `<tr>
        <td class="ps-3"><strong>${escapeHtml(a.nome)}</strong><br><small class="text-muted">${escapeHtml(a.matricula)}</small></td>
        <td class="small">${escapeHtml(a.classe || '-')} · ${escapeHtml(a.turma || '-')}</td>
        <td class="text-center">${a.faltas_efectivas}</td><td class="text-center">${a.propinas_em_atraso}</td>
        <td>${motivos}</td>
        <td class="text-end pe-3"><button class="btn btn-sm btn-outline-primary py-0 px-2" onclick="crmAbrirFicha('${escapeHtml(a.aluno_id)}')"><i class="bi bi-person-lines-fill"></i> Ficha</button></td>
      </tr>`);
    });
    crmState.alertasOffset += itens.length;
    document.getElementById('crmAlertasResumo').textContent = `${Math.min(crmState.alertasOffset, res.total || 0)} de ${res.total || 0} aluno(s) sinalizado(s)`;
    document.getElementById('crmAlertasMais').classList.toggle('d-none', crmState.alertasOffset >= (res.total || 0));
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-danger">Erro ao carregar os alertas.</td></tr>';
  }
};

window.crmAbrirFicha = async function (alunoId) {
  const corpo = document.getElementById('crmFichaCorpo');
  corpo.innerHTML = '<div class="text-center text-muted py-4"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar...</div>';
  crmModal('crmModalFicha').show();
  try {
    const f = await apiFetch(`/api/v1/crm/encarregado/${alunoId}/`);
    const com = (f.comunicacoes_recentes || []).map(c => `<li class="list-group-item small">
      <span class="badge bg-light text-dark border me-1">${escapeHtml(c.tipo)}</span>${escapeHtml(c.mensagem)}
      <div class="text-muted">${escapeHtml(new Date(c.created_at).toLocaleString('pt-PT'))} · ${escapeHtml(c.canal)}</div></li>`).join('');
    const contas = (f.contas_encarregado || []).map(c =>
      `<li class="list-group-item d-flex justify-content-between align-items-center small py-1">${escapeHtml(c.email)}
        <button class="btn btn-sm btn-outline-danger py-0 px-2" title="Remover a associação" onclick="crmRemoverVinculo('${escapeHtml(c.id)}','${escapeHtml(alunoId)}')"><i class="bi bi-x-lg"></i></button></li>`).join('');
    document.getElementById('crmFichaTitulo').textContent = f.aluno.nome;
    corpo.innerHTML = `
      <div class="row g-3 mb-3">
        <div class="col-md-6"><div class="small text-muted">Aluno</div>
          <div>${escapeHtml(f.aluno.matricula)} · ${escapeHtml(f.aluno.classe || '-')} · ${escapeHtml(f.aluno.turma || '-')}</div></div>
        <div class="col-md-6"><div class="small text-muted">Encarregado</div>
          <div>${escapeHtml(f.encarregado.nome || 'Não registado')}</div>
          <div class="small">${escapeHtml(f.encarregado.contacto || '')} ${escapeHtml(f.encarregado.email || '')}</div></div>
      </div>
      <div class="row g-2 mb-3 text-center">
        <div class="col-4"><div class="border rounded p-2"><div class="fs-4">${f.faltas_efectivas}</div><div class="small text-muted">Faltas efectivas</div></div></div>
        <div class="col-4"><div class="border rounded p-2"><div class="fs-4">${f.propinas_em_atraso.quantidade}</div><div class="small text-muted">Propinas em atraso (${escapeHtml(f.propinas_em_atraso.valor)} MZN)</div></div></div>
        <div class="col-4"><div class="border rounded p-2"><div class="fs-4">${f.atendimentos_abertos}</div><div class="small text-muted">Atendimentos abertos</div></div></div>
      </div>
      <h6 class="fw-bold">Contas de encarregado associadas</h6>
      ${contas ? `<ul class="list-group mb-2">${contas}</ul>` : '<p class="text-muted small mb-2">Nenhuma conta de encarregado associada a este aluno.</p>'}
      <div class="input-group input-group-sm mb-3">
        <input id="crmVinEmail" type="email" class="form-control" placeholder="E-mail da conta do encarregado" onkeydown="if(event.key==='Enter'){crmAssociarEncarregado('${escapeHtml(alunoId)}');}">
        <button class="btn btn-outline-primary" onclick="crmAssociarEncarregado('${escapeHtml(alunoId)}')">Associar</button>
      </div>
      <h6 class="fw-bold">Registar contacto com o encarregado</h6>
      <div class="row g-2 mb-3">
        <div class="col-6 col-md-3"><select id="crmCoTipo" class="form-select form-select-sm"><option value="FALTAS">Faltas</option><option value="PROPINA">Propina</option><option value="REUNIAO">Reunião</option><option value="PAUTA">Pauta / Notas</option><option value="OUTRO">Outro</option></select></div>
        <div class="col-6 col-md-3"><select id="crmCoCanal" class="form-select form-select-sm"><option value="TELEFONE">Telefone</option><option value="PRESENCIAL">Presencial</option><option value="EMAIL">E-mail</option><option value="INAPP">Aplicação</option></select></div>
        <div class="col-12 col-md-6"><div class="input-group input-group-sm"><input id="crmCoMsg" class="form-control" placeholder="Resumo do contacto">
          <button class="btn btn-primary" onclick="crmGravarComunicacao('${escapeHtml(alunoId)}')">Registar</button></div></div>
      </div>
      <h6 class="fw-bold">Últimos contactos</h6>
      ${com ? `<ul class="list-group list-group-flush">${com}</ul>` : '<p class="text-muted small mb-0">Ainda não há contactos registados com este encarregado.</p>'}`;
  } catch (e) {
    corpo.innerHTML = '<p class="text-danger mb-0">Erro ao carregar a ficha.</p>';
  }
};

window.crmAssociarEncarregado = async function (alunoId) {
  const email = document.getElementById('crmVinEmail').value.trim();
  if (!email) { mostrarToast('Indique o e-mail da conta do encarregado.', 'warning'); return; }
  try {
    await apiFetch('/api/v1/crm/vinculos/', { method: 'POST', body: JSON.stringify({ aluno: alunoId, email }) });
    mostrarToast('Conta associada ao aluno.', 'success');
    crmAbrirFicha(alunoId);
  } catch (e) {
    mostrarToast(e.message || 'Não foi possível associar a conta.', 'danger');
  }
};

window.crmRemoverVinculo = async function (id, alunoId) {
  if (!window.confirm('Remover a associação desta conta ao aluno?')) return;
  try {
    await apiFetch(`/api/v1/crm/vinculos/${id}/`, { method: 'DELETE' });
    mostrarToast('Associação removida.', 'success');
    crmAbrirFicha(alunoId);
  } catch (e) {
    mostrarToast('Erro ao remover: ' + e.message, 'danger');
  }
};

window.crmGravarComunicacao = async function (alunoId) {
  const mensagem = document.getElementById('crmCoMsg').value.trim();
  if (!mensagem) { mostrarToast('Indique o resumo do contacto.', 'warning'); return; }
  try {
    await apiFetch('/api/v1/crm/comunicacoes/', { method: 'POST', body: JSON.stringify({
      aluno: alunoId, mensagem, tipo: document.getElementById('crmCoTipo').value, canal: document.getElementById('crmCoCanal').value }) });
    mostrarToast('Contacto registado.', 'success');
    crmAbrirFicha(alunoId);
  } catch (e) {
    mostrarToast('Erro ao registar o contacto: ' + e.message, 'danger');
  }
};

const CRM_BADGE_ESTADO = { ABERTO: 'bg-danger', EM_CURSO: 'bg-warning text-dark', RESOLVIDO: 'bg-success' };

window.crmCarregarAtendimentos = async function (reiniciar) {
  if (reiniciar) crmState.atendPagina = 1;
  const tbody = document.getElementById('crmTabelaAtend');
  const q = new URLSearchParams({ limit: CRM_PAGINA, page: crmState.atendPagina });
  const estado = document.getElementById('crmFiltroEstado').value;
  const prio = document.getElementById('crmFiltroPrioridade').value;
  if (estado) q.set('estado', estado);
  if (prio) q.set('prioridade', prio);
  try {
    const res = await apiFetch('/api/v1/crm/atendimentos/?' + q.toString());
    const itens = crmLista(res);
    if (reiniciar) tbody.innerHTML = '';
    if (reiniciar && !itens.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">Nenhum atendimento registado.</td></tr>';
    }
    itens.forEach(a => {
      const resolver = a.estado === 'RESOLVIDO' ? '' :
        `<button class="btn btn-sm btn-outline-success py-0 px-2" onclick="crmResolver('${escapeHtml(a.id)}')"><i class="bi bi-check2"></i> Resolver</button>`;
      const ficha = a.aluno ? `<button class="btn btn-sm btn-outline-primary py-0 px-2 me-1" onclick="crmAbrirFicha('${escapeHtml(a.aluno)}')">Ficha</button>` : '';
      tbody.insertAdjacentHTML('beforeend', `<tr>
        <td class="ps-3 small text-muted">${escapeHtml(new Date(a.created_at).toLocaleDateString('pt-PT'))}</td>
        <td><strong>${escapeHtml(a.assunto)}</strong><br><small class="text-muted">${escapeHtml(a.descricao || '')}</small></td>
        <td class="small">${escapeHtml(a.aluno_nome || '-')}</td><td class="small">${escapeHtml(a.prioridade)}</td>
        <td><span class="badge ${CRM_BADGE_ESTADO[a.estado] || 'bg-secondary'}">${escapeHtml(a.estado.replace('_', ' '))}</span></td>
        <td class="text-end pe-3">${ficha}${resolver}</td></tr>`);
    });
    const total = res?.total ?? itens.length;
    crmState.atendPagina += 1;
    document.getElementById('crmAtendResumo').textContent = `${tbody.querySelectorAll('tr').length} de ${total}`;
    document.getElementById('crmAtendMais').classList.toggle('d-none', !res?.next);
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-danger">Erro ao carregar os atendimentos.</td></tr>';
  }
};

window.crmNovoAtendimento = function () {
  ['crmAtAssunto', 'crmAtDescricao', 'crmAtBusca'].forEach(id => { document.getElementById(id).value = ''; });
  document.getElementById('crmAtAluno').innerHTML = '<option value="">Sem aluno associado</option>';
  crmModal('crmModalAtend').show();
};

window.crmBuscarAluno = async function () {
  const termo = document.getElementById('crmAtBusca').value.trim();
  const sel = document.getElementById('crmAtAluno');
  if (termo.length < 2) { mostrarToast('Escreva pelo menos 2 letras.', 'warning'); return; }
  try {
    const res = await apiFetch(`/api/v1/alunos/?search=${encodeURIComponent(termo)}&status=ATIVO&limit=10`);
    const itens = crmLista(res);
    sel.innerHTML = '<option value="">Sem aluno associado</option>' + itens.map(a =>
      `<option value="${escapeHtml(a.id)}">${escapeHtml(a.nome)} (${escapeHtml(a.matricula)})</option>`).join('');
    if (!itens.length) mostrarToast('Nenhum aluno encontrado.', 'info');
  } catch (e) {
    mostrarToast('Erro na pesquisa: ' + e.message, 'danger');
  }
};

window.crmGravarAtendimento = async function () {
  const assunto = document.getElementById('crmAtAssunto').value.trim();
  if (!assunto) { mostrarToast('Indique o assunto.', 'warning'); return; }
  const corpo = {
    assunto, descricao: document.getElementById('crmAtDescricao').value.trim(),
    canal: document.getElementById('crmAtCanal').value, prioridade: document.getElementById('crmAtPrioridade').value
  };
  const aluno = document.getElementById('crmAtAluno').value;
  if (aluno) corpo.aluno = aluno;
  try {
    await apiFetch('/api/v1/crm/atendimentos/', { method: 'POST', body: JSON.stringify(corpo) });
    crmModal('crmModalAtend').hide();
    mostrarToast('Atendimento registado.', 'success');
    crmCarregarAtendimentos(true);
  } catch (e) {
    mostrarToast('Erro ao registar: ' + e.message, 'danger');
  }
};

window.crmResolver = async function (id) {
  const resolucao = (window.prompt('Descreva como o pedido foi resolvido:') || '').trim();
  if (!resolucao) return;
  try {
    await apiFetch(`/api/v1/crm/atendimentos/${id}/resolver/`, { method: 'POST', body: JSON.stringify({ resolucao }) });
    mostrarToast('Atendimento resolvido.', 'success');
    crmCarregarAtendimentos(true);
  } catch (e) {
    mostrarToast('Erro ao resolver: ' + e.message, 'danger');
  }
};

crmIniciar();
