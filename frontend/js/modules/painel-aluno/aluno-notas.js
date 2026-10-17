/**
 * SIGE - PAINEL-ALUNO | As Minhas Notas & Boletim
 * Ficheiro de código independente do menu: aluno-notas.js
 * 3 Possibilidades de Visualização e Publicação: I, II, III Trimestres e Todos
 */

let stateAlunoNotas = {
  periodoAtivo: 'TODOS',
  dados: null
};

async function alternarTrimestreAluno(periodo) {
  stateAlunoNotas.periodoAtivo = periodo || 'TODOS';
  
  // Atualizar visual dos botões
  const botoes = {
    'TODOS': 'btnAlunoTrimestreTodos',
    '1_TRIMESTRE': 'btnAlunoTrimestre1',
    '2_TRIMESTRE': 'btnAlunoTrimestre2',
    '3_TRIMESTRE': 'btnAlunoTrimestre3'
  };

  Object.entries(botoes).forEach(([p, id]) => {
    const el = document.getElementById(id);
    if (el) {
      if (p === stateAlunoNotas.periodoAtivo) {
        el.classList.add('active', 'btn-primary');
        el.classList.remove('btn-outline-primary');
      } else {
        el.classList.remove('active', 'btn-primary');
        el.classList.add('btn-outline-primary');
      }
    }
  });

  await carregarAlunoNotas(stateAlunoNotas.periodoAtivo);
}

