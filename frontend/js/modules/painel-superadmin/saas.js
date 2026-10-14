/**
 * SIGE - PAINEL-SUPERADMIN | Gestão de Escolas & Planos SaaS
 * Ficheiro de código independente do menu: saas.js
 * Isolamento estrito de painel: Nenhuma ligação entre painéis de níveis distintos.
 */

// ==================== 1. CARREGAMENTO DO PAINEL SAAS ====================
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
            const statusUpper = (e.status || 'ATIVA').toUpperCase();
            const isAtiva = statusUpper === 'ATIVA';
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

            let badgeClasse = 'bg-success';
            if (statusUpper === 'SUSPENSA') badgeClasse = 'bg-warning text-dark';
            else if (statusUpper === 'EXPIRADA' || statusUpper === 'INACTIVA') badgeClasse = 'bg-danger';

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
                <td><span class="badge ${badgeClasse}">${statusUpper}</span></td>
                <td><small>${totalAlunos} alunos<br>${totalProfs} profs</small></td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm">
                    <!-- Botão Entrar como Escola -->
                    <button class="btn btn-primary" title="Entrar na Escola como SuperAdmin" onclick="alternarEscolaSuperAdmin('${e.id}', '${nomeEscapado}', '${statusUpper}')">
                      <i class="bi bi-box-arrow-in-right me-1"></i> Entrar
                    </button>
                    <!-- Botão Toggle Ativar / Desativar -->
                    <button class="btn ${isAtiva ? 'btn-outline-danger' : 'btn-outline-success'}" 
                            title="${isAtiva ? 'Desactivar Escola' : 'Activar Escola'}"
                            onclick="toggleStatusEscola('${e.id}', '${nomeEscapado}', '${statusUpper}')">
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

