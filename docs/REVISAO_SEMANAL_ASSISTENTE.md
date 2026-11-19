# Revisão semanal do Assistente Virtual

Objectivo: usar as perguntas reais dos utilizadores para decidir, uma vez por semana, o que o assistente deve aprender a seguir.
Quem faz: Super Admin (todas as escolas) ou a Direcção (a sua escola). Dura 15 a 30 minutos.

## 1. Obter a lista
1. Menu **Relatório do Assistente** → período **Últimos 7 dias**.
2. Ver os números no topo:
   - **Sem resposta** acima de 10% → o assistente não percebe muitas perguntas (prioridade).
   - **Não úteis** acima de 5% → há respostas erradas ou pouco úteis.
   - **Fora do painel** é normal quando há curiosidade sobre outros painéis; só preocupa se for uma pergunta que **devia** ser do painel.
3. **Exportar CSV** (abre no Excel). A tabela vem ordenada por número de vezes e com a coluna **Decisão (preencher)**.

## 2. Decidir cada pergunta (de cima para baixo)
| Motivo na lista | Pergunte-se | Decisão típica |
|---|---|---|
| **Sem resposta** | É uma pergunta legítima do painel? | **A)** Já existe a capacidade → acrescentar palavras-chave. **B)** Não existe → nova capacidade (dados) ou novo guia. **C)** Fora do âmbito do sistema → ignorar (ex.: "receita de bolo"). |
| **Fora do painel** | O módulo pertence mesmo a outro painel? | **A)** Sim → está certo, nada a fazer. **B)** Não, devia estar no painel → ligar o módulo em `modulos.py` (e confirmar com o menu do frontend). |
| **Não útil** | A capacidade escolhida foi a errada, ou a resposta é fraca? | **A)** Capacidade errada → ajustar palavras-chave/pesos. **B)** Resposta fraca → melhorar o texto do guia ou do handler. |

Escreva a letra e uma nota na coluna **Decisão**. Perguntas com muitas repetições primeiro.

## 3. Como aplicar (para quem programa)
- Novas palavras-chave ou guia: `backend/apps/assistente/guias.py` (guias) e `capacidades.py` / `capacidades_extra.py` (dados). As chaves são normalizadas (sem acentos, sem artigos, plural→singular, verbos no infinitivo): escreva-as no infinitivo e no singular.
- Nova capacidade de dados: função `h_xxx(ctx)` só de leitura + entrada em `EXTRA` com `perfis` (quem), `destino` (módulo do painel) e `exemplos`. **O módulo tem de existir no painel do perfil** (`modulos.py`); caso contrário o assistente recusa por segurança.
- Acrescentar a pergunta real (sem nomes de pessoas) a `backend/tests/test_assistente_cobertura.py` com a capacidade esperada, e correr `pytest tests/test_assistente_*.py`.
- Actualizar `docs/DOCUMENTACAO_COMPLETA_DO_SISTEMA.md` e publicar com `.\scripts\sige-git-deploy.ps1`.

## 4. Privacidade e segurança
- O relatório mostra **só o texto das perguntas** (cortado a 120 caracteres) e contagens; nunca as respostas nem dados de alunos.
- Se uma pergunta contiver o nome de uma pessoa, **não a copie para os testes**: substitua por um nome genérico.
- O CSV neutraliza células que começam por `=`, `+`, `-` ou `@` (texto de utilizadores nunca vira fórmula no Excel).
- Perfis de escola nunca devem passar a ver dados da plataforma, e o assistente nunca responde fora do painel: ao decidir "ligar o módulo", confirme sempre o menu real do perfil.

## 5. Registo da revisão (modelo)
| Data | Período | Perguntas | Sem resposta % | Não úteis % | Capacidades novas / alteradas | Responsável |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

Meta sugerida: **sem resposta abaixo de 5%** e **não úteis abaixo de 3%** ao fim de 4 semanas de uso.
