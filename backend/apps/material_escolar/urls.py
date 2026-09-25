from django.urls import path, include
from common.routers import OptionalSlashRouter
from .views import MaterialEscolarViewSet, ClassesMaterialView

router = OptionalSlashRouter()
router.register(r'', MaterialEscolarViewSet, basename='material_escolar')

urlpatterns = [
    path('classes', ClassesMaterialView.as_view(), name='material_classes_no_slash'),
    path('classes/', ClassesMaterialView.as_view(), name='material_classes'),
    path('', include(router.urls)),
]
