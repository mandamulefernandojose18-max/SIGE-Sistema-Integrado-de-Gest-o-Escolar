from rest_framework import serializers
from common.utils.tenant import get_tenant_escola
from .models import Atendimento, Comunicacao


def _escola_do_pedido(serializer):
    return get_tenant_escola(serializer.context.get('request'))


class _TenantValidacao:
    def validate_aluno(self, aluno):
        escola = _escola_do_pedido(self)
        if aluno is not None and (not escola or aluno.escola_id != escola.id):
            raise serializers.ValidationError('Aluno não pertence à sua escola.')
        return aluno


class AtendimentoSerializer(_TenantValidacao, serializers.ModelSerializer):
    aluno_nome = serializers.CharField(source='aluno.nome', read_only=True, default=None)

    class Meta:
        model = Atendimento
        fields = ['id', 'aluno', 'aluno_nome', 'assunto', 'descricao', 'canal', 'estado', 'prioridade',
                  'responsavel', 'criado_por', 'resolucao', 'resolvido_em', 'created_at', 'updated_at']
        read_only_fields = ['id', 'criado_por', 'resolvido_em', 'created_at', 'updated_at']

    def validate_responsavel(self, user):
        escola = _escola_do_pedido(self)
        if user is not None and (not escola or user.escola_id != escola.id):
            raise serializers.ValidationError('Responsável não pertence à sua escola.')
        return user


class ComunicacaoSerializer(_TenantValidacao, serializers.ModelSerializer):
    aluno_nome = serializers.CharField(source='aluno.nome', read_only=True)

    class Meta:
        model = Comunicacao
        fields = ['id', 'aluno', 'aluno_nome', 'tipo', 'canal', 'mensagem', 'destinatario', 'registado_por', 'created_at']
        read_only_fields = ['id', 'registado_por', 'created_at']
