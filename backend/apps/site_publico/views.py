import logging
import re

from django.conf import settings
from django.db import DatabaseError, transaction
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MensagemContacto

logger = logging.getLogger(__name__)
CONTROLO = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


class ContactoSerializer(serializers.Serializer):
    nome = serializers.CharField(max_length=120)
    email = serializers.EmailField(max_length=254)
    assunto = serializers.CharField(max_length=160)
    mensagem = serializers.CharField(min_length=10, max_length=3000)
    site = serializers.CharField(required=False, allow_blank=True, max_length=200)   # armadilha anti-robô: tem de ficar vazio

    def validate(self, dados):
        for campo in ('nome', 'assunto', 'mensagem'):
            dados[campo] = CONTROLO.sub('', dados[campo]).strip()
            if '<' in dados[campo] and '>' in dados[campo]:
                raise serializers.ValidationError({campo: 'Não use código HTML nem marcas < >.'})
        return dados


class SiteInfoView(APIView):
    """GET /site/info/ — dados públicos do site (contactos oficiais definidos no servidor; vazios se não configurados)."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        c = getattr(settings, 'SITE_CONTACTO', {}) or {}
        return Response({'contacto': {'email': c.get('email', ''), 'telefone': c.get('telefone', ''), 'endereco': c.get('endereco', '')},
                         'dominio': 'https://sigesaas.duckdns.org/'})


class ContactoView(APIView):
    """POST /site/contacto/ — guarda a mensagem do formulário de contacto (público, limitado a poucas por hora)."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = 'contacto'

    def post(self, request):
        s = ContactoSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        if d.get('site'):                       # robô preencheu a armadilha: finge sucesso sem guardar
            return Response({'success': True}, status=201)
        try:
            with transaction.atomic():
                MensagemContacto.objects.create(nome=d['nome'], email=d['email'], assunto=d['assunto'], mensagem=d['mensagem'])
        except DatabaseError:
            # tabela em falta (migração por aplicar) ou base de dados indisponível: nunca um 500 sem explicação
            logger.exception('Contacto do site: não foi possível guardar a mensagem')
            return Response({'success': False, 'message': 'De momento não conseguimos receber a sua mensagem. Tente novamente dentro de instantes.'}, status=503)
        return Response({'success': True}, status=201)
