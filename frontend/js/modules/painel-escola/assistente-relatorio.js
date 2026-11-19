// Relatório do Assistente (Super Admin e Direcção). API: GET /api/v1/assistente/relatorio/?dias=
const REL_ROTULO_INTENCAO = { desconhecida: 'Sem resposta', fora_do_painel: 'Fora do painel', navegacao: 'Onde fica…', escolher_escola: 'Pediu escola' };
const REL_COR_MOTIVO = { 'sem resposta': 'danger', 'fora do painel': 'secondary', 'não útil': 'warning' };

function relKpi(titulo, valor, cor, dica) {
  return `<div class="col-6 col-md"><div class="card border-0 shadow-sm h-100"><div class="card-body py-2 text-center">
    <div class="fs-4 fw-bold text-${cor}">${valor}</div><div class="small text-muted" title="${escapeHtml(dica || '')}">${escapeHtml(titulo)}</div></div></div></div>`;
}

window.relCarregar = async function () {
  const dias = document.getElementById('relDias')?.value || 30;
  const kpis = document.getElementById('relKpis');
  try {
    const d = await apiFetch(`/api/v1/assistente/relatorio/?dias=${encodeURIComponent(dias)}`, { noCache: true });
    const t = d?.taxas || {};
    if (!d?.total) {
      kpis.innerHTML = relKpi('Perguntas', 0, 'primary', '');
      document.getElementById('relTabelaMelhorar').innerHTML = '<tr><td colspan="4" class="text-center py-4 text-muted">Ainda não houve perguntas ao assistente neste período.</td></tr>';
      document.getElementById('relTabelaIntencoes').innerHTML = '<tr><td class="text-center py-3 text-muted">Sem registos.</td></tr>';
      document.getElementById('relTabelaPerfis').innerHTML = '<tr><td class="text-center py-3 text-muted">Sem registos.</td></tr>';
      return;
    }
    kpis.innerHTML = relKpi('Perguntas', d.total, 'primary', 'Total no período')
      + relKpi('Sem resposta', `${t.sem_resposta_pct}%`, t.sem_resposta_pct > 10 ? 'danger' : 'success', 'O assistente não percebeu a pergunta')
      + relKpi('Fora do painel', `${t.fora_do_painel_pct}%`, 'secondary', 'Recusadas por não pertencerem ao painel do utilizador')
      + relKpi('Úteis', `${t.util_pct}%`, 'success', `${t.com_feedback} resposta(s) com feedback`)
      + relKpi('Não úteis', `${t.nao_util_pct}%`, t.nao_util_pct > 5 ? 'warning' : 'success', 'Marcadas com 👎');
    const verEscolas = d.ambito === 'plataforma';
    document.getElementById('relColEscola').style.display = verEscolas ? '' : 'none';
    const linhas = (d.perguntas_a_melhorar || []).map(p => `<tr>
      <td class="ps-3 small">${escapeHtml(p.pergunta)}</td><td class="text-center">${p.vezes}</td>
      <td>${(p.motivos || []).map(m => `<span class="badge bg-${REL_COR_MOTIVO[m] || 'secondary'} me-1">${escapeHtml(m)}</span>`).join('')}</td>
      <td class="pe-3 small text-muted" style="${verEscolas ? '' : 'display:none'}">${escapeHtml((p.escolas || []).join(', '))}</td></tr>`).join('');
    document.getElementById('relTabelaMelhorar').innerHTML = linhas || '<tr><td colspan="4" class="text-center py-4 text-muted">Nenhuma pergunta a melhorar neste período.</td></tr>';
    document.getElementById('relTabelaIntencoes').innerHTML = (d.por_intencao || []).map(r =>
      `<tr><td class="small ps-3">${escapeHtml(REL_ROTULO_INTENCAO[r.intencao] || r.intencao)}</td><td class="text-end pe-3">${r.n}</td></tr>`).join('');
    document.getElementById('relTabelaPerfis').innerHTML = (d.por_perfil || []).map(r =>
      `<tr><td class="small ps-3">${escapeHtml(r.usuario__role || 'Plataforma')}</td><td class="text-end pe-3">${r.n}</td></tr>`).join('');
  } catch (e) {
    kpis.innerHTML = '';
    document.getElementById('relTabelaMelhorar').innerHTML = `<tr><td colspan="4" class="text-center py-4 text-danger">${escapeHtml(e.message || 'Erro ao carregar o relatório.')}</td></tr>`;
  }
};

// O router chama relCarregar() sempre que o ecrã é aberto.