// ==================== 2. MODO INSPEÇÃO & VALIDAÇÃO DE ESTADO ====================
async function alternarEscolaSuperAdmin(escolaId, escolaNome = '', escolaStatus = '') {
  if (!escolaId) {
    sairModoInspecaoSuperAdmin();
    return;
  }

  const st = (escolaStatus || '').toUpperCase();
  // Bloqueio rigoroso: escolas suspensas, inactivas ou expiradas NÃO PODEM ABRIR nem acessar o sistema
  if (st && st !== 'ATIVA') {
    let motivo = 'encontra-se com acesso INACTIVO';
    if (st === 'SUSPENSA') {
      motivo = 'encontra-se SUSPENSA por irregularidades administrativas ou falta de liquidação';
    } else if (st === 'EXPIRADA') {
      motivo = 'está com a anuidade / período de subscrição EXPIRADO';
    } else if (st === 'INACTIVA') {
      motivo = 'está DESACTIVADA pelo Administrador do SIGE';
    }
    alert(`Acesso bloqueado: A instituição de ensino [${escolaNome || 'Escola'}] ${motivo}.\nO acesso ao painel escolar está totalmente vedado até à regularização do estado da conta.`);
    return;
  }

  try {
    localStorage.setItem('sige_selected_tenant', escolaId);
    state.filtroAlunoClasse = 'TODAS';
    state.filtroAlunoTurma = 'TODAS';
    const nomeLimpo = (escolaNome || '').replace(/\\'/g, "'");
    state.tenant = { id: escolaId, nome: nomeLimpo || 'Escola Seleccionada', status: 'ATIVA' };

    // Sincronizar selector no topo
    const select = document.getElementById('superAdminTenantSelect');
    if (select) select.value = escolaId;

    // Atualizar badges
    atualizarBadgeTenant(state.tenant);
    if (typeof atualizarBotaoToggleNotasDap === 'function') {
      atualizarBotaoToggleNotasDap(state.tenant.permitir_visualizacao_notas !== false);
    }

    // Activar banner de inspeção
    const bannerInspecao = document.getElementById('superAdminInspecaoBanner');
    if (bannerInspecao) {
      bannerInspecao.style.setProperty('display', 'flex', 'important');
      const elNome = document.getElementById('superAdminInspecaoNome');
      if (elNome) elNome.textContent = `A Inspecionar: ${state.tenant.nome}`;
      const elStatus = document.getElementById('superAdminInspecaoStatus');
      if (elStatus) elStatus.textContent = 'ATIVA';
    }

    // Re-renderizar sidebar para navegação escolar em modo inspeção
    renderizarSidebarPorNivel('ADMIN_ESCOLA');

    mostrarNotificacao(`Acesso directo concedido à instituição [${state.tenant.nome}] em modo de inspeção.`, 'success');

    // Navegar para o painel principal da instituição
    navegarPara('dashboard');

    // Carregar dados complementares em segundo plano
    try {
      const res = await apiFetch('/api/v1/escola-admin/info', { ignoreAuthRedirect: true });
      if (res && res.success && res.data) {
        state.tenant = res.data;
        atualizarBadgeTenant(state.tenant);
      }
      if (typeof carregarDadosGlobaisEscola === 'function') {
        carregarDadosGlobaisEscola();
      }
    } catch (_) {}
  } catch (err) {
    console.error('Erro ao alternar para a escola:', err);
    alert('Não foi possível entrar na escola: ' + (err.message || 'Erro desconhecido'));
  }
}

function sairModoInspecaoSuperAdmin() {
  localStorage.removeItem('sige_selected_tenant');
  state.tenant = null;

  const select = document.getElementById('superAdminTenantSelect');
  if (select) select.value = '';

  const bannerInspecao = document.getElementById('superAdminInspecaoBanner');
  if (bannerInspecao) bannerInspecao.style.setProperty('display', 'none', 'important');

  // Restaurar badge da sidebar para SIGE Master
  const elNome = document.getElementById('sidebarEscolaNome');
  if (elNome) elNome.textContent = 'SIGE';
  const elStatus = document.getElementById('sidebarStatusBadge');
  if (elStatus) elStatus.textContent = 'ATIVA';
  const elProv = document.getElementById('sidebarProvinciaBadge');
  if (elProv) elProv.textContent = 'SaaS Master';
  const elAno = document.getElementById('headerAnoLetivo');
  if (elAno) elAno.textContent = 'Ano Lectivo: 2026';

  // Restaurar menus do SuperAdmin
  renderizarSidebarPorNivel('SUPERADMIN');

  mostrarNotificacao('Modo de inspeção encerrado. Retornou à Gestão Master SaaS.', 'info');
  navegarPara('saas');
}

// ==================== 3. ACTIVAR / DESACTIVAR ESCOLA ====================
async function toggleStatusEscola(escolaId, nome, statusAtual) {
  const stUpper = (statusAtual || 'ATIVA').toUpperCase();
  const proximo = stUpper === 'ATIVA' ? 'SUSPENSA' : 'ATIVA';
  if (!confirm(`Confirma a alteração de estado da instituição [${nome}] para [${proximo}]?`)) return;

  try {
    const res = await apiFetch(`/api/v1/saas-admin/escolas/${escolaId}/toggle-status`, {
      method: 'PATCH'
    });
    if (res && res.success) {
      alert(res.message || `Estado da escola alterado para ${proximo} com sucesso.`);
      carregarPainelSaaS();
    } else {
      alert((res && res.message) || 'Erro ao alterar estado da escola.');
    }
  } catch (err) {
    alert('Erro ao alterar estado da escola: ' + (err.message || 'Erro de comunicação'));
  }
}

// ==================== 4. CADASTRO DE NOVA ESCOLA ====================
async function modalCadastrarEscolaSuperAdmin() {
  try {
    const planosRes = await apiFetch('/api/v1/saas-admin/planos');
    const optPlanos = (planosRes.data || []).map(p => 
      `<option value="${p.id}">${p.nome} (${p.duracao_dias} dias) — ${Number(p.preco || 0).toLocaleString('pt-PT')} MZN</option>`
    ).join('');

    const optProvincias = (state.geografia?.provincias || [
      'Maputo Cidade', 'Maputo Província', 'Gaza', 'Inhambane', 'Sofala',
      'Manica', 'Tete', 'Zambézia', 'Nampula', 'Cabo Delgado', 'Niassa'
    ]).map(p => `<option value="${p}">${p}</option>`).join('');

    abrirModal('Cadastrar Nova Escola no SIGE', `
      <form id="formModalCadastrarEscola">
        <div class="alert alert-primary border-primary bg-primary bg-opacity-10 py-2 px-3 mb-3">
          <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <div>
              <small class="fw-bold text-primary d-block"><i class="bi bi-upc-scan me-1"></i> Geração Automática do Código Único da Escola & Órgãos:</small>
              <small class="text-muted" style="font-size: 0.73rem;">[2 díg. Província] + [2 díg. Distrito] + [P/B/S Nível] + [Nº Escola]</small>
            </div>
            <span class="badge bg-primary fs-6 font-monospace px-3 py-2" id="cadPreviewCodEscola">0101S0001</span>
          </div>
          <div class="row g-2 mt-1 pt-2 border-top border-primary border-opacity-25 text-center small">
            <div class="col-4">
              <span class="text-muted d-block" style="font-size: 0.7rem;">Gabinete do Director (GD)</span>
              <code class="fw-bold text-primary" id="cadPreviewCodGD">GD0101S0001</code>
            </div>
            <div class="col-4">
              <span class="text-muted d-block" style="font-size: 0.7rem;">Direcção Pedagógica (DP)</span>
              <code class="fw-bold text-info" id="cadPreviewCodDP">DP0101S0001</code>
            </div>
            <div class="col-4">
              <span class="text-muted d-block" style="font-size: 0.7rem;">Chefe da Secretaria (SECR)</span>
              <code class="fw-bold text-secondary" id="cadPreviewCodSECR">SECR0101S0001</code>
            </div>
          </div>
        </div>

        <div class="row g-3">
          <div class="col-md-5">
            <label class="form-label small fw-semibold">Nome da Instituição</label>
            <input type="text" id="cadEscolaNome" class="form-control" required placeholder="Ex: Escola Secundária de Massinga" oninput="atualizarPreviewModalCadastroEscola()">
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-bold text-primary">Nível / Tipo de Escola</label>
            <select id="cadEscolaTipo" class="form-select border-primary fw-semibold" onchange="atualizarPreviewModalCadastroEscola()" required>
              <option value="S" selected>S — Escola Secundária</option>
              <option value="B">B — Escola Básica</option>
              <option value="P">P — Escola Primária</option>
            </select>
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-semibold">NUIT da Escola</label>
            <input type="text" id="cadEscolaNUIT" class="form-control" required placeholder="Ex: 400123456">
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">E-mail Administrativo</label>
            <input type="email" id="cadEscolaEmail" class="form-control" required placeholder="secretaria@escola.edu.mz">
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Telefone (+258 Padrão)</label>
            <input type="text" id="cadEscolaTelefone" class="form-control" value="+258 " required>
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">Província</label>
            <select id="cadEscolaProvincia" class="form-select" onchange="atualizarDistritosCadastroEscola(this.value); atualizarPreviewModalCadastroEscola();" required>
              <option value="">Selecione a Província</option>
              ${optProvincias}
            </select>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Distrito</label>
            <select id="cadEscolaDistrito" class="form-select" onchange="atualizarPreviewModalCadastroEscola()" required>
              <option value="">Selecione primeiro a província</option>
            </select>
          </div>

          <div class="col-md-7">
            <label class="form-label small fw-semibold">Plano de Subscrição Inicial</label>
            <select id="cadEscolaPlano" class="form-select" required>${optPlanos}</select>
          </div>
          <div class="col-md-5">
            <label class="form-label small fw-semibold">Valor do Contrato (MZN)</label>
            <input type="number" id="cadEscolaValor" class="form-control" placeholder="Valor acordado em MZN">
          </div>

          <div class="col-md-4">
            <label class="form-label small fw-semibold">Director da Escola (GD)</label>
            <input type="text" id="cadEscolaAdminNome" class="form-control" placeholder="Nome do Director">
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Director Pedagógico (DP)</label>
            <input type="text" id="cadEscolaDapNome" class="form-control" placeholder="Nome do Director Pedagógico">
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-semibold">Chefe da Secretaria (SECR)</label>
            <input type="text" id="cadEscolaChefeSecNome" class="form-control" placeholder="Nome do Chefe da Secretaria">
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">E-mail do Director (Opcional)</label>
            <input type="email" id="cadEscolaAdminEmail" class="form-control" placeholder="director@escola.edu.mz">
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Senha Inicial Padrão</label>
            <input type="password" id="cadEscolaAdminSenha" class="form-control" placeholder="123456 (Padrão)">
          </div>

          <div class="col-12">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" id="cadEscolaEmblema" checked>
              <label class="form-check-label small fw-semibold" for="cadEscolaEmblema">
                Utilizar Emblema Oficial nos documentos e pautas
              </label>
            </div>
          </div>

          <div class="col-12">
            <div class="card bg-light border p-3">
              <label class="form-label small fw-bold mb-2">
                <i class="bi bi-image me-1 text-primary"></i> Logótipo da Instituição
              </label>
              <div class="d-flex align-items-center gap-3">
                <div class="border rounded bg-white p-1 text-center d-flex align-items-center justify-content-center shadow-sm" style="width: 60px; height: 60px; overflow: hidden;">
                  <img id="cadEscolaLogoPreview" src="img/emblema-mocambique.png" alt="Logo" style="max-width: 100%; max-height: 100%; object-fit: contain;">
                </div>
                <div class="flex-grow-1">
                  <input type="file" id="cadEscolaLogoFile" accept="image/*" class="form-control form-control-sm mb-1" onchange="processarUploadLogoModal(this, 'cadEscolaLogoFinal', 'cadEscolaLogoPreview')">
                  <input type="hidden" id="cadEscolaLogoFinal" value="">
                </div>
              </div>
            </div>
          </div>
        </div>
        <button type="submit" class="btn btn-primary w-100 mt-4">Concluir Cadastro da Escola</button>
      </form>
    `);

    // Event listener do formulário
    document.getElementById('formModalCadastrarEscola')?.addEventListener('submit', submeterCadastroEscolaSuperAdmin);
  } catch (err) {
    console.error('Erro ao abrir modal de cadastro:', err);
    alert('Erro ao carregar dados do cadastro: ' + err.message);
  }
}

function atualizarDistritosCadastroEscola(provincia) {
  const distritos = state.geografia?.distritos?.[provincia] || [];
  const select = document.getElementById('cadEscolaDistrito');
  if (select) {
    if (distritos.length === 0) {
      select.innerHTML = '<option value="">Nenhum distrito registado</option>';
    } else {
      select.innerHTML = distritos.map(d => `<option value="${d}">${d}</option>`).join('');
    }
  }
}

function atualizarPreviewModalCadastroEscola() {
  const prov = document.getElementById('cadEscolaProvincia')?.value || '';
  const dist = document.getElementById('cadEscolaDistrito')?.value || '';
  const tipo = document.getElementById('cadEscolaTipo')?.value || 'S';

  let codProv = '01';
  let codDist = '01';

  const mapaProv = {
    'Niassa': '01', 'Cabo Delgado': '02', 'Nampula': '03', 'Zambézia': '04',
    'Tete': '05', 'Manica': '06', 'Sofala': '07', 'Inhambane': '08',
    'Gaza': '09', 'Maputo Província': '10', 'Maputo Cidade': '11'
  };
  if (mapaProv[prov]) codProv = mapaProv[prov];

  const codFinal = `${codProv}${codDist}${tipo}0001`;

  const elCod = document.getElementById('cadPreviewCodEscola');
  if (elCod) elCod.textContent = codFinal;
  const elGD = document.getElementById('cadPreviewCodGD');
  if (elGD) elGD.textContent = `GD${codFinal}`;
  const elDP = document.getElementById('cadPreviewCodDP');
  if (elDP) elDP.textContent = `DP${codFinal}`;
  const elSECR = document.getElementById('cadPreviewCodSECR');
  if (elSECR) elSECR.textContent = `SECR${codFinal}`;
}

async function submeterCadastroEscolaSuperAdmin(e) {
  e.preventDefault();
  try {
    const nome = document.getElementById('cadEscolaNome')?.value?.trim();
    const tipo = document.getElementById('cadEscolaTipo')?.value || 'S';
    const nuit = document.getElementById('cadEscolaNUIT')?.value?.trim();
    const email = document.getElementById('cadEscolaEmail')?.value?.trim();
    const telefone = document.getElementById('cadEscolaTelefone')?.value?.trim();
    const provincia = document.getElementById('cadEscolaProvincia')?.value;
    const distrito = document.getElementById('cadEscolaDistrito')?.value;
    const planoId = document.getElementById('cadEscolaPlano')?.value;
    const valor = Number(document.getElementById('cadEscolaValor')?.value) || undefined;
    const adminNome = document.getElementById('cadEscolaAdminNome')?.value?.trim();
    const dapNome = document.getElementById('cadEscolaDapNome')?.value?.trim();
    const secrNome = document.getElementById('cadEscolaChefeSecNome')?.value?.trim();
    const adminEmail = document.getElementById('cadEscolaAdminEmail')?.value?.trim();
    const adminSenha = document.getElementById('cadEscolaAdminSenha')?.value?.trim() || '123456';
    const usarEmblema = document.getElementById('cadEscolaEmblema')?.checked !== false;
    const logoUrl = document.getElementById('cadEscolaLogoFinal')?.value || null;

    if (!nome || !nuit || !email || !provincia) {
      alert('Preencha os campos obrigatórios: Nome da Escola, NUIT, E-mail e Província.');
      return;
    }

    const payload = {
      nome,
      tipo_escola: tipo,
      nif_cnpj: nuit,
      email,
      telefone,
      provincia,
      distrito,
      plano_id: planoId,
      valor_contrato: valor,
      director_nome: adminNome || undefined,
      dap_nome: dapNome || undefined,
      chefe_secretaria_nome: secrNome || undefined,
      adminEmail: adminEmail || undefined,
      adminSenha: adminSenha || undefined,
      usar_emblema_nacional: usarEmblema,
      logo_url: logoUrl
    };

    const res = await apiFetch('/api/v1/saas-admin/escolas', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    if (res && res.success) {
      alert(res.message || 'Instituição de ensino cadastrada com sucesso!');
      fecharModal();
      carregarPainelSaaS();
    } else {
      alert((res && res.message) || 'Erro ao cadastrar instituição de ensino.');
    }
  } catch (err) {
    alert('Erro ao cadastrar escola: ' + (err.message || 'Erro de comunicação'));
  }
}

// ==================== 5. EDIÇÃO DE ESCOLA & PRAZO ====================
async function modalEditarEscolaSuperAdmin(escolaId) {
  try {
    const res = await apiFetch('/api/v1/saas-admin/escolas');
    const escola = (res.data || []).find(e => e.id === escolaId);
    if (!escola) return alert('Escola não encontrada');

    const ass = escola.assinaturas && escola.assinaturas[0];
    const dataFimStr = ass?.data_fim ? new Date(ass.data_fim).toISOString().split('T')[0] : '';
    const optProvincias = (state.geografia?.provincias || [
      'Maputo Cidade', 'Maputo Província', 'Gaza', 'Inhambane', 'Sofala',
      'Manica', 'Tete', 'Zambézia', 'Nampula', 'Cabo Delgado', 'Niassa'
    ]).map(p => 
      `<option value="${p}" ${p === escola.provincia ? 'selected' : ''}>${p}</option>`
    ).join('');
    const codEscola = escola.codigo_escola || '0101S0001';

    abrirModal(`Editar Escola: ${escola.nome} [${codEscola}]`, `
      <form id="formModalEditarEscola">
        <div class="alert alert-light border py-2 px-3 mb-3 d-flex justify-content-between align-items-center flex-wrap gap-2">
          <div class="small">
            <strong>Código Único da Escola:</strong> <code class="fs-6 fw-bold text-primary ms-1">${codEscola}</code>
          </div>
          <div class="d-flex gap-2 small">
            <span class="badge bg-primary-subtle text-primary border font-monospace">GD: ${escola.codigo_gabinete_director || 'GD' + codEscola}</span>
            <span class="badge bg-info-subtle text-info-emphasis border font-monospace">DP: ${escola.codigo_direccao_pedagogica || 'DP' + codEscola}</span>
            <span class="badge bg-secondary-subtle text-secondary-emphasis border font-monospace">SECR: ${escola.codigo_secretaria || 'SECR' + codEscola}</span>
          </div>
        </div>
        <div class="row g-3">
          <div class="col-md-5">
            <label class="form-label small fw-semibold">Nome da Instituição</label>
            <input type="text" id="editEscolaNome" class="form-control" value="${escola.nome}" required>
          </div>
          <div class="col-md-4">
            <label class="form-label small fw-bold text-primary">Nível / Tipo de Escola</label>
            <select id="editEscolaTipo" class="form-select border-primary fw-semibold">
              <option value="S" ${(escola.tipo_escola || 'S') === 'S' ? 'selected' : ''}>S — Escola Secundária</option>
              <option value="B" ${escola.tipo_escola === 'B' ? 'selected' : ''}>B — Escola Básica</option>
              <option value="P" ${escola.tipo_escola === 'P' ? 'selected' : ''}>P — Escola Primária</option>
            </select>
          </div>
          <div class="col-md-3">
            <label class="form-label small fw-semibold">NUIT</label>
            <input type="text" id="editEscolaNUIT" class="form-control" value="${escola.nif_cnpj}" required>
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">E-mail</label>
            <input type="email" id="editEscolaEmail" class="form-control" value="${escola.email}" required>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Telefone</label>
            <input type="text" id="editEscolaTelefone" class="form-control" value="${escola.telefone || '+258 '}">
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">Data de Vencimento do Contrato</label>
            <input type="date" id="editEscolaDataFim" class="form-control" value="${dataFimStr}">
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Estender Prazo (Dias Adicionais)</label>
            <input type="number" id="editEscolaDiasAdicionais" class="form-control" placeholder="Ex: 30" min="0">
          </div>

          <div class="col-md-6">
            <label class="form-label small fw-semibold">Província</label>
            <select id="editEscolaProvincia" class="form-select" onchange="atualizarDistritosEdicaoEscola(this.value)">
              ${optProvincias}
            </select>
          </div>
          <div class="col-md-6">
            <label class="form-label small fw-semibold">Distrito</label>
            <select id="editEscolaDistrito" class="form-select"></select>
          </div>

          <div class="col-12">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" id="editEscolaEmblema" ${escola.usar_emblema_nacional ? 'checked' : ''}>
              <label class="form-check-label small fw-semibold" for="editEscolaEmblema">
                Utilizar Emblema Oficial nos documentos
              </label>
            </div>
          </div>

          <div class="col-12">
            <div class="card bg-light border p-3">
              <label class="form-label small fw-bold mb-2">
                <i class="bi bi-image me-1 text-primary"></i> Logótipo da Instituição
              </label>
              <div class="d-flex align-items-center gap-3 mb-2">
                <div class="border rounded bg-white p-1 text-center d-flex align-items-center justify-content-center shadow-sm" style="width: 60px; height: 60px; overflow: hidden;">
                  <img id="editEscolaLogoPreview" src="${escola.logo_url || 'img/emblema-mocambique.png'}" alt="Logo" style="max-width: 100%; max-height: 100%; object-fit: contain;">
                </div>
                <div class="flex-grow-1">
                  <input type="file" id="editEscolaLogoFile" accept="image/*" class="form-control form-control-sm mb-1" onchange="processarUploadLogoModal(this, 'editEscolaLogoFinal', 'editEscolaLogoPreview')">
                  <input type="hidden" id="editEscolaLogoFinal" value="${escola.logo_url || ''}">
                  <div class="d-flex gap-2 align-items-center mt-1">
                    <button type="button" class="btn btn-outline-secondary btn-sm py-0 px-2" style="font-size: 0.75rem;" onclick="document.getElementById('editEscolaLogoFinal').value=''; document.getElementById('editEscolaLogoPreview').src='img/emblema-mocambique.png';">
                      <i class="bi bi-arrow-counterclockwise me-1"></i> Usar Emblema Nacional
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <button type="submit" class="btn btn-primary w-100 mt-4">Actualizar Dados e Prazo</button>
      </form>
    `);

    atualizarDistritosEdicaoEscola(escola.provincia || 'Maputo Cidade', escola.distrito);

    document.getElementById('formModalEditarEscola')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const body = {
          nome: document.getElementById('editEscolaNome').value,
          tipo_escola: document.getElementById('editEscolaTipo')?.value || 'S',
          nif_cnpj: document.getElementById('editEscolaNUIT').value,
          email: document.getElementById('editEscolaEmail').value,
          telefone: document.getElementById('editEscolaTelefone').value,
          data_fim: document.getElementById('editEscolaDataFim').value || undefined,
          data_fim_assinatura: document.getElementById('editEscolaDataFim').value || undefined,
          dias_adicionais: Number(document.getElementById('editEscolaDiasAdicionais').value) || undefined,
          provincia: document.getElementById('editEscolaProvincia').value,
          distrito: document.getElementById('editEscolaDistrito').value,
          usar_emblema_nacional: document.getElementById('editEscolaEmblema').checked,
          logo_url: document.getElementById('editEscolaLogoFinal')?.value || null
        };

        const updRes = await apiFetch(`/api/v1/saas-admin/escolas/${escolaId}`, {
          method: 'PATCH',
          body: JSON.stringify(body)
        });
        if (updRes && updRes.success) {
          alert('Dados da escola e prazo contratual actualizados com sucesso!');
          fecharModal();
          carregarPainelSaaS();
        } else {
          alert((updRes && updRes.message) || 'Erro ao actualizar dados');
        }
      } catch (err) {
        alert(err.message || 'Erro ao actualizar dados');
      }
    });
  } catch (err) {
    alert('Erro ao carregar dados da escola para edição: ' + err.message);
  }
}

