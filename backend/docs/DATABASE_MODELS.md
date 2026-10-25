# CatÃ¡logo de Modelos de Dados â SIGE (Django ORM)

> Gerado automaticamente via introspecÃ§Ã£o do Django ORM.

---

## AplicaÃ§Ã£o: `apps.accounts`

### Modelo: `Usuario`

Usuario(password, last_login, is_superuser, first_name, last_name, is_staff, is_active, date_joined, id, email, nome, role, escola, ativo, telefone, avatar_url, aluno_id, professor_id, codigo_acesso, senha_redefinida, username)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `password` | `CharField` | NÃ£o |  |
| `last_login` | `DateTimeField` | Sim |  |
| `is_superuser` | `BooleanField` | NÃ£o |  |
| `first_name` | `CharField` | NÃ£o |  |
| `last_name` | `CharField` | NÃ£o |  |
| `is_staff` | `BooleanField` | NÃ£o |  |
| `is_active` | `BooleanField` | NÃ£o |  |
| `date_joined` | `DateTimeField` | NÃ£o |  |
| `id` | `UUIDField` | NÃ£o |  |
| `email` | `CharField` | NÃ£o |  |
| `nome` | `CharField` | NÃ£o |  |
| `role` | `CharField` | NÃ£o |  |
| `escola` | `ForeignKey` | Sim |  -> `Escola` |
| `ativo` | `BooleanField` | NÃ£o |  |
| `telefone` | `CharField` | Sim |  |
| `avatar_url` | `CharField` | Sim |  |
| `aluno_id` | `UUIDField` | Sim |  |
| `professor_id` | `UUIDField` | Sim |  |
| `codigo_acesso` | `CharField` | Sim |  |
| `senha_redefinida` | `BooleanField` | NÃ£o |  |
| `username` | `CharField` | NÃ£o |  |
| `groups` | `ManyToManyField` | NÃ£o |  -> `Group` |
| `user_permissions` | `ManyToManyField` | NÃ£o |  -> `Permission` |


### Modelo: `LogAcesso`

