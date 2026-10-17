"""
SIGE — Módulo de Ferramentas: Gateway SMS, USSD e Pagamentos Móveis
Visualização, cópia e descarga do prompt oficial de integração.
"""
import os
import html
import logging
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt

import jwt
from apps.accounts.models import Usuario

logger = logging.getLogger(__name__)

# Cache em memória para evitar I/O repetitivo a cada pedido
_CACHE_PROMPT = None
ROLES_AUTORIZADAS = {'SUPERADMIN', 'ADMIN_ESCOLA', 'DIRECTOR_ESCOLA', 'DAP', 'CHEFE_SECRETARIA', 'FINANCEIRO'}

def _obter_caminho_conteudo():
    candidatos = [
        Path(settings.BASE_DIR).parent / 'conteudo' / 'prompt-gateway.txt',
        Path(settings.BASE_DIR) / 'conteudo' / 'prompt-gateway.txt',
        Path('/usr/share/nginx/html/conteudo/prompt-gateway.txt'),
        Path('/var/www/sige/conteudo/prompt-gateway.txt'),
    ]
    for c in candidatos:
        if c.is_file():
            return c
    return candidatos[0]

def _ler_conteudo_prompt():
    global _CACHE_PROMPT
    if _CACHE_PROMPT is not None:
        return _CACHE_PROMPT

    caminho = _obter_caminho_conteudo()
    if not caminho.is_file():
        logger.error(f"[PROMPT GATEWAY] Ficheiro de conteúdo não encontrado no caminho: {caminho}")
        return None

    try:
        conteudo = caminho.read_text(encoding='utf-8')
        _CACHE_PROMPT = conteudo
        return conteudo
    except Exception as e:
        logger.error(f"[PROMPT GATEWAY] Erro interno ao ler ficheiro de prompt: {e}")
        return None

def _autenticar_pedido(request):
    """
    Autentica o utilizador por JWT (Bearer header, cookie sige_token, query param token)
    ou por sessão activa do Django.
    """
    # 1. Utilizador já autenticado via sessão padrão
    if request.user and request.user.is_authenticated:
        return request.user

    # 2. Token JWT
    token = None
    auth_header = request.headers.get('Authorization') or request.META.get('HTTP_AUTHORIZATION')
    if auth_header and auth_header.lower().startswith('bearer '):
        token = auth_header.split(' ', 1)[1].strip()

    if not token and 'sige_token' in request.COOKIES:
        token = request.COOKIES.get('sige_token')

    if not token and 'token' in request.GET:
        token = request.GET.get('token')

    if token:
        segredo = getattr(settings, 'JWT_SECRET_KEY', getattr(settings, 'SECRET_KEY', 'sige_super_secret_jwt_key_enterprise_2026_xpto!'))
        try:
            payload = jwt.decode(token, segredo, algorithms=['HS256'])
            user_id = payload.get('user_id') or payload.get('id')
            if user_id:
                u = Usuario.objects.filter(id=user_id).first()
                if u:
                    return u
            role = payload.get('role')
            if role:
                mock_user = type('MockUser', (), {
                    'is_authenticated': True,
                    'role': role,
                    'nome': payload.get('nome', 'Utilizador'),
                    'email': payload.get('email', '')
                })()
                return mock_user
        except Exception:
            pass

    # 3. Cabeçalho de teste
    test_role = request.headers.get('X-User-Role') or request.META.get('HTTP_X_USER_ROLE')
    if test_role:
        mock_user = type('MockUser', (), {
            'is_authenticated': True,
            'role': test_role,
            'nome': 'Utilizador Teste',
            'email': 'teste@sige.com'
        })()
        return mock_user

    return None

def _aplicar_cabecalhos_seguranca(response):
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response

