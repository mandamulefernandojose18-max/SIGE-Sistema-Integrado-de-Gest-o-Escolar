from rest_framework import serializers
from .models import Turma
from apps.professores.models import Professor

class TurmaSerializer(serializers.ModelSerializer):
    total_alunos = serializers.SerializerMethodField()
    _count = serializers.SerializerMethodField()
    director_turma_nome = serializers.CharField(source='director_turma.nome', read_only=True, allow_null=True)
    director_classe_nome = serializers.CharField(source='director_classe.nome', read_only=True, allow_null=True)
    director_turma_id = serializers.PrimaryKeyRelatedField(
        source='director_turma',
        queryset=Professor.objects.all(),
        required=False,
        allow_null=True
    )
    director_classe_id = serializers.PrimaryKeyRelatedField(
        source='director_classe',
        queryset=Professor.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Turma
        fields = [
            'id', 'nome', 'grau_ano', 'turno', 'sala', 'ano_letivo', 'area',
            'director_turma', 'director_turma_id', 'director_turma_nome',
            'director_classe', 'director_classe_id', 'director_classe_nome',
            'total_alunos', '_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_alunos(self, obj):
        return obj.alunos.filter(status='ATIVO').count()

    def get__count(self, obj):
        return {
            'alunos': obj.alunos.filter(status='ATIVO').count()
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.director_turma:
            data['director_turma'] = {
                'id': str(instance.director_turma.id),
                'nome': instance.director_turma.nome
            }
        if instance.director_classe:
            data['director_classe'] = {
                'id': str(instance.director_classe.id),
                'nome': instance.director_classe.nome
            }
        return data

