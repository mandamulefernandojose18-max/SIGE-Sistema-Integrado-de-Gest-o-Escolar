from django.contrib import admin
from django.urls import path, re_path, include
from django.http import JsonResponse
from apps.ferramentas.views import pagina_ia_prova
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

def health_check(request):
    return JsonResponse({
        'status': 'ok',
        'service': 'SIGE — Sistema Integrado de Gestão Escolar (Django REST Framework SaaS)',
        'version': '2.5.0',
        'build': '20261017_1200'
    })

api_v1_patterns = [
    re_path(r'^health/?', health_check, name='api_v1_health'),
    re_path(r'^auth/?', include('apps.accounts.urls')),
    re_path(r'^escola-admin/turmas/?', include('apps.turmas.urls')),
    re_path(r'^turmas/?', include('apps.turmas.urls')),
    re_path(r'^alunos/?', include('apps.alunos.urls')),
    re_path(r'^professores/?', include('apps.professores.urls')),
    re_path(r'^disciplinas/?', include('apps.disciplinas.urls')),
    re_path(r'^notas/?', include('apps.notas.urls')),
    re_path(r'^pautas/?', include('apps.pautas.urls')),
    re_path(r'^material-escolar/?', include('apps.material_escolar.urls')),
    re_path(r'^pagamentos/?', include('apps.pagamentos.urls')),
    re_path(r'^certificados/?', include('apps.certificados.urls')),
    re_path(r'^impressao/?', include('apps.documentos.urls')),
    re_path(r'^documentos/?', include('apps.documentos.urls')),
    re_path(r'^dashboard/?', include('apps.dashboard.urls')),
    re_path(r'^ferramentas/?', include('apps.ferramentas.urls')),
    path('', include('apps.tenants.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health', health_check, name='health_no_slash'),
    path('health/', health_check, name='health'),

    # Rotas diretas de Ferramentas /ferramentas/prompt-gateway
    re_path(r'^ferramentas/?', include('apps.ferramentas.urls')),

    # Página pública com as instruções para IA, aberta pelo QR Code das provas codificadas
    path('ia/', pagina_ia_prova, name='pagina_ia_geral'),
    path('ia/<str:codigo>/', pagina_ia_prova, name='pagina_ia_prova'),

    # API Versionada /api/v1/
    re_path(r'^api/v1/?', include(api_v1_patterns)),

    # OpenAPI Schema & Swagger UI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

