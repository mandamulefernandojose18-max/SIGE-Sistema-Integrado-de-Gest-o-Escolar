from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MaterialEscolarViewSet, ClassesMaterialView

router = DefaultRouter()
router.register(r'', MaterialEscolarViewSet, basename='material_escolar')

urlpatterns = [
    path('classes', ClassesMaterialView.as_view(), name='material_classes_no_slash'),
    path('classes/', ClassesMaterialView.as_view(), name='material_classes'),
    path('', include(router.urls)),
]
