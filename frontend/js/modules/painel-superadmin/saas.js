/**
 * SIGE - PAINEL-SUPERADMIN | Gestão de Escolas & Planos SaaS
 * Ficheiro de código independente do menu: saas.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */
// ==================== 2. SUPERADMIN SAAS ====================
async function carregarPainelSaaS() {
  try {
    const res = await apiFetch('/api/v1/saas-admin/metrics');
    if (res && res.success) {
      const d = res.data || res.metrics || {};
      const mrr = Number(d.mrr ?? d.receitaMensalEstimada ?? 0);
      const arr = Number(d.arr ?? (mrr * 12));
      const churn = Number(d.churn ?? 0);
      const totalEscolas = d.escolas?.total ?? d.totalEscolas ?? 0;
      const ativas = d.escolas?.ativas ?? d.escolasAtivas ?? 0;
      const expiradas = d.escolas?.expiradas ?? d.escolasExpiradas ?? 0;

      const elMRR = document.getElementById('saasMRR');
      if (elMRR) elMRR.innerHTML = formatarMoeda(mrr);

      const elARR = document.getElementById('saasARR');
      if (elARR) elARR.innerHTML = formatarMoeda(arr);

      const elChurn = document.getElementById('saasChurn');
      if (elChurn) elChurn.textContent = churn + '%';

      const elTotal = document.getElementById('saasTotalEscolas');
      if (elTotal) elTotal.textContent = totalEscolas;

      const elAtivas = document.getElementById('saasEscolasAtivas');
      if (elAtivas) elAtivas.textContent = ativas;

      const elExpiradas = document.getElementById('saasEscolasExpiradas');
      if (elExpiradas) elExpiradas.textContent = expiradas;
    }

    // Tabela de Escolas
    const resEscolas = await apiFetch('/api/v1/saas-admin/escolas');
    if (resEscolas && resEscolas.success && Array.isArray(resEscolas.data)) {
      const tbody = document.getElementById('tabelaSaasEscolas');
      if (tbody) {
        if (resEscolas.data.length === 0) {
          tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted">Nenhuma escola cadastrada no momento.</td></tr>';
        } else {
          tbody.innerHTML = resEscolas.data.map(e => {
            const ass = (e.assinaturas && e.assinaturas[0]) || e.assinatura_ativa || null;
            const dataFim = ass?.data_fim ? new Date(ass.data_fim).toLocaleDateString('pt-PT') : '-';
            const isAtiva = e.status === 'ATIVA';
            const emblemaIcon = e.usar_emblema_nacional 
              ? '<span class="badge bg-warning text-dark me-1" title="Emblema Nacional">🇲🇿 Emblema</span>' 
              : '';
            const valorContratoNum = Number(ass?.valor_pago ?? ass?.valor ?? e.plano?.preco ?? 0);
            const valorContrato = formatarMoeda(valorContratoNum);
            const planoNome = e.plano?.nome || e.plano_nome || 'MENSAL';
            const totalAlunos = e._count?.alunos ?? e.total_alunos ?? 0;
            const totalProfs = e._count?.professores ?? e.total_professores ?? 0;
            const nomeEscapado = (e.nome || '').replace(/'/g, "\\'");
            const codEscola = e.codigo_escola || '0101S0001';
            const codGD = e.codigo_gabinete_director || `GD${codEscola}`;
            const codDP = e.codigo_direccao_pedagogica || `DP${codEscola}`;
            const codSECR = e.codigo_secretaria || `SECR${codEscola}`;

            return `
              <tr>
                <td>
                  <div class="d-flex align-items-center gap-2">
                    <div>
                      <span class="badge bg-primary font-monospace me-1" title="Código Único Oficial da Escola">${codEscola}</span>
                      <strong>${e.nome}</strong> ${emblemaIcon}
                      <br><small class="text-muted">${e.email} | ${e.telefone || '-'}</small>
                      <div class="mt-1 d-flex flex-wrap gap-1">
                        <span class="badge bg-light text-primary border font-monospace" style="font-size: 0.68rem;" title="Gabinete do Director (Admin Geral)">${codGD}</span>
                        <span class="badge bg-light text-info border font-monospace" style="font-size: 0.68rem;" title="Direcção Pedagógica (Sub-Admin)">${codDP}</span>
                        <span class="badge bg-light text-secondary border font-monospace" style="font-size: 0.68rem;" title="Chefe da Secretaria">${codSECR}</span>
                      </div>
                    </div>
                  </div>
                </td>
                <td><small>${e.provincia || '-'}<br><span class="text-muted">${e.distrito || '-'}</span></small></td>
                <td><code>${e.nif_cnpj}</code></td>
                <td>
                  <span class="badge bg-light text-dark border">${planoNome}</span>
                  <br><strong class="small text-success">${valorContrato}</strong>
                </td>
                <td><small>${dataFim}</small></td>
                <td><span class="badge badge-${(e.status || 'ativa').toLowerCase()}">${e.status}</span></td>
                <td><small>${totalAlunos} alunos<br>${totalProfs} profs</small></td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm">
                    <!-- Botão Entrar como Escola -->
                    <button class="btn btn-primary" title="Entrar na Escola como SuperAdmin (Acesso Imediato sem Credenciais)" onclick="alternarEscolaSuperAdmin('${e.id}', '${nomeEscapado}')">
                      <i class="bi bi-box-arrow-in-right me-1"></i> Entrar
                    </button>
                    <!-- Botão Toggle Ativar / Desativar -->
                    <button class="btn ${isAtiva ? 'btn-outline-danger' : 'btn-outline-success'}" 
                            title="${isAtiva ? 'Desactivar Escola' : 'Activar Escola'}"
                            onclick="toggleStatusEscola('${e.id}', '${nomeEscapado}', '${e.status}')">
                      <i class="bi ${isAtiva ? 'bi-toggle-on text-success' : 'bi-toggle-off text-danger'}"></i>
                      ${isAtiva ? 'Activa' : 'Inactiva'}
                    </button>
                    <!-- Botão Editar Dados e Prazo -->
                    <button class="btn btn-outline-primary" title="Editar Dados & Prazo" onclick="modalEditarEscolaSuperAdmin('${e.id}')">
                      <i class="bi bi-pencil"></i>
                    </button>
                    <!-- Botão Descarregar Extrato / Contrato -->
                    <button class="btn btn-outline-info" title="Descarregar Extrato / Contrato da Escola" onclick="descarregarExtratoEscolaSuperAdmin('${e.id}')">
                      <i class="bi bi-file-earmark-pdf"></i>
                    </button>
                    <!-- Botão Eliminar Escola (Exclusivo SuperAdmin) -->
                    <button class="btn btn-outline-danger" title="Eliminar Escola Definitivamente" onclick="eliminarEscolaSuperAdmin('${e.id}', '${nomeEscapado}')">
                      <i class="bi bi-trash"></i>
                    </button>
                  </div>
                </td>
              </tr>
            `;
          }).join('');
        }
      }
    }

    // Tabela de Preços dos Planos
    const resPlanos = await apiFetch('/api/v1/saas-admin/planos');
    if (resPlanos && resPlanos.success && Array.isArray(resPlanos.data)) {
      const tbodyPlanos = document.getElementById('tabelaSaasPlanos');
      if (tbodyPlanos) {
        if (resPlanos.data.length === 0) {
          tbodyPlanos.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-muted">Nenhum plano cadastrado.</td></tr>';
        } else {
          tbodyPlanos.innerHTML = resPlanos.data.map(p => {
            const precoNum = Number(p.preco || 0);
            return `
              <tr>
                <td><strong>${p.nome}</strong></td>
                <td>${p.duracao_dias} dias</td>
                <td><strong class="text-primary">${formatarMoeda(precoNum)}</strong></td>
                <td><small class="text-muted">${p.descricao || 'Plano de subscrição SIGE'}</small></td>
                <td class="text-end">
                  <button class="btn btn-outline-primary btn-sm" onclick="modalEditarPrecoPlano('${p.id}', '${p.nome}', ${precoNum})">
                    <i class="bi bi-currency-exchange me-1"></i> Alterar Preço
                  </button>
                </td>
              </tr>
            `;
          }).join('');
        }
      }
    }
  } catch (err) {
    console.error('Erro ao carregar Painel SaaS:', err);
  }
}


// ==================== LOGÓTIPO SAAS CADASTRO ====================
function processarLogoCadastroLocal(input) {
  const file = input.files?.[0];
  if (!file) return;
  if (!file.type.startsWith('image/')) {
    alert('Por favor, seleccione um ficheiro de imagem válido.');
    return;
  }
  const reader = new FileReader();
  reader.onload = (e) => {
    const hidden = document.getElementById('cadEscolaLogoBase64');
    if (hidden) hidden.value = e.target.result;
  };
  reader.readAsDataURL(file);
}

function processarUploadLogoModal(input, hiddenInputId, previewImgId) {
  const file = input.files?.[0];
  if (!file) return;
  if (!file.type.startsWith('image/')) {
    alert('Por favor, seleccione um ficheiro de imagem válido (PNG, JPG, WebP).');
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    alert('A imagem seleccionada é muito pesada (máximo 5MB).');
    return;
  }
  const reader = new FileReader();
  reader.onload = (e) => {
    const dataUrl = e.target.result;
    const hidden = document.getElementById(hiddenInputId);
    if (hidden) hidden.value = dataUrl;
    const preview = document.getElementById(previewImgId);
    if (preview) preview.src = dataUrl;
  };
  reader.readAsDataURL(file);
}

