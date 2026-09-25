from rest_framework import serializers
from .models import Aluno
from apps.turmas.serializers import TurmaSerializer

class AlunoSerializer(serializers.ModelSerializer):
    turma_nome = serializers.CharField(source='turma.nome', read_only=True, allow_null=True)
    turma_grau = serializers.CharField(source='turma.grau_ano', read_only=True, allow_null=True)

    class Meta:
        model = Aluno
        fields = [
            'id', 'matricula', 'nome', 'apelido', 'turma', 'turma_nome', 'turma_grau',
            'data_nascimento', 'genero', 'tipo_documento', 'numero_documento', 'nuit',
            'nacionalidade', 'provincia', 'distrito', 'pai', 'mae',
            'nome_responsavel', 'contato_responsavel', 'email_responsavel', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class TransferirAlunoSerializer(serializers.Serializer):
    turma_destino_id = serializers.UUIDField()
    motivo = serializers.CharField(required=False, allow_blank=True)
