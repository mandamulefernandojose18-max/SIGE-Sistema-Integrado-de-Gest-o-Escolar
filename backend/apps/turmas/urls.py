from django.urls import path, include
from common.routers import OptionalSlashRouter
from .views import TurmaViewSet, HorarioEscolarViewSet

router = OptionalSlashRouter()
router.register(r'horarios', HorarioEscolarViewSet, basename='turmas-horarios')
router.register(r'', TurmaViewSet, basename='turmas')

urlpatterns = [
    path('', include(router.urls)),
]
