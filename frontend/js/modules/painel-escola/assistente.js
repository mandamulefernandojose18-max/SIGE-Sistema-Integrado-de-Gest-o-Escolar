// Assistente Virtual (nível 0) — só leitura. API: POST /api/v1/assistente/perguntar/
// Conversa em caixa de altura fixa com rolagem; guarda só as últimas mensagens (altura constante para qualquer n).
const assState = { alunoId: '', alunoNome: '', msgs: [] };
const ASS_MAX_MSGS = 30;
const ASS_SUGESTOES = [
  'Quantas faltas tem o aluno?',
  'Há propinas em atraso?',
  'Como se calcula a média trimestral (MT)?',
  'Como se calcula a média final da disciplina (MFD)?',
  'Quais são as regras de aprovação?',
  'Como funcionam as faltas em aula dupla?'
];

function assEhProprio() { return ['ALUNO', 'ENCARREGADO'].includes(state.user?.role); }
function assLista(res) { return res?.data || res?.results || (Array.isArray(res) ? res : []); }

function assRender() {
  const box = document.getElementById('assConversa');
  if (!box) return;
  if (!assState.msgs.length) {
    box.innerHTML = '<p class="text-muted small mb-0">Olá! Faça uma pergunta ou escolha uma sugestão abaixo.</p>';
    return;
  }
  box.innerHTML = assState.msgs.map(m => m.de === 'eu'
    ? `<div class="d-flex justify-content-end mb-2"><div class="bg-primary text-white rounded-3 px-3 py-2 small" style="max-width: 85%;">${escapeHtml(m.texto)}</div></div>`
    : `<div class="d-flex justify-content-start mb-2"><div class="bg-white border rounded-3 px-3 py-2 small" style="max-width: 85%;"><i class="bi bi-robot text-primary me-1"></i>${escapeHtml(m.texto)}</div></div>`
  ).join('');
  box.scrollTop = box.scrollHeight;
}

function assAdicionar(de, texto) {
  assState.msgs.push({ de, texto });
  if (assState.msgs.length > ASS_MAX_MSGS) assState.msgs.splice(0, assState.msgs.length - ASS_MAX_MSGS);
  assRender();
}

function assIniciar() {
  document.getElementById('assAlunoCard').style.display = assEhProprio() ? 'none' : '';
  const sug = document.getElementById('assSugestoes');
  sug.innerHTML = ASS_SUGESTOES.map((s, i) =>
    `<button type="button" class="btn btn-sm btn-outline-secondary py-0" onclick="assUsarSugestao(${i})">${escapeHtml(s)}</button>`).join('');
  assRender();
}

window.assUsarSugestao = function (i) {
  document.getElementById('assPergunta').value = ASS_SUGESTOES[i];
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
  assAdicionar('eu', pergunta);
  const btn = document.getElementById('assBtnEnviar');
  btn.disabled = true;
  try {
    const corpo = { pergunta };
    if (assState.alunoId && !assEhProprio()) corpo.aluno_id = assState.alunoId;
    const res = await apiFetch('/api/v1/assistente/perguntar/', { method: 'POST', body: JSON.stringify(corpo) });
    assAdicionar('bot', res?.resposta || 'Sem resposta.');
  } catch (e) {
    assAdicionar('bot', 'Não foi possível obter resposta: ' + (e.message || 'erro desconhecido'));
  } finally {
    btn.disabled = false;
    campo.focus();
  }
};

assIniciar();
