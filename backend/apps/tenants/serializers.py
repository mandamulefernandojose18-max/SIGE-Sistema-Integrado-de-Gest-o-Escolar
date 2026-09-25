from rest_framework import serializers
from .models import Plano, Escola, AssinaturaEscola

class PlanoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plano
        fields = '__all__'

class AssinaturaEscolaSerializer(serializers.ModelSerializer):
    plano_nome = serializers.CharField(source='plano.nome', read_only=True)

    class Meta:
        model = AssinaturaEscola
        fields = '__all__'

class EscolaSerializer(serializers.ModelSerializer):
    plano_nome = serializers.CharField(source='plano.nome', read_only=True)
    assinatura_ativa = serializers.SerializerMethodField()

    class Meta:
        model = Escola
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_assinatura_ativa(self, obj):
        ass = obj.assinaturas.order_by('-data_fim').first()
        if ass:
            return {
                'id': str(ass.id),
                'plano': ass.plano.nome,
                'data_inicio': ass.data_inicio,
                'data_fim': ass.data_fim,
                'status': ass.status,
                'valor': str(ass.valor)
            }
        return None
