/**
 * SIGE — Testes Automatizados da Página e Rotas do Prompt do Gateway
 * Executado nativamente com node:test e node:assert (sem dependências externas adicionais).
 */
const { test, describe, before, after } = require('node:test');
const assert = require('node:assert');
const http = require('node:http');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const {
  server,
  carregarCachePrompt,
  verificarTokenJWT,
  JWT_SECRET,
  escaparHtml,
  setCachePromptParaTeste
} = require('../server.js');

function gerarTokenTeste(role, exp = Math.floor(Date.now() / 1000) + 3600) {
  const header = { alg: 'HS256', typ: 'JWT' };
  const payload = {
    user_id: 999,
    role: role,
    nome: `Teste ${role}`,
    exp: exp
  };
  const hB64 = Buffer.from(JSON.stringify(header)).toString('base64url');
  const pB64 = Buffer.from(JSON.stringify(payload)).toString('base64url');
  const sig = crypto.createHmac('sha256', JWT_SECRET).update(`${hB64}.${pB64}`).digest('base64url');
  return `${hB64}.${pB64}.${sig}`;
}

describe('Testes da Página e Rotas: Prompt do Gateway SMS, USSD e Pagamentos Móveis', () => {
  let serverInstance;
  let baseUrl;
  let conteudoOriginal;

  before(async () => {
    // Carregar cache real inicial
    carregarCachePrompt();

    // Ler conteúdo real de prompt-gateway.txt para validação
    const caminhoConteudo = [
      path.join(__dirname, '..', '..', 'conteudo', 'prompt-gateway.txt'),
      path.join(__dirname, '..', 'conteudo', 'prompt-gateway.txt')
    ].find(p => fs.existsSync(p));

    conteudoOriginal = caminhoConteudo ? fs.readFileSync(caminhoConteudo, 'utf8') : '[COLA AQUI, SEM ALTERAÇÕES, O PROMPT DO GATEWAY SMS, USSD E PAGAMENTOS]';

    await new Promise((resolve) => {
      serverInstance = server.listen(0, '127.0.0.1', () => {
        const port = serverInstance.address().port;
        baseUrl = `http://127.0.0.1:${port}`;
        resolve();
      });
    });
  });

  after(async () => {
    setCachePromptParaTeste(conteudoOriginal);
    await new Promise((resolve) => serverInstance.close(resolve));
  });

  // ---------------------------------------------------------------------------
  // 1. Sem sessão: a página e o download não devolvem conteúdo (redirecção ou 401)
  // ---------------------------------------------------------------------------
  test('1. Sem sessão: pedido HTML para /ferramentas/prompt-gateway redireciona para login (302) sem expor prompt', async () => {
    const res = await fetch(`${baseUrl}/ferramentas/prompt-gateway`, {
      headers: { 'Accept': 'text/html' },
      redirect: 'manual'
    });

    assert.ok(res.status === 302 || res.status === 401, `Esperado status 302 ou 401, obtido: ${res.status}`);
    if (res.status === 302) {
      assert.ok(res.headers.get('location'), 'Deverá conter cabeçalho Location para redireccionamento');
    }
    const texto = await res.text();
    assert.ok(!texto.includes(conteudoOriginal), 'Não deve devolver o conteúdo do prompt sem sessão');
  });

  test('1.1. Sem sessão: pedido de API ou descarregamento devolve 401 (ou 302) sem conteúdo', async () => {
    const resApi = await fetch(`${baseUrl}/ferramentas/prompt-gateway`, {
      headers: { 'Accept': 'application/json' },
      redirect: 'manual'
    });
    assert.ok(resApi.status === 401 || resApi.status === 302, `Esperado status 401 ou 302 para API sem sessão, obtido: ${resApi.status}`);

    const resDownload = await fetch(`${baseUrl}/ferramentas/prompt-gateway/descarregar`, {
      redirect: 'manual'
    });
    assert.ok(resDownload.status === 401 || resDownload.status === 302, `Esperado 401 ou 302 no download sem sessão, obtido: ${resDownload.status}`);
    const texto = await resDownload.text();
    assert.ok(!texto.includes(conteudoOriginal), 'O download sem sessão não deve expor o conteúdo do prompt');
  });

  // ---------------------------------------------------------------------------
  // 2. Com sessão sem permissão: 403
  // ---------------------------------------------------------------------------
  test('2. Com sessão sem permissão (ALUNO ou PROFESSOR): devolve 403 Forbidden em ambas as rotas', async () => {
    const tokenAluno = gerarTokenTeste('ALUNO');
    const tokenProf = gerarTokenTeste('PROFESSOR');

    // Testar com papel ALUNO
    const resPaginaAluno = await fetch(`${baseUrl}/ferramentas/prompt-gateway`, {
      headers: { 'Authorization': `Bearer ${tokenAluno}` }
    });
    assert.strictEqual(resPaginaAluno.status, 403, 'Acesso de ALUNO à página deve devolver 403');
    const txtAlunoPag = await resPaginaAluno.text();
    assert.ok(!txtAlunoPag.includes(conteudoOriginal), '403 não deve expor o prompt');

    const resDownloadAluno = await fetch(`${baseUrl}/ferramentas/prompt-gateway/descarregar`, {
      headers: { 'Authorization': `Bearer ${tokenAluno}` }
    });
    assert.strictEqual(resDownloadAluno.status, 403, 'Acesso de ALUNO ao download deve devolver 403');

    // Testar com papel PROFESSOR
    const resPaginaProf = await fetch(`${baseUrl}/ferramentas/prompt-gateway`, {
      headers: { 'Authorization': `Bearer ${tokenProf}` }
    });
    assert.strictEqual(resPaginaProf.status, 403, 'Acesso de PROFESSOR à página deve devolver 403');

    const resDownloadProf = await fetch(`${baseUrl}/ferramentas/prompt-gateway/descarregar`, {
      headers: { 'Authorization': `Bearer ${tokenProf}` }
    });
    assert.strictEqual(resDownloadProf.status, 403, 'Acesso de PROFESSOR ao download deve devolver 403');
  });

  // ---------------------------------------------------------------------------
  // 3. Com sessão de administrador: página devolve 200, título, texto e escape
  // ---------------------------------------------------------------------------
  test('3. Com sessão de administrador: página devolve 200, título, subtítulo, texto e caracteres especiais (<, >, &) escapados', async () => {
    // Configurar conteúdo com caracteres especiais para validar escape contra XSS
    const textoComEspeciais = 'PROMPT GATEWAY: Teste de Caracteres Especiais <script>alert("xss")</script> & <html> "aspas" e \'plicas\'.';
    setCachePromptParaTeste(textoComEspeciais);

    const tokenAdmin = gerarTokenTeste('ADMIN_ESCOLA');
    const res = await fetch(`${baseUrl}/ferramentas/prompt-gateway`, {
      headers: { 'Authorization': `Bearer ${tokenAdmin}` }
    });

    assert.strictEqual(res.status, 200, 'Página deve devolver 200 para ADMIN_ESCOLA');
    assert.strictEqual(res.headers.get('cache-control'), 'no-store', 'Deve conter Cache-Control: no-store');
    assert.strictEqual(res.headers.get('x-robots-tag'), 'noindex', 'Deve conter X-Robots-Tag: noindex');

    const html = await res.text();

    // Validação de meta robots
    assert.ok(html.includes('<meta name="robots" content="noindex">'), 'HTML deve conter <meta name="robots" content="noindex">');

    // Validação do título e subtítulo oficiais
    assert.ok(html.includes('Prompt: Gateway SMS, USSD e Pagamentos Móveis'), 'HTML deve conter o título oficial');
    assert.ok(html.includes('Para Node.js. Copia e cola no teu assistente de código.'), 'HTML deve conter o subtítulo oficial');

    // Validação dos botões exigidos
    assert.ok(html.includes('id="btnCopiarPrompt"'), 'HTML deve conter o botão de copiar');
    assert.ok(html.includes('id="btnDescarregarPrompt"'), 'HTML deve conter o botão de descarregar');
    assert.ok(html.includes('href="/ferramentas/prompt-gateway/descarregar"'), 'Botão de download deve apontar para rota correspondente');
    assert.ok(html.includes('id="statusCopiado"'), 'HTML deve conter elemento para região aria-live');
    assert.ok(html.includes('aria-live="polite"'), 'Região de status deve ter aria-live="polite"');

    // Validação da inclusão do script estático próprio sem inline scripts
    assert.ok(html.includes('<script src="/js/prompt-gateway.js"></script>'), 'HTML deve referenciar /js/prompt-gateway.js');

    // Validação de escape rigoroso de caracteres especiais
    assert.ok(html.includes('&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;'), 'Tags HTML e aspas devem aparecer escapadas');
    assert.ok(html.includes('&amp; &lt;html&gt;'), 'E comercial e tags devem aparecer escapados');
    assert.ok(!html.includes('<script>alert("xss")</script>'), 'Não deve conter tags perigosas não-escapadas');

    // Restaurar conteúdo padrão
    setCachePromptParaTeste(conteudoOriginal);
  });

  test('3.1. Suporte com token SUPERADMIN e acesso via Cookie', async () => {
    const tokenSuper = gerarTokenTeste('SUPERADMIN');
    const res = await fetch(`${baseUrl}/ferramentas/prompt-gateway`, {
      headers: { 'Cookie': `sige_token=${tokenSuper}` }
    });

    assert.strictEqual(res.status, 200, 'SUPERADMIN via Cookie deve receber 200');
    const html = await res.text();
    assert.ok(html.includes('Prompt: Gateway SMS, USSD e Pagamentos Móveis'));
    assert.ok(html.includes(conteudoOriginal));
  });

  // ---------------------------------------------------------------------------
  // 4. Download: 200, Content-Type, Content-Disposition, corpo idêntico
  // ---------------------------------------------------------------------------
  test('4. Download: 200, Content-Type text/plain; charset=utf-8, Content-Disposition com nome correto e corpo idêntico', async () => {
    setCachePromptParaTeste(conteudoOriginal);
    const tokenAdmin = gerarTokenTeste('DIRECTOR_ESCOLA');

    const res = await fetch(`${baseUrl}/ferramentas/prompt-gateway/descarregar`, {
      headers: { 'Authorization': `Bearer ${tokenAdmin}` }
    });

    assert.strictEqual(res.status, 200, 'Download deve responder 200 com token válido');

    const contentType = res.headers.get('content-type');
    assert.ok(contentType && contentType.includes('text/plain') && contentType.includes('charset=utf-8'), `Content-Type deve ser text/plain; charset=utf-8, obtido: ${contentType}`);

    const contentDisposition = res.headers.get('content-disposition');
    assert.ok(contentDisposition && contentDisposition.includes('attachment') && contentDisposition.includes('filename="prompt-gateway-sms-ussd.txt"'), `Content-Disposition incorrecto: ${contentDisposition}`);

    assert.strictEqual(res.headers.get('cache-control'), 'no-store');
    assert.strictEqual(res.headers.get('x-robots-tag'), 'noindex');

    const corpo = await res.text();
    assert.strictEqual(corpo, conteudoOriginal, 'O corpo descarregado deve ser estritamente idêntico ao ficheiro de conteúdo');
  });

  // ---------------------------------------------------------------------------
  // 5. Ficheiro de conteúdo em falta: resposta 500 genérica, sem detalhes internos
  // ---------------------------------------------------------------------------
  test('5. Ficheiro de conteúdo em falta: resposta 500 genérica sem detalhes internos ou caminhos do servidor', async () => {
    // Simular que o ficheiro de conteúdo está em falta ou não foi lido
    setCachePromptParaTeste(null);
    const tokenAdmin = gerarTokenTeste('SUPERADMIN');

    // Testar na página principal
    const resPagina = await fetch(`${baseUrl}/ferramentas/prompt-gateway`, {
      headers: { 'Authorization': `Bearer ${tokenAdmin}` }
    });
    assert.strictEqual(resPagina.status, 500, 'Deve devolver 500 quando ficheiro não existe');
    const corpoPagina = await resPagina.text();
    assert.ok(corpoPagina.includes('Erro interno do servidor'), 'Deve conter mensagem genérica de erro amigável');
    assert.ok(!corpoPagina.includes('prompt-gateway.txt'), 'Não deve expor o nome do ficheiro ou caminhos internos');
    assert.ok(!corpoPagina.includes('d:\\'), 'Não deve expor directórios locais do servidor');
    assert.ok(!corpoPagina.includes('C:\\'), 'Não deve expor caminhos C:\\');

    // Testar no download
    const resDownload = await fetch(`${baseUrl}/ferramentas/prompt-gateway/descarregar`, {
      headers: { 'Authorization': `Bearer ${tokenAdmin}` }
    });
    assert.strictEqual(resDownload.status, 500, 'Download deve devolver 500 quando ficheiro não existe');
    const corpoDownload = await resDownload.text();
    assert.ok(corpoDownload.includes('Erro interno do servidor'), 'Deve conter mensagem genérica');
    assert.ok(!corpoDownload.includes('prompt-gateway.txt'));

    // Restaurar conteúdo
    setCachePromptParaTeste(conteudoOriginal);
  });
});
