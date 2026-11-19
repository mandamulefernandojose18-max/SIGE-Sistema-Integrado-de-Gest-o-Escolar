from rest_framework import serializers
from common.utils.tenant import get_tenant_escola
from apps.accounts.models import Usuario
from .models import Atendimento, Comunicacao, VinculoEncarregado


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


class VinculoEncarregadoSerializer(_TenantValidacao, serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    conta = serializers.CharField(source='usuario.email', read_only=True)

    class Meta:
        model = VinculoEncarregado
        fields = ['id', 'aluno', 'email', 'conta', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        escola = _escola_do_pedido(self)
        email = attrs.pop('email')
        usuario = Usuario.objects.filter(escola=escola, email__iexact=email, role='ENCARREGADO').first() if escola else None
        if not usuario:
            raise serializers.ValidationError({'email': 'Não existe uma conta de Encarregado de Educação com esse e-mail nesta escola.'})
        if VinculoEncarregado.objects.filter(escola=escola, usuario=usuario, aluno=attrs['aluno']).exists():
            raise serializers.ValidationError({'email': 'Esta conta já está associada a este aluno.'})
        attrs['usuario'] = usuario
        return attrs
