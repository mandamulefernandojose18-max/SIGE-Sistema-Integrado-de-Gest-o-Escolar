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
    professor_nome = serializers.SerializerMethodField()
    turma_nome = serializers.CharField(source='turma.nome', read_only=True)
    disciplina_nome = serializers.SerializerMethodField()
    expirada = serializers.BooleanField(read_only=True)

    class Meta:
        model = PermissaoEdicaoNotas
        fields = '__all__'
        read_only_fields = ['id', 'escola', 'created_at', 'updated_at', 'expirada']

    def get_professor_nome(self, obj):
        if obj.professor:
            return obj.professor.nome
        return '(Todos os Docentes da Turma)'

    def get_disciplina_nome(self, obj):
        if obj.disciplina:
            return obj.disciplina.nome
        return '(Todas as Disciplinas)'


from .models import PlanoAulaSumario, OcorrenciaDisciplinar

class PlanoAulaSumarioSerializer(serializers.ModelSerializer):
    turma_nome = serializers.CharField(source='turma.nome', read_only=True)
    disciplina_nome = serializers.CharField(source='disciplina.nome', read_only=True)
    professor_nome = serializers.CharField(source='professor.nome', read_only=True)

    class Meta:
        model = PlanoAulaSumario
        fields = [
            'id', 'escola', 'turma', 'turma_nome', 'disciplina', 'disciplina_nome',
            'professor', 'professor_nome', 'numero_aula', 'data', 'tempo_aula',
            'unidade_tematica', 'tema', 'sumario', 'objetivos', 'tarefa_casa',
            'status_validacao', 'observacoes_dap', 'validado_por', 'data_validacao',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class OcorrenciaDisciplinarSerializer(serializers.ModelSerializer):
    aluno_nome = serializers.CharField(source='aluno.nome_completo', read_only=True)
    aluno_matricula = serializers.CharField(source='aluno.matricula', read_only=True)
    turma_nome = serializers.CharField(source='turma.nome', read_only=True, default='')
    autor_nome = serializers.CharField(source='autor.nome', read_only=True, default='')

    class Meta:
        model = OcorrenciaDisciplinar
        fields = [
            'id', 'escola', 'aluno', 'aluno_nome', 'aluno_matricula',
            'turma', 'turma_nome', 'autor', 'autor_nome', 'data',
            'gravidade', 'descricao', 'medida_tomada', 'notificar_encarregado',
            'status_validacao', 'parecer_dap', 'validado_por',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
