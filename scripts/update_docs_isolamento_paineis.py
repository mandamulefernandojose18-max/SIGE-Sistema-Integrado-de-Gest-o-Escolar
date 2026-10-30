# -*- coding: utf-8 -*-
with open('docs/DOCUMENTACAO_COMPLETA_DO_SISTEMA.md', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''4. **Preservação Integral do Painel do Aluno:** O perfil `ALUNO` possui painel próprio dedicado (`painel-aluno`) contendo O Meu Perfil, Minhas Notas, Minhas Propinas, Material Escolar, Presenças e Horários, garantindo visualização intuitiva e sem sobreposição de funções administrativas.'''

replacement = '''4. **Preservação Integral do Painel do Aluno:** O perfil `ALUNO` possui painel próprio dedicado (`painel-aluno`) contendo O Meu Perfil, Minhas Notas, Minhas Propinas, Material Escolar, Presenças e Horários, garantindo visualização intuitiva e sem sobreposição de funções administrativas.

### 4.4 Isolamento Estrito dos Painéis Departamentais (Acesso "Só e Só ao Seu Painel")
Em conformidade com a directiva institucional, cada departamento possui acesso **estritamente confinado ao seu respectivo painel**, impedindo que qualquer perfil visualize, aceda ou execute módulos de outros domínios:

1. **Professores (`painel-professor` — Painel do Docente):**
   - **Acesso Exclusivo:** Caderneta do Professor (lançamento de notas das suas turmas), Registo de Presenças e Faltas, Planos de Aula e Sumários Diários, Registo de Ocorrências Disciplinares, Horário Semanal do Docente, Pautas e Actas da Turma (emissão se DT homologado), Consulta de Exames, Estatística de Rendimento da Turma, Material Didáctico e Comunicados Oficiais.
   - **Bloqueio Total:** Sem acesso a matrículas, arquivo de funcionários, parametrização escolar, cobranças/despesas ou auditoria.

2. **Secretaria (`painel-secretaria` — Painel da Secretaria Escolar):**
   - **Acesso Exclusivo:** Gestão de Matrículas e Processo do Aluno, Transferências e Anulações, Consulta de Presenças, Turmas e Lotação, Emissão de Pautas e Boletins, Certificados com QR Code e Declarações, Central de Impressão, Calendário Escolar, Horários das Turmas, Registo de Pessoal, Cobrança de Propinas/Recibos, Arquivo de Ocorrências e Comunicados.
   - **Bloqueio Total:** Sem acesso a lançamento pedagógico de notas, despesas/caixa, validação pedagógica ou configurações directivas.

3. **Aluno & Encarregado (`painel-aluno` — Portal do Aluno):**
   - **Acesso Exclusivo:** O Meu Perfil Biográfico e Matrícula, Minhas Notas e Boletim (com respeito ao bloqueio do DAP), Minhas Faltas e Presenças, Meu Horário Escolar, Minhas Propinas e Recibos (com liquidação móvel M-Pesa/e-Mola), Material Escolar da Classe e Comunicados.
   - **Bloqueio Total:** Sem acesso a qualquer módulo directivo, pedagógico, administrativo ou financeiro.

4. **Administração e Finanças (`painel-financeiro` — Painel Financeiro):**
   - **Acesso Exclusivo:** Visão Geral Financeira, Gestão de Propinas e Emissão em Lote, Registo de Receitas e Despesas de Caixa, Central de Impressão de Recibos, Gateway de Pagamentos, Consulta Financeira de Matrículas, Quitação de Transferências, Calendário Escolar e Comunicados.
   - **Bloqueio Total & Separação de Funções:** A aprovação de despesas é terminantemente bloqueada para Finanças (exclusiva da Direcção da Escola). Sem acesso a cadernetas, notas ou gestão de professores.

5. **Outros Perfis Habituais:**
   - **Direcção da Escola (`painel-direcao`):** Governação institucional executiva, homologações de turmas/DT/DC, aprovação de despesas, pautas gerais e trilha de auditoria (`auditoria`).
   - **Direcção Pedagógica / DAP (`painel-pedagogico`):** Supervisão pedagógica, classes/disciplinas, horários, desbloqueio de notas, validação de sumários e controle de visibilidade aos alunos.
   - **Superadmin SaaS Master (`painel-superadmin`):** Governação multi-tenant global do ecossistema SaaS.'''

text_norm = text.replace('\r\n', '\n')
target_norm = target.replace('\r\n', '\n')
replacement_norm = replacement.replace('\r\n', '\n')

if target_norm in text_norm:
    text_norm = text_norm.replace(target_norm, replacement_norm)
    with open('docs/DOCUMENTACAO_COMPLETA_DO_SISTEMA.md', 'w', encoding='utf-8') as f:
        f.write(text_norm)
    print("Documentação atualizada com sucesso com a seção 4.4!")
else:
    print("Alvo não encontrado em DOCUMENTACAO_COMPLETA_DO_SISTEMA.md")