async function carregarAlunoNotas(periodoParam) {
  const periodo = periodoParam || stateAlunoNotas.periodoAtivo || 'TODOS';
  stateAlunoNotas.periodoAtivo = periodo;

  try {
    const res = await apiFetch(`/api/v1/alunos/me/notas?periodo=${encodeURIComponent(periodo)}`);
    if (!res || !res.success || !res.data) return;

    const d = res.data;
    stateAlunoNotas.dados = d;

    const bannerBloqueado = document.getElementById('bannerNotasBloqueadas');
    const bannerNaoPub = document.getElementById('bannerTrimestreNaoPublicado');
    const tabelaContainer = document.getElementById('tabelaAlunoNotasCorpo')?.closest('.table-responsive');
    const elMediaGeral = document.getElementById('alunoMediaGeral');
    const elPub = document.getElementById('lblPublicacaoEscola');

    // 1. Tratamento de bloqueio total pela escola
    if (d.permitirVisualizacaoNotas === false || d.publicacaoNotasTrimestre === 'NENHUM') {
      if (bannerBloqueado) bannerBloqueado.classList.remove('d-none');
      if (bannerNaoPub) bannerNaoPub.classList.add('d-none');
      if (tabelaContainer) tabelaContainer.style.display = 'none';
      if (elMediaGeral) elMediaGeral.textContent = '--';
      if (elPub) elPub.innerHTML = '<span class="text-danger fw-bold"><i class="bi bi-lock-fill me-1"></i>Ocultas / Suspensas</span>';
      return;
    } else {
      if (bannerBloqueado) bannerBloqueado.classList.add('d-none');
      if (tabelaContainer) tabelaContainer.style.display = 'block';
    }

    // 2. Rótulo de publicação oficial da escola
    if (elPub) {
      const pubMap = {
        '1_TRIMESTRE': '<span class="text-primary fw-bold"><i class="bi bi-1-circle-fill me-1"></i>I Trimestre Publicado</span>',
        '2_TRIMESTRE': '<span class="text-primary fw-bold"><i class="bi bi-2-circle-fill me-1"></i>I e II Trimestres Publicados</span>',
        '3_TRIMESTRE': '<span class="text-primary fw-bold"><i class="bi bi-3-circle-fill me-1"></i>III Trimestre Publicado</span>',
        'TODOS': '<span class="text-success fw-bold"><i class="bi bi-check-all me-1"></i>Todos os Trimestres Publicados (I, II e III)</span>'
      };
      let txtPub = pubMap[d.publicacaoNotasTrimestre] || '<span class="text-success fw-bold">Todos os Trimestres</span>';
      if (d.modoPublicacaoNotas === 'DATAS' && d.infoPeriodo && d.infoPeriodo.inicio) {
        if (!d.infoPeriodo.fim || d.infoPeriodo.fim === 'Infinito') {
          txtPub += ` <span class="badge bg-success-subtle text-success-emphasis border ms-1"><i class="bi bi-infinity me-1"></i>A partir de: ${d.infoPeriodo.inicio} (Visualização por Infinito)</span>`;
        } else {
          txtPub += ` <span class="badge bg-info-subtle text-info-emphasis border ms-1"><i class="bi bi-calendar-event me-1"></i>Período: ${d.infoPeriodo.inicio} até ${d.infoPeriodo.fim}</span>`;
        }
      }
      elPub.innerHTML = txtPub;
    }

    // 3. Verificação de publicação do trimestre selecionado
    const trimestresPublicados = d.trimestresPublicados || ['1_TRIMESTRE', '2_TRIMESTRE', '3_TRIMESTRE'];
    const periodoEstaPublicado = (periodo === 'TODOS') || trimestresPublicados.includes(periodo);

    if (!periodoEstaPublicado) {
      if (bannerNaoPub) {
        bannerNaoPub.classList.remove('d-none');
        const nomesT = { '1_TRIMESTRE': '1º Trimestre', '2_TRIMESTRE': '2º Trimestre', '3_TRIMESTRE': '3º Trimestre' };
        bannerNaoPub.innerHTML = `<i class="bi bi-info-circle-fill me-2 fs-5"></i><strong>Trimestre em Consolidação:</strong> As notas do <strong>${nomesT[periodo] || periodo}</strong> ainda não foram publicadas pela Direcção Pedagógica.`;
      }
    } else {
      if (bannerNaoPub) bannerNaoPub.classList.add('d-none');
    }

    // 4. Média e Situação
    if (elMediaGeral) {
      elMediaGeral.textContent = d.mediaGeral !== null && d.mediaGeral !== undefined ? `${d.mediaGeral} valores` : '--';
    }

    const badgeSit = document.getElementById('alunoSituacaoBadge');
    if (badgeSit) {
      if (d.situacao === 'APROVADO' || d.situacao === 'Aprovado') {
        badgeSit.textContent = 'Aprovado';
        badgeSit.className = 'badge bg-success p-2 ms-2';
      } else if (d.situacao === 'REPROVADO' || d.situacao === 'Reprovado') {
        badgeSit.textContent = 'Reprovado';
        badgeSit.className = 'badge bg-danger p-2 ms-2';
      } else {
        badgeSit.textContent = d.situacao || 'Em Curso';
        badgeSit.className = 'badge bg-secondary p-2 ms-2';
      }
    }

    // 5. Atualização do Cabeçalho da Tabela Conforme Período Selecionado
    const thead = document.getElementById('tabelaAlunoNotasCabecalho');
    if (thead) {
      if (periodo === 'TODOS') {
        thead.innerHTML = `
          <tr>
            <th class="text-start">Disciplina</th>
            <th>1º Trimestre (T1)</th>
            <th>2º Trimestre (T2)</th>
            <th>3º Trimestre (T3)</th>
            <th>Média Final (MFD)</th>
            <th>Faltas Totais</th>
            <th>Situação Anual</th>
          </tr>
        `;
      } else {
        const nomesPer = { '1_TRIMESTRE': 'I Trimestre', '2_TRIMESTRE': 'II Trimestre', '3_TRIMESTRE': 'III Trimestre' };
        thead.innerHTML = `
          <tr>
            <th class="text-start">Disciplina</th>
            <th>Teste 1 (ACS 1)</th>
            <th>Teste 2 (ACS 2)</th>
            <th>Trabalho (ACT)</th>
            <th>Aval. Trimestral (APT)</th>
            <th>Média ${nomesPer[periodo]}</th>
            <th>Faltas</th>
            <th>Situação</th>
          </tr>
        `;
      }
    }

    // 6. Atualização do Corpo da Tabela
    const tbody = document.getElementById('tabelaAlunoNotasCorpo');
    if (!tbody) return;

    if (!d.disciplinas || d.disciplinas.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-muted">Nenhuma avaliação registada para este aluno.</td></tr>';
      return;
    }

    if (periodo === 'TODOS') {
      tbody.innerHTML = d.disciplinas.map(item => {
        const mfdVal = item.mfd !== null && item.mfd !== undefined ? item.mfd : (item.mediaFinal !== null ? item.mediaFinal : null);
        const mfdCls = mfdVal !== null ? (Number(mfdVal) >= 9.5 ? 'text-success fw-bold' : 'text-danger fw-bold') : 'text-muted';

        const fmtNotaCol = (val, pub) => {
          if (!pub) return '<span class="badge bg-light text-muted border" title="Não publicado pela escola"><i class="bi bi-lock me-1"></i>Oculto</span>';
          if (val === null || val === undefined || val === '-') return '<span class="text-muted">-</span>';
          const n = Number(val);
          return `<span class="${n >= 9.5 ? 'fw-bold text-dark' : 'fw-bold text-danger'}">${n}</span>`;
        };

        const sitBadge = mfdVal !== null 
          ? (Number(mfdVal) >= 9.5 ? '<span class="badge bg-success">Positiva</span>' : '<span class="badge bg-danger">Negativa</span>')
          : '<span class="badge bg-light text-dark border">Pendente</span>';

        return `
          <tr>
            <td class="text-start fw-bold text-dark">${item.nome}</td>
            <td>${fmtNotaCol(item.t1, item.publicadoT1 !== false)}</td>
            <td>${fmtNotaCol(item.t2, item.publicadoT2 !== false)}</td>
            <td>${fmtNotaCol(item.t3, item.publicadoT3 !== false)}</td>
            <td class="fs-6 ${mfdCls}">${mfdVal !== null ? mfdVal : '-'}</td>
            <td>${item.faltas || 0}</td>
            <td>${sitBadge}</td>
          </tr>
        `;
      }).join('');
    } else {
      // Exibição detalhada das avaliações do trimestre específico selecionado
      tbody.innerHTML = d.disciplinas.map(item => {
        const det = (item.detalhes && item.detalhes[periodo]) || {};
        if (det.publicado === false) {
          return `
            <tr>
              <td class="text-start fw-bold text-dark">${item.nome}</td>
              <td colspan="6" class="text-muted py-2"><i class="bi bi-lock me-1"></i>Notas deste trimestre ainda não publicadas pela escola.</td>
            </tr>
          `;
        }

        const medNum = det.media_final !== null && det.media_final !== undefined ? Number(det.media_final) : null;
        const cls = medNum !== null ? (medNum >= 9.5 ? 'text-success fw-bold fs-6' : 'text-danger fw-bold fs-6') : 'text-muted';

        const fmtVal = v => (v !== null && v !== undefined && v !== '') ? (Number(v) >= 9.5 ? `<strong>${v}</strong>` : `<strong class="text-danger">${v}</strong>`) : '-';

        const sitBadge = medNum !== null 
          ? (medNum >= 9.5 ? '<span class="badge bg-success">Aprovado</span>' : '<span class="badge bg-danger">Reprovado</span>')
          : '<span class="badge bg-light text-dark border">Pendente</span>';

        return `
          <tr>
            <td class="text-start fw-bold text-dark">${item.nome}</td>
            <td>${fmtVal(det.teste1)}</td>
            <td>${fmtVal(det.teste2)}</td>
            <td>${fmtVal(det.trabalho)}</td>
            <td>${fmtVal(det.avaliacao_trimestral)}</td>
            <td class="${cls}">${medNum !== null ? medNum : '-'}</td>
            <td>${det.faltas || 0}</td>
            <td>${sitBadge}</td>
          </tr>
        `;
      }).join('');
    }
  } catch (err) {
    console.warn('[NOTAS] Falha ao carregar notas do aluno:', err);
  }
}
