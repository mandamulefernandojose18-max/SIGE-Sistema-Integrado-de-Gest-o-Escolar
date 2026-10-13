/**
 * SIGE - PAINEL-ESCOLA | Certificados Oficiais
 * Ficheiro de código independente do menu: certificados.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
// ==================== 9. CERTIFICADOS (QR CODE) ====================
async function carregarCertificados() {
  try {
    const res = await apiFetch('/api/v1/certificados');
    if (res.success) {
      const tbody = document.getElementById('tabelaCertificados');
      tbody.innerHTML = res.data.map(c => `
        <tr>
          <td><code class="text-primary">${c.codigo_autenticidade}</code></td>
          <td><strong>${c.aluno.nome}</strong></td>
          <td><span class="badge bg-light text-dark border">${c.tipo}</span></td>
          <td>${new Date(c.emitido_em).toLocaleDateString('pt-PT')}</td>
          <td>
            <img src="${c.qrcode_data}" alt="QR" width="38" height="38" class="border rounded" style="cursor: pointer;" onclick="verQrCodeGrande('${c.qrcode_data}', '${c.codigo_autenticidade}')">
          </td>
          <td class="text-end">
            <div class="btn-group btn-group-sm">
              <button class="btn btn-primary" onclick="descarregarDocumentoOficialPdf('CERTIFICADO', '${c.aluno.id}')" title="Descarregar Certificado Oficial em PDF">
                <i class="bi bi-file-earmark-pdf me-1"></i> PDF
              </button>
              <a href="/verificar-certificado.html?codigo=${c.codigo_autenticidade}" target="_blank" class="btn btn-outline-primary">
                <i class="bi bi-shield-check me-1"></i> Validar
              </a>
            </div>
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {}
}

function verQrCodeGrande(qrSrc, codigo) {
  abrirModal('Autenticação Digital por QR Code', `
    <div class="text-center p-3">
      <img src="${qrSrc}" width="220" height="220" class="img-fluid border rounded p-2 mb-3 shadow-sm">
      <p class="font-monospace small text-muted">${codigo}</p>
      <div class="alert alert-info small mb-0">
        Qualquer cidadão ou instituição pode ler este QR Code com a câmara do telemóvel para certificar a autenticidade deste documento emitido pelo SIGE.
      </div>
    </div>
  `);
}

async function modalEmitirCertificado() {
  const alunosRes = await apiFetch('/api/v1/alunos');
  const optAlunos = (alunosRes.data || []).map(a => `<option value="${a.id}">${a.nome} (${a.matricula})</option>`).join('');

  abrirModal('Emitir Certificado com QR Code', `
    <form id="formModalCert">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Aluno Titular</label>
        <select id="mcertAluno" class="form-select" required>${optAlunos}</select>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Tipo de Certificado Oficial</label>
        <select id="mcertTipo" class="form-select">
          <option value="CONCLUSAO">Certificado de Conclusão de Estudos</option>
          <option value="TRANSFERENCIA">Guia de Transferência Oficial</option>
          <option value="MATRICULA">Declaração de Matrícula e Frequência</option>
        </select>
      </div>
      <button type="submit" class="btn btn-primary w-100">Emitir Certificado Criptográfico</button>
    </form>
  `);

  document.getElementById('formModalCert').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch('/api/v1/certificados', {
        method: 'POST',
        body: JSON.stringify({
          aluno_id: document.getElementById('mcertAluno').value,
          tipo: document.getElementById('mcertTipo').value
        })
      });
      if (res.success) {
        fecharModal();
        carregarCertificados();
      }
    } catch (err) {
      alert('Erro ao emitir certificado');
    }
  });
}

