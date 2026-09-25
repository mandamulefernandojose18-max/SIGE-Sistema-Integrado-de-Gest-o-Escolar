from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DisciplinaViewSet, DisciplinaStatsView

router = DefaultRouter()
router.register(r'', DisciplinaViewSet, basename='disciplinas')

urlpatterns = [
    path('stats', DisciplinaStatsView.as_view(), name='disciplinas_stats_no_slash'),
    path('stats/', DisciplinaStatsView.as_view(), name='disciplinas_stats'),
    path('', include(router.urls)),
]
