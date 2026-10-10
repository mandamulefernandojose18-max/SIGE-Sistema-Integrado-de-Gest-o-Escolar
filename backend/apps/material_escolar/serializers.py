from rest_framework import serializers
from .models import MaterialEscolar
from apps.disciplinas.models import Disciplina

class MaterialEscolarSerializer(serializers.ModelSerializer):
    disciplina_nome = serializers.CharField(source='disciplina.nome', read_only=True, allow_null=True)
    disciplina_id = serializers.PrimaryKeyRelatedField(
        queryset=Disciplina.objects.all(),
        source='disciplina',
        required=False,
        allow_null=True
    )

    class Meta:
        model = MaterialEscolar
        fields = [
            'id', 'titulo', 'descricao', 'classe', 'disciplina', 'disciplina_id', 'disciplina_nome',
            'tipo', 'nome_arquivo', 'extensao', 'tamanho_bytes', 'tipo_mime',
            'conteudo_base64', 'arquivo_url', 'publicado_por', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'conteudo_base64': {'write_only': True}
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['createdAt'] = instance.created_at.isoformat() if instance.created_at else None
        ret['disciplina'] = {
            'id': str(instance.disciplina.id),
            'nome': instance.disciplina.nome
        } if instance.disciplina else None
        return ret

