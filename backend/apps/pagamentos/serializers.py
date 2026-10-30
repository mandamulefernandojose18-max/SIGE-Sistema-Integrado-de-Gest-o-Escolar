from rest_framework import serializers
from .models import Pagamento, PlanoPagamentoEscola
from apps.alunos.models import Aluno


class PlanoPagamentoEscolaSerializer(serializers.ModelSerializer):
    escola_nome = serializers.CharField(source='escola.nome', read_only=True)
    periodicidade_display = serializers.CharField(source='get_periodicidade_display', read_only=True)
    total_faturas = serializers.SerializerMethodField()

    class Meta:
        model = PlanoPagamentoEscola
        fields = [
            'id', 'escola', 'escola_nome', 'nome', 'descricao', 'valor',
            'periodicidade', 'periodicidade_display', 'dia_vencimento_padrao',
            'multa_atraso_percentual', 'multa_atraso_fixo', 'ativo',
            'total_faturas', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'escola', 'created_at', 'updated_at']

    def get_total_faturas(self, obj):
        return obj.pagamentos.count()


class PagamentoSerializer(serializers.ModelSerializer):
    aluno_nome = serializers.CharField(source='aluno.nome', read_only=True)
    aluno_matricula = serializers.CharField(source='aluno.matricula', read_only=True)
    turma_nome = serializers.CharField(source='aluno.turma.nome', read_only=True, allow_null=True)
    plano_nome = serializers.CharField(source='plano_pagamento.nome', read_only=True, allow_null=True)
    aluno_id = serializers.PrimaryKeyRelatedField(
        queryset=Aluno.objects.all(),
        source='aluno',
        required=False
    )
    plano_pagamento_id = serializers.PrimaryKeyRelatedField(
        queryset=PlanoPagamentoEscola.objects.all(),
        source='plano_pagamento',
        required=False,
        allow_null=True
    )

    class Meta:
        model = Pagamento
        fields = [
            'id', 'aluno', 'aluno_id', 'aluno_nome', 'aluno_matricula', 'turma_nome',
            'plano_pagamento', 'plano_pagamento_id', 'plano_nome',
            'descricao', 'mes_referencia', 'valor', 'valor_pago', 'status',
            'data_vencimento', 'data_pagamento', 'metodo_pagamento', 'recibo_numero',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'aluno': {'required': False}
        }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        aluno = attrs.get('aluno') or (self.instance.aluno if self.instance else None)
        mes_referencia = attrs.get('mes_referencia') or (self.instance.mes_referencia if self.instance else None)
        status_val = attrs.get('status') or (self.instance.status if self.instance else 'PENDENTE')

        if aluno and mes_referencia and status_val != 'CANCELADO':
            qs = Pagamento.objects.filter(
                aluno=aluno,
                mes_referencia=mes_referencia
            ).exclude(status='CANCELADO')
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("A factura já foi gerada no sistema.")
        return attrs

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        al = instance.aluno
        ret['aluno'] = {
            'id': str(al.id),
            'nome': al.nome,
            'apelido': al.apelido or '',
            'matricula': al.matricula,
            'turma': {
                'id': str(al.turma.id),
                'nome': al.turma.nome,
                'grau_ano': al.turma.grau_ano
            } if getattr(al, 'turma', None) else None
        } if al else None
        if instance.plano_pagamento:
            ret['plano'] = {
                'id': str(instance.plano_pagamento.id),
                'nome': instance.plano_pagamento.nome,
                'valor': float(instance.plano_pagamento.valor),
                'periodicidade': instance.plano_pagamento.periodicidade
            }
        else:
            ret['plano'] = None
        return ret

class LiquidarPagamentoSerializer(serializers.Serializer):
    valor_pago = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    metodo_pagamento = serializers.CharField(default='MPESA')
    telefone = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    referencia = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')

class GerarPagamentosTurmaSerializer(serializers.Serializer):
    turma_id = serializers.UUIDField()
    plano_id = serializers.UUIDField(required=False, allow_null=True)
    descricao = serializers.CharField()
    mes_referencia = serializers.CharField()
    valor = serializers.DecimalField(max_digits=12, decimal_places=2)
    data_vencimento = serializers.DateField()



from .models import TransacaoFinanceira, FolhaSalario, ItemPatrimonio

class TransacaoFinanceiraSerializer(serializers.ModelSerializer):
    registado_por_nome = serializers.CharField(source='registado_por.nome', read_only=True, default='')
    aprovado_por_nome = serializers.CharField(source='aprovado_por.nome', read_only=True, default='')

    class Meta:
        model = TransacaoFinanceira
        fields = [
            'id', 'escola', 'tipo', 'categoria', 'descricao', 'valor',
            'data', 'forma_pagamento', 'numero_documento', 'status_aprovacao',
            'registado_por', 'registado_por_nome', 'aprovado_por', 'aprovado_por_nome',
            'data_aprovacao', 'observacoes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class FolhaSalarioSerializer(serializers.ModelSerializer):
    processado_por_nome = serializers.CharField(source='processado_por.nome', read_only=True, default='')
    aprovado_por_nome = serializers.CharField(source='aprovado_por.nome', read_only=True, default='')

    class Meta:
        model = FolhaSalario
        fields = [
            'id', 'escola', 'funcionario_nome', 'funcionario_cargo', 'professor',
            'mes', 'ano', 'salario_base', 'subsidios', 'descontos', 'salario_liquido',
            'status', 'processado_por', 'processado_por_nome', 'aprovado_por', 'aprovado_por_nome',
            'data_pagamento', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class ItemPatrimonioSerializer(serializers.ModelSerializer):
    registado_por_nome = serializers.CharField(source='registado_por.nome', read_only=True, default='')
    homologado_por_nome = serializers.CharField(source='homologado_por.nome', read_only=True, default='')

    class Meta:
        model = ItemPatrimonio
        fields = [
            'id', 'escola', 'codigo', 'nome', 'categoria', 'sala_localizacao',
            'quantidade', 'estado_conservacao', 'valor_estimado', 'status_validacao',
            'registado_por', 'registado_por_nome', 'homologado_por', 'homologado_por_nome',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
