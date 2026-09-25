# Regras Oficiais de Avaliação Pedagógica — MINEDH (Moçambique)

> **Documento Normativo**: Sistema Nacional de Educação de Moçambique  
> **Implementação**: `backend/common/utils/avaliacoes_mocambique.py` e `backend/apps/notas/models.py`

---

## 1. Escala e Valores de Avaliação
- **Escala de Notas:** Valores inteiros de **0 a 20**.
- **Nota Mínima Positiva:** $\ge 10$ valores (ou média ponderada $\ge 9.5$ que arredonda para $10$).
- **Nota Negativa:** $\le 9$ valores.

---

## 2. Cálculo da Média Trimestral (MT)

A nota final de cada disciplina em cada trimestre letivo é calculada pela fórmula oficial:

$$MAC = \frac{\sum_{i=1}^{n} \text{Avaliações Contínuas}}{n}$$

$$MT = \text{round}\left(\frac{2 \times MAC + AT}{3}\right)$$

Onde:
- **MAC**: Média das Avaliações Contínuas (testes sumativos 1 a 4 e trabalhos práticos/pesquisas).
- **AT**: Avaliação Trimestral (prova global de fim de trimestre).
- **Arredondamento**: Obrigatório para o número inteiro mais próximo (ex: $15.5 \to 16$, $9.5 \to 10$, $9.4 \to 9$).

### 2.1. Classificação do Comportamento Qualitativo
Conforme a nota obtida na média trimestral ou anual:

| Intervalo de Notas | Sigla Oficial | Significado | Cor Visual no Boletim |
| :--- | :---: | :--- | :---: |
| **18.5 a 20.0** | **E** | Excelente | Preto |
| **16.5 a 18.4** | **MB** | Muito Bom | Preto |
| **13.5 a 16.4** | **B** | Bom | Preto |
| **9.5 a 13.4** | **S** | Suficiente | Preto |
| **0.0 a 9.4** | **NS** | Não Suficiente | Vermelho |

---

## 3. Critérios Oficiais de Aprovação na Pauta Anual

A aprovação é avaliada pela função `avaliar_aprovacao_pauta(notas_disciplinas, grau_ano)`:

### 3.1. Regra Geral (Todas as classes excepto 12ª)
> **Princípio dos 100% de Positivas**:  
> O estudante **SÓ APROVA** se tiver aproveitamento positivo em **TODAS** as disciplinas do plano de estudos curricular (ou seja, exatamente **zero notas negativas**).
- Havendo **1 ou mais notas negativas**, o aluno é considerado **Reprovado**.

### 3.2. Regra Específica da 12ª Classe
A 12ª Classe possui regime diferenciado de tolerância curricular:
O estudante **APROVA** se satisfizer cumulativamente:
1. **Média Geral:** Maior ou igual a **9.5 valores** ($\ge 10$ após arredondamento);
2. **Total de Negativas:** No máximo **2 notas negativas** toleradas;
3. **Piso Mínimo de Nota:** **Nenhuma negativa pode ser inferior a 8 valores**.

> [!WARNING] Reprovação Sumária na 12ª Classe
> Se o estudante da 12ª classe tiver qualquer disciplina com nota $\le 7$ valores, ele é automaticamente **Reprovado**, independentemente da sua média geral.

---

## 4. Anotações Oficiais de Situação Escolar

Na caderneta e pauta, os seguintes códigos padronizados representam a situação administrativa do aluno:

| Sigla | Significado Oficial | Impacto no Aproveitamento |
| :---: | :--- | :--- |
| **D** | Dispensado | Dispensado de exame ou prova por aproveitamento de excelência |
| **T** | Transferido | Transferiu-se para outra escola antes da conclusão do período |
| **VT** | Veio Transferido | Admitido por transferência externa no decurso do período |
| **F** | Faleceu | Óbito registado no livro de ponto |
| **AM** | Anulou Matrícula | Cancelamento voluntário ou legal da matrícula |
| **PPF** | Perdeu por Faltas | Ultrapassou o limite legal de faltas injustificadas |
| **PDF** | Perdeu por Disciplina | Suspensão ou expulsão disciplinar nos termos do regulamento escolar |
