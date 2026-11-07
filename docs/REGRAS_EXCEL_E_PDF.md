# Regras de Qualidade de Ficheiros Excel e PDF do SIGE

> **LEIA PRIMEIRO, SEMPRE.** Antes de criar ou alterar qualquer exportação Excel (`.xlsx`) ou PDF, consulte este documento.
> Está referenciado em `CLAUDE.md` (raiz e `backend/`) como leitura obrigatória. Qualquer nova exportação que não cumpra estas regras não pode ser entregue.

## 1. Excel (`.xlsx`) — regras obrigatórias

Ponto único de aplicação: **`guardar_xlsx_seguro(wb)`** em `backend/apps/documentos/services/xlsx_seguro.py` (também chamado por `salvar_xlsx_padronizado`). Toda a exportação tem de gravar por aqui; nunca usar `wb.save()` directo.

| # | Regra | Como é garantida |
|---|---|---|
| 1 | **Ocultar linhas e colunas sem conteúdo**: só a área com conteúdo fica visível | `embelezar_workbook` (`zeroHeight` nas linhas e colunas a partir da primeira vazia escondidas) |
| 2 | **Todo o texto em Times New Roman, tamanho 12** (negrito, itálico e cor preservados) | `padronizar_fontes_e_cabecalhos` |
| 3 | **Cabeçalhos sempre centrados** (horizontal e vertical, com quebra de linha): qualquer célula com fundo escuro e letra clara | `padronizar_fontes_e_cabecalhos` |
| 4 | **Sem sobreposição nem corte de palavras**: as palavras só mudam de linha nos espaços; as colunas alargam até caber a palavra mais comprida; a altura da linha ajusta-se ao texto | `garantir_palavras_inteiras`, `ajustar_larguras_ao_conteudo`, `_ajustar_alturas` |
| 5 | **Tabelas de qualidade superior com estilos de linha** (secção 1.1) | `aplicar_moldura_tabelas` |
| 6 | Sem fórmulas: qualquer valor iniciado por `=` é texto | `sanear_workbook` |
| 7 | Sem grelha de fundo; impressão centrada; cabeçalho da tabela repetido em cada página impressa; zebra nas linhas de dados | `embelezar_workbook`, `_melhorar_tabela` |
| 8 | Logótipo oficial da escola centrado sobre o cabeçalho | `_centrar_logo` |

Só são aceites exceções com `guardar_xlsx_seguro(wb, embelezar=False)` para ficheiros **de terceiros** (provas carregadas pelo professor no Escudo Anti-IA), nunca para documentos emitidos pelo SIGE.

### 1.1 Estilos de linha das tabelas (caixa «Estilo» do Excel)

| Zona | Estilo | Cor |
|---|---|---|
| Moldura exterior da tabela | **grossa** (`thick`) | azul institucional `1E3A8A` |
| Por baixo do cabeçalho | **dupla** (`double`) | dourado `C9A227` |
| Entre células do cabeçalho | fina (`thin`) | azul claro `5B74B8` |
| Entre grupos de colunas (ex.: bloco de cada disciplina) | **média** (`medium`) | azul `1E3A8A` / branco no cabeçalho |
| Entre linhas de dados | **ponteada** (`dotted`) | cinzento `94A3B8` |
| Verticais de dados | fina (`thin`) | cinzento `CBD5E1` |

Sugestões adoptadas (a mais): fundo branco sólido em todas as tabelas (nunca transparente), zebra `F1F5F9`, cabeçalho azul `1E3A8A` com letra branca, notas negativas a vermelho, números alinhados à direita e texto à esquerda, e uma só moldura por tabela. Para formulários (ex.: folha de resposta) cada alternativa é uma célula rectangular com moldura.

## 2. PDF — regras obrigatórias

Ponto único de aplicação: `backend/apps/documentos/services/pdf_service.py` (estilos globais Times New Roman 12 pt, entrelinha 18 pt = espaçamento 1,5; `TableStyle` e `Paragraph` do SIGE forçam 12/18 pt).

| # | Regra |
|---|---|
| 1 | **Times New Roman** (`Times-Roman`/`Times-Bold`); texto corrido em **12 pt** com entrelinha 18 pt |
| 2 | **Tabelas**: células com `Paragraph` (nunca texto solto), para que as palavras quebrem nos espaços e **nunca se sobreponham**; larguras de coluna calculadas pelo conteúdo e que somam a largura útil da página |
| 3 | **Cabeçalho de tabela** centrado (horizontal e vertical), fundo azul `#1E3A8A`, letra branca a negrito, repetido em cada página (`repeatRows=1`) |
| 4 | **Linhas**: moldura exterior mais grossa (≈1,2 pt) em azul institucional, linha dupla/mais grossa por baixo do cabeçalho, linhas interiores finas (0,4 pt) e cinzentas, zebra suave nas linhas de dados |
| 5 | Notas negativas a vermelho; números por extenso nas actas |
| 6 | Logótipo/emblema oficial no topo; nenhum documento sem o logótipo escolhido pela escola |
| 7 | **Formulários de preenchimento** (ex.: folha de resposta) desenhados directamente no canvas podem usar corpos menores para caberem **numa só página A4**, mas mantêm Times New Roman, cabeçalhos centrados/legíveis e nada sobreposto |

## 3. Lista de verificação antes de entregar uma exportação

- [ ] Excel grava por `guardar_xlsx_seguro`; fontes TNR 12; cabeçalhos centrados; só a área com conteúdo visível.
- [ ] Nenhuma palavra cortada/sobreposta (testar com nomes longos).
- [ ] PDF com tabelas conforme a secção 2 e, se for formulário, numa só página.
- [ ] Teste automático em `backend/tests/` (ex.: `test_regras_excel.py`).
- [ ] Documentação actualizada (`docs/`) e esta lista respeitada.
