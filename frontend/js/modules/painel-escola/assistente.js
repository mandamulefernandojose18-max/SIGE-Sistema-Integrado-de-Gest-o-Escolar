// Assistente Virtual (nível 0) — só leitura. API: /api/v1/assistente/{perguntar,sugestoes,feedback}/
// Conversa em caixa de altura fixa com rolagem; guarda só as últimas mensagens (altura constante para qualquer n).
const assState = { alunoId: '', alunoNome: '', msgs: [], pagina: '', anterior: '' };
const ASS_SEM_SEGUIMENTO = ['desconhecida', 'fora_do_painel', 'navegacao', 'escolher_escola'];
const ASS_MAX_MSGS = 30;

function assEhProprio() { return ['ALUNO', 'ENCARREGADO'].includes(state.user?.role); }
function assLista(res) { return res?.data || res?.results || (Array.isArray(res) ? res : []); }

// O destino do atalho só aparece se existir no menu do perfil actual (cada painel mostra só o que o perfil pode ver).
function assDestinoPermitido(destino) {
  try {
    const role = state.user?.role || '';
    const painel = (typeof MAPA_PAINEIS !== 'undefined' && MAPA_PAINEIS[role]) || 'painel-escola';
    const menus = (typeof MENUS_POR_PAINEL !== 'undefined' && MENUS_POR_PAINEL[painel]) || [];
    return menus.some(m => m.id === destino);
  } catch (e) {
    return false;
  }
}

function assRender() {
  const box = document.getElementById('assConversa');
  if (!box) return;
  if (!assState.msgs.length) {
    box.innerHTML = '<p class="text-muted small mb-0">Olá! Faça uma pergunta ou escolha uma sugestão abaixo.</p>';
    return;
  }
  box.innerHTML = assState.msgs.map((m, i) => {
    if (m.de === 'eu') {
      return `<div class="d-flex justify-content-end mb-2"><div class="bg-primary text-white rounded-3 px-3 py-2 small" style="max-width: 85%;">${escapeHtml(m.texto)}</div></div>`;
    }
    const acao = m.acao && assDestinoPermitido(m.acao.destino)
      ? `<div class="mt-2"><button type="button" class="btn btn-sm btn-outline-primary py-0" onclick="assAbrir('${escapeHtml(m.acao.destino)}')"><i class="bi bi-box-arrow-up-right me-1"></i>${escapeHtml(m.acao.rotulo)}</button></div>` : '';
    const candidatos = (m.candidatos || []).map((c, j) =>
      `<button type="button" class="btn btn-sm btn-outline-secondary py-0 me-1 mt-1" onclick="assEscolherCandidato(${i}, ${j})">${escapeHtml(c.nome)}</button>`).join('');
    const util = m.consulta
      ? `<div class="mt-1 small text-muted">${m.util === undefined
        ? `Foi útil? <a href="javascript:void(0)" class="text-decoration-none ms-1" onclick="assUtil(${i}, true)" title="Foi útil">👍</a> <a href="javascript:void(0)" class="text-decoration-none ms-1" onclick="assUtil(${i}, false)" title="Não ajudou">👎</a>`
        : (m.util ? 'Obrigado pelo feedback.' : 'Obrigado — vamos melhorar esta resposta.')}</div>` : '';
    return `<div class="d-flex justify-content-start mb-2"><div class="bg-white border rounded-3 px-3 py-2 small" style="max-width: 85%;"><i class="bi bi-robot text-primary me-1"></i>${escapeHtml(m.texto)}${candidatos ? `<div>${candidatos}</div>` : ''}${acao}${util}</div></div>`;
  }).join('');
  box.scrollTop = box.scrollHeight;
}

function assAdicionar(msg) {
  assState.msgs.push(msg);
  if (assState.msgs.length > ASS_MAX_MSGS) assState.msgs.splice(0, assState.msgs.length - ASS_MAX_MSGS);
  assRender();
}

