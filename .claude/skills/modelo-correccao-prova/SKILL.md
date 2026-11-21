---
name: modelo-correccao-prova
description: Usar SEMPRE que se criar, alterar, rever ou testar a folha de resposta corrigida (vistos, círculos, acertos, nota, assinatura), o PDF das provas corrigidas, a lista de notas da avaliação ou a correcção automática de provas. Obriga a consultar o modelo oficial do professor e a respeitar a sua aparência e a rapidez exigida.
---

# Modelo obrigatório da correcção de provas (SIGE)

O professor definiu **um modelo único e obrigatório** de como uma prova corrigida tem de ficar. Não se inventa outro
estilo. Antes de tocar em qualquer código de correcção, **abrir e olhar para o modelo**:

- Modelo (PDF digitalizado, uma folha corrigida à mão): `docs/modelos/Modelo_de_correccao_da_prova.pdf`
- Folha digitalizada de teste (16 folhas reais, 40 perguntas, 4 alternativas): `D:\8 SIGE Seguranca System\Testes AT Fisica 11a Classe-Turma 12.pdf` (fora do repositório; só existe na máquina do professor)
- Código: `backend/apps/notas/omr_servico.py` → `anotar_folha` (+ `_circulo_a_mao`, `_visto_a_mao`, `_textos_pil`)
- Endpoints: `backend/apps/notas/views_omr.py` (`leitura-omr`, `confirmar-omr`, `folhas-pendentes`), `views_correcao.py` (`folhas-corrigidas`, `lista-notas`)

## Como abrir o modelo para o ver

Renderizar a página em PNG com PyMuPDF (não há `pdftoppm` nesta máquina) e **ler a imagem**:

```powershell
cd D:\SIGE\backend
.\venv\Scripts\python.exe -c "import fitz; d=fitz.open(r'..\docs\modelos\Modelo_de_correccao_da_prova.pdf'); d[0].get_pixmap(dpi=110).save(r'$env:TEMP\modelo.png')"
```

Ampliar a grelha (dpi 200, recorte) e o quadro «IV Classificação» para comparar pormenores.

## Regras do modelo (todas obrigatórias)

1. **Marcas CLÁSSICAS e nítidas a vermelho** (decisão do professor, 21/11/2026): **círculo** = elipse perfeita e fechada; **certo** = visto ✓ clássico; traço firme mas fino (≈ 0,4 mm), para se ver logo que foi o sistema que corrigiu. Nada de traços tremidos, grossos nem cores berrantes. Os centros ajustam-se ao quadrinho impresso (_afinar_centro).
2. **Resposta certa** → um **visto pequeno** à **direita** da alternativa assinalada pelo aluno: traço curto para baixo e
   traço longo a subir para a direita (~7 mm).
3. **Resposta errada, em branco ou nula** → um **círculo fino à volta da letra da alternativa CERTA** (≈ 7 mm de diâmetro,
   laçada que não fecha exactamente). Não se desenha nada na alternativa errada do aluno.
4. **«Questão nula»** (vale 0), **automaticamente e sem pedir revisão**, quando o aluno assinalou **mais de uma alternativa**
   **ou não assinalou nenhuma** (pergunta sem sinalização): escrever **«Questão nula»** a vermelho **por cima da pergunta**
   (logo acima da linha das alternativas, alinhado à primeira alternativa) e **circular a alternativa certa**. Códigos
   internos da resposta: `N` (mais de uma) e `-` (nenhuma); ambos saem como «Questão nula».
   **Não acertou** (errada ou nula) → **circundar a alternativa certa** (círculo fino à volta da letra), nunca marcar a
   errada do aluno.
5. **«Acertos (n.º)»** e **«Correcção normal (valores)»** escritos a vermelho, letra grande de caneta; a **nota** com uma casa
   decimal e vírgula (ex.: `14,0`).
6. **«Ass. do Professor»**: o **NOME do professor por extenso** (não rubrica), a vermelho, em itálico fino, acima da linha.
7. **Só tinta azul ou preta** vale como resposta do aluno; a tinta de outra cor (vermelho/verde/laranja) **não** conta.
8. A folha corrigida mantém a folha do aluno intacta por baixo (a marcação do aluno continua visível); sai em A4, uma por página.
9. **Nome do PDF das provas corrigidas**: `Avaliacao corrigida - Disciplina - Tipo de avaliação - Ano.pdf`.
   **Nome da lista**: `Lista de notas - Disciplina - Tipo de avaliação - Ano` (`.pdf` / `.xlsx`).
