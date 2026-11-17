window.__auditoriaEstado = window.__auditoriaEstado || { offset: 0, limite: 50 };

const AUDITORIA_ROTULOS_CAMPOS = {
  teste1: 'Teste 1', teste2: 'Teste 2', teste3: 'Teste 3', teste4: 'Teste 4',
  trabalho: 'Trabalho', avaliacao_trimestral: 'Avaliação trimestral', media_final: 'Média final',
  resultado: 'Resultado', comportamento: 'Comportamento', faltas: 'Faltas',
  nota_frequencia: 'Frequência', exame_1epoca: 'Exame 1ª época', exame_2epoca: 'Exame 2ª época',
  nota_final: 'Nota final', periodo: 'Período', duracao_horas: 'Duração (h)',
};

// Resume as alterações guardadas em detalhes_antes / detalhes_depois (valores antes → depois).
function resumoAlteracaoAuditoria(item) {
  const antes = item.detalhes_antes;
  const depois = item.detalhes_depois;
  if (!depois || typeof depois !== 'object') return '';
  const rotulo = k => AUDITORIA_ROTULOS_CAMPOS[k] || k;
  const val = v => (v === null || v === undefined || v === '' ? '—' : String(v));
  const partes = [];
  Object.keys(depois).forEach(k => {
    if (k.endsWith('_id')) return;
    const a = antes && typeof antes === 'object' ? antes[k] : undefined;
    if (!antes) partes.push(`${rotulo(k)}: ${val(depois[k])}`);
    else if (val(a) !== val(depois[k])) partes.push(`${rotulo(k)}: ${val(a)} → ${val(depois[k])}`);
  });
  return partes.join(' · ');
}

async function carregarTrilhaAuditoria(reiniciar = true) {
  const tbody = document.getElementById('tabelaTrilhaAuditoria');
  if (!tbody) return;
  const estado = window.__auditoriaEstado;
  if (reiniciar) estado.offset = 0;
  tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar auditoria...</td></tr>';
  const ent = document.getElementById('filtroEntidadeAuditoria')?.value || '';
  const acao = document.getElementById('filtroAcaoAuditoria')?.value || '';
  const dataInicio = document.getElementById('filtroDataInicioAuditoria')?.value || '';
  const dataFim = document.getElementById('filtroDataFimAuditoria')?.value || '';
  const params = new URLSearchParams({ limit: String(estado.limite), offset: String(estado.offset) });
  if (ent) params.set('entidade', ent);
  if (acao) params.set('acao', acao);
  if (dataInicio) params.set('data_inicio', dataInicio);
  if (dataFim) params.set('data_fim', dataFim);
  try {
    const res = await apiFetch('/api/v1/auth/auditoria/?' + params.toString());
    const lista = res?.data || res || [];
    const total = Number(res?.total ?? (Array.isArray(lista) ? lista.length : 0));
    atualizarPaginacaoAuditoria(total, Array.isArray(lista) ? lista.length : 0);
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
        'ALTERACAO': '<span class="badge bg-primary">Alteração</span>',
        'VALIDACAO': '<span class="badge bg-info text-dark">Validação</span>',
        'APROVACAO': '<span class="badge bg-success">Aprovação</span>',
        'ELIMINACAO': '<span class="badge bg-danger">Eliminação</span>',
        'DESBLOQUEIO': '<span class="badge bg-warning text-dark">Desbloqueio</span>',
        'REVOGACAO': '<span class="badge bg-secondary">Revogação</span>',
      }[item.acao] || `<span class="badge bg-secondary">${escapeHtml(item.acao)}</span>`;
      const resumo = resumoAlteracaoAuditoria(item);

      html += `<tr>
        <td class="ps-3 small text-muted">${escapeHtml(dt)}</td>
        <td><strong>${escapeHtml(item.usuario_nome || 'Sistema')}</strong></td>
        <td><span class="badge bg-light text-dark border">${escapeHtml(item.usuario_role || '-')}</span></td>
        <td><span class="fw-semibold text-dark">${escapeHtml(item.entidade)}</span></td>
        <td>${badgeAcao}</td>
        <td class="pe-3 small">${escapeHtml(item.descricao)}${resumo ? `<div class="text-muted mt-1" style="font-size:0.8rem;">${escapeHtml(resumo)}</div>` : ''}</td>
      </tr>`;
    });
    tbody.innerHTML = html;
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-danger">Erro ao carregar auditoria.</td></tr>';
  }
}

function atualizarPaginacaoAuditoria(total, naPagina) {
  const estado = window.__auditoriaEstado;
  const info = document.getElementById('infoPaginaAuditoria');
  const ant = document.getElementById('btnAuditoriaAnterior');
  const seg = document.getElementById('btnAuditoriaSeguinte');
  const de = total === 0 ? 0 : estado.offset + 1;
  const ate = estado.offset + naPagina;
  if (info) info.textContent = `${de}–${ate} de ${total}`;
  if (ant) ant.disabled = estado.offset <= 0;
  if (seg) seg.disabled = ate >= total;
}

function paginaAuditoria(direcao) {
  const estado = window.__auditoriaEstado;
  estado.offset = Math.max(0, estado.offset + direcao * estado.limite);
  carregarTrilhaAuditoria(false);
}

if (typeof carregarTrilhaAuditoria === 'function') {
  carregarTrilhaAuditoria();
}
