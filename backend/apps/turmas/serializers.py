from rest_framework import serializers
from .models import Turma

class TurmaSerializer(serializers.ModelSerializer):
    total_alunos = serializers.SerializerMethodField()
    director_turma_nome = serializers.CharField(source='director_turma.nome', read_only=True, allow_null=True)
    director_classe_nome = serializers.CharField(source='director_classe.nome', read_only=True, allow_null=True)

    class Meta:
        model = Turma
        fields = [
            'id', 'nome', 'grau_ano', 'turno', 'sala', 'ano_letivo', 'area',
            'director_turma', 'director_turma_nome',
            'director_classe', 'director_classe_nome',
            'total_alunos', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_alunos(self, obj):
        return obj.alunos.filter(status='ATIVO').count()
