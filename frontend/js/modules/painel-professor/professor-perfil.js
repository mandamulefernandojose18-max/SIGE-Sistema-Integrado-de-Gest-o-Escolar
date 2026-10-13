/**
 * SIGE - PAINEL-PROFESSOR | Meu Perfil Docente
 * Ficheiro de código independente do menu: professor-perfil.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
// Perfil Docente
async function carregarPerfilDocente() {
  try {
    const res = await apiFetch('/api/v1/professores/meu-perfil');
    if (res && res.success && res.data) {
      const p = res.data;
      if (document.getElementById('profPerfilNome')) document.getElementById('profPerfilNome').textContent = p.nome || '-';
      if (document.getElementById('profPerfilEmail')) document.getElementById('profPerfilEmail').textContent = p.email || '-';
      if (document.getElementById('profPerfilTelefone')) document.getElementById('profPerfilTelefone').textContent = p.telefone || '-';
      if (document.getElementById('profPerfilNuit')) document.getElementById('profPerfilNuit').textContent = p.nuit || '-';
      if (document.getElementById('profPerfilFormacao')) document.getElementById('profPerfilFormacao').textContent = p.grau_academico || '-';
    }
  } catch (err) {
    console.warn('Erro ao carregar perfil docente:', err);
  }
}

