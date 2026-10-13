/**
 * SIGE - PAINEL-ALUNO | O Meu Perfil & Filiação
 * Ficheiro de código independente do menu: aluno-perfil.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
async function carregarAlunoPerfil() {
  try {
    const res = await apiFetch('/api/v1/alunos/perfil/me');
    if (res.success) {
      const a = res.data;
      if (document.getElementById('alunoPerfilNome')) document.getElementById('alunoPerfilNome').textContent = a.nome;
      if (document.getElementById('alunoPerfilApelido')) document.getElementById('alunoPerfilApelido').textContent = a.apelido || '-';
      if (document.getElementById('alunoPerfilMatricula')) document.getElementById('alunoPerfilMatricula').textContent = a.matricula;
      if (document.getElementById('alunoPerfilTurma')) document.getElementById('alunoPerfilTurma').textContent = a.turma ? `${a.turma.nome} (${a.turma.grau_ano})` : 'Sem Turma';
      if (document.getElementById('alunoPerfilDoc')) document.getElementById('alunoPerfilDoc').textContent = `${a.tipo_documento || 'BI'}: ${a.numero_documento || '-'}`;
      if (document.getElementById('alunoPerfilNUIT')) document.getElementById('alunoPerfilNUIT').textContent = a.nuit || '-';
      if (document.getElementById('alunoPerfilLocal')) document.getElementById('alunoPerfilLocal').textContent = `${a.distrito || '-'}, ${a.provincia || '-'}`;

      if (document.getElementById('alunoPerfilPai')) document.getElementById('alunoPerfilPai').textContent = a.pai || '-';
      if (document.getElementById('alunoPerfilMae')) document.getElementById('alunoPerfilMae').textContent = a.mae || '-';
      if (document.getElementById('alunoPerfilDataNasc')) {
        document.getElementById('alunoPerfilDataNasc').textContent = a.data_nascimento 
          ? new Date(a.data_nascimento).toLocaleDateString('pt-MZ') 
          : '-';
      }
      if (document.getElementById('alunoPerfilResp')) document.getElementById('alunoPerfilResp').textContent = a.nome_responsavel || '-';
      if (document.getElementById('alunoPerfilTelResp')) document.getElementById('alunoPerfilTelResp').textContent = a.contato_responsavel || '-';
      if (document.getElementById('alunoPerfilEmailResp')) document.getElementById('alunoPerfilEmailResp').textContent = a.email_responsavel || '-';
    }
  } catch (err) {
    console.warn('Erro ao carregar perfil do aluno:', err);
  }
}
