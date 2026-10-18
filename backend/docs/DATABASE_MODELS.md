# Catálogo de Modelos de Dados — SIGE (Django ORM)

> Gerado automaticamente via introspecção do Django ORM.

---

## Aplicação: `apps.accounts`

### Modelo: `Usuario`

Usuario(password, last_login, is_superuser, first_name, last_name, is_staff, is_active, date_joined, id, email, nome, role, escola, ativo, telefone, avatar_url, aluno_id, professor_id, codigo_acesso, senha_redefinida, username)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `password` | `CharField` | Não |  |
| `last_login` | `DateTimeField` | Sim |  |
| `is_superuser` | `BooleanField` | Não |  |
| `first_name` | `CharField` | Não |  |
| `last_name` | `CharField` | Não |  |
| `is_staff` | `BooleanField` | Não |  |
| `is_active` | `BooleanField` | Não |  |
| `date_joined` | `DateTimeField` | Não |  |
| `id` | `UUIDField` | Não |  |
| `email` | `CharField` | Não |  |
| `nome` | `CharField` | Não |  |
| `role` | `CharField` | Não |  |
| `escola` | `ForeignKey` | Sim |  -> `Escola` |
| `ativo` | `BooleanField` | Não |  |
| `telefone` | `CharField` | Sim |  |
| `avatar_url` | `CharField` | Sim |  |
| `aluno_id` | `UUIDField` | Sim |  |
| `professor_id` | `UUIDField` | Sim |  |
| `codigo_acesso` | `CharField` | Sim |  |
| `senha_redefinida` | `BooleanField` | Não |  |
| `username` | `CharField` | Não |  |
| `groups` | `ManyToManyField` | Não |  -> `Group` |
| `user_permissions` | `ManyToManyField` | Não |  -> `Permission` |


### Modelo: `LogAcesso`

