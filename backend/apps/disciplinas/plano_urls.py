from django.urls import path
from .plano_views import PlanoEstruturaView, PlanoClasseView, PlanoAreasView, PlanoAreaDetalheView, PlanoAreaDisciplinasView

urlpatterns = [
    path('estrutura/', PlanoEstruturaView.as_view(), name='plano_estrutura'),
    path('classe/', PlanoClasseView.as_view(), name='plano_classe'),
    path('areas/', PlanoAreasView.as_view(), name='plano_areas'),
    path('areas/<uuid:pk>/', PlanoAreaDetalheView.as_view(), name='plano_area_detalhe'),
    path('areas/<uuid:pk>/disciplinas/', PlanoAreaDisciplinasView.as_view(), name='plano_area_disciplinas'),
]
