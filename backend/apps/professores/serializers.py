from rest_framework import serializers
from .models import Professor, AlocacaoDocente
from apps.disciplinas.models import Disciplina
from apps.turmas.models import Turma

class AlocacaoDocenteSerializer(serializers.ModelSerializer):
    professor_nome = serializers.CharField(source='professor.nome', read_only=True)
    disciplina_nome = serializers.CharField(source='disciplina.nome', read_only=True)
    disciplina_codigo = serializers.CharField(source='disciplina.codigo', read_only=True)
    turma_nome = serializers.CharField(source='turma.nome', read_only=True)
    turma_grau = serializers.CharField(source='turma.grau_ano', read_only=True)

    class Meta:
        model = AlocacaoDocente
        fields = [
            'id', 'professor', 'professor_nome', 'disciplina', 'disciplina_nome',
            'disciplina_codigo', 'turma', 'turma_nome', 'turma_grau', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class ProfessorSerializer(serializers.ModelSerializer):
    alocacoes = AlocacaoDocenteSerializer(many=True, read_only=True)

    class Meta:
        model = Professor
        fields = [
            'id', 'nome', 'apelido', 'genero', 'email', 'telefone',
            'tipo_documento', 'numero_documento', 'nuit', 'nacionalidade',
            'provincia', 'distrito', 'carreira', 'especialidade',
            'carga_horaria_semanal', 'ativo', 'alocacoes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class CriarAlocacaoSerializer(serializers.Serializer):
    professor_id = serializers.UUIDField()
    disciplina_id = serializers.UUIDField()
    turma_id = serializers.UUIDField()