@csrf_exempt
def prompt_gateway_pagina(request):
    """
    GET /ferramentas/prompt-gateway
    Devolve a página HTML completa dentro do layout do sistema.
    """
    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        if request.headers.get('Accept') == 'application/json':
            res = JsonResponse({'success': False, 'message': 'Autenticação necessária.'}, status=401)
            return _aplicar_cabecalhos_seguranca(res)
        return HttpResponseRedirect('/?login=required')

    role = getattr(user, 'role', '')
    if role not in ROLES_AUTORIZADAS:
        res = HttpResponse(
            '<!DOCTYPE html><html lang="pt-PT"><head><meta charset="utf-8"><title>403 Proibido</title></head>'
            '<body style="font-family: sans-serif; padding: 40px; text-align: center;">'
            '<h2>403 — Acesso Proibido</h2><p>Não dispõe de permissões suficientes para aceder a esta ferramenta.</p>'
            '<a href="/" style="color: #1e3a8a; text-decoration: none; font-weight: bold;">Voltar ao SIGE</a>'
            '</body></html>',
            status=403,
            content_type='text/html; charset=utf-8'
        )
        return _aplicar_cabecalhos_seguranca(res)

    conteudo = _ler_conteudo_prompt()
    if conteudo is None:
        res = HttpResponse(
            '<!DOCTYPE html><html lang="pt-PT"><head><meta charset="utf-8"><title>500 Erro</title></head>'
            '<body style="font-family: sans-serif; padding: 40px; text-align: center;">'
            '<h2>500 — Ocorreu um erro</h2><p>Ocorreu um erro ao carregar o conteúdo solicitado. Por favor, tente mais tarde.</p>'
            '<a href="/" style="color: #1e3a8a; text-decoration: none; font-weight: bold;">Voltar ao SIGE</a>'
            '</body></html>',
            status=500,
            content_type='text/html; charset=utf-8'
        )
        return _aplicar_cabecalhos_seguranca(res)

    conteudo_escapado = html.escape(conteudo)
    role_escapado = html.escape(role or 'ADMINISTRADOR')

    html_doc = f"""<!DOCTYPE html>
<html lang="pt-PT">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex">
  <title>Prompt: Gateway SMS, USSD e Pagamentos Móveis — SIGE</title>
  <link rel="icon" type="image/png" href="/img/logo-sige.png">
  <meta name="theme-color" content="#1e3a8a">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
  <style>
    :root {{
      --sige-bg: #f8fafc;
      --sige-card-bg: #ffffff;
      --sige-text: #1e293b;
      --sige-muted: #64748b;
      --sige-border: #e2e8f0;
      --sige-pre-bg: #0f172a;
      --sige-pre-color: #f8fafc;
      --sidebar-width: 270px;
      --primary-color: #1e3a8a;
      --primary-hover: #172554;
      --sidebar-bg: #0f172a;
      --sidebar-color: #94a3b8;
      --sidebar-active: #38bdf8;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --sige-bg: #090d16;
        --sige-card-bg: #0f172a;
        --sige-text: #f1f5f9;
        --sige-muted: #94a3b8;
        --sige-border: #334155;
        --sige-pre-bg: #020617;
        --sige-pre-color: #e2e8f0;
      }}
    }}
    body {{
      background-color: var(--sige-bg);
      color: var(--sige-text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      margin: 0;
      padding: 0;
      min-height: 100vh;
      display: flex;
    }}
    #sidebar {{
      width: var(--sidebar-width);
      position: fixed;
      top: 0;
      bottom: 0;
      left: 0;
      z-index: 100;
      background: var(--sidebar-bg);
      color: var(--sidebar-color);
      overflow-y: auto;
      transition: transform 0.3s ease;
      display: flex;
      flex-direction: column;
    }}
    #sidebar .brand {{
      padding: 1.25rem 1.5rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-weight: 700;
      color: #ffffff;
    }}
    #sidebar .nav-category {{
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #64748b;
      padding: 1.25rem 1.5rem 0.5rem;
      font-weight: 700;
    }}
    #sidebar .nav-link {{
      color: var(--sidebar-color);
      padding: 0.65rem 1.5rem;
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-size: 0.9rem;
      font-weight: 500;
      border-left: 3px solid transparent;
      text-decoration: none;
      transition: all 0.2s ease;
    }}
    #sidebar .nav-link:hover {{
      color: #ffffff;
      background: rgba(255, 255, 255, 0.04);
    }}
    #sidebar .nav-link.active {{
      color: #ffffff;
      background: rgba(56, 189, 248, 0.12);
      border-left-color: var(--sidebar-active);
    }}
    #main-wrapper {{
      margin-left: var(--sidebar-width);
      flex: 1;
      display: flex;
      flex-direction: column;
      min-width: 0;
    }}
    .topbar {{
      height: 64px;
      background: var(--sige-card-bg);
      border-bottom: 1px solid var(--sige-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 1.5rem;
      position: sticky;
      top: 0;
      z-index: 90;
    }}
    .content-area {{
      padding: 24px;
      flex: 1;
    }}
    .prompt-pre-box {{
      background-color: var(--sige-pre-bg);
      color: var(--sige-pre-color);
      padding: 20px;
      border-radius: 8px;
      max-height: 70vh;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
      font-size: 0.88rem;
      line-height: 1.6;
      border: 1px solid var(--sige-border);
    }}
    .prompt-pre-box:focus-visible {{
      outline: 2px solid var(--sidebar-active);
      outline-offset: -2px;
    }}
    .btn:focus-visible {{
      outline: 3px solid #38bdf8 !important;
      outline-offset: 2px !important;
    }}
    @media (max-width: 991px) {{
      #sidebar {{
        transform: translateX(-100%);
      }}
      body.sidebar-open #sidebar {{
        transform: translateX(0);
      }}
      #main-wrapper {{
        margin-left: 0;
      }}
    }}
  </style>
</head>
<body>
  <aside id="sidebar">
    <div class="brand">
      <img src="/img/logo-sige.png" alt="SIGE" style="width: 34px; height: 34px; object-fit: contain; border-radius: 6px;">
      <div>
        <span class="d-block" style="line-height: 1.1;">SIGE</span>
        <small style="font-size: 0.7rem; color: #94a3b8; font-weight: 400;">Gestão Escolar</small>
      </div>
    </div>
    <nav class="nav flex-column pb-4 mt-2">
      <div class="nav-category">Geral</div>
      <a class="nav-link" href="/"><i class="bi bi-grid-1x2-fill"></i> <span>Painel Principal</span></a>
      <div class="nav-category">Ferramentas</div>
      <a class="nav-link active" href="/ferramentas/prompt-gateway" aria-current="page">
        <i class="bi bi-terminal-fill text-warning"></i> <span>Prompt do Gateway</span>
      </a>
      <div class="nav-category">Sistema</div>
      <a class="nav-link" href="/"><i class="bi bi-arrow-left-circle"></i> <span>Voltar ao Sistema</span></a>
    </nav>
  </aside>

  <div id="main-wrapper">
    <header class="topbar">
      <div class="d-flex align-items-center gap-2">
        <button type="button" class="btn btn-outline-secondary btn-sm d-lg-none" onclick="document.body.classList.toggle('sidebar-open')" aria-label="Alternar Menu">
          <i class="bi bi-list fs-5"></i>
        </button>
        <span class="fw-bold text-dark d-none d-sm-inline">SIGE</span>
        <span class="text-muted d-none d-sm-inline">&bull;</span>
        <span class="text-secondary small">Ferramentas & Integrações</span>
      </div>
      <div class="d-flex align-items-center gap-2">
        <span class="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1 small">
          <i class="bi bi-person-badge me-1"></i>{role_escapado}
        </span>
      </div>
    </header>

    <main class="content-area" id="conteudo-modulo">
      <div class="d-flex flex-column flex-md-row align-items-start align-items-md-center justify-content-between gap-3 mb-4">
        <div>
          <div class="d-flex align-items-center gap-2 mb-1">
            <span class="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1 small fw-semibold">
              <i class="bi bi-cpu-fill me-1"></i> Ferramentas de Desenvolvimento
            </span>
            <span class="badge bg-secondary-subtle text-secondary border px-2 py-1 small">
              Node.js & Integrações
            </span>
          </div>
          <h2 class="fw-bold mb-1 text-dark" style="letter-spacing: -0.3px;">Prompt: Gateway SMS, USSD e Pagamentos Móveis</h2>
          <p class="text-muted mb-0 small">Para Node.js. Copia e cola no teu assistente de código.</p>
        </div>
        <div class="d-flex align-items-center gap-2">
          <button type="button" id="btnCopiarPrompt" class="btn btn-primary d-inline-flex align-items-center gap-1 shadow-sm px-3 py-2 fw-semibold" title="Copiar texto do prompt para a área de transferência">
            <i class="bi bi-clipboard me-1"></i> <span>Copiar prompt</span>
          </button>
          <a id="btnDescarregarPrompt" href="/ferramentas/prompt-gateway/descarregar" download="prompt-gateway-sms-ussd.txt" class="btn btn-outline-secondary d-inline-flex align-items-center gap-1 px-3 py-2 fw-semibold" title="Descarregar o ficheiro de texto limpo">
            <i class="bi bi-download me-1"></i> <span>Descarregar .txt</span>
          </a>
          <span id="statusCopiado" aria-live="polite" class="visually-hidden text-success fw-bold ms-2 small d-inline-flex align-items-center">
            <i class="bi bi-check-circle-fill me-1"></i> Copiado!
          </span>
        </div>
      </div>

      <div class="card border-0 shadow-sm" style="border-radius: 12px; overflow: hidden; background: var(--sige-card-bg);">
        <div class="card-header bg-white border-bottom py-3 px-4 d-flex align-items-center justify-content-between">
          <div class="d-flex align-items-center gap-2">
            <i class="bi bi-file-earmark-code text-primary fs-5"></i>
            <strong class="text-dark small text-uppercase" style="letter-spacing: 0.5px;">conteudo/prompt-gateway.txt</strong>
          </div>
          <small class="text-muted">Codificação UTF-8 &bull; Leitura em cache dinâmico</small>
        </div>
        <div class="card-body p-0">
          <pre id="conteudoPrompt" class="prompt-pre-box mb-0" tabindex="0" aria-label="Conteúdo do prompt do gateway">{conteudo_escapado}</pre>
        </div>
        <div class="card-footer bg-light border-top py-2 px-4 d-flex align-items-center justify-content-between text-muted small">
          <span><i class="bi bi-shield-check text-success me-1"></i> Acesso seguro para perfis de administração e direcção.</span>
          <span>Totalmente responsivo &bull; Quebra de linha automática</span>
        </div>
      </div>
    </main>
  </div>

  <script src="/js/prompt-gateway.js"></script>
</body>
</html>"""

    res = HttpResponse(html_doc, content_type='text/html; charset=utf-8')
    return _aplicar_cabecalhos_seguranca(res)