function atualizarDistritosEdicaoEscola(provincia, distritoSelecionado = '') {
  const distritos = state.geografia?.distritos?.[provincia] || [];
  const select = document.getElementById('editEscolaDistrito');
  if (select) {
    select.innerHTML = distritos.map(d => 
      `<option value="${d}" ${d === distritoSelecionado ? 'selected' : ''}>${d}</option>`
    ).join('');
  }
}

// ==================== 6. PREÇO DO PLANO ====================
function modalEditarPrecoPlano(planoId, nome, precoAtual) {
  const precoStr = prompt(`Defina o novo preço mensal para o plano [${nome}] em Meticais (MZN):`, precoAtual);
  if (precoStr === null) return;
  const novoPreco = parseFloat(precoStr);
  if (isNaN(novoPreco) || novoPreco < 0) {
    alert('Por favor insira um valor monetário válido.');
    return;
  }

  apiFetch(`/api/v1/saas-admin/planos/${planoId}/preco`, {
    method: 'PATCH',
    body: JSON.stringify({ preco: novoPreco })
  }).then(res => {
    if (res && res.success) {
      alert(`Preço do plano [${nome}] actualizado com sucesso para ${novoPreco.toLocaleString('pt-PT')} MZN.`);
      carregarPainelSaaS();
    } else {
      alert((res && res.message) || 'Erro ao actualizar preço.');
    }
  }).catch(err => {
    alert('Erro de comunicação: ' + err.message);
  });
}

