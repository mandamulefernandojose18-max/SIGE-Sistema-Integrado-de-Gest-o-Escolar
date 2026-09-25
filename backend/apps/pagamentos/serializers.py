from rest_framework import serializers
from .models import Pagamento

class PagamentoSerializer(serializers.ModelSerializer):
    aluno_nome = serializers.CharField(source='aluno.nome', read_only=True)
    aluno_matricula = serializers.CharField(source='aluno.matricula', read_only=True)
    turma_nome = serializers.CharField(source='aluno.turma.nome', read_only=True, allow_null=True)

    class Meta:
        model = Pagamento
        fields = [
            'id', 'aluno', 'aluno_nome', 'aluno_matricula', 'turma_nome',
            'descricao', 'mes_referencia', 'valor', 'valor_pago', 'status',
            'data_vencimento', 'data_pagamento', 'metodo_pagamento', 'recibo_numero',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class LiquidarPagamentoSerializer(serializers.Serializer):
    valor_pago = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    metodo_pagamento = serializers.CharField(default='MPESA')

class GerarPagamentosTurmaSerializer(serializers.Serializer):
    turma_id = serializers.UUIDField()
    descricao = serializers.CharField()
    mes_referencia = serializers.CharField()
    valor = serializers.DecimalField(max_digits=12, decimal_places=2)
    data_vencimento = serializers.DateTimeField()
