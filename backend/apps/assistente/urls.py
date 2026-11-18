from django.urls import path
from .views import PerguntarView

urlpatterns = [
    path('perguntar/', PerguntarView.as_view(), name='assistente_perguntar'),
]