// ==================== 7. EXTRATO / CONTRATO EM PDF ====================
async function descarregarExtratoEscolaSuperAdmin(escolaId) {
  try {
    const res = await apiFetch(`/api/v1/saas-admin/escolas/${escolaId}/comprovativo-contrato`);
    if (!res || !res.success) throw new Error((res && res.message) || 'Falha ao obter comprovativo');

    const c = res.data;
    const agora = new Date();
    const dataEmissao = agora.toLocaleDateString('pt-PT') + ' ' + agora.toLocaleTimeString('pt-PT');

    abrirModal('Extrato Oficial de Contrato de Prestação de Serviços SIGE', `
      <div id="printExtratoContrato" class="p-4 bg-white" style="font-family: 'Times New Roman', serif;">
        <div class="text-center border-bottom pb-3 mb-4">
          <img src="/img/emblema-mocambique.png" style="width: 50px; height: 50px; margin-bottom: 4px;" alt="Emblema Nacional">
          <h5 class="fw-bold mb-0 text-uppercase">REPÚBLICA DE MOÇAMBIQUE</h5>
          <h6 class="fw-bold text-primary mb-1">SIGE — SISTEMA INTEGRADO DE GESTÃO ESCOLAR</h6>
          <small class="text-muted">EXTRATO OFICIAL DE LICENCIAMENTO E TERMO DE CONTRATO SAAS</small>
        </div>

        <div class="row g-3 mb-4 small">
          <div class="col-6">
            <strong>Instituição de Ensino:</strong> ${c.escola?.nome}<br>
            <strong>NUIT / NIF:</strong> ${c.escola?.nif_cnpj}<br>
            <strong>Localização:</strong> ${c.escola?.distrito || '-'}, ${c.escola?.provincia || '-'}<br>
            <strong>Contacto:</strong> ${c.escola?.telefone || '-'} | ${c.escola?.email || '-'}
          </div>
          <div class="col-6 text-end">
            <strong>Referência Contratual:</strong> ${c.comprovativo_numero}<br>
            <strong>Plano Subscrito:</strong> <span class="badge bg-primary">${c.plano?.nome || 'MENSAL'}</span><br>
            <strong>Estado da Licença:</strong> <span class="badge bg-success">${c.status_atual}</span><br>
            <strong>Valor Contratual:</strong> ${formatarMoeda(c.assinatura?.valor || 0)}
          </div>
        </div>

        <div class="table-responsive">
          <table class="table table-bordered table-sm small mb-4">
            <tr class="table-light"><th colspan="2" class="text-center fw-bold">VIGÊNCIA E CLÁUSULAS CONTRATUAIS</th></tr>
            <tr><th class="w-40">Data de Início:</th><td>${c.assinatura?.data_inicio ? new Date(c.assinatura.data_inicio).toLocaleDateString('pt-PT') : '-'}</td></tr>
            <tr><th>Data de Vencimento:</th><td>${c.assinatura?.data_fim ? new Date(c.assinatura.data_fim).toLocaleDateString('pt-PT') : '-'}</td></tr>
            <tr><th>Capacidade Licenciada:</th><td>Até ${c.plano?.max_alunos || 5000} alunos matriculados e ${c.plano?.max_professores || 500} docentes</td></tr>
            <tr><th>Alunos Registados:</th><td>${c.estatisticas?.total_alunos ?? 0} alunos</td></tr>
            <tr><th>Corpo Docente Ativo:</th><td>${c.estatisticas?.total_professores ?? 0} professores</td></tr>
            <tr><th>Turmas Cadastradas:</th><td>${c.estatisticas?.total_turmas ?? 0} turmas ativas</td></tr>
          </table>
        </div>

        <div class="alert alert-light border small text-muted text-center py-2 mb-4">
          Extrato emitido aos <strong>${dataEmissao}</strong> | Assinado digitalmente pelo Engenheiro de Sistemas SuperAdmin
        </div>

        <div class="row text-center pt-4 border-top small">
          <div class="col-6">
            <p class="mb-0 border-top pt-2 mx-4 fw-bold">O Engenheiro do Sistema (SuperAdmin)</p>
            <small class="text-muted">mandamulefj.@sige.com</small>
          </div>
          <div class="col-6">
            <p class="mb-0 border-top pt-2 mx-4 fw-bold">A Direcção da Escola</p>
            <small class="text-muted">${c.escola?.nome}</small>
          </div>
        </div>
      </div>
      <div class="d-flex justify-content-end gap-2 mt-3">
        <button class="btn btn-primary" onclick="window.print()"><i class="bi bi-printer me-1"></i> Imprimir Extrato</button>
      </div>
    `);
  } catch (err) {
    alert('Erro ao gerar extrato: ' + (err.message || 'Erro desconhecido'));
  }
}

