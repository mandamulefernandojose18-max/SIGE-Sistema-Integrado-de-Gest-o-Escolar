/**
 * SIGE | As Minhas Actividades de Cargo (visão do professor com cargo atribuído).
 * Só mostra o que a Direcção Pedagógica atribuiu; sem atribuições mostra o estado vazio.
 */
let maPagina = 1;

function maEsc(t) {
  const d = document.createElement('div');
  d.textContent = t == null ? '' : String(t);
  return d.innerHTML.replace(/"/g, '&quot;');
}

async function carregarMinhasAtividades(pagina) {
  maPagina = pagina || 1;
  const lista = document.getElementById('maLista');
  if (!lista) return;
  const q = new URLSearchParams({ page: maPagina, page_size: 10 });
  const cargo = document.getElementById('maCargo').value;
  const estado = document.getElementById('maEstado').value;
  if (cargo) q.set('cargo', cargo);
  if (estado) q.set('estado', estado);
  lista.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm text-primary"></div></div>';
  try {
    const res = await apiFetch(`/api/v1/atribuicoes/?${q}`, { noCache: true });
    maRender(res);
  } catch (err) {
    lista.innerHTML = `<div class="alert alert-danger small mb-0">${maEsc(err.message || 'Erro ao carregar.')}</div>`;
  }
}

function maRender(res) {
  const lista = document.getElementById('maLista');
  const itens = res.data || [];
  if (!itens.length) {
    lista.innerHTML = '<div class="text-center text-muted py-4"><i class="bi bi-clipboard fs-3 d-block mb-1"></i>Não tem actividades atribuídas de momento. A Direcção Pedagógica atribuirá as actividades do seu cargo aqui.</div>';
    document.getElementById('maPaginacao').innerHTML = '';
    return;
  }
  lista.innerHTML = `
    <div class="table-responsive">
      <table class="table table-sm table-bordered align-middle small mb-0">
        <thead class="table-light text-center"><tr><th>Cargo</th><th>Classe / Local</th><th class="text-start">Actividade</th><th>Prazo</th><th style="min-width: 130px;">Estado</th><th style="min-width: 200px;">Nota</th></tr></thead>
        <tbody>
          ${itens.map(a => `
            <tr>
              <td>${maEsc(a.cargo_nome)}</td>
              <td>${maEsc(a.classe)}${a.turma_nome ? ' — ' + maEsc(a.turma_nome) : ''}${a.disciplina_nome ? ' — ' + maEsc(a.disciplina_nome) : ''}</td>
              <td class="text-start"><span class="fw-semibold">${maEsc(a.titulo)}</span>${a.prioridade === 'ALTA' ? ' <span class="badge bg-danger">Alta</span>' : ''}
                ${a.descricao ? `<div class="text-muted" style="font-size: 0.75rem;">${maEsc(a.descricao)}</div>` : ''}
                <div class="text-muted" style="font-size: 0.7rem;">Atribuído por ${maEsc(a.atribuido_por)}</div></td>
              <td class="text-center ${a.atrasada ? 'text-danger fw-bold' : ''}">${a.prazo ? new Date(a.prazo + 'T00:00:00').toLocaleDateString('pt-PT') : '-'}${a.atrasada ? '<br>(em atraso)' : ''}</td>
              <td>
                <select class="form-select form-select-sm" onchange="maActualizar('${a.id}', {estado: this.value})">
                  ${[['PENDENTE', 'Pendente'], ['EM_CURSO', 'Em curso'], ['CONCLUIDA', 'Concluída']].map(([v, t]) => `<option value="${v}" ${a.estado === v ? 'selected' : ''}>${t}</option>`).join('')}
                </select>
              </td>
              <td><input type="text" class="form-control form-control-sm" value="${maEsc(a.nota_responsavel)}" placeholder="Observação..." maxlength="500" onchange="maActualizar('${a.id}', {nota_responsavel: this.value})"></td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>`;
  const totalPaginas = Math.max(1, Math.ceil(res.total / res.page_size));
  document.getElementById('maPaginacao').innerHTML = `
    <span class="text-muted">${res.total} actividade(s) · página ${res.page} de ${totalPaginas}</span>
    <div class="btn-group btn-group-sm">
      <button class="btn btn-outline-secondary" ${res.page <= 1 ? 'disabled' : ''} onclick="carregarMinhasAtividades(${res.page - 1})"><i class="bi bi-chevron-left"></i></button>
      <button class="btn btn-outline-secondary" ${res.page >= totalPaginas ? 'disabled' : ''} onclick="carregarMinhasAtividades(${res.page + 1})"><i class="bi bi-chevron-right"></i></button>
    </div>`;
}

async function maActualizar(id, dados) {
  try {
    await apiFetch(`/api/v1/atribuicoes/${id}/`, { method: 'PATCH', body: JSON.stringify(dados) });
    if (dados.estado) await carregarMinhasAtividades(maPagina);
  } catch (err) {
    alert(err.message || 'Erro ao actualizar.');
    await carregarMinhasAtividades(maPagina);
  }
}
