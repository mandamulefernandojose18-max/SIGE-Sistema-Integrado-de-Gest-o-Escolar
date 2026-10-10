from rest_framework import serializers
from .models import Turma
from apps.professores.models import Professor

class TurmaSerializer(serializers.ModelSerializer):
    total_alunos = serializers.SerializerMethodField()
    _count = serializers.SerializerMethodField()
    director_turma_nome = serializers.CharField(source='director_turma.nome', read_only=True, allow_null=True)
    director_classe_nome = serializers.CharField(source='director_classe.nome', read_only=True, allow_null=True)
    director_turma_id = serializers.PrimaryKeyRelatedField(
        source='director_turma',
        queryset=Professor.objects.all(),
        required=False,
        allow_null=True
    )
    director_classe_id = serializers.PrimaryKeyRelatedField(
        source='director_classe',
        queryset=Professor.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Turma
        fields = [
            'id', 'nome', 'grau_ano', 'turno', 'sala', 'capacidade_maxima', 'ano_letivo', 'area',
            'director_turma', 'director_turma_id', 'director_turma_nome',
            'director_classe', 'director_classe_id', 'director_classe_nome',
            'total_alunos', '_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_alunos(self, obj):
        return obj.alunos.filter(status='ATIVO').count()

    def get__count(self, obj):
        return {
            'alunos': obj.alunos.filter(status='ATIVO').count()
        }

    def validate(self, attrs):
        nome = attrs.get('nome') or (self.instance.nome if self.instance else None)
        grau_ano = attrs.get('grau_ano') or (self.instance.grau_ano if self.instance else None)
        ano_letivo = attrs.get('ano_letivo') or (self.instance.ano_letivo if self.instance else '2026')

        request = self.context.get('request')
        escola = None
        if request:
            escola = getattr(request, 'tenant', None) or getattr(request.user, 'escola', None)
            if not escola and getattr(request.user, 'role', '') == 'SUPERADMIN':
                escola_id = request.data.get('escola_id') or request.headers.get('X-Tenant-ID')
                if escola_id:
                    from apps.tenants.models import Escola
                    escola = Escola.objects.filter(id=escola_id).first()
        if not escola and self.instance:
            escola = self.instance.escola

        if escola and grau_ano and nome:
            from .utils import validar_unicidade_turma_na_classe
            from django.core.exceptions import ValidationError as DjangoValidationError
            try:
                validar_unicidade_turma_na_classe(
                    escola=escola,
                    grau_ano=grau_ano,
                    nome=nome,
                    ano_letivo=ano_letivo,
                    exclude_id=self.instance.id if self.instance else None
                )
            except DjangoValidationError as e:
                raise serializers.ValidationError({'nome': str(e.message)})

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.director_turma:
            data['director_turma'] = {
                'id': str(instance.director_turma.id),
                'nome': instance.director_turma.nome
            }
        if instance.director_classe:
            data['director_classe'] = {
                'id': str(instance.director_classe.id),
                'nome': instance.director_classe.nome
            }
        return data