function assRenderSugestoes(lista) {
  const sug = document.getElementById('assSugestoes');
  if (!sug) return;
  assState.sugestoes = Array.isArray(lista) ? lista.slice(0, 6) : [];
  sug.innerHTML = assState.sugestoes.map((s, i) =>
    `<button type="button" class="btn btn-sm btn-outline-secondary py-0" onclick="assUsarSugestao(${i})">${escapeHtml(s)}</button>`).join('');
}

function assEhEncarregado() { return state.user?.role === 'ENCARREGADO'; }

// Encarregado: em vez de pesquisar, escolhe entre os educandos que a escola associou à sua conta.
async function assCarregarEducandos() {
  const sel = document.getElementById('assAluno');
  document.getElementById('assBuscaGrupo').style.display = 'none';
  document.getElementById('assAlunoRotulo').textContent = 'Educando a que as perguntas se referem';
  let lista = [];
  try {
    lista = (await apiFetch('/api/v1/assistente/educandos/'))?.educandos || [];
  } catch (e) { /* sem lista: o assistente pede para escolher quando for preciso */ }
  if (!lista.length) {
    sel.innerHTML = '<option value="">Nenhum educando associado à sua conta</option>';
    return;
  }
  sel.innerHTML = (lista.length > 1 ? '<option value="">Escolha o educando</option>' : '') +
    lista.map(a => `<option value="${escapeHtml(a.id)}">${escapeHtml(a.nome)}${a.classe ? ' — ' + escapeHtml(a.classe) : ''}</option>`).join('');
  if (lista.length === 1) sel.selectedIndex = 0;
  assEscolherAluno();
}

// Painel "Merece atenção": alertas reais do perfil (calculados no servidor). Sem alertas, diz que não há nada a assinalar.
const ASS_COR_ALERTA = { alta: 'danger', media: 'warning', info: 'secondary' };
window.assRenderAlertas = function () {
  const box = document.getElementById('assAlertas');
  if (!box) return;
  const lista = window._sigeAlertas?.lista || [];
  if (!lista.length) { box.innerHTML = '<span class="small text-muted">Nada a assinalar neste momento.</span>'; return; }
  box.innerHTML = lista.map(a => {
    const botao = a.destino && assDestinoPermitido(a.destino)
      ? `<button type="button" class="btn btn-sm btn-outline-primary py-0 ms-2" onclick="assAbrir('${escapeHtml(a.destino)}')">${escapeHtml(a.rotulo || 'Abrir')}</button>` : '';
    return `<div class="d-flex align-items-start gap-2 py-1 border-bottom small">
      <span class="badge bg-${ASS_COR_ALERTA[a.nivel] || 'secondary'} mt-1">&nbsp;</span>
      <div class="flex-grow-1"><strong>${escapeHtml(a.titulo)}</strong>${a.detalhe ? `<div class="text-muted">${escapeHtml(a.detalhe)}</div>` : ''}</div>${botao}</div>`;
  }).join('');
};

async function assIniciar() {
  if (typeof sigeAtualizarAlertas === 'function') sigeAtualizarAlertas(true);
  assRenderAlertas();
  // Aluno: sem escolha de aluno. Super Admin em modo plataforma (sem escola em inspecção): sem alunos, só dados da plataforma.
  const modoPlataforma = state.user?.role === 'SUPERADMIN' && !localStorage.getItem('sige_selected_tenant');
  document.getElementById('assAlunoCard').style.display = ((assEhProprio() && !assEhEncarregado()) || modoPlataforma) ? 'none' : '';
  if (assEhEncarregado()) assCarregarEducandos();
  assState.pagina = String(window._sigeUltimaPagina || '').replace(/[^a-z0-9-]/g, '').slice(0, 60);
  assRender();
  try {
    const res = await apiFetch('/api/v1/assistente/sugestoes/' + (assState.pagina ? `?pagina=${encodeURIComponent(assState.pagina)}` : ''));
    assRenderSugestoes(res?.sugestoes);
  } catch (e) {
    assRenderSugestoes(['Como se calcula a média trimestral (MT)?', 'Quais são as regras de aprovação?']);
  }
}

window.assUsarSugestao = function (i) {
  document.getElementById('assPergunta').value = (assState.sugestoes || [])[i] || '';
  assEnviar();
};

