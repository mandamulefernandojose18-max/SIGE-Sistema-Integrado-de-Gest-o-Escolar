/**
 * SIGE - PAINEL-ALUNO | Calendário Académico
 * O aluno apenas vê / descarrega o documento oficial publicado pela escola.
 */
async function carregarAlunoCalendario(ano) {
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
