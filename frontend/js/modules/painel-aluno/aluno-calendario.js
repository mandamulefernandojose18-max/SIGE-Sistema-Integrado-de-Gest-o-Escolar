/**
 * SIGE - PAINEL-ALUNO | Calendário Académico
 * O aluno apenas vê / descarrega o documento oficial publicado pela escola.
 */
async function carregarAlunoExames(ano) {
  const el = document.getElementById('alunoExamesCorpo');
  if (!el) return;
  const esc = (t) => String(t == null ? '' : t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const periodos = { MANHA: 'Manhã', TARDE: 'Tarde', NOITE: 'Noturno' };
  const dataPt = (iso) => { if (!iso) return 'Por definir'; const p = iso.split('-'); return `${p[2]}/${p[1]}/${p[0]}`; };
  try {
    const res = await apiFetch(`/api/v1/alunos/me/calendario-exames/?ano=${encodeURIComponent(ano)}`, { noCache: true });
    const itens = (res && res.data && res.data.itens) || [];
    if (!itens.length) {
      el.innerHTML = '<div class="text-center py-3"><i class="bi bi-calendar-x display-6 d-block mb-2 text-muted"></i>Não há exames para si neste ano lectivo.</div>';
      return;
    }
    const linhas = [];
    itens.forEach((it) => {
      if (it.estado === 'EXCLUIDO') {
        linhas.push(`<tr><td class="fw-semibold">${esc(it.disciplina)}</td><td colspan="6" class="text-danger">Excluído(a) do exame: nota de frequência <strong>${String(it.nota_frequencia).replace('.', ',')}</strong> (igual ou inferior a 9,4).</td></tr>`);
        return;
      }
      (it.chamadas || []).forEach((c) => {
        const horario = c.hora_inicio ? `${esc(c.hora_inicio)} – ${esc(c.hora_fim)}` : 'Por definir';
        const juri = c.juri ? `Júri ${c.juri}` : '<span class="text-muted">Ainda não formado</span>';
        linhas.push(`<tr><td class="fw-semibold">${esc(it.disciplina)}</td><td class="text-center">${c.epoca}ª</td><td class="text-center">${dataPt(c.data)}</td>` +
          `<td class="text-center">${periodos[c.periodo] || '—'}</td><td class="text-center">${horario}</td><td class="text-center">${juri}</td>` +
          `<td class="text-center">${esc(c.sala || (c.juri ? 'Por atribuir' : '—'))}</td></tr>`);
      });
    });
    el.innerHTML = `<div class="table-responsive"><table class="table table-sm table-striped align-middle mb-0">
      <thead class="table-primary text-center"><tr><th class="text-start">Disciplina</th><th>Chamada</th><th>Data</th><th>Período</th><th>Horário</th><th>Júri</th><th>Sala</th></tr></thead>
      <tbody>${linhas.join('')}</tbody></table></div>`;
  } catch (err) {
    el.innerHTML = `<div class="alert alert-danger mb-0">${esc(err.message || 'Erro ao carregar os exames.')}</div>`;
  }
}

async function carregarAlunoCalendario(ano) {
  carregarAlunoExames(ano);
  const corpo = document.getElementById('alunoCalendarioCorpo');
  if (!corpo) return;
  try {
    const res = await apiFetch(`/api/v1/documentos/calendario/documento_oficial?ano=${encodeURIComponent(ano)}`);
    const doc = res && res.success ? res.data : null;
    if (!doc) {
      corpo.innerHTML = '<div class="text-center py-4"><i class="bi bi-calendar-x display-5 d-block mb-2 text-muted"></i>A escola ainda não publicou o calendário académico deste ano lectivo.</div>';
      return;
    }
    const titulo = String(doc.titulo || 'Calendário Escolar').replace(/</g, '&lt;');
    corpo.innerHTML = `
      <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
        <div><div class="fw-bold text-dark">${titulo}</div><div class="small text-muted">Ano lectivo ${ano}</div></div>
        <button type="button" class="btn btn-danger btn-sm fw-bold" onclick="descarregarAlunoCalendario('${encodeURIComponent(ano)}')">
          <i class="bi bi-file-earmark-pdf-fill me-1"></i> Ver / Descarregar PDF
        </button>
      </div>`;
  } catch (err) {
    corpo.innerHTML = `<div class="alert alert-danger mb-0">Erro ao contactar o servidor: ${err.message || ''}</div>`;
  }
}

async function descarregarAlunoCalendario(anoCodificado) {
  await downloadFicheiroBinario(`/api/v1/documentos/calendario/download_documento_oficial?ano=${anoCodificado}`, 'calendario_escolar.pdf');
}
