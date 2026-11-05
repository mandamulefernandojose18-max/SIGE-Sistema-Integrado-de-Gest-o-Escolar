/**
 * SIGE - PAINEL-ALUNO | As Minhas Faltas
 * Visualização no ecrã (por disciplina e registos) + exportação PDF/XLSX, sempre a partir das presenças reais.
 */
function _anoFaltasSelecionado() {
  return String(state.anosPorView?.['aluno-faltas'] || '');
}

const _FALTAS_ESTADOS = {
  FALTA_JUSTIFICADA: { rotulo: 'Falta justificada', cls: 'warning' },
  FALTA_INJUSTIFICADA: { rotulo: 'Falta injustificada', cls: 'danger' },
  ATRASO: { rotulo: 'Atraso', cls: 'secondary' }
};

function _faltasCartao(rotulo, valor, cls) {
  return `<div class="col-6 col-md-3"><div class="border rounded py-2"><div class="fs-4 fw-bold text-${cls}">${valor}</div><div class="small text-muted">${rotulo}</div></div></div>`;
}

async function carregarAlunoFaltas(ano) {
  const reg = (state.anosAluno || []).find(a => String(a.ano) === String(ano));
  const el = document.getElementById('alunoFaltasClasse');
  if (el) el.textContent = reg ? `${reg.classe} — Turma ${reg.turma} — ${reg.ano}` : 'Sem matrícula neste ano lectivo.';
  ['btnAlunoFaltasPdf', 'btnAlunoFaltasXlsx'].forEach(id => { const b = document.getElementById(id); if (b) b.disabled = !reg; });

  const cartoes = document.getElementById('alunoFaltasCartoes');
  const tabela = document.getElementById('alunoFaltasTabela');
  const registos = document.getElementById('alunoFaltasRegistos');
  if (!tabela || !registos) return;
  const vazio = (msg) => {
    if (cartoes) cartoes.innerHTML = '';
    tabela.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-3">${msg}</td></tr>`;
    registos.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-3">—</td></tr>';
  };
  if (!reg) { vazio('Sem matrícula neste ano lectivo.'); return; }

  tabela.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-3"><i class="bi bi-arrow-repeat spin me-2"></i>A carregar...</td></tr>';
  try {
    const res = await apiFetch(`/api/v1/alunos/me/faltas?ano=${encodeURIComponent(ano)}`);
    if (!res?.success) { vazio(escapeHtml(res?.message || 'Não foi possível carregar as faltas.')); return; }
    const discs = res.disciplinas || [];
    if (!discs.length) { vazio('Ainda não existem registos de presenças/faltas neste ano lectivo.'); return; }

    const tot = discs.reduce((t, d) => ({
      aulas: t.aulas + d.aulas, presencas: t.presencas + d.presencas, justificadas: t.justificadas + d.justificadas,
      injustificadas: t.injustificadas + d.injustificadas, atrasos: t.atrasos + d.atrasos
    }), { aulas: 0, presencas: 0, justificadas: 0, injustificadas: 0, atrasos: 0 });
    const pct = (f, a) => (a ? (100 * f / a).toFixed(1).replace('.', ',') + '%' : '—');

    if (cartoes) cartoes.innerHTML =
      _faltasCartao('Aulas registadas', tot.aulas, 'dark') + _faltasCartao('Presenças', tot.presencas, 'success') +
      _faltasCartao('Faltas', tot.justificadas + tot.injustificadas, 'danger') + _faltasCartao('Atrasos', tot.atrasos, 'secondary');

    tabela.innerHTML = discs.map(d => `<tr>
        <td class="fw-semibold">${escapeHtml(d.disciplina)}</td>
        <td class="text-center">${d.aulas}</td><td class="text-center">${d.presencas}</td>
        <td class="text-center">${d.justificadas}</td>
        <td class="text-center ${d.injustificadas ? 'text-danger fw-semibold' : ''}">${d.injustificadas}</td>
        <td class="text-center">${d.atrasos}</td><td class="text-center">${pct(d.faltas, d.aulas)}</td></tr>`).join('') +
      `<tr class="table-light fw-bold"><td>TOTAL</td><td class="text-center">${tot.aulas}</td><td class="text-center">${tot.presencas}</td>
        <td class="text-center">${tot.justificadas}</td><td class="text-center ${tot.injustificadas ? 'text-danger' : ''}">${tot.injustificadas}</td>
        <td class="text-center">${tot.atrasos}</td><td class="text-center">${pct(tot.justificadas + tot.injustificadas, tot.aulas)}</td></tr>`;

    const regs = res.registos || [];
    registos.innerHTML = regs.length ? regs.map(r => {
      const e = _FALTAS_ESTADOS[r.status] || { rotulo: r.status, cls: 'secondary' };
      const [a, m, d] = String(r.data).split('-');
      const nota = [r.observacao, r.justificacao ? `Justificação: ${r.justificacao}` : '',
        (r.pedido_justificacao && r.status === 'FALTA_INJUSTIFICADA') ? `Pedido enviado: ${r.pedido_justificacao}` : '']
        .filter(Boolean).join(' · ');
      return `<tr><td>${d}/${m}/${a}</td><td>${escapeHtml(r.disciplina)}</td>
        <td><span class="badge bg-${e.cls}">${e.rotulo}</span></td><td class="small text-muted">${escapeHtml(nota)}</td></tr>`;
    }).join('') : '<tr><td colspan="4" class="text-center text-muted py-3">Sem faltas nem atrasos registados.</td></tr>';
  } catch (e) {
    vazio('Erro ao carregar as faltas.');
  }
}

async function descarregarAlunoFaltasPdf() {
  const ano = _anoFaltasSelecionado();
  if (!ano) return;
  await downloadFicheiroBinario(`/api/v1/alunos/me/faltas/pdf?ano=${encodeURIComponent(ano)}`, `faltas_${ano}.pdf`);
}

async function descarregarAlunoFaltasXlsx() {
  const ano = _anoFaltasSelecionado();
  if (!ano) return;
  await downloadFicheiroBinario(`/api/v1/alunos/me/faltas/xlsx?ano=${encodeURIComponent(ano)}`, `faltas_${ano}.xlsx`);
}
