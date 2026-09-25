from rest_framework import serializers
from .models import Plano, Escola, AssinaturaEscola

class PlanoSerializer(serializers.ModelSerializer):
    preco = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False)

    class Meta:
        model = Plano
        fields = '__all__'

class AssinaturaEscolaSerializer(serializers.ModelSerializer):
    plano_nome = serializers.CharField(source='plano.nome', read_only=True)
    valor = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False)
    valor_pago = serializers.DecimalField(source='valor', max_digits=12, decimal_places=2, coerce_to_string=False, read_only=True)

    class Meta:
        model = AssinaturaEscola
        fields = '__all__'

class EscolaSerializer(serializers.ModelSerializer):
    plano_nome = serializers.CharField(source='plano.nome', read_only=True)
    assinatura_ativa = serializers.SerializerMethodField()
    assinaturas = AssinaturaEscolaSerializer(many=True, read_only=True)
    _count = serializers.SerializerMethodField()

    class Meta:
        model = Escola
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_assinatura_ativa(self, obj):
        ass = obj.assinaturas.order_by('-data_fim').first()
        if ass:
            val = float(ass.valor) if ass.valor is not None else 0.0
            return {
                'id': str(ass.id),
                'plano': ass.plano.nome if ass.plano else 'MENSAL',
                'data_inicio': ass.data_inicio,
                'data_fim': ass.data_fim,
                'status': ass.status,
                'valor': val,
                'valor_pago': val
            }
        return None

    def get__count(self, obj):
        from apps.alunos.models import Aluno
        from apps.professores.models import Professor
        return {
            'alunos': Aluno.objects.filter(escola=obj).count(),
            'professores': Professor.objects.filter(escola=obj).count()
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.plano:
            data['plano_id'] = str(instance.plano.id)
            data['plano'] = {
                'id': str(instance.plano.id),
                'nome': instance.plano.nome,
                'preco': float(instance.plano.preco) if instance.plano.preco is not None else 0.0,
                'duracao_dias': instance.plano.duracao_dias
            }
        else:
            data['plano_id'] = None
            data['plano'] = None
        return data

