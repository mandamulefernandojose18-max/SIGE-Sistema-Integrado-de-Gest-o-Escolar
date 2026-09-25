from rest_framework import serializers
from .models import Aluno, gerar_proxima_matricula
from apps.turmas.models import Turma
from apps.turmas.serializers import TurmaSerializer

class AlunoSerializer(serializers.ModelSerializer):
    turma = serializers.PrimaryKeyRelatedField(
        queryset=Turma.objects.all(),
        required=False,
        allow_null=True
    )
    turma_id = serializers.PrimaryKeyRelatedField(
        source='turma',
        queryset=Turma.objects.all(),
        required=False,
        allow_null=True
    )
    turma_nome = serializers.CharField(source='turma.nome', read_only=True, allow_null=True)
    turma_grau = serializers.CharField(source='turma.grau_ano', read_only=True, allow_null=True)
    matricula = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    nuit = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Aluno
        fields = [
            'id', 'matricula', 'nome', 'apelido', 'turma', 'turma_id', 'turma_nome', 'turma_grau',
            'data_nascimento', 'genero', 'tipo_documento', 'numero_documento', 'nuit',
            'nacionalidade', 'provincia', 'distrito', 'pai', 'mae',
            'nome_responsavel', 'contato_responsavel', 'email_responsavel', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        if 'nuit' in attrs and (attrs['nuit'] is None or str(attrs['nuit']).strip() == ''):
            attrs['nuit'] = None
        return attrs

    def create(self, validated_data):
        if not validated_data.get('matricula'):
            escola = validated_data.get('escola')
            validated_data['matricula'] = gerar_proxima_matricula(escola=escola)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if not validated_data.get('matricula'):
            validated_data.pop('matricula', None)
        return super().update(instance, validated_data)

class TransferirAlunoSerializer(serializers.Serializer):
    turma_destino_id = serializers.UUIDField(required=False)
    novaTurmaId = serializers.UUIDField(required=False)
    motivo = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        dest = attrs.get('turma_destino_id') or attrs.get('novaTurmaId')
        if not dest:
            raise serializers.ValidationError({'turma_destino_id': 'A turma de destino é obrigatória.'})
        attrs['turma_destino_id'] = dest
        return attrs