// ==================== 8. ELIMINAR ESCOLA ====================
async function eliminarEscolaSuperAdmin(escolaId, nome) {
  if (!confirm(`ATENÇÃO ENGENHEIRO:\nTem a certeza que deseja ELIMINAR DEFINITIVAMENTE a instituição [${nome}] e todos os seus dados?\nEsta operação não pode ser revertida!`)) return;

  try {
    const res = await apiFetch(`/api/v1/saas-admin/escolas/${escolaId}`, {
      method: 'DELETE'
    });
    if (res && res.success) {
      alert(res.message || 'Instituição eliminada com sucesso.');
      carregarPainelSaaS();
      if (typeof carregarEscolasSuperAdminSelect === 'function') {
        carregarEscolasSuperAdminSelect();
      }
    } else {
      alert((res && res.message) || 'Erro ao eliminar instituição.');
    }
  } catch (err) {
    alert(err.message || 'Erro ao eliminar escola');
  }
}

// ==================== 9. LOGÓTIPO SAAS CADASTRO ====================
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

async function executarCronVerificacaoManual() {
  try {
    const res = await apiFetch('/api/v1/saas-admin/verificar-expiracoes', { method: 'POST' });
    if (res && res.success) {
      alert(`Verificação de expiração executada com sucesso!\nProcessadas: ${res.data?.processadas ?? 0}\nExpiradas: ${res.data?.expiradas ?? 0}`);
      carregarPainelSaaS();
    } else {
      alert((res && res.message) || 'Erro ao executar verificação.');
    }
  } catch (err) {
    alert('Erro ao executar verificação de expiração: ' + (err.message || 'Erro de comunicação'));
  }
}

