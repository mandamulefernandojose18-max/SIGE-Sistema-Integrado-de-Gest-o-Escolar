# ⚙️ Manual Operacional dos Módulos do Sistema — SIGE (v2.5.0)

> **Guia Passo a Passo de Utilização dos 19 Módulos Funcionais**  
> **Público:** SuperAdmins, Administradores da Escola, Diretores, DAPs, Chefes de Secretaria, Financeiro, Professores e Alunos

---

## 📑 Índice dos 19 Módulos Funcionais

1. [Módulo 1: Portal Público de Auto-Inscrição](#módulo-1-portal-público-de-auto-inscrição-modalinscricaopublica)
2. [Módulo 2: Painel Master SaaS (SuperAdmin)](#módulo-2-painel-master-saas-view-saas)
3. [Módulo 3: Administração Institucional da Escola](#módulo-3-administração-institucional-da-escola-view-escola)
4. [Módulo 4: Gestão de Turmas, Lotação e Homologações](#módulo-4-gestão-de-turmas-lotação-e-homologações-view-turmas)
5. [Módulo 5: Alunos, Matrículas e Transferências](#módulo-5-alunos-matrículas-e-transferências-view-alunos)
6. [Módulo 6: Professores, Carreiras MEC e Alocações](#módulo-6-professores-carreiras-mec-e-alocações-view-professores)
7. [Módulo 7: Disciplinas e Matriz Curricular](#módulo-7-disciplinas-e-matriz-curricular-view-disciplinas)
8. [Módulo 8: Biblioteca Digital de Material Escolar](#módulo-8-biblioteca-digital-de-material-escolar-view-material-escolar)
9. [Módulo 9: Caderneta Electrónica do Professor](#módulo-9-caderneta-electrónica-do-professor-view-caderneta)
10. [Módulo 10: Calendário de Notas e Desbloqueio](#módulo-10-calendário-de-notas-e-desbloqueio-view-desbloqueio)
11. [Módulo 11: Pautas Gerais e Actas do Conselho de Avaliação](#módulo-11-pautas-gerais-e-actas-do-conselho-view-pautas)
12. [Módulo 12: Estatística Oficial do Aproveitamento Pedagógico](#módulo-12-estatística-oficial-do-aproveitamento-view-estatisticas-aproveitamento)
13. [Módulo 13: Emissão de Certificados com QR Code](#módulo-13-emissão-de-certificados-com-qr-code-view-certificados)
14. [Módulo 14: Gestão Financeira e Propinas](#módulo-14-gestão-financeira-e-propinas-view-pagamentos)
15. [Módulo 15: Central de Impressão e Cofre de Arquivos](#módulo-15-central-de-impressão-e-cofre-de-arquivos-view-impressao)
16. [Módulo 16: Portal Privado do Aluno](#módulo-16-portal-privado-do-aluno-view-aluno-*)
17. [Módulo 17: Cofre de Credenciais e Gestão de Senhas](#módulo-17-cofre-de-credenciais-e-gestão-de-senhas-view-usuarios-senhas)
18. [Módulo 18: Auditoria e Registo de Acessos](#módulo-18-auditoria-e-registo-de-acessos-view-acessos)
19. [Módulo 19: Assinatura e Pagamentos SaaS da Escola](#módulo-19-assinatura-e-pagamentos-saas-da-escola-view-assinatura-escola)

---

### Módulo 1: Portal Público de Auto-Inscrição (`#modalInscricaoPublica`)
- **Quem usa:** Candidatos externos, estudantes e encarregados de educação (sem necessidade de login prévio).
- **Como aceder:** Clique no botão *"Fazer Auto-Inscrição Online"* localizado na página inicial de login.
- **Passo a Passo:**
  1. Selecione a **Província** e o **Distrito** para carregar a lista de escolas ativas com período de inscrições aberto.
  2. Selecione a **Escola**, a **Classe pretendida** (7ª à 12ª) e, no caso da 11ª ou 12ª classe, selecione a **Secção / Área Curricular**.
  3. Preencha os dados biográficos completos: Nome, Apelido, Género, Data de Nascimento, Tipo de Documento e Número de BI (com validação estrita de 12 dígitos + 1 letra), Filiação e Contacto moçambicano (`+258 8X`).
  4. Defina uma palavra-passe pessoal e confirme.
- **Resultado Operacional:** O sistema enturma automaticamente o aluno numa turma com vagas livres, gera o número de matrícula sequencial (`2026001`), cria o utilizador `ALUNO` e exibe o **Cartão de Confirmação de Matrícula** com o seu código de acesso estruturado.

---

### Módulo 2: Painel Master SaaS (`#view-saas`)
- **Quem usa:** Exclusivo para o perfil `SUPERADMIN` (Diretoria Executiva do SIGE).
- **Métricas em Tempo Real:** Exibe MRR (*Monthly Recurring Revenue*), ARR (*Annual Recurring Revenue*), Churn Rate, Escolas Ativas vs. Vencidas e quantitativo total de alunos e professores na nuvem.
- **Operações Principais:**
  - **Cadastrar Nova Escola:** Formulário completo com província, distrito, plano escolhido e data de adesão. Gera imediatamente o código institucional da escola (`0808S0001`) e cria automaticamente as 4 contas diretivas (`ADMIN_ESCOLA`, `DIRECTOR_ESCOLA`, `DAP`, `CHEFE_SECRETARIA`).
  - **Entrar na Escola ("Botão Inspecionar"):** Permite ao SuperAdmin abrir o painel de qualquer escola com um clique, sem pedir a senha local.
  - **Renovar Assinatura:** Acrescenta dias de vigência ao contrato da escola selecionada e restaura o status `ATIVA`.
  - **Emitir Comprovativo de Contrato em PDF:** Download imediato da minuta contratual oficial em PDF com os termos do plano e limites de utilização.

---

### Módulo 3: Administração Institucional da Escola (`#view-escola`)
- **Quem usa:** `ADMIN_ESCOLA`, `DIRECTOR_ESCOLA` e `DAP`.
- **Configurações Globais:**
  - **Identidade:** Nome da escola, NUIT, endereço, telefones de contacto e e-mail institucional.
  - **Período Letivo:** Seleção do **Ano Letivo Ativo** (ex: `2026`) e do **Trimestre Ativo** (`1_TRIMESTRE`, `2_TRIMESTRE`, `3_TRIMESTRE`).
  - **Identidade Visual & Logótipo:** Ativação do Emblema Oficial da República de Moçambique, gestão de galeria de logótipos e upload do Logótipo da Escola em formato Base64 ou URL (impresso automaticamente em pautas, cadernetas, boletins e certificados).
  - **Personalização de Temas e Espectro de Cores:** Cada instituição cadastrada pode escolher o seu esquema cromático institucional através de um **Espectro Visual de 32 Cores Rápidas** (clique direto em qualquer cor), de uma **Barra de Espectro Contínuo de Gradiente (360°)** com ajuste fino de matiz, do seletor livre com conta-gotas (`<input type="color">`), ou entre os 8 temas institucionais pré-definidos (Azul SIGE, Índigo Save, Verde Esmeralda, Bordeaux Rubi, Âmbar Dourado, Grafite Safira, Púrpura Real e Petróleo Ciano). Ao selecionar qualquer cor do espectro, o sistema calcula e aplica automaticamente uma **paleta harmónica** (cor primária, hover, barra lateral e destaques).
  - **Imagem de Fundo e Marca de Água:** Possibilidade de cada escola definir a sua imagem de fundo e marca d'água no sistema (usando o logótipo próprio, emblema nacional, imagens de campus ou upload próprio do computador/URL), configurando o modo de exibição (Marca de Água Central Sutil, Papel de Parede Total Wallpaper, Padrão de Textura Suave ou Sem Fundo Liso) e controle deslizante de opacidade com pré-visualização ao vivo em tempo real.
  - **Assinaturas Institucionais:** Registo dos nomes do Diretor da Escola, do DAP e do Chefe da Secretaria para impressão nas linhas de homologação documental.
  - **Prazos de Inscrição:** Abertura e fecho das matrículas online para o público externo.
  - **Liberação de Notas aos Alunos:** Ativação ou bloqueio do interruptor *"Permitir Visualização de Notas pelos Alunos"*.

---

### Módulo 4: Gestão de Turmas, Lotação e Homologações (`#view-turmas`)
- **Quem usa:** `DAP`, `DIRECTOR_ESCOLA` e `ADMIN_ESCOLA`.
- **Funcionalidades:**
  - **Criação Individual ou em Lote:** Criação de múltiplas turmas de uma só vez por classe e turno com capacidade máxima padrão (50 alunos).
  - **Barra de Ocupação:** Indicadores coloridos de capacidade em tempo real (Verde $<80\%$, Amarelo $\ge 80\%$, Vermelho $100\%$ Lotada).
  - **Formação e Distribuição Automática:** Motor algorítmico que aloca alunos sem turma por ordem alfabética ou balanceamento de género.
  - **Renumerar Turmas:** Normaliza automaticamente os nomes das turmas (`Turma 1`, `Turma 2`, `Turma 3`...) evitando inconsistências.
  - **Nomeação e Homologação de DT e DC:** O DAP nomeia o professor; o Diretor da Escola homologa formalmente o cargo, emitindo o código `DT...` ou `DC...` no Cofre de Senhas.

---

### Módulo 5: Alunos, Matrículas e Transferências (`#view-alunos`)
- **Quem usa:** `CHEFE_SECRETARIA`, `ADMIN_ESCOLA` e `DAP`.
- **Funcionalidades:**
  - **Registo Biográfico:** Cadastro completo com filiação, NUIT, identificação, contactos e enturmação.
  - **Transferência Interna de Turma:** Transfere o aluno de turma preservando e migrando automaticamente todas as notas já lançadas no ano letivo.
  - **Indicadores Demográficos:** Monitorização de taxas de retenção, evasão e distribuição de género (H vs M).

---

### Módulo 6: Professores, Carreiras MEC e Alocações (`#view-professores`)
- **Quem usa:** `DAP` e `ADMIN_ESCOLA`.
- **Carreiras Oficiais:** Enquadramento nas categorias do MEC (`DN4`, `DN3`, `DN2`, `DN1`, `Especialista`, `Mestre`, `Doutor`).
- **Carga Horária Inteligente:** Controlo da carga máxima semanal e cálculo automático entre **Horas Normais** e **Horas Extras** por classe.
- **Alocação Docente:** Associação de `Professor + Turma + Disciplina`. Inicializa automaticamente as grelhas dos 3 trimestres da caderneta.

---

### Módulo 7: Disciplinas e Matriz Curricular (`#view-disciplinas`)
- **Quem usa:** `DAP` e `ADMIN_ESCOLA`.
- **Auto-Seed Nacional:** Sincronização do plano curricular oficial da 7ª à 12ª Classe com um clique (`/seed-curriculo`).
- **Ranking de Reprovação:** Gráfico dinâmico que destaca as disciplinas com maiores índices de insucesso pedagógico na escola.

---

### Módulo 8: Biblioteca Digital de Material Escolar (`#view-material-escolar`)
- **Quem usa:** Professores, Alunos e Direção.
- **Acervo Pedagógico:** Manuais escolares oficiais, fichas didáticas, planos de aula e livros organizados da 1ª à 12ª Classe.
- **Upload e Download:** Suporte a ficheiros locais até 15 MB (PDF, DOCX, XLSX, PPTX, Imagens) ou links externos com controlo de permissão por perfil.

---

### Módulo 9: Caderneta Electrónica do Professor (`#view-caderneta`)
- **Quem usa:** `PROFESSOR`, `DAP` e `DIRECTOR_ESCOLA`.
- **Estrutura Visual:** Exibe lado a lado as colunas dos **3 Trimestres** (`1ª ACS`, `2ª ACS`, `3ª ACS`, `MAP`, `MAS`, `AT`, `MT`, `COM`, `Faltas`) mais a **Média Final da Disciplina (MFD)**.
- **Estatísticas no Rodapé por Coluna:** Apuração demográfica automática de Avaliados, Positivos ($\ge 10$) e Negativos ($< 10$) discriminados por Rapazes (`H`), Raparigas (`M`) e Total (`HM`), com respetivas percentagens.
- **Exportação:** Descarregamento em Excel (`.xlsx`), PDF (`.pdf`) ou impressão direta em formato horizontal (Landscape).

---

### Módulo 10: Calendário de Notas e Desbloqueio (`#view-desbloqueio`)
- **Quem usa:** `DAP` e `DIRECTOR_ESCOLA`.
- **Prazos Trimestrais:** Definição das datas de abertura e encerramento do lançamento de notas para os 3 trimestres.
- **Autorização de Desbloqueio:** Concessão de credencial temporária e justificada a um docente para lançar ou retificar notas fora do prazo ou com pauta fechada.

---

### Módulo 11: Pautas Gerais e Actas do Conselho (`#view-pautas`)
- **Quem usa:** `DT` (Director de Turma), `DAP` e `DIRECTOR_ESCOLA`.
- **Aba 1 — Pauta Geral da Turma:** Mapa integral com todas as disciplinas da área da turma, médias trimestrais, MFD, faltas, média global e quadro estatístico do MEC.
- **Aba 2 — Acta Oficial do Conselho de Avaliação:** Documento formal da sessão de avaliação com conversão automática de valores e percentagens **por extenso em língua portuguesa**, tabela demográfica consolidada e linhas para assinaturas institucionais.
- **Painel do Director de Turma (`#view-director-turma`):** Configuração de data, hora de início/término e nome do Presidente da Sessão para cada trimestre.

---

### Módulo 12: Estatística Oficial do Aproveitamento (`#view-estatisticas-aproveitamento`)
- **Quem usa:** `DAP`, `DIRECTOR_ESCOLA` e `ADMIN_ESCOLA`.
- **4 Níveis de Análise:**
  1. *Resumo Geral da Escola* (taxa global de aprovação, matriculados e avaliados).
  2. *Aproveitamento por Classe* (comparativo da 7ª à 12ª Classe).
  3. *Aproveitamento por Turma* (desempenho turma a turma com identificação do DT).
  4. *Aproveitamento por Disciplina e Docente* (taxas de aprovação por professor).
- **Exportação:** Geração de relatórios analíticos em PDF e planilhas eletrónicas Excel (`.xlsx`).

---

### Módulo 13: Emissão de Certificados com QR Code (`#view-certificados`)
- **Quem usa:** `CHEFE_SECRETARIA` e `DIRECTOR_ESCOLA`.
- **Tipos de Certificado:** Conclusão de Classe/Ciclo, Guia de Transferência, Declaração com Notas e Comprovativo de Matrícula.
- **Autenticidade Criptográfica:** Código alfanumérico único e QR Code para verificação online imediata.

---

### Módulo 14: Gestão Financeira e Propinas (`#view-pagamentos`)
- **Quem usa:** `FINANCEIRO` e `CHEFE_SECRETARIA`.
- **Geração em Lote:** Criação de faturas mensais de propina para todos os estudantes de uma turma simultaneamente.
- **Liquidação Multicanal:** Suporte a M-Pesa, e-Mola, POS, Transferência Bancária e Dinheiro vivo, com emissão de recibo numerado oficial (`REC-...`).
- **Dashboard de Inadimplência:** Controlo de adimplência, total pendente e gráfico de receitas mês a mês.
- **Validação e Notificações In-App:** Bloqueio preventivo e no backend contra faturas duplicadas (*"A factura já foi gerada no sistema."*), utilizando modais e avisos in-app estilizados (`mostrarAlerta`) sem exibir qualquer link ou cabeçalho do navegador (*"sigesaas.duckdns.org diz"*).

---

### Módulo 15: Central de Impressão e Cofre de Arquivos (`#view-impressao`)
- **Quem usa:** Todos os utilizadores autorizados.
- **Emissão Individual ou em Lote:** Impressão em lote de todos os alunos de uma turma num único arquivo paginado.
- **Três Formatos Nativos:** PDF vetorial de alta definição, Word (.docx editável em Times New Roman) e Excel (.xlsx formatado para impressão A4).
- **Cofre Histórico (`DocumentoSalvo`):** Arquivo de todos os documentos gerados pelo sistema para download posterior.

---

### Módulo 16: Portal Privado do Aluno (`#view-aluno-*`)
- **Quem usa:** Alunos matriculados e encarregados de educação.
- **Funcionalidades:** Acesso simplificado e protegido com três abas principais:
  - *O Meu Perfil:* Dados pessoais e comprovativo de enturmação.
  - *As Minhas Notas:* Boletim digital com notas contínuas, médias trimestrais e anuais (sujeito à liberação do DAP).
  - *As Minhas Propinas:* Consulta de faturas pagas e pendentes.

---

### Módulo 17: Cofre de Credenciais e Gestão de Senhas (`#view-usuarios-senhas`)
- **Quem usa:** `ADMIN_ESCOLA`, `DIRECTOR_ESCOLA`, `DAP` e `CHEFE_SECRETARIA`.
- **Sincronização Automática:** Deteta e gera instantaneamente contas de acesso em falta para órgãos diretivos, professores, diretores de turma e alunos.
- **Controlo de Senhas:** Visualização dos códigos oficiais de acesso, redefinição de palavras-passe esquecidas e bloqueio/desbloqueio de utilizadores.

---

### Módulo 18: Auditoria e Registo de Acessos (`#view-acessos`)
- **Quem usa:** `ADMIN_ESCOLA` e `SUPERADMIN`.
- **Rastreamento Total:** Log cronológico de todas as sessões iniciadas, tentativas inválidas de autenticação e bloqueios por assinatura expirada com registo de data, hora e dispositivo (`user-agent`).

---

### Módulo 19: Assinatura e Pagamentos SaaS da Escola (`#view-assinatura-escola`)
- **Quem usa:** `ADMIN_ESCOLA`, `DIRECTOR_ESCOLA` e `SUPERADMIN`.
- **Painel Financeiro Institucional:**
  - **Estado da Subscrição:** Acompanhamento em tempo real (`Activa`, `Fatura Aberta`, `Em Atraso`, `Restrita` ou `Suspensa`) com badge e alertas de prazo.
  - **Plano Contratado:** Apresentação clara e oficial como **Plano Básico** (com periodicidade e valor mensal em Meticais `MZN`).
  - **Próximo Vencimento & Faturas:** Cronograma de faturação com botão para envio de comprovativos de liquidação.
  - **Coordenadas Oficiais em Moçambique:** Carteiras móveis M-Pesa (Vodacom) e e-Mola (Movitel), e contas bancárias Millennium BIM e BCI com validação pelo SuperAdmin.

