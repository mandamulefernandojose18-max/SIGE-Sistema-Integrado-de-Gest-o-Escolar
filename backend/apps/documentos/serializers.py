from rest_framework import serializers
from .models import CalendarioEscolar, ComunicadoEscolar, DocumentoCalendarioOficial

class CalendarioEscolarSerializer(serializers.ModelSerializer):
    criado_por_nome = serializers.CharField(source='criado_por.nome', read_only=True, default='')
    aprovado_por_nome = serializers.CharField(source='aprovado_por.nome', read_only=True, default='')
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    tem_documento = serializers.SerializerMethodField()

    class Meta:
        model = CalendarioEscolar
        fields = [
            'id', 'escola', 'titulo', 'tipo', 'tipo_display', 'data_inicio', 'data_fim',
            'trimestre', 'descricao', 'nome_documento', 'documento_tipo', 'documento_tamanho',
            'documento_base64', 'tem_documento', 'status_aprovacao', 'criado_por',
            'criado_por_nome', 'aprovado_por', 'aprovado_por_nome', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'documento_base64': {'write_only': True}
        }

    def get_tem_documento(self, obj):
        return bool(obj.documento_base64 or obj.nome_documento)


class DocumentoCalendarioOficialSerializer(serializers.ModelSerializer):
    publicado_por_nome = serializers.CharField(source='publicado_por.nome', read_only=True, default='')

    class Meta:
        model = DocumentoCalendarioOficial
        fields = [
            'id', 'escola', 'titulo', 'ano_lectivo', 'descricao', 'nome_arquivo',
            'extensao', 'tamanho_bytes', 'tipo_mime', 'conteudo_base64',
            'publicado_por', 'publicado_por_nome', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'conteudo_base64': {'write_only': True}
        }


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