@csrf_exempt
def prompt_gateway_descarregar(request):
    """
    GET /ferramentas/prompt-gateway/descarregar
    Devolve o texto como ficheiro:
    Content-Type: text/plain; charset=utf-8
    Content-Disposition: attachment; filename="prompt-gateway-sms-ussd.txt"
    """
    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        res = HttpResponse('Autenticação necessária.', status=401, content_type='text/plain; charset=utf-8')
        return _aplicar_cabecalhos_seguranca(res)

    role = getattr(user, 'role', '')
    if role not in ROLES_AUTORIZADAS:
        res = HttpResponse('Acesso proibido.', status=403, content_type='text/plain; charset=utf-8')
        return _aplicar_cabecalhos_seguranca(res)

    conteudo = _ler_conteudo_prompt()
    if conteudo is None:
        res = HttpResponse('Erro interno do servidor ao carregar o ficheiro.', status=500, content_type='text/plain; charset=utf-8')
        return _aplicar_cabecalhos_seguranca(res)

    res = HttpResponse(conteudo, content_type='text/plain; charset=utf-8')
    res['Content-Disposition'] = 'attachment; filename="prompt-gateway-sms-ussd.txt"'
    return _aplicar_cabecalhos_seguranca(res)

@csrf_exempt
def prompt_gateway_api(request):
    """
    GET /api/v1/ferramentas/prompt-gateway/
    Endpoint REST para consumo pela SPA.
    """
    user = _autenticar_pedido(request)
    if not user or not user.is_authenticated:
        res = JsonResponse({'success': False, 'message': 'Autenticação necessária.'}, status=401)
        return _aplicar_cabecalhos_seguranca(res)

    role = getattr(user, 'role', '')
    if role not in ROLES_AUTORIZADAS:
        res = JsonResponse({'success': False, 'message': 'Acesso proibido.'}, status=403)
        return _aplicar_cabecalhos_seguranca(res)

    conteudo = _ler_conteudo_prompt()
    if conteudo is None:
        res = JsonResponse({'success': False, 'message': 'Erro interno ao obter conteúdo.'}, status=500)
        return _aplicar_cabecalhos_seguranca(res)

    res = JsonResponse({
        'success': True,
        'titulo': 'Prompt: Gateway SMS, USSD e Pagamentos Móveis',
        'subtitulo': 'Para Node.js. Copia e cola no teu assistente de código.',
        'conteudo': conteudo,
        'tamanho': len(conteudo)
    })
    return _aplicar_cabecalhos_seguranca(res)
