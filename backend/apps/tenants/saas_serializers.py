from rest_framework import serializers
from .models import Escola, SaasPlano, SaasAssinatura, SaasFatura, SaasPagamento, SaasLogAssinatura, SaasCoordenadasPagamento


class SaasPlanoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaasPlano
        fields = '__all__'


class SaasAssinaturaSerializer(serializers.ModelSerializer):
    plano_detalhes = SaasPlanoSerializer(source='plano', read_only=True)
    instituicao_nome = serializers.CharField(source='instituicao.nome', read_only=True)
    instituicao_codigo = serializers.CharField(source='instituicao.codigo_escola', read_only=True)
    instituicao_nuit = serializers.CharField(source='instituicao.nif_cnpj', read_only=True)
    instituicao_provincia = serializers.CharField(source='instituicao.provincia', read_only=True)
    instituicao_status = serializers.CharField(source='instituicao.status', read_only=True)
    instituicao_bloqueada_manualmente = serializers.BooleanField(source='instituicao.bloqueada_manualmente', read_only=True)
    modo_controlo = serializers.SerializerMethodField()

    class Meta:
        model = SaasAssinatura
        fields = '__all__'

    def get_modo_controlo(self, obj):
        if getattr(obj.instituicao, 'bloqueada_manualmente', False):
            return 'manual'
        return 'automatico'


class SaasFaturaSerializer(serializers.ModelSerializer):
    instituicao_nome = serializers.CharField(source='instituicao.nome', read_only=True)
    data_limite_efectiva = serializers.SerializerMethodField()
    total_devido = serializers.SerializerMethodField()
    saldo_devedor = serializers.SerializerMethodField()

    class Meta:
        model = SaasFatura
        fields = '__all__'

    def get_data_limite_efectiva(self, obj):
        from .saas_services import calcular_data_limite_efectiva_python
        return calcular_data_limite_efectiva_python(obj)

    def get_total_devido(self, obj):
        return float(obj.valor + obj.multa_aplicada)

    def get_saldo_devedor(self, obj):
        total = obj.valor + obj.multa_aplicada
        return float(max(0, total - obj.valor_pago))


class SaasPagamentoSerializer(serializers.ModelSerializer):
    instituicao_nome = serializers.CharField(source='instituicao.nome', read_only=True)
    numero_fatura = serializers.CharField(source='fatura.numero_fatura', read_only=True)
    fatura_periodo = serializers.SerializerMethodField()

    class Meta:
        model = SaasPagamento
        fields = '__all__'

    def get_fatura_periodo(self, obj):
        if obj.fatura:
            return f"{obj.fatura.periodo_inicio.strftime('%d/%m/%Y')} a {obj.fatura.periodo_fim.strftime('%d/%m/%Y')}"
        return ''


class SaasLogAssinaturaSerializer(serializers.ModelSerializer):
    instituicao_nome = serializers.CharField(source='instituicao.nome', read_only=True)

    class Meta:
        model = SaasLogAssinatura
        fields = '__all__'


class SaasCoordenadasPagamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaasCoordenadasPagamento
        fields = [
            'id',
            'mpesa_numero', 'mpesa_titular',
            'emola_numero', 'emola_titular',
            'bim_conta', 'bim_nib', 'bim_titular',
            'bci_conta', 'bci_nib', 'bci_titular',
            'nuit_entidade', 'instrucoes_adicionais',
            'updated_at'
        ]

    def validate_nuit_entidade(self, value):
        if value:
            import re
            nuit_str = str(value).strip()
            if not re.match(r'^\d{1,9}$', nuit_str):
                raise serializers.ValidationError("O NUIT da entidade deve conter apenas números (no máximo 9 dígitos). Não aceita letras.")
            return nuit_str
        return value

    def validate(self, attrs):
        import re
        if 'nuit_entidade' in attrs and attrs.get('nuit_entidade'):
            nuit_str = str(attrs['nuit_entidade']).strip()
            if not re.match(r'^\d{1,9}$', nuit_str):
                raise serializers.ValidationError({"nuit_entidade": "O NUIT da entidade deve conter apenas números (no máximo 9 dígitos). Não aceita letras."})
            attrs['nuit_entidade'] = nuit_str

        campos_telefone = ['mpesa_numero', 'emola_numero']
        for campo in campos_telefone:
            if campo in attrs and attrs.get(campo):
                if re.search(r'[a-zA-Z\u00C0-\u017F]', str(attrs[campo])):
                    raise serializers.ValidationError({campo: f"O campo {campo} não pode aceitar letras. Insira apenas números."})

        campos_bancarios = ['bim_conta', 'bim_nib', 'bci_conta', 'bci_nib']
        for campo in campos_bancarios:
            if campo in attrs and attrs.get(campo):
                if re.search(r'[a-zA-Z\u00C0-\u017F]', str(attrs[campo])):
                    raise serializers.ValidationError({campo: f"O campo {campo} deve conter apenas números e não pode aceitar letras."})

        return super().validate(attrs)
