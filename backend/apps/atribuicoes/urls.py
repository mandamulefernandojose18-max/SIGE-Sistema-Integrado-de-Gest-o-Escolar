from django.urls import path

from .views import AtribuicoesView, AtribuicaoDetalheView, SugestoesView, ModeloDetalheView

urlpatterns = [
    path('sugestoes', SugestoesView.as_view()),
    path('sugestoes/', SugestoesView.as_view()),
    path('modelos/<uuid:pk>', ModeloDetalheView.as_view()),
    path('modelos/<uuid:pk>/', ModeloDetalheView.as_view()),
    path('<uuid:pk>', AtribuicaoDetalheView.as_view()),
    path('<uuid:pk>/', AtribuicaoDetalheView.as_view()),
    path('', AtribuicoesView.as_view()),
]
