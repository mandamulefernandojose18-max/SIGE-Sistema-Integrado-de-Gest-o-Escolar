from django.urls import path, include
from common.routers import OptionalSlashRouter
from .views import MaterialEscolarViewSet, ClassesMaterialView, DisciplinasAlunoView

router = OptionalSlashRouter()
router.register(r'', MaterialEscolarViewSet, basename='material_escolar')

urlpatterns = [
    path('classes', ClassesMaterialView.as_view(), name='material_classes_no_slash'),
    path('classes/', ClassesMaterialView.as_view(), name='material_classes'),
    path('disciplinas-aluno', DisciplinasAlunoView.as_view(), name='material_disciplinas_aluno_no_slash'),
    path('disciplinas-aluno/', DisciplinasAlunoView.as_view(), name='material_disciplinas_aluno'),
    path('', include(router.urls)),
]
