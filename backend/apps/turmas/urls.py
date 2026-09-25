from django.urls import path, include
from common.routers import OptionalSlashRouter
from .views import TurmaViewSet

router = OptionalSlashRouter()
router.register(r'', TurmaViewSet, basename='turmas')

urlpatterns = [
    path('', include(router.urls)),
]
