from rest_framework import serializers
from .models import Nota, PermissaoEdicaoNotas

class NotaSerializer(serializers.ModelSerializer):
    aluno_nome = serializers.CharField(source='aluno.nome', read_only=True)
    aluno_matricula = serializers.CharField(source='aluno.matricula', read_only=True)
    disciplina_nome = serializers.CharField(source='disciplina.nome', read_only=True)

    class Meta:
        model = Nota
        fields = '__all__'
        read_only_fields = ['id', 'escola', 'created_at', 'updated_at']

class SalvarNotasBulkSerializer(serializers.Serializer):
    turma_id = serializers.UUIDField()
    disciplina_id = serializers.UUIDField()
    periodo = serializers.CharField()
    notas = serializers.ListField(child=serializers.DictField())

class PermissaoEdicaoNotasSerializer(serializers.ModelSerializer):
    professor_nome = serializers.CharField(source='professor.nome', read_only=True)
    turma_nome = serializers.CharField(source='turma.nome', read_only=True)
    disciplina_nome = serializers.CharField(source='disciplina.nome', read_only=True)

    class Meta:
        model = PermissaoEdicaoNotas
        fields = '__all__'
        read_only_fields = ['id', 'escola', 'created_at', 'updated_at']