LogAcesso(id, escola, usuario, ip, user_agent, tipo, created_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Sim |  -> `Escola` |
| `usuario` | `ForeignKey` | Sim |  -> `Usuario` |
| `ip` | `CharField` | Não |  |
| `user_agent` | `TextField` | Sim |  |
| `tipo` | `CharField` | Não |  |
| `created_at` | `DateTimeField` | Não |  |


## Aplicação: `apps.tenants`

### Modelo: `Plano`

Plano(id, nome, descricao, preco, duracao_dias, max_alunos, max_professores, ativo, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `nome` | `CharField` | Não |  |
| `descricao` | `TextField` | Sim |  |
| `preco` | `DecimalField` | Não |  |
| `duracao_dias` | `IntegerField` | Não |  |
| `max_alunos` | `IntegerField` | Não |  |
| `max_professores` | `IntegerField` | Não |  |
| `ativo` | `BooleanField` | Não |  |
| `created_at` | `DateTimeField` | Não |  |
| `updated_at` | `DateTimeField` | Não |  |


### Modelo: `Escola`

Escola(id, nome, nif_cnpj, endereco, telefone, email, logo_url, status, ano_letivo_ativo, trimestre_ativo, plano, data_adesao, provincia, distrito, tipo_escola, director_nome, director_carreira, dap_nome, chefe_secretaria_nome, usar_emblema_nacional, codigo_escola, logo_base64, galeria_logos, tema_codigo, tema_cor_primaria, tema_cor_hover, tema_cor_sidebar, tema_cor_sidebar_ativa, imagem_fundo_url, imagem_fundo_base64, imagem_fundo_modo, imagem_fundo_opacidade, galeria_fundos, bloqueada_manualmente, permitir_visualizacao_notas, modo_publicacao_notas, publicacao_notas_trimestre, data_inicio_pub_t1, data_fim_pub_t1, data_inicio_pub_t2, data_fim_pub_t2, data_inicio_pub_todos, data_fim_pub_todos, inscricoes_abertas, inscricoes_inicio, inscricoes_fim, modo_calendarizacao, tipo_duracao_automatica, valor_duracao_automatica, data_base_automatica, data_inicio_t1, data_fim_t1, data_inicio_t2, data_fim_t2, data_inicio_t3, data_fim_t3, permitir_sempre_t1, permitir_sempre_t2, permitir_sempre_t3, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `nome` | `CharField` | Não |  |
| `nif_cnpj` | `CharField` | Não |  |
| `endereco` | `TextField` | Sim |  |
| `telefone` | `CharField` | Sim |  |
| `email` | `CharField` | Não |  |
| `logo_url` | `CharField` | Sim |  |
| `status` | `CharField` | Não |  |
| `ano_letivo_ativo` | `CharField` | Não |  |
| `trimestre_ativo` | `CharField` | Não |  |
| `plano` | `ForeignKey` | Sim |  -> `Plano` |
| `data_adesao` | `DateTimeField` | Não |  |
| `provincia` | `CharField` | Não |  |
| `distrito` | `CharField` | Não |  |
| `tipo_escola` | `CharField` | Não |  |
| `director_nome` | `CharField` | Não |  |
| `director_carreira` | `CharField` | Não |  |
| `dap_nome` | `CharField` | Não |  |
| `chefe_secretaria_nome` | `CharField` | Não |  |
| `usar_emblema_nacional` | `BooleanField` | Não |  |
| `codigo_escola` | `CharField` | Sim |  |
| `logo_base64` | `TextField` | Sim |  |
| `galeria_logos` | `JSONField` | Não |  |
| `tema_codigo` | `CharField` | Não |  |
| `tema_cor_primaria` | `CharField` | Não |  |
| `tema_cor_hover` | `CharField` | Não |  |
| `tema_cor_sidebar` | `CharField` | Não |  |
| `tema_cor_sidebar_ativa` | `CharField` | Não |  |
| `imagem_fundo_url` | `TextField` | Sim |  |
| `imagem_fundo_base64` | `TextField` | Sim |  |
| `imagem_fundo_modo` | `CharField` | Não |  |
| `imagem_fundo_opacidade` | `IntegerField` | Não |  |
| `galeria_fundos` | `JSONField` | Não |  |
| `bloqueada_manualmente` | `BooleanField` | Não |  |
| `permitir_visualizacao_notas` | `BooleanField` | Não |  |
| `modo_publicacao_notas` | `CharField` | Não |  |
| `publicacao_notas_trimestre` | `CharField` | Não |  |
| `data_inicio_pub_t1` | `DateField` | Sim |  |
| `data_fim_pub_t1` | `DateField` | Sim |  |
| `data_inicio_pub_t2` | `DateField` | Sim |  |
| `data_fim_pub_t2` | `DateField` | Sim |  |
| `data_inicio_pub_todos` | `DateField` | Sim |  |
| `data_fim_pub_todos` | `DateField` | Sim |  |
| `inscricoes_abertas` | `BooleanField` | Não |  |
| `inscricoes_inicio` | `DateTimeField` | Sim |  |
| `inscricoes_fim` | `DateTimeField` | Sim |  |
| `modo_calendarizacao` | `CharField` | Não |  |
| `tipo_duracao_automatica` | `CharField` | Não |  |
| `valor_duracao_automatica` | `IntegerField` | Não |  |
| `data_base_automatica` | `DateField` | Sim |  |
| `data_inicio_t1` | `DateField` | Sim |  |
| `data_fim_t1` | `DateField` | Sim |  |
| `data_inicio_t2` | `DateField` | Sim |  |
| `data_fim_t2` | `DateField` | Sim |  |
| `data_inicio_t3` | `DateField` | Sim |  |
| `data_fim_t3` | `DateField` | Sim |  |
| `permitir_sempre_t1` | `BooleanField` | Não |  |
| `permitir_sempre_t2` | `BooleanField` | Não |  |
| `permitir_sempre_t3` | `BooleanField` | Não |  |
| `created_at` | `DateTimeField` | Não |  |
| `updated_at` | `DateTimeField` | Não |  |


### Modelo: `AssinaturaEscola`

AssinaturaEscola(id, escola, plano, data_inicio, data_fim, valor, status, metodo_pagamento, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
| `plano` | `ForeignKey` | Não |  -> `Plano` |
| `data_inicio` | `DateTimeField` | Não |  |
| `data_fim` | `DateTimeField` | Não |  |
| `valor` | `DecimalField` | Não |  |
| `status` | `CharField` | Não |  |
| `metodo_pagamento` | `CharField` | Não |  |
| `created_at` | `DateTimeField` | Não |  |
| `updated_at` | `DateTimeField` | Não |  |


### Modelo: `AnoLectivo`

AnoLectivo(id, escola, ano, descricao, ativo, data_inicio, data_fim, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
| `ano` | `CharField` | Não |  |
| `descricao` | `CharField` | Não |  |
| `ativo` | `BooleanField` | Não |  |
| `data_inicio` | `DateField` | Sim |  |
| `data_fim` | `DateField` | Sim |  |
| `created_at` | `DateTimeField` | Não |  |
| `updated_at` | `DateTimeField` | Não |  |


### Modelo: `SaasPlano`

SaasPlano(id, nome, descricao, preco_mensal, limite_alunos, limite_professores, limites, activo, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `nome` | `CharField` | Não |  |
| `descricao` | `TextField` | Sim |  |
| `preco_mensal` | `DecimalField` | Não |  |
| `limite_alunos` | `IntegerField` | Não |  |
| `limite_professores` | `IntegerField` | Não |  |
| `limites` | `JSONField` | Não |  |
| `activo` | `BooleanField` | Não |  |
| `created_at` | `DateTimeField` | Não |  |
| `updated_at` | `DateTimeField` | Não |  |


### Modelo: `SaasAssinatura`

SaasAssinatura(id, instituicao, plano, periodicidade, modo_data_limite, dia_limite, dias_tolerancia, dias_ate_suspensao, data_bloqueio_manual, multa_tipo, multa_valor, estado, data_inicio, proxima_fatura_em, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `instituicao` | `ForeignKey` | Não |  -> `Escola` |
| `plano` | `ForeignKey` | Não |  -> `SaasPlano` |
| `periodicidade` | `CharField` | Não |  |
| `modo_data_limite` | `CharField` | Não |  |
| `dia_limite` | `IntegerField` | Sim |  |
| `dias_tolerancia` | `IntegerField` | Não |  |
| `dias_ate_suspensao` | `IntegerField` | Não |  |
| `data_bloqueio_manual` | `DateField` | Sim |  |
| `multa_tipo` | `CharField` | Não |  |
| `multa_valor` | `DecimalField` | Não |  |
| `estado` | `CharField` | Não |  |
| `data_inicio` | `DateTimeField` | Não |  |
| `proxima_fatura_em` | `DateField` | Não |  |
| `created_at` | `DateTimeField` | Não |  |
| `updated_at` | `DateTimeField` | Não |  |


### Modelo: `SaasFatura`

SaasFatura(id, assinatura, instituicao, numero_fatura, periodo_inicio, periodo_fim, valor, multa_aplicada, valor_pago, data_abertura, data_limite, data_limite_manual, estado, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `assinatura` | `ForeignKey` | Não |  -> `SaasAssinatura` |
| `instituicao` | `ForeignKey` | Não |  -> `Escola` |
| `numero_fatura` | `CharField` | Não |  |
| `periodo_inicio` | `DateField` | Não |  |
| `periodo_fim` | `DateField` | Não |  |
| `valor` | `DecimalField` | Não |  |
| `multa_aplicada` | `DecimalField` | Não |  |
| `valor_pago` | `DecimalField` | Não |  |
| `data_abertura` | `DateField` | Não |  |
| `data_limite` | `DateField` | Não |  |
| `data_limite_manual` | `DateField` | Sim |  |
| `estado` | `CharField` | Não |  |
| `created_at` | `DateTimeField` | Não |  |
| `updated_at` | `DateTimeField` | Não |  |


### Modelo: `SaasPagamento`

SaasPagamento(id, fatura, instituicao, metodo, referencia, valor, comprovativo_path, comprovativo_url, estado, confirmado_por, confirmado_em, motivo_rejeicao, criado_em, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `fatura` | `ForeignKey` | Não |  -> `SaasFatura` |
| `instituicao` | `ForeignKey` | Não |  -> `Escola` |
| `metodo` | `CharField` | Não |  |
| `referencia` | `CharField` | Não |  |
| `valor` | `DecimalField` | Não |  |
| `comprovativo_path` | `TextField` | Sim |  |
| `comprovativo_url` | `TextField` | Sim |  |
| `estado` | `CharField` | Não |  |
| `confirmado_por` | `CharField` | Sim |  |
| `confirmado_em` | `DateTimeField` | Sim |  |
| `motivo_rejeicao` | `TextField` | Sim |  |
| `criado_em` | `DateTimeField` | Não |  |
| `updated_at` | `DateTimeField` | Não |  |


### Modelo: `SaasLogAssinatura`

SaasLogAssinatura(id, instituicao, assinatura, fatura, accao, estado_anterior, estado_novo, valor_anterior, valor_novo, feito_por, motivo, criado_em)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `instituicao` | `ForeignKey` | Não |  -> `Escola` |
| `assinatura` | `ForeignKey` | Sim |  -> `SaasAssinatura` |
| `fatura` | `ForeignKey` | Sim |  -> `SaasFatura` |
| `accao` | `CharField` | Não |  |
| `estado_anterior` | `CharField` | Sim |  |
| `estado_novo` | `CharField` | Sim |  |
| `valor_anterior` | `DecimalField` | Sim |  |
| `valor_novo` | `DecimalField` | Sim |  |
| `feito_por` | `CharField` | Não |  |
| `motivo` | `TextField` | Sim |  |
| `criado_em` | `DateTimeField` | Não |  |


### Modelo: `SaasCoordenadasPagamento`

SaasCoordenadasPagamento(id, mpesa_numero, mpesa_titular, emola_numero, emola_titular, bim_conta, bim_nib, bim_titular, bci_conta, bci_nib, bci_titular, nuit_entidade, instrucoes_adicionais, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `mpesa_numero` | `CharField` | Não |  |
| `mpesa_titular` | `CharField` | Não |  |
| `emola_numero` | `CharField` | Não |  |
| `emola_titular` | `CharField` | Não |  |
| `bim_conta` | `CharField` | Não |  |
| `bim_nib` | `CharField` | Não |  |
| `bim_titular` | `CharField` | Não |  |
| `bci_conta` | `CharField` | Não |  |
| `bci_nib` | `CharField` | Não |  |
| `bci_titular` | `CharField` | Não |  |
| `nuit_entidade` | `CharField` | Não |  |
| `instrucoes_adicionais` | `TextField` | Não |  |
| `updated_at` | `DateTimeField` | Não |  |


## Aplicação: `apps.alunos`

### Modelo: `Aluno`

Aluno(id, escola, turma, classe, area, ano_ingresso, matricula, nome, apelido, data_nascimento, genero, tipo_documento, numero_documento, nuit, nacionalidade, provincia, distrito, pai, mae, nome_responsavel, contato_responsavel, email_responsavel, status, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
| `turma` | `ForeignKey` | Sim |  -> `Turma` |
| `classe` | `CharField` | Sim |  |
| `area` | `CharField` | Sim |  |
| `ano_ingresso` | `CharField` | Sim |  |
| `matricula` | `CharField` | Não |  |
| `nome` | `CharField` | Não |  |
| `apelido` | `CharField` | Sim |  |
| `data_nascimento` | `DateField` | Não |  |
| `genero` | `CharField` | Não |  |
| `tipo_documento` | `CharField` | Não |  |
| `numero_documento` | `CharField` | Sim |  |
| `nuit` | `CharField` | Sim |  |
| `nacionalidade` | `CharField` | Não |  |
| `provincia` | `CharField` | Não |  |
| `distrito` | `CharField` | Não |  |
| `pai` | `CharField` | Sim |  |
| `mae` | `CharField` | Sim |  |
| `nome_responsavel` | `CharField` | Sim |  |
| `contato_responsavel` | `CharField` | Sim |  |
| `email_responsavel` | `CharField` | Sim |  |
| `status` | `CharField` | Não |  |
| `created_at` | `DateTimeField` | Não |  |
| `updated_at` | `DateTimeField` | Não |  |


## Aplicação: `apps.professores`

### Modelo: `Professor`

Professor(id, escola, codigo, nome, apelido, genero, email, telefone, tipo_documento, numero_documento, nuit, nacionalidade, provincia, distrito, carreira, especialidade, carga_horaria_semanal, carga_maxima_por_classe, ativo, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
| `codigo` | `CharField` | Sim |  |
| `nome` | `CharField` | Não |  |
| `apelido` | `CharField` | Sim |  |
| `genero` | `CharField` | Não |  |
| `email` | `CharField` | Não |  |
| `telefone` | `CharField` | Sim |  |
| `tipo_documento` | `CharField` | Não |  |
| `numero_documento` | `CharField` | Sim |  |
| `nuit` | `CharField` | Sim |  |
| `nacionalidade` | `CharField` | Não |  |
| `provincia` | `CharField` | Não |  |
| `distrito` | `CharField` | Não |  |
| `carreira` | `CharField` | Não |  |
| `especialidade` | `CharField` | Não |  |
| `carga_horaria_semanal` | `IntegerField` | Não |  |
| `carga_maxima_por_classe` | `JSONField` | Sim |  |
| `ativo` | `BooleanField` | Não |  |
| `created_at` | `DateTimeField` | Não |  |
| `updated_at` | `DateTimeField` | Não |  |


### Modelo: `AlocacaoDocente`

AlocacaoDocente(id, escola, professor, disciplina, turma, created_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
| `professor` | `ForeignKey` | Não |  -> `Professor` |
| `disciplina` | `ForeignKey` | Não |  -> `Disciplina` |
| `turma` | `ForeignKey` | Não |  -> `Turma` |
| `created_at` | `DateTimeField` | Não |  |


## Aplicação: `apps.turmas`

### Modelo: `Turma`

Turma(id, escola, nome, grau_ano, turno, sala, capacidade_maxima, ano_letivo, area, director_turma, dt_status_homologacao, dt_nomeado_por, dt_data_nomeacao, dt_homologado_por, dt_data_homologacao, codigo_director_turma, director_classe, dc_status_homologacao, dc_nomeado_por, dc_data_nomeacao, dc_homologado_por, dc_data_homologacao, codigo_director_classe, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
| `nome` | `CharField` | Não |  |
| `grau_ano` | `CharField` | Não |  |
| `turno` | `CharField` | Não |  |
| `sala` | `CharField` | Sim |  |
| `capacidade_maxima` | `PositiveIntegerField` | Não |  |
| `ano_letivo` | `CharField` | Não |  |
| `area` | `CharField` | Não |  |
| `director_turma` | `ForeignKey` | Sim |  -> `Professor` |
| `dt_status_homologacao` | `CharField` | Não |  |
| `dt_nomeado_por` | `CharField` | Sim |  |
| `dt_data_nomeacao` | `DateTimeField` | Sim |  |
| `dt_homologado_por` | `CharField` | Sim |  |
| `dt_data_homologacao` | `DateTimeField` | Sim |  |
| `codigo_director_turma` | `CharField` | Sim |  |
| `director_classe` | `ForeignKey` | Sim |  -> `Professor` |
| `dc_status_homologacao` | `CharField` | Não |  |
| `dc_nomeado_por` | `CharField` | Sim |  |
| `dc_data_nomeacao` | `DateTimeField` | Sim |  |
| `dc_homologado_por` | `CharField` | Sim |  |
| `dc_data_homologacao` | `DateTimeField` | Sim |  |
| `codigo_director_classe` | `CharField` | Sim |  |
| `created_at` | `DateTimeField` | Não |  |
| `updated_at` | `DateTimeField` | Não |  |


## Aplicação: `apps.disciplinas`

### Modelo: `Disciplina`

Disciplina(id, escola, nome, codigo, classe, area, carga_horaria, ano_letivo, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
| `nome` | `CharField` | Não |  |
| `codigo` | `CharField` | Não |  |
| `classe` | `CharField` | Não |  |
| `area` | `CharField` | Não |  |
| `carga_horaria` | `IntegerField` | Não |  |
| `ano_letivo` | `CharField` | Não |  |
| `created_at` | `DateTimeField` | Não |  |
| `updated_at` | `DateTimeField` | Não |  |


## Aplicação: `apps.notas`

### Modelo: `Nota`

Nota(id, escola, aluno, disciplina, turma, periodo, teste1, teste2, teste3, teste4, trabalho, avaliacao_trimestral, media_final, faltas, anotacao, comportamento, resultado, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
| `aluno` | `ForeignKey` | Não |  -> `Aluno` |
| `disciplina` | `ForeignKey` | Não |  -> `Disciplina` |
| `turma` | `ForeignKey` | Não |  -> `Turma` |
| `periodo` | `CharField` | Não |  |
| `teste1` | `FloatField` | Sim |  |
| `teste2` | `FloatField` | Sim |  |
| `teste3` | `FloatField` | Sim |  |
| `teste4` | `FloatField` | Sim |  |
| `trabalho` | `FloatField` | Sim |  |
| `avaliacao_trimestral` | `FloatField` | Sim |  |
| `media_final` | `FloatField` | Não |  |
| `faltas` | `IntegerField` | Não |  |
| `anotacao` | `CharField` | Sim |  |
| `comportamento` | `CharField` | Sim |  |
| `resultado` | `CharField` | Não |  |
| `created_at` | `DateTimeField` | Não |  |
| `updated_at` | `DateTimeField` | Não |  |


### Modelo: `PermissaoEdicaoNotas`

PermissaoEdicaoNotas(id, escola, professor, turma, disciplina, periodo, autorizado_por, motivo, duracao_horas, data_expiracao, ativa, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
| `professor` | `ForeignKey` | Sim |  -> `Professor` |
| `turma` | `ForeignKey` | Não |  -> `Turma` |
| `disciplina` | `ForeignKey` | Sim |  -> `Disciplina` |
| `periodo` | `CharField` | Não |  |
| `autorizado_por` | `CharField` | Não |  |
| `motivo` | `TextField` | Sim |  |
| `duracao_horas` | `IntegerField` | Não |  |
| `data_expiracao` | `DateTimeField` | Sim |  |
| `ativa` | `BooleanField` | Não |  |
| `created_at` | `DateTimeField` | Não |  |
| `updated_at` | `DateTimeField` | Não |  |


## Aplicação: `apps.pautas`

### Modelo: `Pauta`

Pauta(id, escola, turma, ano_letivo, periodo, status, data_fechamento, homologado_por, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
| `turma` | `ForeignKey` | Não |  -> `Turma` |
| `ano_letivo` | `CharField` | Não |  |
| `periodo` | `CharField` | Não |  |
| `status` | `CharField` | Não |  |
| `data_fechamento` | `DateTimeField` | Sim |  |
| `homologado_por` | `CharField` | Sim |  |
| `created_at` | `DateTimeField` | Não |  |
| `updated_at` | `DateTimeField` | Não |  |


## Aplicação: `apps.material_escolar`

### Modelo: `MaterialEscolar`

MaterialEscolar(id, escola, disciplina, classe, titulo, descricao, nome_arquivo, extensao, tamanho_bytes, conteudo_base64, tipo_mime, arquivo_url, tipo, publicado_por, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
| `disciplina` | `ForeignKey` | Sim |  -> `Disciplina` |
| `classe` | `CharField` | Não |  |
| `titulo` | `CharField` | Não |  |
| `descricao` | `TextField` | Sim |  |
| `nome_arquivo` | `CharField` | Não |  |
| `extensao` | `CharField` | Não |  |
| `tamanho_bytes` | `BigIntegerField` | Não |  |
| `conteudo_base64` | `TextField` | Sim |  |
| `tipo_mime` | `CharField` | Não |  |
| `arquivo_url` | `CharField` | Sim |  |
| `tipo` | `CharField` | Não |  |
| `publicado_por` | `CharField` | Sim |  |
| `created_at` | `DateTimeField` | Não |  |
| `updated_at` | `DateTimeField` | Não |  |


## Aplicação: `apps.documentos`

### Modelo: `LogImpressao`

LogImpressao(id, escola, usuario, tipo_documento, descricao, conteudo_json, data_emissao, created_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
| `usuario` | `ForeignKey` | Sim |  -> `Usuario` |
| `tipo_documento` | `CharField` | Não |  |
| `descricao` | `CharField` | Não |  |
| `conteudo_json` | `TextField` | Sim |  |
| `data_emissao` | `DateTimeField` | Não |  |
| `created_at` | `DateTimeField` | Não |  |


### Modelo: `DocumentoSalvo`

DocumentoSalvo(id, escola, usuario, aluno, turma, tipo_documento, titulo, ano_letivo, dados_json, hash_md5, criado_em)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
| `usuario` | `ForeignKey` | Sim |  -> `Usuario` |
| `aluno` | `ForeignKey` | Sim |  -> `Aluno` |
| `turma` | `ForeignKey` | Sim |  -> `Turma` |
| `tipo_documento` | `CharField` | Não |  |
| `titulo` | `CharField` | Não |  |
| `ano_letivo` | `CharField` | Não |  |
| `dados_json` | `TextField` | Não |  |
| `hash_md5` | `CharField` | Sim |  |
| `criado_em` | `DateTimeField` | Não |  |


## Aplicação: `apps.pagamentos`

### Modelo: `PlanoPagamentoEscola`

Plano de Pagamentos / Tabela de Propinas e Emolumentos Própria da Instituição.
    Isolamento total:
    - O plano do Super Admin aplica-se unicamente às instituições (B2B SaaS).
    - Cada instituição cria e gere os seus próprios planos para aplicar aos seus alunos.
    - O que uma instituição faz no seu sistema não compromete nem reflecte noutra.

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
| `nome` | `CharField` | Não |  |
| `descricao` | `TextField` | Não |  |
| `valor` | `DecimalField` | Não |  |
| `periodicidade` | `CharField` | Não |  |
| `dia_vencimento_padrao` | `IntegerField` | Não |  |
| `multa_atraso_percentual` | `DecimalField` | Não |  |
| `multa_atraso_fixo` | `DecimalField` | Não |  |
| `ativo` | `BooleanField` | Não |  |
| `created_at` | `DateTimeField` | Não |  |
| `updated_at` | `DateTimeField` | Não |  |


### Modelo: `Pagamento`

Pagamento(id, escola, aluno, plano_pagamento, descricao, mes_referencia, valor, valor_pago, status, data_vencimento, data_pagamento, metodo_pagamento, recibo_numero, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
| `aluno` | `ForeignKey` | Não |  -> `Aluno` |
| `plano_pagamento` | `ForeignKey` | Sim |  -> `PlanoPagamentoEscola` |
| `descricao` | `CharField` | Não |  |
| `mes_referencia` | `CharField` | Não |  |
| `valor` | `DecimalField` | Não |  |
| `valor_pago` | `DecimalField` | Não |  |
| `status` | `CharField` | Não |  |
| `data_vencimento` | `DateTimeField` | Não |  |
| `data_pagamento` | `DateTimeField` | Sim |  |
| `metodo_pagamento` | `CharField` | Sim |  |
| `recibo_numero` | `CharField` | Sim |  |
| `created_at` | `DateTimeField` | Não |  |
| `updated_at` | `DateTimeField` | Não |  |


## Aplicação: `apps.certificados`

### Modelo: `Certificado`

Certificado(id, escola, aluno, tipo, codigo_autenticidade, qrcode_data, emitido_em, emitido_por, created_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
| `aluno` | `ForeignKey` | Não |  -> `Aluno` |
| `tipo` | `CharField` | Não |  |
| `codigo_autenticidade` | `CharField` | Não |  |
| `qrcode_data` | `TextField` | Não |  |
| `emitido_em` | `DateTimeField` | Não |  |
| `emitido_por` | `CharField` | Sim |  |
| `created_at` | `DateTimeField` | Não |  |


## Aplicação: `apps.ferramentas`

### Modelo: `MensagemSMS`

MensagemSMS(id, escola, destinatario, nome_destinatario, operadora, mensagem, tipo, caracteres, segmentos_sms, status, mensagem_id_operadora, created_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Sim |  -> `Escola` |
| `destinatario` | `CharField` | Não |  |
| `nome_destinatario` | `CharField` | Não |  |
| `operadora` | `CharField` | Não |  |
| `mensagem` | `TextField` | Não |  |
| `tipo` | `CharField` | Não |  |
| `caracteres` | `IntegerField` | Não |  |
| `segmentos_sms` | `IntegerField` | Não |  |
| `status` | `CharField` | Não |  |
| `mensagem_id_operadora` | `CharField` | Não |  |
| `created_at` | `DateTimeField` | Não |  |


### Modelo: `TransacaoGatewayMovel`

TransacaoGatewayMovel(id, escola, pagamento, aluno, metodo, telefone, valor, referencia_transacao, recibo_emitido, status, mensagem_retorno, created_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Sim |  -> `Escola` |
| `pagamento` | `ForeignKey` | Sim |  -> `Pagamento` |
| `aluno` | `ForeignKey` | Sim |  -> `Aluno` |
| `metodo` | `CharField` | Não |  |
| `telefone` | `CharField` | Não |  |
| `valor` | `DecimalField` | Não |  |
| `referencia_transacao` | `CharField` | Não |  |
| `recibo_emitido` | `CharField` | Não |  |
| `status` | `CharField` | Não |  |
| `mensagem_retorno` | `TextField` | Não |  |
| `created_at` | `DateTimeField` | Não |  |