window.assAbrir = function (destino) {
  if (typeof navegarPara === 'function') navegarPara(destino);
};

window.assUtil = async function (i, util) {
  const m = assState.msgs[i];
  if (!m || !m.consulta || m.util !== undefined) return;
  m.util = util;
  assRender();
  try {
    await apiFetch('/api/v1/assistente/feedback/', { method: 'POST', body: JSON.stringify({ consulta_id: m.consulta, util }) });
  } catch (e) { /* o feedback é opcional: não interrompe a conversa */ }
};

// Vários alunos com o mesmo nome: o utilizador escolhe um e a pergunta anterior continua com esse aluno.
window.assEscolherCandidato = function (i, j) {
  const c = assState.msgs[i]?.candidatos?.[j];
  if (!c) return;
  const sel = document.getElementById('assAluno');
  if (sel && (!assEhProprio() || assEhEncarregado())) {
    if (![...sel.options].some(o => o.value === c.id)) sel.insertAdjacentHTML('beforeend', `<option value="${escapeHtml(c.id)}">${escapeHtml(c.nome)}</option>`);
    sel.value = c.id;
    assEscolherAluno();
  }
  document.getElementById('assPergunta').value = c.nome;
  assEnviar();
};

window.assBuscarAluno = async function () {
  const termo = document.getElementById('assBusca').value.trim();
  const sel = document.getElementById('assAluno');
  if (termo.length < 2) { mostrarToast('Escreva pelo menos 2 letras.', 'warning'); return; }
  try {
    const res = await apiFetch(`/api/v1/alunos/?search=${encodeURIComponent(termo)}&status=ATIVO&limit=10`);
    const itens = assLista(res);
    sel.innerHTML = '<option value="">Nenhum aluno escolhido</option>' + itens.map(a =>
      `<option value="${escapeHtml(a.id)}">${escapeHtml(a.nome)} (${escapeHtml(a.matricula)})</option>`).join('');
    if (!itens.length) mostrarToast('Nenhum aluno encontrado.', 'info');
  } catch (e) {
    mostrarToast('Erro na pesquisa: ' + e.message, 'danger');
  }
};

window.assEscolherAluno = function () {
  const sel = document.getElementById('assAluno');
  assState.alunoId = sel.value;
  assState.alunoNome = sel.value ? sel.options[sel.selectedIndex].text : '';
};

window.assEnviar = async function () {
  const campo = document.getElementById('assPergunta');
  const pergunta = campo.value.trim();
  if (!pergunta) return;
  campo.value = '';
  assAdicionar({ de: 'eu', texto: pergunta });
  const btn = document.getElementById('assBtnEnviar');
  btn.disabled = true;
  try {
    const corpo = { pergunta };
    if (assState.alunoId && (!assEhProprio() || assEhEncarregado())) corpo.aluno_id = assState.alunoId;
    if (assState.pagina) corpo.pagina = assState.pagina;
    if (assState.anterior) corpo.anterior = assState.anterior;     // permite perguntas de seguimento ("e do João?")
    const res = await apiFetch('/api/v1/assistente/perguntar/', { method: 'POST', body: JSON.stringify(corpo) });
    if (res?.intencao && !ASS_SEM_SEGUIMENTO.includes(res.intencao)) assState.anterior = res.intencao;
    assAdicionar({ de: 'bot', texto: res?.resposta || 'Sem resposta.', acao: res?.acao || null, consulta: res?.consulta_id || '', candidatos: res?.candidatos || null });
    if (res?.precisa_aluno) (assEhEncarregado() ? document.getElementById('assAluno') : document.getElementById('assBusca'))?.focus();
    if (Array.isArray(res?.sugestoes) && res.sugestoes.length) assRenderSugestoes(res.sugestoes);
  } catch (e) {
    assAdicionar({ de: 'bot', texto: 'Não foi possível obter resposta: ' + (e.message || 'erro desconhecido') });
  } finally {
    btn.disabled = false;
    campo.focus();
  }
};

// Chamado pelo router sempre que o ecrã é aberto (actualiza o contexto da página anterior e as sugestões).
window.assIniciar = assIniciar;
