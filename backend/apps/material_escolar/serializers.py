from rest_framework import serializers
from .models import MaterialEscolar

class MaterialEscolarSerializer(serializers.ModelSerializer):
    disciplina_nome = serializers.CharField(source='disciplina.nome', read_only=True, allow_null=True)

    class Meta:
        model = MaterialEscolar
        fields = [
            'id', 'titulo', 'descricao', 'classe', 'disciplina', 'disciplina_nome',
            'tipo', 'nome_arquivo', 'extensao', 'tamanho_bytes', 'tipo_mime',
            'conteudo_base64', 'arquivo_url', 'publicado_por', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
