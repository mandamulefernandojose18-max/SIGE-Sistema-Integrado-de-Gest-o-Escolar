from django.urls import path, re_path

from . import views

urlpatterns = [
    path('catalogo/', views.catalogo_view),
    path('lista/', views.lista),
    path('criar/', views.criar),
    path('<str:pid>/', views.detalhe),
    path('<str:pid>/data/', views.alterar_data),
    path('<str:pid>/libertar/', views.libertar),
    path('<str:pid>/apagar/', views.apagar),
    path('<str:pid>/editar/', views.editar),
    path('<str:pid>/configurar/', views.configurar),
    path('<str:pid>/pagina/<int:n>.png', views.pagina_png),
    path('<str:pid>/previa/', views.previa),
    path('<str:pid>/gerar/', views.gerar),
    path('<str:pid>/gabarito-copias/', views.gabarito_copias),
    path('<str:pid>/conferir/', views.conferir),
    path('<str:pid>/guiao/', views.guiao_estado),
    path('<str:pid>/guiao/gerar/', views.guiao_gerar),
    path('<str:pid>/guiao/corrigir/', views.guiao_corrigir),
    path('<str:pid>/guiao/descarregar/', views.guiao_descarregar),
]
publico = [
    re_path(r'^ia/v/(?P<pid>[A-Z0-9]{8})/?$', views.verificar),
    re_path(r'^ia/v/(?P<pid>[A-Z0-9]{8})/(?P<serial>\d+)/?$', views.verificar),
    re_path(r'^ia/v/(?P<pid>[A-Z0-9]{8})/(?P<serial>\d+)/p(?P<n>\d+)/?$', views.verificar_pagina),
    re_path(r'^ia/v/(?P<pid>[A-Z0-9]{8})/(?P<serial>\d+)/q(?P<n>\d+)/?$', views.verificar_pergunta),
    re_path(r'^ia/v/(?P<pid>[A-Z0-9]{8})/(?P<tipo>prova|gabarito)\.pdf$', views.publica_pdf),
]