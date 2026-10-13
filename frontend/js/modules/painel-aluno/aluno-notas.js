/**
 * SIGE - PAINEL-ALUNO | As Minhas Notas & Boletim
 * Ficheiro de código independente do menu: aluno-notas.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
async function carregarAlunoNotas() {
  try {
    const res = await apiFetch('/api/v1/alunos/me/notas');
    if (res.success) {
      const d = res.data;

      const banner = document.getElementById('bannerNotasBloqueadas');
      const tabelaContainer = document.getElementById('tabelaAlunoNotasCorpo')?.closest('.table-responsive');

      if (d.permitirVisualizacaoNotas === false) {
        if (banner) banner.style.display = 'block';
        if (tabelaContainer) tabelaContainer.style.display = 'none';
        document.getElementById('alunoMediaGeral').textContent = '--';
        return;
      } else {
        if (banner) banner.style.display = 'none';
        if (tabelaContainer) tabelaContainer.style.display = 'block';
      }

      if (document.getElementById('alunoMediaGeral')) {
        document.getElementById('alunoMediaGeral').textContent = d.mediaGeral ? `${Math.round(d.mediaGeral)} valores` : '--';
      }
      
      const badgeSit = document.getElementById('alunoSituacaoBadge');
      if (badgeSit) {
        if (d.situacao === 'APROVADO') {
          badgeSit.textContent = 'Aprovado';
          badgeSit.className = 'badge badge-aprovado p-2 ms-2';
        } else if (d.situacao === 'REPROVADO') {
          badgeSit.textContent = 'Reprovado';
          badgeSit.className = 'badge badge-reprovado p-2 ms-2';
        } else {
          badgeSit.textContent = d.situacao || 'Em Curso';
          badgeSit.className = 'badge bg-secondary p-2 ms-2';
        }
      }

      const tbody = document.getElementById('tabelaAlunoNotasCorpo');
      if (!tbody) return;
      if (!d.disciplinas || d.disciplinas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4">Nenhuma avaliação lançada até ao momento.</td></tr>';
        return;
      }

      tbody.innerHTML = d.disciplinas.map(item => {
        const medNum = item.mediaFinal !== null ? Number(item.mediaFinal) : null;
        const cls = medNum !== null ? (medNum >= 9.5 ? 'nota-positiva' : 'nota-negativa') : 'text-muted';

        return `
          <tr>
            <td class="text-start"><strong>${item.nome}</strong></td>
            <td>${item.t1 !== null ? item.t1 : '-'}</td>
            <td>${item.t2 !== null ? item.t2 : '-'}</td>
            <td>${item.t3 !== null ? item.t3 : '-'}</td>
            <td class="fw-bold fs-6 ${cls}">${medNum !== null ? Math.round(medNum) : '-'}</td>
            <td>${item.faltas || 0}</td>
            <td>
              ${medNum !== null 
                ? (medNum >= 9.5 ? '<span class="badge badge-aprovado">Positiva</span>' : '<span class="badge badge-reprovado">Negativa</span>')
                : '<span class="badge bg-light text-dark border">Pendente</span>'
              }
            </td>
          </tr>
        `;
      }).join('');
    }
  } catch (err) {
    console.warn('Erro ao carregar notas do aluno:', err);
  }
}
