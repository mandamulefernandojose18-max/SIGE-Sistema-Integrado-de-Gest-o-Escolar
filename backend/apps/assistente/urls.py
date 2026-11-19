from django.urls import path
from .views import AlertasView, EducandosView, FeedbackView, PerguntarView, SugestoesView

urlpatterns = [
    path('perguntar/', PerguntarView.as_view(), name='assistente_perguntar'),
    path('feedback/', FeedbackView.as_view(), name='assistente_feedback'),
    path('sugestoes/', SugestoesView.as_view(), name='assistente_sugestoes'),
    path('educandos/', EducandosView.as_view(), name='assistente_educandos'),
    path('alertas/', AlertasView.as_view(), name='assistente_alertas'),
]
