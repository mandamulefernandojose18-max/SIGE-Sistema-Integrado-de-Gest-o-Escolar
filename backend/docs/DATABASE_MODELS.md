# Catálogo de Modelos de Dados — SIGE (Django ORM)

> Gerado automaticamente via introspecção do Django ORM.

---

## Aplicação: `apps.accounts`

### Modelo: `Usuario`

Usuario(password, last_login, is_superuser, first_name, last_name, is_staff, is_active, date_joined, id, email, nome, role, escola, ativo, telefone, avatar_url, aluno_id, professor_id, username)

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

Escola(id, nome, nif_cnpj, endereco, telefone, email, logo_url, status, ano_letivo_ativo, trimestre_ativo, plano, data_adesao, provincia, distrito, director_nome, director_carreira, dap_nome, chefe_secretaria_nome, usar_emblema_nacional, codigo_escola, logo_base64, bloqueada_manualmente, permitir_visualizacao_notas, inscricoes_abertas, inscricoes_inicio, inscricoes_fim, created_at, updated_at)

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
| `director_nome` | `CharField` | Não |  |
| `director_carreira` | `CharField` | Não |  |
| `dap_nome` | `CharField` | Não |  |
| `chefe_secretaria_nome` | `CharField` | Não |  |
| `usar_emblema_nacional` | `BooleanField` | Não |  |
| `codigo_escola` | `CharField` | Sim |  |
| `logo_base64` | `TextField` | Sim |  |
| `bloqueada_manualmente` | `BooleanField` | Não |  |
| `permitir_visualizacao_notas` | `BooleanField` | Não |  |
| `inscricoes_abertas` | `BooleanField` | Não |  |
| `inscricoes_inicio` | `DateTimeField` | Sim |  |
| `inscricoes_fim` | `DateTimeField` | Sim |  |
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


## Aplicação: `apps.alunos`

### Modelo: `Aluno`

Aluno(id, escola, turma, matricula, nome, apelido, data_nascimento, genero, tipo_documento, numero_documento, nuit, nacionalidade, provincia, distrito, pai, mae, nome_responsavel, contato_responsavel, email_responsavel, status, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
| `turma` | `ForeignKey` | Sim |  -> `Turma` |
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

Professor(id, escola, nome, apelido, genero, email, telefone, tipo_documento, numero_documento, nuit, nacionalidade, provincia, distrito, carreira, especialidade, carga_horaria_semanal, ativo, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
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

Turma(id, escola, nome, grau_ano, turno, sala, ano_letivo, area, director_turma, director_classe, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
| `nome` | `CharField` | Não |  |
| `grau_ano` | `CharField` | Não |  |
| `turno` | `CharField` | Não |  |
| `sala` | `CharField` | Sim |  |
| `ano_letivo` | `CharField` | Não |  |
| `area` | `CharField` | Não |  |
| `director_turma` | `ForeignKey` | Sim |  -> `Professor` |
| `director_classe` | `ForeignKey` | Sim |  -> `Professor` |
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
| `comportamento` | `CharField` | Não |  |
| `resultado` | `CharField` | Não |  |
| `created_at` | `DateTimeField` | Não |  |
| `updated_at` | `DateTimeField` | Não |  |


### Modelo: `PermissaoEdicaoNotas`

PermissaoEdicaoNotas(id, escola, professor, turma, disciplina, periodo, autorizado_por, motivo, ativa, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
| `professor` | `ForeignKey` | Não |  -> `Professor` |
| `turma` | `ForeignKey` | Não |  -> `Turma` |
| `disciplina` | `ForeignKey` | Não |  -> `Disciplina` |
| `periodo` | `CharField` | Não |  |
| `autorizado_por` | `CharField` | Não |  |
| `motivo` | `TextField` | Sim |  |
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

### Modelo: `Pagamento`

Pagamento(id, escola, aluno, descricao, mes_referencia, valor, valor_pago, status, data_vencimento, data_pagamento, metodo_pagamento, recibo_numero, created_at, updated_at)

| Campo | Tipo | Nulo / Opcional | Descrição / Relação |
| :--- | :--- | :---: | :--- |
| `id` | `UUIDField` | Não |  |
| `escola` | `ForeignKey` | Não |  -> `Escola` |
| `aluno` | `ForeignKey` | Não |  -> `Aluno` |
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

