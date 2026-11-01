/**
 * SIGE - PAINEL-ALUNO | As Minhas Faltas
 * Consulta e PDF gerado automaticamente a partir das faltas de todas as disciplinas.
 */
function _anoFaltasSelecionado() {
  return String(state.anosPorView?.['aluno-faltas'] || '');
}

async function carregarAlunoFaltas(ano) {
  const reg = (state.anosAluno || []).find(a => String(a.ano) === String(ano));
  const el = document.getElementById('alunoFaltasClasse');
  if (el) el.textContent = reg ? `${reg.classe} — Turma ${reg.turma} — ${reg.ano}` : 'Sem matrícula neste ano lectivo.';
  const btn = document.getElementById('btnAlunoFaltasPdf');
  if (btn) btn.disabled = !reg;
}

async function descarregarAlunoFaltasPdf() {
  const ano = _anoFaltasSelecionado();
  if (!ano) return;
  await downloadFicheiroBinario(`/api/v1/alunos/me/faltas/pdf?ano=${encodeURIComponent(ano)}`, `faltas_${ano}.pdf`);
}
