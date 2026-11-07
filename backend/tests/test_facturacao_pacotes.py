import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

from apps.tenants.models import Escola, Pacote, SaasPlano, SaasAssinatura, SaasFatura
from apps.tenants.pacotes import PACOTES_PADRAO, DESCONTOS_PADRAO
from apps.tenants.saas_middleware import limpar_cache_assinatura
from apps.tenants.saas_services import (
    executar_rotina_diaria_saas_python, valor_fatura_periodo, preco_mensal_contratado,
    usa_preco_do_pacote, calcular_tempo_correspondente_valor,
)


def _pacote(codigo):
    dados = next(p for p in PACOTES_PADRAO if p['codigo'] == codigo)
    obj, _ = Pacote.objects.get_or_create(
        codigo=codigo, defaults={**{k: v for k, v in dados.items() if k != 'codigo'}, 'descontos': dict(DESCONTOS_PADRAO)})
    return obj


@pytest.mark.django_db
class TestFacturacaoPorPacote:
    def setup_method(self):
        limpar_cache_assinatura()
        self.plano = SaasPlano.objects.create(nome='Plano Legado', preco_mensal=Decimal('1000'))
        self.hoje = timezone.localdate()

    def _escola(self, nif, pacote=None, por_pacote=False):
        return Escola.objects.create(nome=f'Escola {nif}', nif_cnpj=nif, email=f'{nif.lower()}@sige.mz',
                                     status='ATIVA', pacote=pacote, facturar_por_pacote=por_pacote)

    def _ass(self, escola, periodicidade):
        return SaasAssinatura.objects.create(
            instituicao=escola, plano=self.plano, periodicidade=periodicidade,
            proxima_fatura_em=self.hoje, estado='activa')

    def test_valores_por_periodo_seguem_a_tabela_do_pacote(self):
        esperado = {'mensal': 1500, 'trimestral': 4200, 'semestral': 7800, 'anual': 14500}
        for per, valor in esperado.items():
            ass = self._ass(self._escola(f'NIF_{per}', _pacote('pedagogico'), True), per)
            assert valor_fatura_periodo(ass) == Decimal(valor), per

    def test_rotina_gera_fatura_com_preco_do_pacote(self):
        ass = self._ass(self._escola('NIF_ROT', _pacote('completo'), True), 'trimestral')
        executar_rotina_diaria_saas_python()
        fat = SaasFatura.objects.get(assinatura=ass)
        assert fat.valor == Decimal('6700')

    def test_contrato_legado_mantem_preco_do_plano(self):
        # Escola com pacote atribuído mas SEM facturar por pacote: contratos antigos não sobem
        escola = self._escola('NIF_LEG', _pacote('completo'), False)
        ass = self._ass(escola, 'mensal')
        assert not usa_preco_do_pacote(ass)
        assert preco_mensal_contratado(ass) == Decimal('1000')
        executar_rotina_diaria_saas_python()
        assert SaasFatura.objects.get(assinatura=ass).valor == Decimal('1000')

    def test_legado_trimestral_continua_com_desconto_antigo(self):
        ass = self._ass(self._escola('NIF_LEG3', None, False), 'trimestral')
        assert valor_fatura_periodo(ass) == Decimal('1000') * 3 * Decimal('0.95')

    def test_adiantamento_usa_desconto_do_pacote(self):
        # 4200 MZN no trimestral Pedagógico = 3 meses (1500 x 3 x 0,9333 = 4200)
        pac = _pacote('pedagogico')
        t = calcular_tempo_correspondente_valor(Decimal('4200'), pac.preco_mensal, 'trimestral', desconto_pct=Decimal('6.67'))
        assert t['meses'] == 3 and t['dias'] == 0
