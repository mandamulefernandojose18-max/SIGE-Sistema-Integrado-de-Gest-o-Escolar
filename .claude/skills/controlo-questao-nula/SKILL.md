---
name: controlo-questao-nula
description: Usar SEMPRE que se alterar a leitura óptica das folhas (omr_servico.py: decidir, _pontuar, endireitar, alinhamento), o desenho da folha corrigida (anotar_folha, círculos, vistos, «Questão nula») ou ao rever qualquer correcção automática. Controla o ERRO GRAVE «Questão nula» onde o aluno assinalou UMA alternativa. Regra inquebrável, com auditoria obrigatória.
---

# Controlo do erro grave: «Questão nula» indevida (SIGE)

## Regra inquebrável (decisão do professor)

**«Questão nula» só se, e só se:**
1. o aluno marcou **mais de uma** alternativa nessa pergunta (duas marcas fortes), **ou**
2. o aluno **não marcou nenhuma** (todas as alternativas em branco).

**Nunca** pode sair «Questão nula» (nem «Questão errada») quando o aluno marcou **UMA** alternativa que achou certa —
mesmo fraca, rasurada, escura demais, em caneta clara ou numa linha do fim da coluna. Se houver uma só marca, ela é a
resposta do aluno (certa → visto ✓; errada → círculo na certa, **sem** texto «Questão nula»).

## Causas já encontradas (não repetir)

- **Deriva vertical/horizontal** da digitalização (folha esticada/inclinada): a janela de leitura da linha deixava de
  apanhar a tinta nas últimas linhas (perguntas 19, 20, 39, 40) → lia-se «em branco» → nula. Corrigido com o alinhamento
  **por linha** (`_desloc_linha`, correlação com o desenho impresso da própria linha). Não remover.
- **Marca fraca única** (0,09–0,13) tratada como branco → agora é resposta (`decidir`, dúvida `FRACA`).
- Texto «Questão nula» por cima da pergunta lia-se como sendo da pergunta de cima → agora na **mesma linha, à direita**.

## Auditoria obrigatória antes de entregar qualquer alteração a esta área

1. Correr a auditoria na folha digitalizada de teste (16 folhas reais, só existe na máquina do professor):

```powershell
cd D:\SIGE\backend
.\venv\Scripts\python.exe -W ignore -I scripts\auditar_questao_nula.py "D:\8 SIGE Seguranca System\Testes AT Fisica 11a Classe-Turma 12.pdf"
```

   Cada `N` tem de ter **≥ 2** alternativas com tinta forte e cada `-` tem de ter **todas** as alternativas ≈ 0. A saída
   marca `SUSPEITA` em qualquer pergunta que não cumpra: **zero SUSPEITAS** é o critério de aceitação.
2. Abrir o crop do fim das colunas (perguntas 17–20 e 37–40) da folha corrigida e confirmar **a olho** que onde o aluno
   marcou uma só alternativa não há «Questão nula».
3. Testes: `pytest tests/test_omr_leitura.py -k "nula or deriva or fraca or circulo"` (inclui o teste de deriva vertical).
4. Círculos: nunca se cruzam (linhas seguidas) nem tocam nas alternativas vizinhas; envolvem 100 % do quadrinho + letra
   (`test_circulo_envolve_100_por_cento_a_alternativa_sem_cruzar_linhas`).