10. **Tudo fica guardado** no sistema (correcções, folhas corrigidas, folhas sem aluno, gabaritos) e o professor elimina
    quando quiser. A nota só é lançada na caderneta quando o professor carrega em «Iniciar lançamento automático».

## Qualidade de impressão (obrigatória)

A prova corrigida pode ser **impressa e devolvida ao aluno como comprovativo**. Por isso:

- Nunca sai destruída, deformada, desfocada nem em miniatura: a base é a folha **endireitada em alta resolução (≈ 250 dpi,
  2100 × 2970 px)**, obtida **a partir da imagem ORIGINAL** (`pagina_limpa_alta`), nunca a partir da versão reduzida de
  leitura (1240/1680 px). A marcação do aluno não se altera.
- JPEG com qualidade ≥ 90; A4 direito (as 4 marcas dos cantos definem a perspectiva); sem recortes nem distorção.
- As marcas vermelhas desenham-se à resolução da própria imagem (`anotar_folha` usa `ppm = largura / 210`).
- Antes de entregar: abrir a folha corrigida **ampliada** (recorte a 100 %) e confirmar que os vistos, círculos e texto
  estão nítidos e que a folha do aluno por baixo está intacta.

## Rapidez (obrigatória): lote ≤ 60 segundos, qualquer que seja o nº «n» de folhas

A correcção em lote **nunca** pode levar mais de **1 minuto** e **nunca** pode parecer manual. Arquitectura obrigatória
(`backend/apps/notas/lote_servico.py`, `POST /provas-fisicas/<id>/corrigir-lote/` + `GET .../<job_id>/`):

1. O ficheiro envia-se **uma só vez**; o servidor trata **todas** as páginas num só trabalho (nada de vaivém página a página).
2. Leitura + QR + desenho da folha corrigida em **processos paralelos** (`ProcessPoolExecutor`, um por núcleo,
   `cv2.setNumThreads(1)`), com o pool **aquecido** durante o envio (`aquecer()`); o processo principal só grava BD/disco.
3. QR com orçamento ≤ 0,6 s por folha (detector Aruco 1,5×/2× primeiro); sem passos caros por folha.
4. Terminado o trabalho o navegador faz, **sem cliques**: lançar nas cadernetas (`/lancar/`) → descarregar o **PDF das
   provas corrigidas** (`/folhas-corrigidas/`); a lista de notas (PDF/Excel) fica nos botões.
5. A UI mostra `feitas/total` e os segundos decorridos; o estado do trabalho guarda `segundos` e `dentro_orcamento`.
6. **Medir antes de entregar** com a folha de teste (16 folhas) e registar s/folha e folhas/minuto; se
   (n × s/folha ÷ núcleos) > 60 s, optimizar o custo por folha (não esconder com mensagens).
   Medido a 21/11/2026 (4 núcleos, Windows, arranque a frio): 16 folhas ≈ 40 s com ≈ 18 s de arranque dos processos;
   em regime ≈ 1,2 s/folha (≈ 50 folhas/min). Meta contínua: ≤ 1 s/folha.
## Lista de verificação antes de entregar qualquer alteração a esta funcionalidade

- [ ] Abri o modelo (PNG) e comparei lado a lado com uma folha corrigida pelo sistema (`anotar_folha`).
- [ ] Traços finos, círculos só na alternativa certa, vistos à direita da resposta certa, «Nula» nas anuladas.
- [ ] Acertos, nota (vírgula, 1 casa) e nome do professor nos sítios certos do quadro «IV Classificação».
- [ ] Tempo médio por folha medido e dentro do orçamento acima.
- [ ] Testes: `pytest tests/test_omr_leitura.py tests/test_correcao_automatica.py tests/test_correcao_provas.py`.
- [ ] Excel/PDF das listas seguem `docs/REGRAS_EXCEL_E_PDF.md`.
- [ ] Documentação (`docs/DOCUMENTACAO_COMPLETA_DO_SISTEMA.md`, `docs/REFERENCIA_COMPLETA_API.md`), commit semântico e deploy
  (`.\scripts\sige-git-deploy.ps1 -Message "..."`), conforme o `CLAUDE.md`.
