"""Site público: formulário de contacto (validação, armadilha anti-robô, sem sessão) e dados públicos."""
import pytest
from rest_framework.test import APIClient

from apps.site_publico.models import MensagemContacto

VALIDO = {'nome': 'Visitante', 'email': 'visitante@example.org', 'assunto': 'Pedido de demonstração', 'mensagem': 'Gostaria de conhecer o sistema na nossa escola.'}


@pytest.mark.django_db
class TestSitePublico:
    def setup_method(self):
        self.c = APIClient()

    def test_info_publica_sem_autenticacao(self):
        r = self.c.get('/api/v1/site/info/')
        assert r.status_code == 200 and r.data['dominio'] == 'https://sigesaas.duckdns.org/' and set(r.data['contacto']) == {'email', 'telefone', 'endereco'}

    def test_contacto_guarda_mensagem(self):
        r = self.c.post('/api/v1/site/contacto/', VALIDO, format='json')
        assert r.status_code == 201 and MensagemContacto.objects.filter(email='visitante@example.org', lida=False).count() == 1

    def test_limite_de_mensagens_por_hora(self, monkeypatch):
        from rest_framework.throttling import ScopedRateThrottle
        monkeypatch.setattr(ScopedRateThrottle, 'THROTTLE_RATES', {'contacto': '2/hour'})
        codigos = [self.c.post('/api/v1/site/contacto/', VALIDO, format='json').status_code for _ in range(3)]
        assert codigos == [201, 201, 429]

    def test_armadilha_anti_robo_nao_guarda(self):
        r = self.c.post('/api/v1/site/contacto/', {**VALIDO, 'site': 'http://spam.example'}, format='json')
        assert r.status_code == 201 and not MensagemContacto.objects.exists()

    def test_html_nunca_e_guardado(self):
        # o filtro anti-XSS da API neutraliza "<" em "&lt;": nunca fica uma etiqueta HTML activa na base de dados
        self.c.post('/api/v1/site/contacto/', {**VALIDO, 'assunto': '<script>alert(1)</script> Olá'}, format='json')
        assert MensagemContacto.objects.exists() and all('<' not in m.assunto for m in MensagemContacto.objects.all())

    @pytest.mark.parametrize('alteracao', [{'email': 'invalido'}, {'mensagem': 'curta'}, {'nome': ''}])
    def test_dados_invalidos_sao_recusados(self, alteracao):
        r = self.c.post('/api/v1/site/contacto/', {**VALIDO, **alteracao}, format='json')
        assert r.status_code == 400 and not MensagemContacto.objects.exists()
