# -*- coding: utf-8 -*-
import re

with open('docs/DOCUMENTACAO_COMPLETA_DO_SISTEMA.md', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update section 4.1 & add section 4.3
p1 = r'(## 4\. Autenticação Inteligente, Perfis de Acesso \(RBAC\) e Códigos Oficiais\s+### 4\.1 [^\n]+\n)([\s\S]*?)(### 4\.2 Motor de Login Inteligente)'

m = re.search(p1, text)
if m:
    print("Found section 4.1")
    new_section_4 = '''## 4. Autenticação Inteligente, Perfis de Acesso (RBAC), Tarefas e Matriz de Permissões

### 4.1 Os 10 Perfis Nativos + 2 Cargos Homologáveis
O SIGE implementa Controlo de Acesso Baseado em Papéis (`RBAC`) com 10 perfis nativos no modelo `Usuario` e 2 cargos pedagógicos atribuíveis a docentes:

| Perfil / Código Role | Designação Institucional | Formato do Código Oficial de Acesso | Escopo de Atuação Principal |
| :--- | :--- | :--- | :--- |
| `SUPERADMIN` | Administrador Master SaaS | E-mail / Username Master | Governação global de todas as escolas, planos, contratos, métricas MRR/ARR/Churn e inspeção multi-tenant. |
| `ADMIN_ESCOLA` | Administrador da Instituição | E-mail Institucional | Gestão completa da escola, configurações gerais, utilizadores e todos os módulos locais. |
| `DIRECTOR_ESCOLA` | Director da Escola | `GD{CodigoEscola}` *(ex: `GD0808S0001`)* | Órgão executivo máximo da escola; homologa cargos (`DT`/`DC`), aprova despesas financeiras, homologa pautas e relatórios, visualiza auditoria geral e supervisiona toda a instituição. |
| `DAP` | Director Adjunto Pedagógico | `DP{CodigoEscola}` *(ex: `DP0808S0001`)* | Gestão pedagógica integral: turmas, horários semanais, matriz curricular, cadernetas, validação de notas e planos/sumários, pautas, estatísticas, desbloqueio de notas e visibilidade aos alunos. |
| `CHEFE_SECRETARIA` | Chefe da Secretaria Escolar | `SECR{CodigoEscola}` *(ex: `SECR0808S0001`)* | Coordenação de matrículas, transferências e anulações, arquivo de alunos, emissão de certificados, declarações, boletins, recibos e cobrança de propinas. |
| `SECRETARIA` | Assistente / Oficial de Secretaria | `SEC{CodigoEscola}.{Seq:03d}` | Execução operacional de matrículas, atualizações cadastrais, registo de transferências e emissão de declarações/certificados sob supervisão. |
| `FINANCEIRO` | Gestor Financeiro / Tesouraria | E-mail / Username Financeiro | Emissão de mensalidades/propinas em lote, liquidação de pagamentos multicanal, registo de despesas/receitas, folha de salário e património (**Nota:** Não aprova despesas por separação de funções). |
| `PROFESSOR` | Docente | `PR{CodigoEscola}.{Seq:03d}` *(ex: `PR0808S0001.001`)* | Lançamento de notas (`ACS`, `MAP`, `AT`) e faltas/presenças nas suas turmas, submissão de planos de aula e sumários, registo de ocorrências disciplinares e material de estudo. |
| `DT` *(Cargo Docente)* | Director de Turma Homologado | `DT{CodigoEscola}.{Classe}.{Turma}` *(ex: `DT0808S0001.10.01`)* | Atribuído a um Professor e **homologado pelo Director da Escola**: gere a sua turma específica, configura os parâmetros da Sessão do Conselho de Avaliação e emite a Pauta Geral e a Acta do Conselho da turma. |
| `DC` *(Cargo Docente)* | Director de Classe Homologado | `DC{CodigoEscola}.{Classe}` *(ex: `DC0808S0001.10`)* | Atribuído a um Professor e **homologado pelo Director da Escola**: coordena pedagogicamente todas as turmas de uma determinada classe. |
| `ALUNO` | Estudante Matriculado | `{CodigoEscola}.{Classe}.{Turma}.{Ano}.{Area}` | Portal Privado do Aluno: consulta perfil biográfico, boletim de notas (quando liberado pelo DAP), presenças, horários da turma, comunicados, estado de propinas/recibos e material didáctico. |
| `ENCARREGADO` | Encarregado de Educação | Contacto / Username do Encarregado | Acompanhamento do percurso do seu educando: notas validadas, assiduidade, ocorrências disciplinares e histórico de mensalidades. |

'''
    text = text[:m.start()] + new_section_4 + text[m.end(2):]

# 2. Add Matriz de Permissoes after Section 4.2
p2 = r'(### 4\.2 Motor de Login Inteligente[\s\S]*?contexto do cargo diretivo\.\n)'
m2 = re.search(p2, text)
if m2:
    print("Found section 4.2")
    matriz_section = '''
### 4.3 Matriz de Tarefas, Permissões e Regras de Separação de Funções
Em conformidade com as diretrizes oficiais de governação institucional e segurança de dados escolares:

#### 1. Matriz de Permissões por Perfil
| Domínio / Módulo | Director Escola | DAP | Professor | Secretaria | Administração / Finanças | Aluno | Encarregado |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Configurações Gerais da Escola** | ✅ Total | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Ano Lectivo e Calendário Escolar** | ✅ Criar/Editar | ✅ Criar/Editar | 👁️ Ver | 👁️ Ver | 👁️ Ver | 👁️ Ver | 👁️ Ver |
| **Turmas, Classes e Horários** | ✅ Homologar | ✅ Criar/Editar | 👁️ Ver seus | 👁️ Ver | 👁️ Ver | 👁️ Ver sua | 👁️ Ver |
| **Matrículas e Cadastro de Alunos** | 👁️ Ver | 👁️ Ver | ❌ | ✅ Criar/Editar | ❌ | 👁️ Ver seu | 👁️ Ver educando |
| **Transferências e Anulações** | ✅ Homologar | ✅ Validar | ❌ | ✅ Criar/Instruir | ❌ | ❌ | ❌ |
| **Lançamento de Notas (ACS/MAP/AT)** | 👁️ Ver todas | ✅ Validar/Desbloquear | ✅ Lançar suas | ❌ | ❌ | 👁️ Ver suas | 👁️ Ver educando |
| **Pautas e Actas de Avaliação** | ✅ Homologar | ✅ Validar/Gerar | 👁️ Ver / Emitir (DT) | ✅ Imprimir | ❌ | ❌ | ❌ |
| **Presenças e Faltas de Alunos** | 👁️ Ver todas | 👁️ Ver todas | ✅ Marcar suas | ❌ | ❌ | 👁️ Ver suas | 👁️ Ver educando |
| **Planos de Aula e Sumários** | 👁️ Ver todos | ✅ Rever/Validar | ✅ Submeter seus | ❌ | ❌ | ❌ | ❌ |
| **Ocorrências Disciplinares** | ✅ Homologar/Decidir | ✅ Gerir/Instruir | ✅ Registar | 👁️ Arquivar | ❌ | 👁️ Ver suas | 👁️ Notificado |
| **Cobrança de Propinas e Recibos** | 👁️ Ver relatórios | ❌ | ❌ | ✅ Receber/Liquidar | ✅ Total | 👁️ Ver e Pagar | 👁️ Ver e Pagar |
| **Despesas e Pagamentos Gerais** | ✅ Aprovar | ❌ | ❌ | ❌ | ✅ Registar | ❌ | ❌ |
| **Folha de Salário e Património** | ✅ Aprovar | ❌ | ❌ | ❌ | ✅ Gerir/Calcular | ❌ | ❌ |
| **Comunicados e Circulares** | ✅ Publicar/Aprovar | ✅ Publicar pedagógicos | 👁️ Ver | ✅ Distribuir | 👁️ Ver | 👁️ Ver | 👁️ Ver |
| **Trilha de Auditoria do Sistema** | ✅ Ver logs totais | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

#### 2. Regras Mandatórias de Separação de Funções (Guardrails)
1. **Separação de Funções Financeiras:** Quem regista a despesa na Administração e Finanças (`FINANCEIRO`) **NÃO pode aprovar** a despesa. A aprovação é exclusiva da Direcção da Escola (`DIRECTOR_ESCOLA`).
2. **Separação de Funções Pedagógicas:** O Professor lança as notas das suas disciplinas; a validação oficial, encerramento de cadernetas e homologação de pautas competem ao Director Adjunto Pedagógico (`DAP`) e ao Director da Escola (`DIRECTOR_ESCOLA`).
3. **Imutabilidade e Trilha de Auditoria:** Qualquer inserção, alteração ou anulação em Notas, Propinas/Recibos, Dados de Alunos, Despesas e Transferências gera compulsoriamente um registo em `LogAuditoria` com identificador do operador, IP, data/hora e dados antes/depois (`delta`).
4. **Preservação Integral do Painel do Aluno:** O perfil `ALUNO` possui painel próprio dedicado (`painel-aluno`) contendo O Meu Perfil, Minhas Notas, Minhas Propinas, Material Escolar, Presenças e Horários, garantindo visualização intuitiva e sem sobreposição de funções administrativas.
'''
    text = text[:m2.end()] + matriz_section + text[m2.end():]

# 3. Add the newly created modules to Section 6
new_modules = '''
### Módulo 21: Calendário Escolar e Eventos Lectivos (`#view-calendario`)
- **Organização do Ano Lectivo:** Planeamento cronológico de trimestres, períodos de exames, conselhos de avaliação, feriados e actividades extra-curriculares.
- **Permissões Diferenciadas:** Direcção e DAP configuram os eventos lectivos; professores, secretaria, alunos e encarregados acedem para consulta dos prazos oficiais.

### Módulo 22: Presenças e Assiduidade de Alunos (`#view-presencas`)
- **Registo Aula a Aula:** Professores registam presenças, faltas justificadas e faltas não justificadas por disciplina e turma.
- **Monitoria e Alertas:** Estatísticas consolidadas de assiduidade acompanhadas pelo DAP e Direcção de Turma; consulta em tempo real pelo Aluno e Encarregado.

### Módulo 23: Horários Escolares Semanais (`#view-horarios`)
- **Grelha Semanal Compacta:** Alocação de disciplinas, professores, salas e tempos lectivos de 2ª a 6ª feira.
- **Visualização Filtrada:** Professores visualizam a sua agenda lectiva pessoal; cada aluno/turma visualiza o seu horário semanal oficial.

### Módulo 24: Planos de Aula e Sumários (`#view-sumarios`)
- **Gestão Pedagógica Docente:** Submissão de planos quinzenais/mensais e registo diário de sumários de aula leccionados por disciplina e turma.
- **Supervisão Pedagógica:** Revisão, validação e parecer pedagógico realizados exclusivamente pelo DAP.

### Módulo 25: Ocorrências e Acompanhamento Disciplinar (`#view-ocorrencias`)
- **Registo Disciplinar Transparente:** Docentes e secretaria registam ocorrências com gravidade (`LEVE`, `MEDIA`, `GRAVE`), descrição e medidas imediatas.
- **Parecer e Homologação:** Instrução e parecer pedagógico pelo DAP com homologação da decisão/medida disciplinar pelo Director da Escola.

### Módulo 26: Transferências e Anulações de Matrícula (`#view-transferencias`)
- **Fluxo Documental Rigoroso:** Secretaria instrui o processo (`TRANSFERENCIA_SAIDA`, `TRANSFERENCIA_ENTRADA`, `ANULACAO_MATRICULA`), com parecer de quitação e aproveitamento pelo DAP.
- **Homologação e Guia Oficial:** Homologação final pelo Director da Escola com emissão da respectiva Guia Oficial de Transferência.

### Módulo 27: Gestão Financeira com Separação de Funções — Despesas, Folha de Salário e Património (`#view-despesas`)
- **Registo de Despesas e Receitas:** Gestor financeiro introduz comprovativos, valores, categorias orçamentais e fornecedores.
- **Regra Inquebrável de Separação de Funções:** O botão e endpoint de aprovação são bloqueados para o perfil financeiro; aprovação exclusiva do Director da Escola.
- **Folha de Salário e Património:** Processamento salarial mensal e inventário de bens/equipamentos escolares com estado de conservação.

### Módulo 28: Comunicados e Circulares Escolares (`#view-comunicados`)
- **Comunicação Oficial Directa:** Publicação de circulares, avisos institucionais e notas informativas com público-alvo configurável (`TODOS`, `PROFESSORES`, `ALUNOS`, `ENCARREGADOS`, `SECRETARIA`).
- **Aprovação Institucional:** Publicação supervisionada pela Direcção da Escola e pelo DAP.

### Módulo 29: Trilha de Auditoria Transacional (`#view-auditoria`)
- **Auditoria Rigorosa e Imutável:** Registo automático de todas as operações sensíveis no modelo `LogAuditoria` (notas lançadas ou alteradas, pagamentos recebidos ou liquidados, transferências e alterações cadastrais).
- **Acesso Restrito:** Painel exclusivo da Direcção da Escola com filtros por data, utilizador, tipo de acção e comparação de valores (`Antes` vs `Depois`).
'''

p3 = r'(### Módulo 20: Ferramentas & Integrações — Prompt do Gateway[\s\S]*?descarregar`\.\n)'
m3 = re.search(p3, text)
if m3:
    print("Found module 20")
    text = text[:m3.end()] + new_modules + text[m3.end():]

with open('docs/DOCUMENTACAO_COMPLETA_DO_SISTEMA.md', 'w', encoding='utf-8') as f:
    f.write(text)

print("Documentation updated successfully!")
