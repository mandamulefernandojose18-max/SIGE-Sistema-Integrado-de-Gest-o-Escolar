/**
 * SIGE - PAINEL-ESCOLA | Pautas & Actas Oficiais
 * Ficheiro de código independente do menu: pautas.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
// ==================== 8. PAUTAS GERAIS & ACTAS OFICIAIS ====================
let subAbaPautaAtiva = 'pauta';

function mudarSubAbaPauta(aba) {
  subAbaPautaAtiva = aba;
  const btnPauta = document.getElementById('btnAbaPauta');
  const btnActa = document.getElementById('btnAbaActa');
  const viewPauta = document.getElementById('subViewPautaGeral');
  const viewActa = document.getElementById('subViewActaConselho');

  if (aba === 'pauta') {
    btnPauta?.classList.add('active');
    btnActa?.classList.remove('active');
    viewPauta?.classList.remove('d-none');
    viewActa?.classList.add('d-none');
  } else {
    btnActa?.classList.add('active');
    btnPauta?.classList.remove('active');
    viewActa?.classList.remove('d-none');
    viewPauta?.classList.add('d-none');
  }
  alternarVisualizacaoPautaTurma();
}

async function carregarPautas(anoParam, forcarBusca = false) {
  // Nao buscar dados automaticamente — aguardar accao explicita do utilizador (clicar Buscar).
  if (!forcarBusca && !anoParam) {
    const selectTurma = document.getElementById('pautaTurmaSelect');
    if (selectTurma) selectTurma.innerHTML = '<option value="">-- Selecione o Ano e clique em Buscar --</option>';
    const ph = `<div class="text-center py-5 text-muted"><i class="bi bi-calendar2-check display-4 d-block mb-3 opacity-50"></i><p class="fw-semibold">Selecione o <strong>Ano Lectivo</strong> e clique em <strong>Buscar</strong> para visualizar os dados.</p></div>`;
    const containerPauta = document.getElementById('containerTabelaPautaGeral');
    if (containerPauta) containerPauta.innerHTML = ph;
    const containerActa = document.getElementById('containerActaConselhoCorpo');
    if (containerActa) containerActa.innerHTML = ph;
    return;
  }
  try {
    const selAno = document.getElementById('pautaAnoSelect');
    const ano = anoParam || (selAno ? selAno.value : null) || state.anoLectivoVisualizacao || localStorage.getItem('sige_ano_letivo_selecionado') || state.tenant?.ano_letivo_ativo || '2026';
    const queryAno = (ano && ano !== 'TODOS') ? `?ano_letivo=${encodeURIComponent(ano)}` : '';

    const resTurmas = await apiFetch(`/api/v1/escola-admin/turmas${queryAno}`);
    const selectTurma = document.getElementById('pautaTurmaSelect');
    if (!selectTurma) return;

    if (resTurmas.success && resTurmas.data.length > 0) {
      selectTurma.innerHTML = resTurmas.data.map(t => 
        `<option value="${t.id}">${t.grau_ano} &rarr; ${t.nome} (${normalizarArea(t.area || 'Geral')})</option>`
      ).join('');
      alternarVisualizacaoPautaTurma();
    } else {
      selectTurma.innerHTML = '<option value="">Nenhuma turma cadastrada neste ano lectivo</option>';
      const corpoPauta = document.getElementById('tabelaPautaCorpo');
      if (corpoPauta) corpoPauta.innerHTML = `<tr><td colspan="30" class="text-center py-4 text-muted">Nenhuma turma encontrada para o Ano Lectivo de ${ano}.</td></tr>`;
    }
  } catch (err) {
    console.error('Erro ao carregar turmas na pauta:', err);
  }
}

window.aoClicarBuscarPautaAno = async function() {
  const sel = document.getElementById('pautaAnoSelect');
  const ano = sel ? sel.value : '';
  if (!ano) {
    if (typeof mostrarToast === 'function') {
      mostrarToast('Por favor, selecione primeiro um Ano Lectivo antes de clicar em Buscar.', 'warning');
    }
    return;
  }
  state.anoLectivoVisualizacao = ano;
  localStorage.setItem('sige_ano_letivo_selecionado', ano);
  const selHeader = document.getElementById('headerSelectAnoLectivo');
  if (selHeader) selHeader.value = ano;

  if (typeof setCarregandoBuscaAno === 'function') setCarregandoBuscaAno(true);
  try {
    await carregarPautas(ano, true);
  } finally {
    if (typeof setCarregandoBuscaAno === 'function') setCarregandoBuscaAno(false);
  }
};


async function alternarVisualizacaoPautaTurma() {
  const turmaId = document.getElementById('pautaTurmaSelect')?.value;
  if (!turmaId) return;

  if (subAbaPautaAtiva === 'pauta') {
    await carregarPautaGeral(turmaId);
  } else {
    await carregarActaConselho(turmaId);
  }
}

async function carregarPautaGeral(turmaId) {
  const container = document.getElementById('containerTabelaPautaGeral');
  if (!container) return;
  container.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div><p class="small text-muted mt-2">A carregar pauta geral da turma...</p></div>';

  try {
    const res = await apiFetch(`/api/v1/pautas/turma/${turmaId}/completa`);
    if (!res || !res.success) {
      container.innerHTML = '<div class="alert alert-warning text-center py-3">Não foi possível carregar a pauta para esta turma.</div>';
      return;
    }
    const d = res.data || res;

    const turmaNome = d.turma?.nome || 'Turma';
    const turmaGrau = d.turma?.grau_ano || '';
    const turmaArea = d.turma?.area || '';
    const areaTxt = turmaArea && !['geral', 'ensino geral', 'tronco comum'].includes(turmaArea.toLowerCase()) ? ` — Área: ${turmaArea}` : '';
    const anoLetivo = d.turma?.ano_letivo || '2026';
    const turno = d.turma?.turno || 'Diurno';
    const dirTurma = d.turma?.director_turma || 'Direcção Pedagógica';
    const dirTel = d.turma?.director_turma_tel ? ` (${d.turma.director_turma_tel})` : '';

    const elTitulo = document.getElementById('pautaGeralTitulo');
    if (elTitulo) elTitulo.textContent = `Pauta Oficial de Aproveitamento Pedagógico — ${turmaNome} (${turmaGrau}${areaTxt})`;

    const elSubtitulo = document.getElementById('pautaGeralSubtitulo');
    if (elSubtitulo) elSubtitulo.textContent = `Ano Lectivo: ${anoLetivo} | Turno: ${turno} | Director de Turma: ${dirTurma}${dirTel}`;

    const formatNota = (val) => {
      if (val === null || val === undefined || val === '' || val === '-' || isNaN(Number(val))) return '<span class="text-muted">-</span>';
      const num = Number(val);
      const cls = num >= 9.5 ? 'nota-positiva' : 'nota-negativa';
      return `<span class="${cls}">${Number.isInteger(num) ? num : num.toFixed(1)}</span>`;
    };

    const disciplinas = Array.isArray(d.disciplinas) ? d.disciplinas : [];
    const alunos = Array.isArray(d.alunos) ? d.alunos : [];

    const thDisciplinas = disciplinas.map(disc => 
      `<th colspan="4" class="text-center bg-primary bg-opacity-10 text-primary border-start border-end fw-bold" style="font-size: 0.75rem;">${disc.nome || disc.codigo}</th>`
    ).join('');

    const thSubDisciplinas = disciplinas.map(() => 
      `<th style="font-size: 0.65rem;">1º</th><th style="font-size: 0.65rem;">2º</th><th style="font-size: 0.65rem;">3º</th><th style="font-size: 0.65rem;" class="bg-light fw-bold">MFD</th>`
    ).join('');

    const colSpanTotal = 2 + (disciplinas.length * 4) + 9;

    let trsAlunos = '';
    if (alunos.length === 0) {
      trsAlunos = `
        <tr>
          <td colspan="${colSpanTotal}" class="text-center py-5 text-muted">
            <i class="bi bi-people display-6 d-block mb-2 text-secondary opacity-50"></i>
            <span class="fw-semibold">Nenhum aluno matriculado nesta turma (zero alunos na pauta).</span>
            <p class="small mb-0 mt-1">Matricule ou aloque alunos a esta turma para visualizar notas e médias na pauta geral.</p>
          </td>
        </tr>
      `;
    } else {
      trsAlunos = alunos.map(a => {
        const notasDisc = a.notasDisciplinas || a.notas || {};
        const tdDisciplinas = disciplinas.map(disc => {
          const nd = notasDisc[disc.codigo || disc.id] || notasDisc[disc.id] || notasDisc[disc.nome] || {};
          return `
            <td>${formatNota(nd.t1)}</td>
            <td>${formatNota(nd.t2)}</td>
            <td>${formatNota(nd.t3)}</td>
            <td class="bg-light fw-bold">${(nd.t1 !== '-' && nd.t2 !== '-' && nd.t3 !== '-' && nd.t1 !== null && nd.t2 !== null && nd.t3 !== null && Number(nd.t1) > 0 && Number(nd.t2) > 0 && Number(nd.t3) > 0) ? formatNota(nd.mfd) : '<span class="text-muted">-</span>'}</td>
          `;
        }).join('');

        let badgeResultado = '';
        const resTexto = (a.resultadoFinal || a.resultado || '').trim();
        if (resTexto === 'A' || resTexto === 'Aprovado') {
          badgeResultado = '<span class="fw-bold text-dark" style="font-weight: 700; color: #000000 !important;">Aprovado</span>';
        } else if (resTexto === 'R' || resTexto === 'Reprovado') {
          badgeResultado = '<span class="fw-bold text-danger" style="font-weight: 700; color: #dc2626 !important;">Reprovado</span>';
        } else if (resTexto === 'D' || resTexto === 'Desistente') {
          badgeResultado = '<span class="fw-bold text-secondary">Desistente</span>';
        } else if (resTexto === 'T' || resTexto === 'Transferido') {
          badgeResultado = '<span class="fw-bold text-secondary">Transferido</span>';
        } else {
          badgeResultado = `<span class="fw-bold text-secondary">${resTexto || '-'}</span>`;
        }

        const nomeCompleto = (a.nomeCompleto || `${a.nome || ''} ${a.apelido || ''}`).trim() || 'Sem Nome';
        const isFem = (a.genero || 'M').toUpperCase().startsWith('F');

        return `
          <tr>
            <td class="text-start ps-3 fw-semibold">${nomeCompleto}</td>
            <td><span class="badge ${isFem ? 'bg-info text-white' : 'bg-secondary text-white'}" style="min-width: 22px;">${isFem ? 'F' : 'M'}</span></td>
            ${tdDisciplinas}
            <td class="bg-light">${formatNota(a.mediasTrimestrais?.t1)}</td>
            <td class="bg-light">${formatNota(a.mediasTrimestrais?.t2)}</td>
            <td class="bg-light">${formatNota(a.mediasTrimestrais?.t3)}</td>
            <td>${a.negativas?.t1 > 0 ? `<span class="text-danger fw-bold">${a.negativas.t1}</span>` : '0'}</td>
            <td>${a.negativas?.t2 > 0 ? `<span class="text-danger fw-bold">${a.negativas.t2}</span>` : '0'}</td>
            <td>${a.negativas?.t3 > 0 ? `<span class="text-danger fw-bold">${a.negativas.t3}</span>` : '0'}</td>
            <td class="bg-light">${(a.negativas?.fimDoAno || 0) > 0 ? `<span class="text-danger fw-bold">${a.negativas.fimDoAno}</span>` : '0'}</td>
            <td class="bg-primary bg-opacity-10 fw-bold fs-6">${formatNota(a.mediaFinalGeral)}</td>
            <td>${badgeResultado}</td>
          </tr>
        `;
      }).join('');
    }

    const est = d.estatistica || {};
    const totalInscritos = est.inscritos?.total ?? est.totalAlunos ?? alunos.length;
    const homensInscritos = est.inscritos?.h ?? est.homens ?? alunos.filter(a => !(a.genero || '').toUpperCase().startsWith('F')).length;
    const mulheresInscritos = est.inscritos?.m ?? est.mulheres ?? alunos.filter(a => (a.genero || '').toUpperCase().startsWith('F')).length;
    const totalAvaliados = est.avaliados?.total ?? totalInscritos;
    const aprovadosTotal = typeof est.aprovados === 'object' ? (est.aprovados?.total ?? 0) : (est.aprovados ?? 0);
    const aprovadosPct = typeof est.aprovados === 'object' ? (est.aprovados?.pct ?? 0) : (est.taxaAprovacao ?? 0);
    const reprovadosTotal = typeof est.reprovados === 'object' ? (est.reprovados?.total ?? 0) : (est.reprovados ?? 0);
    const reprovadosPct = typeof est.reprovados === 'object' ? (est.reprovados?.pct ?? 0) : (est.taxaReprovacao ?? 0);

    container.innerHTML = `
      <table class="table table-bordered table-hover align-middle text-center small pauta-tabela" style="min-width: 1400px;">
        <thead class="table-light">
          <tr>
            <th rowspan="2" class="align-middle text-start ps-3" style="min-width: 170px;">Nome Completo do Aluno</th>
            <th rowspan="2" class="align-middle" style="width: 45px;">Gén</th>
            ${thDisciplinas}
            <th colspan="3" class="bg-secondary bg-opacity-10 fw-bold" style="font-size: 0.72rem;">Médias Trimestrais</th>
            <th colspan="4" class="bg-secondary bg-opacity-10 fw-bold" style="font-size: 0.72rem;">Disciplinas Negativas</th>
            <th rowspan="2" class="align-middle bg-primary text-white fw-bold" style="width: 70px;">Média<br>Geral</th>
            <th rowspan="2" class="align-middle bg-secondary text-white fw-bold" style="width: 85px;">Resultado</th>
          </tr>
          <tr>
            ${thSubDisciplinas}
            <th style="font-size: 0.68rem;">1º</th>
            <th style="font-size: 0.68rem;">2º</th>
            <th style="font-size: 0.68rem;">3º</th>
            <th style="font-size: 0.68rem;">1º</th>
            <th style="font-size: 0.68rem;">2º</th>
            <th style="font-size: 0.68rem;">3º</th>
            <th style="font-size: 0.68rem;" class="bg-light fw-bold" title="Total de Disciplinas Negativas">Total</th>
          </tr>
        </thead>
        <tbody>
          ${trsAlunos}
        </tbody>
        <tfoot class="table-light">
          <tr class="table-secondary fw-bold text-start">
            <td colspan="${colSpanTotal}" class="ps-3 py-2">
              <div class="d-flex flex-wrap gap-4 align-items-center">
                <span>Total Inscritos: <strong>${totalInscritos}</strong> (H: ${homensInscritos} | M: ${mulheresInscritos})</span>
                <span>Avaliados: <strong>${totalAvaliados}</strong></span>
                <span class="text-success">Aprovados: <strong>${aprovadosTotal}</strong> (${aprovadosPct}%)</span>
                <span class="text-danger">Reprovados: <strong>${reprovadosTotal}</strong> (${reprovadosPct}%)</span>
              </div>
            </td>
          </tr>
        </tfoot>
      </table>
    `;
  } catch (err) {
    console.error('Erro ao carregar pauta geral da turma:', err);
    container.innerHTML = `<div class="alert alert-danger">Erro ao carregar pauta geral da turma: ${err.message || err}</div>`;
  }
}

async function carregarActaConselho(turmaId) {
  const container = document.getElementById('containerActaConselhoCorpo');
  if (!container) return;
  container.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div><p class="small text-muted mt-2">A carregar acta do conselho de avaliação...</p></div>';

  try {
    const savedParamsRaw = localStorage.getItem('sige_acta_params_' + turmaId);
    let cp = {};
    if (savedParamsRaw) {
      try {
        cp = JSON.parse(savedParamsRaw) || {};
        // Se continha os dados fictícios hardcoded de demonstração antigos, limpar para não poluir
        if (cp.dataT1 === '26/05/2026' && cp.dataT2 === '01/09/2026') {
          cp = {};
          localStorage.removeItem('sige_acta_params_' + turmaId);
        }
      } catch (e) {
        cp = {};
      }
    }

    const qParams = new URLSearchParams(cp).toString();
    const res = await apiFetch(`/api/v1/pautas/turma/${turmaId}/acta?${qParams}`);
    if (!res || !res.success) {
      container.innerHTML = '<div class="alert alert-warning text-center py-3">Não foi possível carregar a acta do conselho para esta turma.</div>';
      return;
    }
    const d = res.data || res;

    const te = d.tabelaEfectivo;
    const ta = d.tabelaAproveitamento;
    const escola = d.escola || { nome: 'Escola Secundária', provincia: 'Maputo', distrito: 'Cidade de Maputo' };
    const turma = d.turma || { nome: 'Turma', grau_ano: '', turno: 'Diurno' };
    const disciplinas = Array.isArray(d.disciplinas) ? d.disciplinas : [];

    const anoTurma = turma.ano_letivo || '2026';
    const dirTurma = (cp.directorTurma && cp.directorTurma.trim()) ? cp.directorTurma.trim() : (turma.director_turma?.nome || turma.director_turma || '_________________');
    const p1 = (cp.presidenteT1 && cp.presidenteT1.trim()) ? cp.presidenteT1.trim() : '_________________';
    const p2 = (cp.presidenteT2 && cp.presidenteT2.trim()) ? cp.presidenteT2.trim() : '_________________';
    const p3 = (cp.presidenteT3 && cp.presidenteT3.trim()) ? cp.presidenteT3.trim() : '_________________';

    const dt1 = formatarDataParaExibicao(cp.dataT1, anoTurma);
    const dt2 = formatarDataParaExibicao(cp.dataT2, anoTurma);
    const dt3 = formatarDataParaExibicao(cp.dataT3, anoTurma);

    const hIni1 = (cp.horaInicioT1 && cp.horaInicioT1.trim()) ? cp.horaInicioT1.trim() : '__';
    const mIni1 = (cp.minInicioT1 && cp.minInicioT1.trim()) ? cp.minInicioT1.trim() : '__';
    const hFim1 = (cp.horaFimT1 && cp.horaFimT1.trim()) ? cp.horaFimT1.trim() : '__';
    const mFim1 = (cp.minFimT1 && cp.minFimT1.trim()) ? cp.minFimT1.trim() : '__';

    const hIni2 = (cp.horaInicioT2 && cp.horaInicioT2.trim()) ? cp.horaInicioT2.trim() : '__';
    const mIni2 = (cp.minInicioT2 && cp.minInicioT2.trim()) ? cp.minInicioT2.trim() : '__';
    const hFim2 = (cp.horaFimT2 && cp.horaFimT2.trim()) ? cp.horaFimT2.trim() : '__';
    const mFim2 = (cp.minFimT2 && cp.minFimT2.trim()) ? cp.minFimT2.trim() : '__';

    const hIni3 = (cp.horaInicioT3 && cp.horaInicioT3.trim()) ? cp.horaInicioT3.trim() : '__';
    const mIni3 = (cp.minInicioT3 && cp.minInicioT3.trim()) ? cp.minInicioT3.trim() : '__';
    const hFim3 = (cp.horaFimT3 && cp.horaFimT3.trim()) ? cp.horaFimT3.trim() : '__';
    const mFim3 = (cp.minFimT3 && cp.minFimT3.trim()) ? cp.minFimT3.trim() : '__';

    const textoProtocolar = `Sob presidência do senhor professor <strong>${p1}</strong> (Iº Trimestre); <strong>${p2}</strong> (IIº Trimestre); <strong>${p3}</strong> (IIIº Trimestre); director/substituto do director de turma <strong>${dirTurma}</strong> da turma <strong>${turma.nome}</strong> do grupo da <strong>${turma.grau_ano}</strong>, curso <strong>${turma.turno === 'NOITE' ? 'Nocturno' : 'Diurno'}</strong>, realizou-se o Conselho de Avaliação do Iº; IIº, IIIº, Trimestre no dia <strong>${dt1}</strong>; <strong>${dt2}</strong>; <strong>${dt3}</strong>, com início às <strong>${hIni1}</strong> horas e <strong>${mIni1}</strong> minutos e com término às <strong>${hFim1}</strong> horas e <strong>${mFim1}</strong> minutos (Iº Trim); <strong>${hIni2}</strong> horas e <strong>${mIni2}</strong> minutos e com término às <strong>${hFim2}</strong> horas e <strong>${mFim2}</strong> minutos (IIº Trim); <strong>${hIni3}</strong> horas e <strong>${mIni3}</strong> minutos e com término às <strong>${hFim3}</strong> horas e <strong>${mFim3}</strong> minutos (IIIº Trim). No final deste conselho colheram-se os resultados que abaixo vão discriminados de todos os membros que participaram:`;

    const tc = d.trimestresComNotas || { t1: true, t2: false, t3: false, fimAno: false };

    // Renderizador das Linhas da Tabela 1 (Efectivos e Movimento por Género)
    const renderTeLinhas = (categoria, chave) => {
      return ['H', 'M', 'HM'].map((gen, gIdx) => {
        const prop = gen === 'H' ? 'h' : (gen === 'M' ? 'm' : 'hm');
        const pctProp = gen === 'H' ? 'pctH' : (gen === 'M' ? 'pctM' : 'pct');
        const isInicial = (chave === 'inscritos');

        // Iº Trimestre
        const temT1 = tc.t1 || isInicial;
        const vT1 = (temT1 && te?.t1?.[chave] && te.t1[chave][prop] !== undefined)
          ? te.t1[chave][prop]
          : (isInicial && te?.t1?.inscritos ? te.t1.inscritos[prop] : '-');
        const pT1 = (temT1 && te?.t1?.[chave] && te.t1[chave][pctProp] !== undefined)
          ? `${te.t1[chave][pctProp]}%`
          : (isInicial && vT1 !== '-' ? '100%' : '-');

        // IIº Trimestre (Para Matrículas/Efectivo Inicial, replica automaticamente os matriculados do início do ano)
        const temT2 = tc.t2 || isInicial;
        const vT2 = isInicial
          ? (te?.t2?.[chave]?.[prop] ?? vT1)
          : (temT2 && te?.t2?.[chave] ? te.t2[chave][prop] : '-');
        const pT2 = isInicial
          ? (te?.t2?.[chave]?.[pctProp] !== undefined ? `${te.t2[chave][pctProp]}%` : pT1)
          : (temT2 && te?.t2?.[chave] && te.t2[chave][pctProp] !== undefined ? `${te.t2[chave][pctProp]}%` : '-');

        // IIIº Trimestre (Para Matrículas/Efectivo Inicial, replica automaticamente os matriculados do início do ano)
        const temT3 = tc.t3 || isInicial;
        const vT3 = isInicial
          ? (te?.t3?.[chave]?.[prop] ?? vT1)
          : (temT3 && te?.t3?.[chave] ? te.t3[chave][prop] : '-');
        const pT3 = isInicial
          ? (te?.t3?.[chave]?.[pctProp] !== undefined ? `${te.t3[chave][pctProp]}%` : pT1)
          : (temT3 && te?.t3?.[chave] && te.t3[chave][pctProp] !== undefined ? `${te.t3[chave][pctProp]}%` : '-');

        // Fim do Ano (Para Matrículas/Efectivo Inicial, replica automaticamente os matriculados do início do ano)
        const temFA = tc.fimAno || isInicial;
        const vFA = isInicial
          ? (te?.fimAno?.[chave]?.[prop] ?? vT1)
          : (temFA && te?.fimAno?.[chave] ? te.fimAno[chave][prop] : '-');
        const pFA = isInicial
          ? (te?.fimAno?.[chave]?.[pctProp] !== undefined ? `${te.fimAno[chave][pctProp]}%` : pT1)
          : (temFA && te?.fimAno?.[chave] && te.fimAno[chave][pctProp] !== undefined ? `${te.fimAno[chave][pctProp]}%` : '-');

        const tdCat = gIdx === 0 ? `<td rowspan="3" class="text-start ps-2 fw-bold align-middle bg-light border-end">${categoria}</td>` : '';
        const bgCls = gen === 'HM' ? 'table-light fw-bold' : '';

        return `
          <tr class="${bgCls}">
            ${tdCat}
            <td class="fw-semibold text-center">${gen}</td>
            <td>${vT1}</td><td class="text-muted small">${pT1}</td>
            <td>${vT2}</td><td class="text-muted small">${pT2}</td>
            <td>${vT3}</td><td class="text-muted small">${pT3}</td>
            <td>${vFA}</td><td class="text-muted small">${pFA}</td>
          </tr>
        `;
      }).join('');
    };

    // Renderizador das Linhas da Tabela 2 (Aproveitamento Pedagógico por Género)
    const renderTaLinhas = (classificacao, chave, isAprov = false) => {
      return ['H', 'M', 'HM'].map((gen, gIdx) => {
        const prop = gen === 'H' ? 'h' : (gen === 'M' ? 'm' : 'hm');
        const pctProp = gen === 'H' ? 'pctH' : (gen === 'M' ? 'pctM' : 'pct');

        const temNotasT1 = tc.t1 && (ta?.t1?.avaliados?.hm > 0);
        const vT1 = temNotasT1 && ta?.t1?.[chave] ? ta.t1[chave][prop] : '-';
        const pT1 = temNotasT1 && ta?.t1?.[chave] && ta.t1[chave][pctProp] !== undefined ? `${ta.t1[chave][pctProp]}%` : (temNotasT1 && chave === 'avaliados' ? '100%' : '-');

        const temNotasT2 = tc.t2 && (ta?.t2?.avaliados?.hm > 0);
        const vT2 = temNotasT2 && ta?.t2?.[chave] ? ta.t2[chave][prop] : '-';
        const pT2 = temNotasT2 && ta?.t2?.[chave] && ta.t2[chave][pctProp] !== undefined ? `${ta.t2[chave][pctProp]}%` : (temNotasT2 && chave === 'avaliados' ? '100%' : '-');

        const temNotasT3 = tc.t3 && (ta?.t3?.avaliados?.hm > 0);
        const vT3 = temNotasT3 && ta?.t3?.[chave] ? ta.t3[chave][prop] : '-';
        const pT3 = temNotasT3 && ta?.t3?.[chave] && ta.t3[chave][pctProp] !== undefined ? `${ta.t3[chave][pctProp]}%` : (temNotasT3 && chave === 'avaliados' ? '100%' : '-');

        const temNotasFA = tc.fimAno && (ta?.fimAno?.avaliados?.hm > 0);
        const vFA = temNotasFA && ta?.fimAno?.[chave] ? ta.fimAno[chave][prop] : '-';
        const pFA = temNotasFA && ta?.fimAno?.[chave] && ta.fimAno[chave][pctProp] !== undefined ? `${ta.fimAno[chave][pctProp]}%` : (temNotasFA && chave === 'avaliados' ? '100%' : '-');

        // Cálculo de Crescimento condicionado
        let c1_2 = '<span class="text-muted">-</span>';
        if (temNotasT1 && temNotasT2) {
          const nPT1 = ta?.t1?.[chave] && ta.t1[chave][pctProp] ? Number(ta.t1[chave][pctProp]) : 0;
          const nPT2 = ta?.t2?.[chave] && ta.t2[chave][pctProp] ? Number(ta.t2[chave][pctProp]) : 0;
          const dif1_2 = Number((nPT2 - nPT1).toFixed(1));
          c1_2 = dif1_2 > 0 ? `<span class="badge bg-success bg-opacity-25 text-success">+${dif1_2}% Subiu</span>` : (dif1_2 < 0 ? `<span class="badge bg-danger bg-opacity-25 text-danger">${dif1_2}% Desceu</span>` : '<span class="text-muted">0%</span>');
        }

        let c2_3 = '<span class="text-muted">-</span>';
        if (temNotasT2 && temNotasT3) {
          const nPT2 = ta?.t2?.[chave] && ta.t2[chave][pctProp] ? Number(ta.t2[chave][pctProp]) : 0;
          const nPT3 = ta?.t3?.[chave] && ta.t3[chave][pctProp] ? Number(ta.t3[chave][pctProp]) : 0;
          const dif2_3 = Number((nPT3 - nPT2).toFixed(1));
          c2_3 = dif2_3 > 0 ? `<span class="badge bg-success bg-opacity-25 text-success">+${dif2_3}% Subiu</span>` : (dif2_3 < 0 ? `<span class="badge bg-danger bg-opacity-25 text-danger">${dif2_3}% Desceu</span>` : '<span class="text-muted">0%</span>');
        }

        let cGlo = '<span class="text-muted">-</span>';
        if (temNotasT1 && temNotasFA) {
          const nPT1 = ta?.t1?.[chave] && ta.t1[chave][pctProp] ? Number(ta.t1[chave][pctProp]) : 0;
          const nPFA = ta?.fimAno?.[chave] && ta.fimAno[chave][pctProp] ? Number(ta.fimAno[chave][pctProp]) : 0;
          const difGlo = Number((nPFA - nPT1).toFixed(1));
          cGlo = difGlo > 0 ? `<span class="badge bg-success bg-opacity-25 text-success">+${difGlo}% Subiu</span>` : (difGlo < 0 ? `<span class="badge bg-danger bg-opacity-25 text-danger">${difGlo}% Desceu</span>` : '<span class="text-muted">0%</span>');
        }

        const tdCat = gIdx === 0 ? `<td rowspan="3" class="text-start ps-2 fw-bold align-middle bg-light border-end ${isAprov ? 'text-success' : ''}">${classificacao}</td>` : '';
        const bgCls = isAprov ? 'table-success bg-opacity-25 fw-bold' : (gen === 'HM' ? 'table-light fw-bold' : '');

        return `
          <tr class="${bgCls}">
            ${tdCat}
            <td class="fw-semibold text-center">${gen}</td>
            <td>${vT1}</td><td class="text-muted small">${pT1}</td>
            <td>${vT2}</td><td class="text-muted small">${pT2}</td>
            <td>${vT3}</td><td class="text-muted small">${pT3}</td>
            <td>${vFA}</td><td class="text-muted small">${pFA}</td>
            <td class="text-center small">${c1_2}</td>
            <td class="text-center small">${c2_3}</td>
            <td class="text-center small">${cGlo}</td>
          </tr>
        `;
      }).join('');
    };

    container.innerHTML = `
      <!-- Cabeçalho Oficial Bordado da Acta (Imagem 1) -->
      <div class="border rounded p-3 mb-3 bg-light text-center shadow-sm" style="border-color: #1E3A8A !important;">
        <h6 class="fw-bold mb-0 text-uppercase tracking-wider">REPÚBLICA DE MOÇAMBIQUE</h6>
        <small class="text-muted d-block fw-semibold text-uppercase">GOVERNO DA PROVÍNCIA DE ${(escola.provincia || 'MAPUTO').toUpperCase()} | GOVERNO DO DISTRITO DE ${(escola.distrito || 'CIDADE DE MAPUTO').toUpperCase()}</small>
        <h5 class="fw-bold text-dark my-1">${(escola.nome || 'Escola Secundária').toUpperCase()}</h5>
        <small class="fw-bold text-primary text-uppercase">SECTOR PEDAGÓGICO — ACTA DO CONSELHO DE AVALIAÇÃO</small>
      </div>

      <!-- Texto Protocolar com Campos Editáveis (Fiel à Imagem 1) -->
      <div class="acta-texto-protocolar p-3 bg-white rounded border mb-2 shadow-sm text-dark" style="line-height: 1.45; text-align: justify; font-family: 'Times New Roman', serif; font-size: 0.90rem; border-color: #cbd5e1 !important; page-break-after: avoid !important; break-after: avoid !important; page-break-inside: avoid !important;">
        ${textoProtocolar}
      </div>

      <!-- TABELAS LADO A LADO SEGUNDO O MODELO OFICIAL (Imagem 1) - FLUXO CONTÍNUO SEM QUEBRA DE PÁGINA -->
      <div class="acta-tabelas-lado-a-lado row g-2 mb-3" style="page-break-before: avoid !important; break-before: avoid !important;">
        <!-- TABELA 1: Aproveitamento Escolar por Trimestres e Fim do Ano (Efectivos e Movimento) -->
        <div class="col-6">
          <div class="border rounded p-2 bg-white h-100 shadow-sm">
            <h6 class="fw-bold text-center small text-uppercase mb-2 py-2 rounded text-white" style="background: #1E3A8A;">Aproveitamento por Trimestres e Fim do Ano</h6>
            <div class="table-responsive">
              <table class="table table-bordered table-sm text-center mb-0 align-middle" style="font-size: 0.68rem;">
                <thead class="table-light">
                  <tr>
                    <th rowspan="2" class="align-middle text-start ps-2">CATEGORIA</th>
                    <th rowspan="2" class="align-middle">GÉN</th>
                    <th colspan="2">Iº TRIMESTRE</th>
                    <th colspan="2">IIº TRIMESTRE</th>
                    <th colspan="2">IIIº TRIMESTRE</th>
                    <th colspan="2">FIM DO ANO</th>
                  </tr>
                  <tr>
                    <th>Nº</th><th>%</th>
                    <th>Nº</th><th>%</th>
                    <th>Nº</th><th>%</th>
                    <th>Nº</th><th>%</th>
                  </tr>
                </thead>
                <tbody>
                  ${renderTeLinhas('Matrículas / Efectivo Inicial', 'inscritos')}
                  ${renderTeLinhas('Desistentes', 'desistentes')}
                  ${renderTeLinhas('Transferidos', 'transferidos')}
                  ${renderTeLinhas('Falecidos', 'falecidos')}
                  ${renderTeLinhas('Perdeu Ano por Faltas', 'perdeuFaltas')}
                  ${renderTeLinhas('Anulou Matrícula', 'anulouMatricula')}
                  ${renderTeLinhas('Alunos Avaliados', 'avaliados')}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- TABELA 2: Aproveitamento Pedagógico por Faixas e Crescimento -->
        <div class="col-6">
          <div class="border rounded p-2 bg-white h-100 shadow-sm">
            <h6 class="fw-bold text-center small text-uppercase mb-2 py-2 rounded text-white" style="background: #1E3A8A;">Aproveitamento Pedagógico</h6>
            <div class="table-responsive">
              <table class="table table-bordered table-sm text-center mb-0 align-middle" style="font-size: 0.68rem;">
                <thead class="table-light">
                  <tr>
                    <th rowspan="2" class="align-middle text-start ps-2">CLASSIFICAÇÃO</th>
                    <th rowspan="2" class="align-middle">GÉN</th>
                    <th colspan="2">Iº TRIMESTRE</th>
                    <th colspan="2">IIº TRIMESTRE</th>
                    <th colspan="2">IIIº TRIMESTRE</th>
                    <th colspan="2">FIM DO ANO</th>
                    <th colspan="3">CRESCIMENTO</th>
                  </tr>
                  <tr>
                    <th>Nº</th><th>%</th>
                    <th>Nº</th><th>%</th>
                    <th>Nº</th><th>%</th>
                    <th>Nº</th><th>%</th>
                    <th>Iº-IIº</th><th>IIº-IIIº</th><th>GLOBAL</th>
                  </tr>
                </thead>
                <tbody>
                  ${renderTaLinhas('Alunos Avaliados', 'avaliados')}
                  ${renderTaLinhas('Não Satisfatório (0 a 9,4)', 'naoSatisfatorio')}
                  ${renderTaLinhas('Satisfatório (9,5 a 13,4)', 'satisfatorio')}
                  ${renderTaLinhas('Bom (13,5 a 16,4)', 'bom')}
                  ${renderTaLinhas('Muito Bom (16,5 a 18,4)', 'muitoBom')}
                  ${renderTaLinhas('Excelente (18,5 a 20)', 'excelente')}
                  ${renderTaLinhas('TOTAL APROVADOS', 'aprovados', true)}
                  ${renderTaLinhas('TOTAL REPROVADOS', 'reprovados')}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- TABELA 3: Aproveitamento por Disciplina (Área de Comunicação e Ciências Sociais) -->
      <div class="border rounded p-3 bg-white mb-4 shadow-sm">
        <h6 class="fw-bold text-center small text-uppercase mb-2 py-2 rounded text-white" style="background: #1E3A8A;">Área Curricular & Estatística por Disciplina</h6>
        <div class="table-responsive">
          <table class="table table-bordered table-sm text-center mb-0 align-middle" style="font-size: 0.68rem;">
            <thead class="table-light">
              <tr>
                <th rowspan="2" class="align-middle text-start ps-2">CLASSIFICAÇÃO</th>
                ${d.disciplinas.map(dis => `<th colspan="3" class="fw-bold text-uppercase">${dis.nome}</th>`).join('')}
              </tr>
              <tr>
                ${d.disciplinas.map(() => '<th>H</th><th>M</th><th class="table-secondary">HM</th>').join('')}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="text-start ps-2 fw-semibold">[0 - 9,4 valores]</td>
                ${d.disciplinas.map(dis => `<td>${dis.faixa0_9?.h ?? 0}</td><td>${dis.faixa0_9?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.faixa0_9?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr>
                <td class="text-start ps-2 fw-semibold">[9,5 - 13,4 valores]</td>
                ${d.disciplinas.map(dis => `<td>${dis.faixa10_13?.h ?? 0}</td><td>${dis.faixa10_13?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.faixa10_13?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr>
                <td class="text-start ps-2 fw-semibold">[13,5 - 16,4 valores]</td>
                ${d.disciplinas.map(dis => `<td>${dis.faixa14_16?.h ?? 0}</td><td>${dis.faixa14_16?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.faixa14_16?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr>
                <td class="text-start ps-2 fw-semibold">[16,5 - 18,4 valores]</td>
                ${d.disciplinas.map(dis => `<td>${dis.faixa17_18?.h ?? 0}</td><td>${dis.faixa17_18?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.faixa17_18?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr>
                <td class="text-start ps-2 fw-semibold">[18,5 - 20 valores]</td>
                ${d.disciplinas.map(dis => `<td>${dis.faixa19_20?.h ?? 0}</td><td>${dis.faixa19_20?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.faixa19_20?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr class="table-light fw-bold">
                <td class="text-start ps-2">Alunos Avaliados</td>
                ${d.disciplinas.map(dis => `<td>${dis.avaliados?.h ?? 0}</td><td>${dis.avaliados?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.avaliados?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr class="table-success bg-opacity-25 fw-bold text-success">
                <td class="text-start ps-2">Notas Positivas</td>
                ${d.disciplinas.map(dis => `<td>${dis.positivas?.h ?? 0}</td><td>${dis.positivas?.m ?? 0}</td><td class="table-secondary fw-bold">${dis.positivas?.hm ?? 0}</td>`).join('')}
              </tr>
              <tr class="table-success bg-opacity-25 fw-bold text-success">
                <td class="text-start ps-2">% Positivas</td>
                ${d.disciplinas.map(dis => `<td>${dis.positivas?.pctH ?? 0}%</td><td>${dis.positivas?.pctM ?? 0}%</td><td class="table-secondary fw-bold">${dis.positivas?.pct ?? 0}%</td>`).join('')}
              </tr>
              <tr>
                <td class="text-start ps-2 text-muted fst-italic">Assinatura do Docente</td>
                ${d.disciplinas.map(() => '<td colspan="3" class="text-center text-muted fst-italic">_________________</td>').join('')}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = '<div class="alert alert-danger">Erro ao carregar acta do conselho de avaliação.</div>';
  }
}

function modalConfigurarSessaoActa() {
  const turmaId = document.getElementById('pautaTurmaSelect')?.value;
  if (!turmaId) return alert('Selecione uma turma para configurar a sessão da acta');

  const savedParamsRaw = localStorage.getItem('sige_acta_params_' + turmaId);
  let cp = {};
  if (savedParamsRaw) {
    try {
      cp = JSON.parse(savedParamsRaw) || {};
      if (cp.dataT1 === '26/05/2026' && cp.dataT2 === '01/09/2026') {
        cp = {};
        localStorage.removeItem('sige_acta_params_' + turmaId);
      }
    } catch (e) {
      cp = {};
    }
  }

  abrirModal('Configurar Dados da Sessão do Conselho de Avaliação', `
    <form id="formConfigSessaoActa" onsubmit="salvarConfigSessaoActa(event, '${turmaId}')">
      <div class="alert alert-info py-2 small">
        <i class="bi bi-info-circle me-1"></i> Todos os campos abaixo são <strong>estritamente opcionais</strong>. Se deixados em branco, o sistema utilizará as linhas pontilhadas oficiais para preenchimento manual ou posterior para cada trimestre.
      </div>

      <!-- Director de Turma / Secretário -->
      <div class="card p-3 mb-3 bg-light border-0 shadow-sm">
        <h6 class="fw-bold text-dark mb-2"><i class="bi bi-person-badge me-1"></i> Director de Turma / Secretário (Opcional)</h6>
        <div class="row g-2">
          <div class="col-12">
            <label class="form-label small text-muted">Nome do Director / Substituto (Opcional)</label>
            <input type="text" id="cfgDirectorTurma" class="form-control form-control-sm" value="${cp.directorTurma || ''}" placeholder="Deixe em branco ou nome do director">
          </div>
        </div>
      </div>
      
      <!-- 1º Trimestre -->
      <div class="card p-3 mb-3 bg-light border-0 shadow-sm">
        <h6 class="fw-bold text-primary mb-2">1º Trimestre Lectivo (Opcional)</h6>
        <div class="row g-2">
          <div class="col-md-6">
            <label class="form-label small text-muted">Presidente da Sessão (Opcional)</label>
            <input type="text" id="cfgPresT1" class="form-control form-control-sm" value="${cp.presidenteT1 || ''}" placeholder="Deixe em branco até à realização">
          </div>
          <div class="col-md-6">
            <label class="form-label small text-muted">Data da Realização (Opcional)</label>
            <input type="date" id="cfgDataT1" class="form-control form-control-sm" value="${formatarParaInputDate(cp.dataT1)}">
          </div>
          <div class="col-md-6">
            <label class="form-label small text-muted">Horário Início (Horas : Min)</label>
            <div class="input-group input-group-sm">
              <input type="text" id="cfgHIniT1" class="form-control text-center" value="${cp.horaInicioT1 || ''}" placeholder="HH" maxlength="2">
              <span class="input-group-text">:</span>
              <input type="text" id="cfgMIniT1" class="form-control text-center" value="${cp.minInicioT1 || ''}" placeholder="MM" maxlength="2">
            </div>
          </div>
          <div class="col-md-6">
            <label class="form-label small text-muted">Horário Término (Horas : Min)</label>
            <div class="input-group input-group-sm">
              <input type="text" id="cfgHFimT1" class="form-control text-center" value="${cp.horaFimT1 || ''}" placeholder="HH" maxlength="2">
              <span class="input-group-text">:</span>
              <input type="text" id="cfgMFimT1" class="form-control text-center" value="${cp.minFimT1 || ''}" placeholder="MM" maxlength="2">
            </div>
          </div>
        </div>
      </div>

      <!-- 2º Trimestre -->
      <div class="card p-3 mb-3 bg-light border-0 shadow-sm">
        <h6 class="fw-bold text-info mb-2">2º Trimestre Lectivo (Opcional)</h6>
        <div class="row g-2">
          <div class="col-md-6">
            <label class="form-label small text-muted">Presidente da Sessão (Opcional)</label>
            <input type="text" id="cfgPresT2" class="form-control form-control-sm" value="${cp.presidenteT2 || ''}" placeholder="Deixe em branco até à realização">
          </div>
          <div class="col-md-6">
            <label class="form-label small text-muted">Data da Realização (Opcional)</label>
            <input type="date" id="cfgDataT2" class="form-control form-control-sm" value="${formatarParaInputDate(cp.dataT2)}">
          </div>
          <div class="col-md-6">
            <label class="form-label small text-muted">Horário Início (Horas : Min)</label>
            <div class="input-group input-group-sm">
              <input type="text" id="cfgHIniT2" class="form-control text-center" value="${cp.horaInicioT2 || ''}" placeholder="HH" maxlength="2">
              <span class="input-group-text">:</span>
              <input type="text" id="cfgMIniT2" class="form-control text-center" value="${cp.minInicioT2 || ''}" placeholder="MM" maxlength="2">
            </div>
          </div>
          <div class="col-md-6">
            <label class="form-label small text-muted">Horário Término (Horas : Min)</label>
            <div class="input-group input-group-sm">
              <input type="text" id="cfgHFimT2" class="form-control text-center" value="${cp.horaFimT2 || ''}" placeholder="HH" maxlength="2">
              <span class="input-group-text">:</span>
              <input type="text" id="cfgMFimT2" class="form-control text-center" value="${cp.minFimT2 || ''}" placeholder="MM" maxlength="2">
            </div>
          </div>
        </div>
      </div>

      <!-- 3º Trimestre -->
      <div class="card p-3 mb-3 bg-light border-0 shadow-sm">
        <h6 class="fw-bold text-secondary mb-2">3º Trimestre Lectivo (Opcional)</h6>
        <div class="row g-2">
          <div class="col-md-6">
            <label class="form-label small text-muted">Presidente da Sessão (Opcional)</label>
            <input type="text" id="cfgPresT3" class="form-control form-control-sm" value="${cp.presidenteT3 || ''}" placeholder="Deixe em branco até à realização">
          </div>
          <div class="col-md-6">
            <label class="form-label small text-muted">Data da Realização (Opcional)</label>
            <input type="date" id="cfgDataT3" class="form-control form-control-sm" value="${formatarParaInputDate(cp.dataT3)}">
          </div>
          <div class="col-md-6">
            <label class="form-label small text-muted">Horário Início (Horas : Min)</label>
            <div class="input-group input-group-sm">
              <input type="text" id="cfgHIniT3" class="form-control text-center" value="${cp.horaInicioT3 || ''}" placeholder="HH" maxlength="2">
              <span class="input-group-text">:</span>
              <input type="text" id="cfgMIniT3" class="form-control text-center" value="${cp.minInicioT3 || ''}" placeholder="MM" maxlength="2">
            </div>
          </div>
          <div class="col-md-6">
            <label class="form-label small text-muted">Horário Término (Horas : Min)</label>
            <div class="input-group input-group-sm">
              <input type="text" id="cfgHFimT3" class="form-control text-center" value="${cp.horaFimT3 || ''}" placeholder="HH" maxlength="2">
              <span class="input-group-text">:</span>
              <input type="text" id="cfgMFimT3" class="form-control text-center" value="${cp.minFimT3 || ''}" placeholder="MM" maxlength="2">
            </div>
          </div>
        </div>
      </div>

      <div class="d-flex justify-content-between align-items-center gap-2">
        <button type="button" class="btn btn-outline-secondary btn-sm" onclick="limparConfigSessaoActa('${turmaId}')">
          <i class="bi bi-eraser me-1"></i> Limpar / Deixar em Branco
        </button>
        <div class="d-flex gap-2">
          <button type="button" class="btn btn-secondary btn-sm" onclick="fecharModal()">Cancelar</button>
          <button type="submit" class="btn btn-primary btn-sm"><i class="bi bi-check-lg me-1"></i> Salvar e Actualizar Acta</button>
        </div>
      </div>
    </form>
  `);
}

function limparConfigSessaoActa(turmaId) {
  localStorage.removeItem('sige_acta_params_' + turmaId);
  fecharModal();
  carregarActaConselho(turmaId);
}

function salvarConfigSessaoActa(e, turmaId) {
  e.preventDefault();
  const params = {
    directorTurma: document.getElementById('cfgDirectorTurma')?.value?.trim() || '',

    presidenteT1: document.getElementById('cfgPresT1')?.value?.trim() || '',
    dataT1: document.getElementById('cfgDataT1')?.value?.trim() || '',
    horaInicioT1: document.getElementById('cfgHIniT1')?.value?.trim() || '',
    minInicioT1: document.getElementById('cfgMIniT1')?.value?.trim() || '',
    horaFimT1: document.getElementById('cfgHFimT1')?.value?.trim() || '',
    minFimT1: document.getElementById('cfgMFimT1')?.value?.trim() || '',

    presidenteT2: document.getElementById('cfgPresT2')?.value?.trim() || '',
    dataT2: document.getElementById('cfgDataT2')?.value?.trim() || '',
    horaInicioT2: document.getElementById('cfgHIniT2')?.value?.trim() || '',
    minInicioT2: document.getElementById('cfgMIniT2')?.value?.trim() || '',
    horaFimT2: document.getElementById('cfgHFimT2')?.value?.trim() || '',
    minFimT2: document.getElementById('cfgMFimT2')?.value?.trim() || '',

    presidenteT3: document.getElementById('cfgPresT3')?.value?.trim() || '',
    dataT3: document.getElementById('cfgDataT3')?.value?.trim() || '',
    horaInicioT3: document.getElementById('cfgHIniT3')?.value?.trim() || '',
    minInicioT3: document.getElementById('cfgMIniT3')?.value?.trim() || '',
    horaFimT3: document.getElementById('cfgHFimT3')?.value?.trim() || '',
    minFimT3: document.getElementById('cfgMFimT3')?.value?.trim() || ''
  };

  localStorage.setItem('sige_acta_params_' + turmaId, JSON.stringify(params));
  fecharModal();
  carregarActaConselho(turmaId);
}

async function exportarActaConselhoExcel(turmaIdExplicit = null, anoExplicit = null, orientacaoExplicit = null) {
  const turmaId = await obterTurmaAtivaOuPrimeira(turmaIdExplicit);
  if (!turmaId) return;
  const ano = anoExplicit || document.getElementById('pautaAnoFiltro')?.value || '2026';
  const orientacao = orientacaoExplicit || document.getElementById('pautaOrientacaoSelect')?.value || 'landscape';

  const savedParamsRaw = localStorage.getItem('sige_acta_params_' + turmaId);
  const cp = savedParamsRaw ? JSON.parse(savedParamsRaw) : {};
  const qParams = new URLSearchParams({ anoLetivo: ano, orientacao: orientacao, ...cp }).toString();

  await downloadFicheiroBinario(`/api/v1/pautas/turma/${turmaId}/acta-xlsx?${qParams}`, `Acta_Conselho_Turma_${ano}.xlsx`);
}

function imprimirActaConselhoOficial() {
  const orientacao = document.getElementById('pautaOrientacaoSelect')?.value || 'portrait';
  document.body.classList.remove('print-orientacao-landscape', 'print-orientacao-portrait');
  document.body.classList.add(orientacao === 'landscape' ? 'print-orientacao-landscape' : 'print-orientacao-portrait');
  window.print();
}

async function modalGerarPauta() {
  const turmasRes = await apiFetch('/api/v1/escola-admin/turmas');
  const optTurmas = (turmasRes.data || []).map(t => `<option value="${t.id}">${t.nome} (${t.grau_ano})</option>`
  ).join('');

  abrirModal('Consolidar Pauta Oficial de Turma', `
    <form id="formModalPauta">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Turma a Consolidar</label>
        <select id="mpautTurma" class="form-select">${optTurmas}</select>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Período Lectivo</label>
        <select id="mpautPeriodo" class="form-select">
          <option value="1_TRIMESTRE">1º Trimestre</option>
          <option value="2_TRIMESTRE">2º Trimestre</option>
          <option value="3_TRIMESTRE">3º Trimestre</option>
          <option value="ANUAL">Pauta Anual Consolidada Final</option>
        </select>
      </div>
      <button type="submit" class="btn btn-primary w-100">Gerar Pauta Oficial</button>
    </form>
  `);

  document.getElementById('formModalPauta').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch('/api/v1/pautas/gerar', {
        method: 'POST',
        body: JSON.stringify({
          turma_id: document.getElementById('mpautTurma').value,
          periodo: document.getElementById('mpautPeriodo').value,
          ano_letivo: '2026'
        })
      });
      if (res.success) {
        fecharModal();
        alternarVisualizacaoPautaTurma();
      }
    } catch (err) {
      alert(err.message || 'Erro ao gerar pauta');
    }
  });
}

