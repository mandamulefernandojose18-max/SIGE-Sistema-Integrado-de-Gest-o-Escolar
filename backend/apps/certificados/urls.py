from django.urls import path, include
from common.routers import OptionalSlashRouter
from .views import CertificadoViewSet, VerificarCertificadoView, CarimboConfigView, CarimbarFicheiroView

router = OptionalSlashRouter()
router.register(r'', CertificadoViewSet, basename='certificados')

urlpatterns = [
    path('carimbar', CarimbarFicheiroView.as_view(), name='carimbar_ficheiro_no_slash'),
    path('carimbar/', CarimbarFicheiroView.as_view(), name='carimbar_ficheiro'),
    path('carimbo', CarimboConfigView.as_view(), name='carimbo_config_no_slash'),
    path('carimbo/', CarimboConfigView.as_view(), name='carimbo_config'),
    path('verificar/<str:codigo>', VerificarCertificadoView.as_view(), name='verificar_certificado_no_slash'),
    path('verificar/<str:codigo>/', VerificarCertificadoView.as_view(), name='verificar_certificado'),
    path('', include(router.urls)),
]