// ==================== BINDING GLOBAL PARA ACESSO IMEDIATO ====================
window.carregarPainelSaaS = carregarPainelSaaS;
window.alternarEscolaSuperAdmin = alternarEscolaSuperAdmin;
window.sairModoInspecaoSuperAdmin = sairModoInspecaoSuperAdmin;
window.toggleStatusEscola = toggleStatusEscola;
window.executarCronVerificacaoManual = executarCronVerificacaoManual;
window.modalCadastrarEscolaSuperAdmin = modalCadastrarEscolaSuperAdmin;
window.atualizarDistritosCadastroEscola = atualizarDistritosCadastroEscola;
window.atualizarPreviewModalCadastroEscola = atualizarPreviewModalCadastroEscola;
window.submeterCadastroEscolaSuperAdmin = submeterCadastroEscolaSuperAdmin;
window.modalEditarEscolaSuperAdmin = modalEditarEscolaSuperAdmin;
window.atualizarDistritosEdicaoEscola = atualizarDistritosEdicaoEscola;
window.modalEditarPrecoPlano = modalEditarPrecoPlano;
window.descarregarExtratoEscolaSuperAdmin = descarregarExtratoEscolaSuperAdmin;
window.eliminarEscolaSuperAdmin = eliminarEscolaSuperAdmin;
window.processarLogoCadastroLocal = processarLogoCadastroLocal;
window.processarUploadLogoModal = processarUploadLogoModal;

