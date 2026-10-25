with open('frontend/pages/painel-escola/escola.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = """                <div class="form-check mb-3">
                  <input class="form-check-input" type="checkbox" id="confEscolaEmblema" onchange="alternarEmblemaCheck(this.checked)">
                  <label class="form-check-label small fw-semibold" for="confEscolaEmblema">
                    Usar Emblema Nacional Oficial nos cabeçalhos
                  </label>
                </div>

                <!-- Secção de Logótipo da Escola (Catálogo de Logótipos & Permutação) -->
                <div class="card border-primary border-opacity-25 bg-light p-3 mb-3 shadow-sm">
                  <div class="d-flex align-items-center justify-content-between mb-2">
                    <label class="form-label small fw-bold mb-0 text-primary">
                      <i class="bi bi-image-fill me-1"></i> Logótipo Oficial da Instituição
                    </label>
                    <span class="badge bg-primary-subtle text-primary border border-primary-subtle" style="font-size: 0.72rem;">Identidade Visual</span>
                  </div>
                  <p class="x-small text-muted mb-3" style="font-size: 0.8rem;">
                    O logótipo activo será automaticamente renderizado com precisão nos cabeçalhos de <strong>Pautas, Cadernetas, Boletins e Certificados</strong> desta escola.
                  </p>

                  <!-- Logótipo Activo em Uso -->
                  <div class="d-flex align-items-center gap-3 mb-3 p-2 bg-white rounded border border-primary shadow-sm">
                    <div id="previewLogoContainer" class="border rounded bg-light p-1 text-center d-flex align-items-center justify-content-center shadow-sm" style="width: 76px; height: 76px; overflow: hidden; min-width: 76px;">
                      <img id="confEscolaLogoPreview" src="img/emblema-mocambique.png" alt="Logótipo" style="max-width: 100%; max-height: 100%; object-fit: contain;">
                    </div>
                    <div class="flex-grow-1">
                      <div class="d-flex align-items-center gap-2 mb-1">
                        <span class="badge bg-success" style="font-size: 0.7rem;"><i class="bi bi-check-circle-fill me-1"></i>Activo em Uso</span>
                        <div class="small fw-bold text-dark text-truncate" id="confEscolaLogoStatus" style="max-width: 220px;">Emblema Nacional (Padrão Oficial)</div>
                      </div>
                      <small class="text-muted d-block mb-1" style="font-size: 0.75rem;">Para alternar, clique em qualquer logótipo da galeria abaixo.</small>
                    </div>
                  </div>

                  <!-- Galeria / Catálogo de Logótipos Disponíveis -->
                  <div class="mb-3">
                    <div class="d-flex align-items-center justify-content-between mb-2">
                      <span class="x-small fw-bold text-dark text-uppercase" style="font-size: 0.75rem;">
                        <i class="bi bi-grid-fill text-primary me-1"></i> Logótipos Disponíveis no Sistema:
                      </span>
                      <small class="text-muted fw-semibold" id="contadorGaleriaLogos">1 disponível</small>
                    </div>
                    <div class="alert alert-primary py-1 px-2 mb-2 d-flex align-items-center gap-2" style="font-size: 0.75rem;">
                      <i class="bi bi-cursor-fill text-primary"></i>
                      <span><strong>Clique no logótipo desejado</strong> para trocar imediatamente ou permutar o uso.</span>
                    </div>
                    <div id="galeriaLogosContainer" class="row g-2 mb-2" style="max-height: 290px; overflow-y: auto;">
                      <!-- Itens gerados dinamicamente via JS -->
                    </div>
                  </div>

                  <!-- Carregar Novo Logótipo para a Galeria -->
                  <div class="p-2 rounded bg-white border">
                    <div class="fw-bold text-primary small mb-2 d-flex align-items-center justify-content-between">
                      <span><i class="bi bi-cloud-arrow-up-fill me-1"></i> Carregar Novo Logótipo para a Galeria</span>
                      <span class="badge bg-light text-muted border" style="font-size: 0.65rem;">PNG, JPG, WebP</span>
                    </div>

                    <!-- 1. Carregar Ficheiro de Imagem do Computador -->
                    <div class="mb-2">
                      <label class="form-label x-small text-dark mb-1 fw-bold" style="font-size: 0.76rem;">1. Carregar do Computador</label>
                      <input type="file" id="confEscolaLogoFile" accept="image/*" class="form-control form-control-sm" onchange="processarUploadLogoLocal(this)">
                    </div>

                    <!-- 2. Ou Link / URL -->
                    <div class="mb-1">
                      <label class="form-label x-small text-dark mb-1 fw-bold" style="font-size: 0.76rem;">2. Ou Insira o Link / URL da Imagem</label>
                      <div class="input-group input-group-sm">
                        <input type="url" id="confEscolaLogoUrl" class="form-control" placeholder="https://escola.edu.mz/logo.png">
                        <button type="button" class="btn btn-outline-primary fw-semibold" onclick="processarUrlLogo(document.getElementById('confEscolaLogoUrl').value)">
                          <i class="bi bi-plus-lg me-1"></i> Adicionar
                        </button>
                      </div>
                    </div>
                  </div>
                  <input type="hidden" id="confEscolaLogoFinalValue" value="">
                </div>"""

replacement = """                <div class="form-check mb-3">
                  <input class="form-check-input" type="checkbox" id="confEscolaEmblema" onchange="alternarEmblemaCheck(this.checked)">
                  <label class="form-check-label small fw-semibold" for="confEscolaEmblema">
                    Usar Emblema Nacional Oficial nos cabeçalhos de documentos
                  </label>
                </div>

                <!-- Secção de Logótipo & Marca d'Água da Instituição (Isolada por Escola) -->
                <div class="card border-primary border-opacity-25 bg-light p-3 mb-3 shadow-sm">
                  <div class="d-flex align-items-center justify-content-between mb-2">
                    <label class="form-label small fw-bold mb-0 text-primary">
                      <i class="bi bi-image-fill me-1"></i> Logótipo Oficial & Marca d'Água da Instituição
                    </label>
                    <span class="badge bg-primary-subtle text-primary border border-primary-subtle" style="font-size: 0.72rem;">Identidade Visual Isolada</span>
                  </div>
                  <p class="x-small text-muted mb-3" style="font-size: 0.8rem;">
                    Configure o logótipo de cabeçalho para <strong>Pautas, Cadernetas, Boletins e Certificados</strong> e defina a imagem de <strong>Marca d'Água</strong> oficial desta escola (100% isolada e independente).
                  </p>

                  <!-- 1. PAINEL DE STATUS: LOGÓTIPO DE DOCUMENTOS & MARCA D'ÁGUA EM USO -->
                  <div class="row g-2 mb-3">
                    <!-- Logótipo dos Documentos (Cabeçalho) -->
                    <div class="col-12 col-md-6">
                      <div class="p-2 bg-white rounded border border-primary shadow-xs h-100 d-flex align-items-center gap-2">
                        <div id="previewLogoDocsContainer" class="border rounded bg-light p-1 text-center d-flex align-items-center justify-content-center shadow-xs" style="width: 58px; height: 58px; min-width: 58px; overflow: hidden;">
                          <img id="confEscolaLogoPreview" src="img/emblema-mocambique.png" alt="Logótipo Documentos" style="max-width: 100%; max-height: 100%; object-fit: contain;">
                        </div>
                        <div class="flex-grow-1 min-w-0">
                          <div class="d-flex align-items-center gap-1 mb-1">
                            <span class="badge bg-primary" style="font-size: 0.65rem;"><i class="bi bi-file-earmark-text-fill me-1"></i>Cabeçalho Docs</span>
                          </div>
                          <div class="small fw-bold text-dark text-truncate" id="confEscolaLogoStatus" style="font-size: 0.75rem;">Emblema Nacional (Oficial)</div>
                          <span class="badge bg-light text-secondary border text-truncate d-block mt-1" id="confEscolaModoLogoBadge" style="font-size: 0.65rem; max-width: 150px;">Apenas Documentos</span>
                        </div>
                      </div>
                    </div>

                    <!-- Marca d'Água de Fundo -->
                    <div class="col-12 col-md-6">
                      <div class="p-2 bg-white rounded border border-info shadow-xs h-100 d-flex align-items-center gap-2">
                        <div id="previewMarcaDaguaContainer" class="border rounded bg-light p-1 text-center d-flex align-items-center justify-content-center shadow-xs" style="width: 58px; height: 58px; min-width: 58px; overflow: hidden;">
                          <img id="confEscolaMarcaDaguaPreview" src="img/emblema-mocambique.png" alt="Marca d'Água" style="max-width: 100%; max-height: 100%; object-fit: contain; opacity: 0.6;">
                        </div>
                        <div class="flex-grow-1 min-w-0">
                          <div class="d-flex align-items-center gap-1 mb-1">
                            <span class="badge bg-info text-dark" style="font-size: 0.65rem;"><i class="bi bi-droplet-half me-1"></i>Marca d'Água</span>
                          </div>
                          <div class="small fw-bold text-dark text-truncate" id="confEscolaMarcaDaguaStatus" style="font-size: 0.75rem;">Emblema Nacional (Oficial)</div>
                          <span class="badge bg-light text-secondary border text-truncate d-block mt-1" id="confEscolaMarcaDaguaModoBadge" style="font-size: 0.65rem; max-width: 150px;">Padrão Oficial</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 2. GALERIA DE LOGÓTIPOS & IMAGENS DA INSTITUIÇÃO -->
                  <div class="mb-3">
                    <div class="d-flex align-items-center justify-content-between mb-2">
                      <span class="x-small fw-bold text-dark text-uppercase" style="font-size: 0.75rem;">
                        <i class="bi bi-grid-fill text-primary me-1"></i> Imagens & Logótipos desta Instituição:
                      </span>
                      <small class="text-muted fw-semibold" id="contadorGaleriaLogos">1 disponível</small>
                    </div>
                    <div class="alert alert-primary py-1 px-2 mb-2 d-flex align-items-center gap-2" style="font-size: 0.74rem;">
                      <i class="bi bi-info-circle-fill text-primary"></i>
                      <span>Escolha a finalidade de cada imagem: <strong>Documentos</strong>, <strong>Docs + Marca d'Água</strong> ou <strong>Só Marca d'Água</strong>.</span>
                    </div>
                    <div id="galeriaLogosContainer" class="row g-2 mb-2" style="max-height: 320px; overflow-y: auto;">
                      <!-- Itens gerados dinamicamente via JS -->
                    </div>
                  </div>

                  <!-- 3. CARREGAR / IMPORTAR NOVA IMAGEM OU LOGÓTIPO -->
                  <div class="p-3 rounded bg-white border">
                    <div class="fw-bold text-primary small mb-2 d-flex align-items-center justify-content-between">
                      <span><i class="bi bi-cloud-arrow-up-fill me-1"></i> Carregar / Importar Nova Imagem para a Instituição</span>
                      <span class="badge bg-light text-muted border" style="font-size: 0.65rem;">PNG, JPG, WebP</span>
                    </div>

                    <!-- Seletor de Destino no Momento do Upload -->
                    <div class="mb-2 p-2 bg-light rounded border">
                      <label class="form-label x-small text-dark mb-1 fw-bold" style="font-size: 0.76rem;">
                        <i class="bi bi-gear-fill text-primary me-1"></i> Destino da Imagem a Carregar:
                      </label>
                      <select id="confEscolaDestinoUpload" class="form-select form-select-sm fw-semibold" style="font-size: 0.78rem;">
                        <option value="DOCUMENTOS" selected>1. Usar nos Documentos (Cabeçalho Oficial)</option>
                        <option value="DOCUMENTOS_E_MARCA_DAGUA">2. Usar nos Documentos E Marca de Água (Ambos)</option>
                        <option value="APENAS_MARCA_DAGUA">3. Usar só e só como Marca de Água (Específico)</option>
                        <option value="APENAS_GALERIA">4. Apenas Guardar na Galeria da Instituição</option>
                      </select>
                    </div>

                    <!-- 1. Carregar Ficheiro de Imagem do Computador -->
                    <div class="mb-2">
                      <label class="form-label x-small text-dark mb-1 fw-bold" style="font-size: 0.76rem;">1. Carregar do Computador</label>
                      <input type="file" id="confEscolaLogoFile" accept="image/*" class="form-control form-control-sm" onchange="processarUploadLogoLocal(this)">
                    </div>

                    <!-- 2. Ou Link / URL -->
                    <div class="mb-1">
                      <label class="form-label x-small text-dark mb-1 fw-bold" style="font-size: 0.76rem;">2. Ou Link / URL da Imagem</label>
                      <div class="input-group input-group-sm">
                        <input type="url" id="confEscolaLogoUrl" class="form-control" placeholder="https://escola.edu.mz/logo.png">
                        <button type="button" class="btn btn-outline-primary fw-semibold" onclick="processarUrlLogo(document.getElementById('confEscolaLogoUrl').value)">
                          <i class="bi bi-plus-lg me-1"></i> Adicionar
                        </button>
                      </div>
                    </div>
                  </div>

                  <!-- Campos Ocultos para Persistência -->
                  <input type="hidden" id="confEscolaLogoFinalValue" value="">
                  <input type="hidden" id="confEscolaModoUsoLogo" value="DOCUMENTOS">
                  <input type="hidden" id="confEscolaMarcaDaguaFinalValue" value="">
                  <input type="hidden" id="confEscolaMarcaDaguaModo" value="EMBLEMA_NACIONAL">
                </div>"""

assert target in text, "target not found in escola.html"
text = text.replace(target, replacement, 1)

with open('frontend/pages/painel-escola/escola.html', 'w', encoding='utf-8', newline='') as f:
    f.write(text)

print("SUCCESS")
