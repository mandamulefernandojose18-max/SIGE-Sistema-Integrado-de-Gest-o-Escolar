from django.urls import path

from .views import ContactoView, SiteInfoView

urlpatterns = [
    path('info/', SiteInfoView.as_view(), name='site_info'),
    path('contacto/', ContactoView.as_view(), name='site_contacto'),
]
