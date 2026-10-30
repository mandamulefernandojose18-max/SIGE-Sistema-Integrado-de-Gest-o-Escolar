from rest_framework import serializers
from .models import CalendarioEscolar, ComunicadoEscolar

class CalendarioEscolarSerializer(serializers.ModelSerializer):
    criado_por_nome = serializers.CharField(source='criado_por.nome', read_only=True, default='')
    aprovado_por_nome = serializers.CharField(source='aprovado_por.nome', read_only=True, default='')
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = CalendarioEscolar
        fields = [
            'id', 'escola', 'titulo', 'tipo', 'tipo_display', 'data_inicio', 'data_fim',
            'trimestre', 'descricao', 'status_aprovacao', 'criado_por', 'criado_por_nome',
            'aprovado_por', 'aprovado_por_nome', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class ComunicadoEscolarSerializer(serializers.ModelSerializer):
    autor_nome = serializers.CharField(source='autor.nome', read_only=True, default='')
    aprovado_por_nome = serializers.CharField(source='aprovado_por.nome', read_only=True, default='')
    publico_alvo_display = serializers.CharField(source='get_publico_alvo_display', read_only=True)

    class Meta:
        model = ComunicadoEscolar
        fields = [
            'id', 'escola', 'titulo', 'conteudo', 'publico_alvo', 'publico_alvo_display',
            'prioridade', 'status', 'aprovado_pelo_director', 'autor', 'autor_nome',
            'aprovado_por', 'aprovado_por_nome', 'data_publicacao', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'data_publicacao', 'created_at', 'updated_at']