LogAcesso(id, escola, usuario, ip, user_agent, tipo, created_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `escola` | `ForeignKey` | Sim |  -> `Escola` |
| `usuario` | `ForeignKey` | Sim |  -> `Usuario` |
| `ip` | `CharField` | NÃ£o |  |
| `user_agent` | `TextField` | Sim |  |
| `tipo` | `CharField` | NÃ£o |  |
| `created_at` | `DateTimeField` | NÃ£o |  |


## AplicaÃ§Ã£o: `apps.tenants`

### Modelo: `Plano`

Plano(id, nome, descricao, preco, duracao_dias, max_alunos, max_professores, ativo, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `nome` | `CharField` | NÃ£o |  |
| `descricao` | `TextField` | Sim |  |
| `preco` | `DecimalField` | NÃ£o |  |
| `duracao_dias` | `IntegerField` | NÃ£o |  |
| `max_alunos` | `IntegerField` | NÃ£o |  |
| `max_professores` | `IntegerField` | NÃ£o |  |
| `ativo` | `BooleanField` | NÃ£o |  |
| `created_at` | `DateTimeField` | NÃ£o |  |
| `updated_at` | `DateTimeField` | NÃ£o |  |


### Modelo: `Escola`

Escola(id, nome, nif_cnpj, endereco, telefone, email, logo_url, status, ano_letivo_ativo, trimestre_ativo, plano, data_adesao, provincia, distrito, tipo_escola, director_nome, director_carreira, dap_nome, chefe_secretaria_nome, usar_emblema_nacional, codigo_escola, logo_base64, galeria_logos, tema_codigo, tema_cor_primaria, tema_cor_hover, tema_cor_sidebar, tema_cor_sidebar_ativa, imagem_fundo_url, imagem_fundo_base64, imagem_fundo_modo, imagem_fundo_opacidade, galeria_fundos, bloqueada_manualmente, permitir_visualizacao_notas, modo_publicacao_notas, publicacao_notas_trimestre, data_inicio_pub_t1, data_fim_pub_t1, data_inicio_pub_t2, data_fim_pub_t2, data_inicio_pub_todos, data_fim_pub_todos, inscricoes_abertas, inscricoes_inicio, inscricoes_fim, modo_calendarizacao, tipo_duracao_automatica, valor_duracao_automatica, data_base_automatica, data_inicio_t1, data_fim_t1, data_inicio_t2, data_fim_t2, data_inicio_t3, data_fim_t3, permitir_sempre_t1, permitir_sempre_t2, permitir_sempre_t3, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `nome` | `CharField` | NÃ£o |  |
| `nif_cnpj` | `CharField` | NÃ£o |  |
| `endereco` | `TextField` | Sim |  |
| `telefone` | `CharField` | Sim |  |
| `email` | `CharField` | NÃ£o |  |
| `logo_url` | `CharField` | Sim |  |
| `status` | `CharField` | NÃ£o |  |
| `ano_letivo_ativo` | `CharField` | NÃ£o |  |
| `trimestre_ativo` | `CharField` | NÃ£o |  |
| `plano` | `ForeignKey` | Sim |  -> `Plano` |
| `data_adesao` | `DateTimeField` | NÃ£o |  |
| `provincia` | `CharField` | NÃ£o |  |
| `distrito` | `CharField` | NÃ£o |  |
| `tipo_escola` | `CharField` | NÃ£o |  |
| `director_nome` | `CharField` | NÃ£o |  |
| `director_carreira` | `CharField` | NÃ£o |  |
| `dap_nome` | `CharField` | NÃ£o |  |
| `chefe_secretaria_nome` | `CharField` | NÃ£o |  |
| `usar_emblema_nacional` | `BooleanField` | NÃ£o |  |
| `codigo_escola` | `CharField` | Sim |  |
| `logo_base64` | `TextField` | Sim |  |
| `galeria_logos` | `JSONField` | NÃ£o |  |
| modo_uso_logo | CharField | Não | Modo: DOCUMENTOS, DOCUMENTOS_E_MARCA_DAGUA, APENAS_MARCA_DAGUA |
| marca_dagua_url | TextField | Sim | URL ou Base64 de imagem específica para Marca d'Água |
| marca_dagua_base64 | TextField | Sim |  |
| marca_dagua_modo | CharField | Não | Modo: EMBLEMA_NACIONAL, MESMO_LOGO, ESPECIFICA, NENHUM |
| `tema_codigo` | `CharField` | NÃ£o |  |
| `tema_cor_primaria` | `CharField` | NÃ£o |  |
| `tema_cor_hover` | `CharField` | NÃ£o |  |
| `tema_cor_sidebar` | `CharField` | NÃ£o |  |
| `tema_cor_sidebar_ativa` | `CharField` | NÃ£o |  |
| `imagem_fundo_url` | `TextField` | Sim |  |
| `imagem_fundo_base64` | `TextField` | Sim |  |
| `imagem_fundo_modo` | `CharField` | NÃ£o |  |
| `imagem_fundo_opacidade` | `IntegerField` | NÃ£o |  |
| `galeria_fundos` | `JSONField` | NÃ£o |  |
| `bloqueada_manualmente` | `BooleanField` | NÃ£o |  |
| `permitir_visualizacao_notas` | `BooleanField` | NÃ£o |  |
| `modo_publicacao_notas` | `CharField` | NÃ£o |  |
| `publicacao_notas_trimestre` | `CharField` | NÃ£o |  |
| `data_inicio_pub_t1` | `DateField` | Sim |  |
| `data_fim_pub_t1` | `DateField` | Sim |  |
| `data_inicio_pub_t2` | `DateField` | Sim |  |
| `data_fim_pub_t2` | `DateField` | Sim |  |
| `data_inicio_pub_todos` | `DateField` | Sim |  |
| `data_fim_pub_todos` | `DateField` | Sim |  |
| `inscricoes_abertas` | `BooleanField` | NÃ£o |  |
| `inscricoes_inicio` | `DateTimeField` | Sim |  |
| `inscricoes_fim` | `DateTimeField` | Sim |  |
| `modo_calendarizacao` | `CharField` | NÃ£o |  |
| `tipo_duracao_automatica` | `CharField` | NÃ£o |  |
| `valor_duracao_automatica` | `IntegerField` | NÃ£o |  |
| `data_base_automatica` | `DateField` | Sim |  |
| `data_inicio_t1` | `DateField` | Sim |  |
| `data_fim_t1` | `DateField` | Sim |  |
| `data_inicio_t2` | `DateField` | Sim |  |
| `data_fim_t2` | `DateField` | Sim |  |
| `data_inicio_t3` | `DateField` | Sim |  |
| `data_fim_t3` | `DateField` | Sim |  |
| `permitir_sempre_t1` | `BooleanField` | NÃ£o |  |
| `permitir_sempre_t2` | `BooleanField` | NÃ£o |  |
| `permitir_sempre_t3` | `BooleanField` | NÃ£o |  |
| `created_at` | `DateTimeField` | NÃ£o |  |
| `updated_at` | `DateTimeField` | NÃ£o |  |


### Modelo: `AssinaturaEscola`

AssinaturaEscola(id, escola, plano, data_inicio, data_fim, valor, status, metodo_pagamento, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `escola` | `ForeignKey` | NÃ£o |  -> `Escola` |
| `plano` | `ForeignKey` | NÃ£o |  -> `Plano` |
| `data_inicio` | `DateTimeField` | NÃ£o |  |
| `data_fim` | `DateTimeField` | NÃ£o |  |
| `valor` | `DecimalField` | NÃ£o |  |
| `status` | `CharField` | NÃ£o |  |
| `metodo_pagamento` | `CharField` | NÃ£o |  |
| `created_at` | `DateTimeField` | NÃ£o |  |
| `updated_at` | `DateTimeField` | NÃ£o |  |


### Modelo: `AnoLectivo`

AnoLectivo(id, escola, ano, descricao, ativo, data_inicio, data_fim, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `escola` | `ForeignKey` | NÃ£o |  -> `Escola` |
| `ano` | `CharField` | NÃ£o |  |
| `descricao` | `CharField` | NÃ£o |  |
| `ativo` | `BooleanField` | NÃ£o |  |
| `data_inicio` | `DateField` | Sim |  |
| `data_fim` | `DateField` | Sim |  |
| `created_at` | `DateTimeField` | NÃ£o |  |
| `updated_at` | `DateTimeField` | NÃ£o |  |


### Modelo: `SaasPlano`

SaasPlano(id, nome, descricao, preco_mensal, limite_alunos, limite_professores, limites, activo, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `nome` | `CharField` | NÃ£o |  |
| `descricao` | `TextField` | Sim |  |
| `preco_mensal` | `DecimalField` | NÃ£o |  |
| `limite_alunos` | `IntegerField` | NÃ£o |  |
| `limite_professores` | `IntegerField` | NÃ£o |  |
| `limites` | `JSONField` | NÃ£o |  |
| `activo` | `BooleanField` | NÃ£o |  |
| `created_at` | `DateTimeField` | NÃ£o |  |
| `updated_at` | `DateTimeField` | NÃ£o |  |


### Modelo: `SaasAssinatura`

SaasAssinatura(id, instituicao, plano, periodicidade, modo_data_limite, dia_limite, dias_tolerancia, dias_ate_suspensao, data_bloqueio_manual, multa_tipo, multa_valor, estado, data_inicio, proxima_fatura_em, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `instituicao` | `ForeignKey` | NÃ£o |  -> `Escola` |
| `plano` | `ForeignKey` | NÃ£o |  -> `SaasPlano` |
| `periodicidade` | `CharField` | NÃ£o |  |
| `modo_data_limite` | `CharField` | NÃ£o |  |
| `dia_limite` | `IntegerField` | Sim |  |
| `dias_tolerancia` | `IntegerField` | NÃ£o |  |
| `dias_ate_suspensao` | `IntegerField` | NÃ£o |  |
| `data_bloqueio_manual` | `DateField` | Sim |  |
| `multa_tipo` | `CharField` | NÃ£o |  |
| `multa_valor` | `DecimalField` | NÃ£o |  |
| `estado` | `CharField` | NÃ£o |  |
| `data_inicio` | `DateTimeField` | NÃ£o |  |
| `proxima_fatura_em` | `DateField` | NÃ£o |  |
| `created_at` | `DateTimeField` | NÃ£o |  |
| `updated_at` | `DateTimeField` | NÃ£o |  |


### Modelo: `SaasFatura`

SaasFatura(id, assinatura, instituicao, numero_fatura, periodo_inicio, periodo_fim, valor, multa_aplicada, valor_pago, data_abertura, data_limite, data_limite_manual, estado, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `assinatura` | `ForeignKey` | NÃ£o |  -> `SaasAssinatura` |
| `instituicao` | `ForeignKey` | NÃ£o |  -> `Escola` |
| `numero_fatura` | `CharField` | NÃ£o |  |
| `periodo_inicio` | `DateField` | NÃ£o |  |
| `periodo_fim` | `DateField` | NÃ£o |  |
| `valor` | `DecimalField` | NÃ£o |  |
| `multa_aplicada` | `DecimalField` | NÃ£o |  |
| `valor_pago` | `DecimalField` | NÃ£o |  |
| `data_abertura` | `DateField` | NÃ£o |  |
| `data_limite` | `DateField` | NÃ£o |  |
| `data_limite_manual` | `DateField` | Sim |  |
| `estado` | `CharField` | NÃ£o |  |
| `created_at` | `DateTimeField` | NÃ£o |  |
| `updated_at` | `DateTimeField` | NÃ£o |  |


### Modelo: `SaasPagamento`

SaasPagamento(id, fatura, instituicao, metodo, referencia, valor, comprovativo_path, comprovativo_url, estado, confirmado_por, confirmado_em, motivo_rejeicao, criado_em, updated_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `fatura` | `ForeignKey` | NÃ£o |  -> `SaasFatura` |
| `instituicao` | `ForeignKey` | NÃ£o |  -> `Escola` |
| `metodo` | `CharField` | NÃ£o |  |
| `referencia` | `CharField` | NÃ£o |  |
| `valor` | `DecimalField` | NÃ£o |  |
| `comprovativo_path` | `TextField` | Sim |  |
| `comprovativo_url` | `TextField` | Sim |  |
| `estado` | `CharField` | NÃ£o |  |
| `confirmado_por` | `CharField` | Sim |  |
| `confirmado_em` | `DateTimeField` | Sim |  |
| `motivo_rejeicao` | `TextField` | Sim |  |
| `criado_em` | `DateTimeField` | NÃ£o |  |
| `updated_at` | `DateTimeField` | NÃ£o |  |


### Modelo: `SaasLogAssinatura`

SaasLogAssinatura(id, instituicao, assinatura, fatura, accao, estado_anterior, estado_novo, valor_anterior, valor_novo, feito_por, motivo, criado_em)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `instituicao` | `ForeignKey` | NÃ£o |  -> `Escola` |
| `assinatura` | `ForeignKey` | Sim |  -> `SaasAssinatura` |
| `fatura` | `ForeignKey` | Sim |  -> `SaasFatura` |
| `accao` | `CharField` | NÃ£o |  |
| `estado_anterior` | `CharField` | Sim |  |
| `estado_novo` | `CharField` | Sim |  |
| `valor_anterior` | `DecimalField` | Sim |  |
| `valor_novo` | `DecimalField` | Sim |  |
| `feito_por` | `CharField` | NÃ£o |  |
| `motivo` | `TextField` | Sim |  |
| `criado_em` | `DateTimeField` | NÃ£o |  |


### Modelo: `SaasCoordenadasPagamento`

SaasCoordenadasPagamento(id, mpesa_numero, mpesa_titular, emola_numero, emola_titular, bim_conta, bim_nib, bim_titular, bci_conta, bci_nib, bci_titular, nuit_entidade, instrucoes_adicionais, updated_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `mpesa_numero` | `CharField` | NÃ£o |  |
| `mpesa_titular` | `CharField` | NÃ£o |  |
| `emola_numero` | `CharField` | NÃ£o |  |
| `emola_titular` | `CharField` | NÃ£o |  |
| `bim_conta` | `CharField` | NÃ£o |  |
| `bim_nib` | `CharField` | NÃ£o |  |
| `bim_titular` | `CharField` | NÃ£o |  |
| `bci_conta` | `CharField` | NÃ£o |  |
| `bci_nib` | `CharField` | NÃ£o |  |
| `bci_titular` | `CharField` | NÃ£o |  |
| `nuit_entidade` | `CharField` | NÃ£o |  |
| `instrucoes_adicionais` | `TextField` | NÃ£o |  |
| `updated_at` | `DateTimeField` | NÃ£o |  |


## AplicaÃ§Ã£o: `apps.alunos`

### Modelo: `Aluno`

Aluno(id, escola, turma, classe, area, ano_ingresso, matricula, nome, apelido, data_nascimento, genero, tipo_documento, numero_documento, nuit, nacionalidade, provincia, distrito, pai, mae, nome_responsavel, contato_responsavel, email_responsavel, status, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `escola` | `ForeignKey` | NÃ£o |  -> `Escola` |
| `turma` | `ForeignKey` | Sim |  -> `Turma` |
| `classe` | `CharField` | Sim |  |
| `area` | `CharField` | Sim |  |
| `ano_ingresso` | `CharField` | Sim |  |
| `matricula` | `CharField` | NÃ£o |  |
| `nome` | `CharField` | NÃ£o |  |
| `apelido` | `CharField` | Sim |  |
| `data_nascimento` | `DateField` | NÃ£o |  |
| `genero` | `CharField` | NÃ£o |  |
| `tipo_documento` | `CharField` | NÃ£o |  |
| `numero_documento` | `CharField` | Sim |  |
| `nuit` | `CharField` | Sim |  |
| `nacionalidade` | `CharField` | NÃ£o |  |
| `provincia` | `CharField` | NÃ£o |  |
| `distrito` | `CharField` | NÃ£o |  |
| `pai` | `CharField` | Sim |  |
| `mae` | `CharField` | Sim |  |
| `nome_responsavel` | `CharField` | Sim |  |
| `contato_responsavel` | `CharField` | Sim |  |
| `email_responsavel` | `CharField` | Sim |  |
| `status` | `CharField` | NÃ£o |  |
| `created_at` | `DateTimeField` | NÃ£o |  |
| `updated_at` | `DateTimeField` | NÃ£o |  |


## AplicaÃ§Ã£o: `apps.professores`

### Modelo: `Professor`

Professor(id, escola, codigo, nome, apelido, genero, email, telefone, tipo_documento, numero_documento, nuit, nacionalidade, provincia, distrito, carreira, especialidade, carga_horaria_semanal, carga_maxima_por_classe, ativo, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `escola` | `ForeignKey` | NÃ£o |  -> `Escola` |
| `codigo` | `CharField` | Sim |  |
| `nome` | `CharField` | NÃ£o |  |
| `apelido` | `CharField` | Sim |  |
| `genero` | `CharField` | NÃ£o |  |
| `email` | `CharField` | NÃ£o |  |
| `telefone` | `CharField` | Sim |  |
| `tipo_documento` | `CharField` | NÃ£o |  |
| `numero_documento` | `CharField` | Sim |  |
| `nuit` | `CharField` | Sim |  |
| `nacionalidade` | `CharField` | NÃ£o |  |
| `provincia` | `CharField` | NÃ£o |  |
| `distrito` | `CharField` | NÃ£o |  |
| `carreira` | `CharField` | NÃ£o |  |
| `especialidade` | `CharField` | NÃ£o |  |
| `carga_horaria_semanal` | `IntegerField` | NÃ£o |  |
| `carga_maxima_por_classe` | `JSONField` | Sim |  |
| `ativo` | `BooleanField` | NÃ£o |  |
| `created_at` | `DateTimeField` | NÃ£o |  |
| `updated_at` | `DateTimeField` | NÃ£o |  |


### Modelo: `AlocacaoDocente`

AlocacaoDocente(id, escola, professor, disciplina, turma, created_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `escola` | `ForeignKey` | NÃ£o |  -> `Escola` |
| `professor` | `ForeignKey` | NÃ£o |  -> `Professor` |
| `disciplina` | `ForeignKey` | NÃ£o |  -> `Disciplina` |
| `turma` | `ForeignKey` | NÃ£o |  -> `Turma` |
| `created_at` | `DateTimeField` | NÃ£o |  |


## AplicaÃ§Ã£o: `apps.turmas`

### Modelo: `Turma`

Turma(id, escola, nome, grau_ano, turno, sala, capacidade_maxima, ano_letivo, area, director_turma, dt_status_homologacao, dt_nomeado_por, dt_data_nomeacao, dt_homologado_por, dt_data_homologacao, codigo_director_turma, director_classe, dc_status_homologacao, dc_nomeado_por, dc_data_nomeacao, dc_homologado_por, dc_data_homologacao, codigo_director_classe, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `escola` | `ForeignKey` | NÃ£o |  -> `Escola` |
| `nome` | `CharField` | NÃ£o |  |
| `grau_ano` | `CharField` | NÃ£o |  |
| `turno` | `CharField` | NÃ£o |  |
| `sala` | `CharField` | Sim |  |
| `capacidade_maxima` | `PositiveIntegerField` | NÃ£o |  |
| `ano_letivo` | `CharField` | NÃ£o |  |
| `area` | `CharField` | NÃ£o |  |
| `director_turma` | `ForeignKey` | Sim |  -> `Professor` |
| `dt_status_homologacao` | `CharField` | NÃ£o |  |
| `dt_nomeado_por` | `CharField` | Sim |  |
| `dt_data_nomeacao` | `DateTimeField` | Sim |  |
| `dt_homologado_por` | `CharField` | Sim |  |
| `dt_data_homologacao` | `DateTimeField` | Sim |  |
| `codigo_director_turma` | `CharField` | Sim |  |
| `director_classe` | `ForeignKey` | Sim |  -> `Professor` |
| `dc_status_homologacao` | `CharField` | NÃ£o |  |
| `dc_nomeado_por` | `CharField` | Sim |  |
| `dc_data_nomeacao` | `DateTimeField` | Sim |  |
| `dc_homologado_por` | `CharField` | Sim |  |
| `dc_data_homologacao` | `DateTimeField` | Sim |  |
| `codigo_director_classe` | `CharField` | Sim |  |
| `created_at` | `DateTimeField` | NÃ£o |  |
| `updated_at` | `DateTimeField` | NÃ£o |  |


## AplicaÃ§Ã£o: `apps.disciplinas`

### Modelo: `Disciplina`

Disciplina(id, escola, nome, codigo, classe, area, carga_horaria, ano_letivo, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `escola` | `ForeignKey` | NÃ£o |  -> `Escola` |
| `nome` | `CharField` | NÃ£o |  |
| `codigo` | `CharField` | NÃ£o |  |
| `classe` | `CharField` | NÃ£o |  |
| `area` | `CharField` | NÃ£o |  |
| `carga_horaria` | `IntegerField` | NÃ£o |  |
| `ano_letivo` | `CharField` | NÃ£o |  |
| `created_at` | `DateTimeField` | NÃ£o |  |
| `updated_at` | `DateTimeField` | NÃ£o |  |


## AplicaÃ§Ã£o: `apps.notas`

### Modelo: `Nota`

Nota(id, escola, aluno, disciplina, turma, periodo, teste1, teste2, teste3, teste4, trabalho, avaliacao_trimestral, media_final, faltas, anotacao, comportamento, resultado, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `escola` | `ForeignKey` | NÃ£o |  -> `Escola` |
| `aluno` | `ForeignKey` | NÃ£o |  -> `Aluno` |
| `disciplina` | `ForeignKey` | NÃ£o |  -> `Disciplina` |
| `turma` | `ForeignKey` | NÃ£o |  -> `Turma` |
| `periodo` | `CharField` | NÃ£o |  |
| `teste1` | `FloatField` | Sim |  |
| `teste2` | `FloatField` | Sim |  |
| `teste3` | `FloatField` | Sim |  |
| `teste4` | `FloatField` | Sim |  |
| `trabalho` | `FloatField` | Sim |  |
| `avaliacao_trimestral` | `FloatField` | Sim |  |
| `media_final` | `FloatField` | NÃ£o |  |
| `faltas` | `IntegerField` | NÃ£o |  |
| `anotacao` | `CharField` | Sim |  |
| `comportamento` | `CharField` | Sim |  |
| `resultado` | `CharField` | NÃ£o |  |
| `created_at` | `DateTimeField` | NÃ£o |  |
| `updated_at` | `DateTimeField` | NÃ£o |  |


### Modelo: `PermissaoEdicaoNotas`

PermissaoEdicaoNotas(id, escola, professor, turma, disciplina, periodo, autorizado_por, motivo, duracao_horas, data_expiracao, ativa, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `escola` | `ForeignKey` | NÃ£o |  -> `Escola` |
| `professor` | `ForeignKey` | Sim |  -> `Professor` |
| `turma` | `ForeignKey` | NÃ£o |  -> `Turma` |
| `disciplina` | `ForeignKey` | Sim |  -> `Disciplina` |
| `periodo` | `CharField` | NÃ£o |  |
| `autorizado_por` | `CharField` | NÃ£o |  |
| `motivo` | `TextField` | Sim |  |
| `duracao_horas` | `IntegerField` | NÃ£o |  |
| `data_expiracao` | `DateTimeField` | Sim |  |
| `ativa` | `BooleanField` | NÃ£o |  |
| `created_at` | `DateTimeField` | NÃ£o |  |
| `updated_at` | `DateTimeField` | NÃ£o |  |


## AplicaÃ§Ã£o: `apps.pautas`

### Modelo: `Pauta`

Pauta(id, escola, turma, ano_letivo, periodo, status, data_fechamento, homologado_por, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `escola` | `ForeignKey` | NÃ£o |  -> `Escola` |
| `turma` | `ForeignKey` | NÃ£o |  -> `Turma` |
| `ano_letivo` | `CharField` | NÃ£o |  |
| `periodo` | `CharField` | NÃ£o |  |
| `status` | `CharField` | NÃ£o |  |
| `data_fechamento` | `DateTimeField` | Sim |  |
| `homologado_por` | `CharField` | Sim |  |
| `created_at` | `DateTimeField` | NÃ£o |  |
| `updated_at` | `DateTimeField` | NÃ£o |  |


## AplicaÃ§Ã£o: `apps.material_escolar`

### Modelo: `MaterialEscolar`

MaterialEscolar(id, escola, disciplina, classe, titulo, descricao, nome_arquivo, extensao, tamanho_bytes, conteudo_base64, tipo_mime, arquivo_url, tipo, publicado_por, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `escola` | `ForeignKey` | NÃ£o |  -> `Escola` |
| `disciplina` | `ForeignKey` | Sim |  -> `Disciplina` |
| `classe` | `CharField` | NÃ£o |  |
| `titulo` | `CharField` | NÃ£o |  |
| `descricao` | `TextField` | Sim |  |
| `nome_arquivo` | `CharField` | NÃ£o |  |
| `extensao` | `CharField` | NÃ£o |  |
| `tamanho_bytes` | `BigIntegerField` | NÃ£o |  |
| `conteudo_base64` | `TextField` | Sim |  |
| `tipo_mime` | `CharField` | NÃ£o |  |
| `arquivo_url` | `CharField` | Sim |  |
| `tipo` | `CharField` | NÃ£o |  |
| `publicado_por` | `CharField` | Sim |  |
| `created_at` | `DateTimeField` | NÃ£o |  |
| `updated_at` | `DateTimeField` | NÃ£o |  |


## AplicaÃ§Ã£o: `apps.documentos`

### Modelo: `LogImpressao`

LogImpressao(id, escola, usuario, tipo_documento, descricao, conteudo_json, data_emissao, created_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `escola` | `ForeignKey` | NÃ£o |  -> `Escola` |
| `usuario` | `ForeignKey` | Sim |  -> `Usuario` |
| `tipo_documento` | `CharField` | NÃ£o |  |
| `descricao` | `CharField` | NÃ£o |  |
| `conteudo_json` | `TextField` | Sim |  |
| `data_emissao` | `DateTimeField` | NÃ£o |  |
| `created_at` | `DateTimeField` | NÃ£o |  |


### Modelo: `DocumentoSalvo`

DocumentoSalvo(id, escola, usuario, aluno, turma, tipo_documento, titulo, ano_letivo, dados_json, hash_md5, criado_em)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `escola` | `ForeignKey` | NÃ£o |  -> `Escola` |
| `usuario` | `ForeignKey` | Sim |  -> `Usuario` |
| `aluno` | `ForeignKey` | Sim |  -> `Aluno` |
| `turma` | `ForeignKey` | Sim |  -> `Turma` |
| `tipo_documento` | `CharField` | NÃ£o |  |
| `titulo` | `CharField` | NÃ£o |  |
| `ano_letivo` | `CharField` | NÃ£o |  |
| `dados_json` | `TextField` | NÃ£o |  |
| `hash_md5` | `CharField` | Sim |  |
| `criado_em` | `DateTimeField` | NÃ£o |  |


## AplicaÃ§Ã£o: `apps.pagamentos`

### Modelo: `PlanoPagamentoEscola`

Plano de Pagamentos / Tabela de Propinas e Emolumentos PrÃ³pria da InstituiÃ§Ã£o.
    Isolamento total:
    - O plano do Super Admin aplica-se unicamente Ã s instituiÃ§Ãµes (B2B SaaS).
    - Cada instituiÃ§Ã£o cria e gere os seus prÃ³prios planos para aplicar aos seus alunos.
    - O que uma instituiÃ§Ã£o faz no seu sistema nÃ£o compromete nem reflecte noutra.

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `escola` | `ForeignKey` | NÃ£o |  -> `Escola` |
| `nome` | `CharField` | NÃ£o |  |
| `descricao` | `TextField` | NÃ£o |  |
| `valor` | `DecimalField` | NÃ£o |  |
| `periodicidade` | `CharField` | NÃ£o |  |
| `dia_vencimento_padrao` | `IntegerField` | NÃ£o |  |
| `multa_atraso_percentual` | `DecimalField` | NÃ£o |  |
| `multa_atraso_fixo` | `DecimalField` | NÃ£o |  |
| `ativo` | `BooleanField` | NÃ£o |  |
| `created_at` | `DateTimeField` | NÃ£o |  |
| `updated_at` | `DateTimeField` | NÃ£o |  |


### Modelo: `Pagamento`

Pagamento(id, escola, aluno, plano_pagamento, descricao, mes_referencia, valor, valor_pago, status, data_vencimento, data_pagamento, metodo_pagamento, recibo_numero, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `escola` | `ForeignKey` | NÃ£o |  -> `Escola` |
| `aluno` | `ForeignKey` | NÃ£o |  -> `Aluno` |
| `plano_pagamento` | `ForeignKey` | Sim |  -> `PlanoPagamentoEscola` |
| `descricao` | `CharField` | NÃ£o |  |
| `mes_referencia` | `CharField` | NÃ£o |  |
| `valor` | `DecimalField` | NÃ£o |  |
| `valor_pago` | `DecimalField` | NÃ£o |  |
| `status` | `CharField` | NÃ£o |  |
| `data_vencimento` | `DateTimeField` | NÃ£o |  |
| `data_pagamento` | `DateTimeField` | Sim |  |
| `metodo_pagamento` | `CharField` | Sim |  |
| `recibo_numero` | `CharField` | Sim |  |
| `created_at` | `DateTimeField` | NÃ£o |  |
| `updated_at` | `DateTimeField` | NÃ£o |  |


## AplicaÃ§Ã£o: `apps.certificados`

### Modelo: `Certificado`

Certificado(id, escola, aluno, tipo, codigo_autenticidade, qrcode_data, emitido_em, emitido_por, created_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `escola` | `ForeignKey` | NÃ£o |  -> `Escola` |
| `aluno` | `ForeignKey` | NÃ£o |  -> `Aluno` |
| `tipo` | `CharField` | NÃ£o |  |
| `codigo_autenticidade` | `CharField` | NÃ£o |  |
| `qrcode_data` | `TextField` | NÃ£o |  |
| `emitido_em` | `DateTimeField` | NÃ£o |  |
| `emitido_por` | `CharField` | Sim |  |
| `created_at` | `DateTimeField` | NÃ£o |  |


## AplicaÃ§Ã£o: `apps.ferramentas`

### Modelo: `MensagemSMS`

MensagemSMS(id, escola, destinatario, nome_destinatario, operadora, mensagem, tipo, caracteres, segmentos_sms, status, mensagem_id_operadora, created_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `escola` | `ForeignKey` | Sim |  -> `Escola` |
| `destinatario` | `CharField` | NÃ£o |  |
| `nome_destinatario` | `CharField` | NÃ£o |  |
| `operadora` | `CharField` | NÃ£o |  |
| `mensagem` | `TextField` | NÃ£o |  |
| `tipo` | `CharField` | NÃ£o |  |
| `caracteres` | `IntegerField` | NÃ£o |  |
| `segmentos_sms` | `IntegerField` | NÃ£o |  |
| `status` | `CharField` | NÃ£o |  |
| `mensagem_id_operadora` | `CharField` | NÃ£o |  |
| `created_at` | `DateTimeField` | NÃ£o |  |


### Modelo: `TransacaoGatewayMovel`

TransacaoGatewayMovel(id, escola, pagamento, aluno, metodo, telefone, valor, referencia_transacao, recibo_emitido, status, mensagem_retorno, created_at)

| Campo | Tipo | Nulo / Opcional | DescriÃ§Ã£o / RelaÃ§Ã£o |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | NÃ£o |  |
| `escola` | `ForeignKey` | Sim |  -> `Escola` |
| `pagamento` | `ForeignKey` | Sim |  -> `Pagamento` |
| `aluno` | `ForeignKey` | Sim |  -> `Aluno` |
| `metodo` | `CharField` | NÃ£o |  |
| `telefone` | `CharField` | NÃ£o |  |
| `valor` | `DecimalField` | NÃ£o |  |
| `referencia_transacao` | `CharField` | NÃ£o |  |
| `recibo_emitido` | `CharField` | NÃ£o |  |
| `status` | `CharField` | NÃ£o |  |
| `mensagem_retorno` | `TextField` | NÃ£o |  |
| `created_at` | `DateTimeField` | NÃ£o |  |

