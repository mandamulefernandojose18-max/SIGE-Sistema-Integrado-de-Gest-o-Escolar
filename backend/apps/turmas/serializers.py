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
    codigo_director_turma_previsto = serializers.SerializerMethodField()
    codigo_director_classe_previsto = serializers.SerializerMethodField()
    codigo_aluno_padrao_turma = serializers.SerializerMethodField()

    class Meta:
        model = Turma
        fields = [
            'id', 'nome', 'grau_ano', 'turno', 'sala', 'capacidade_maxima', 'ano_letivo', 'area',
            'director_turma', 'director_turma_id', 'director_turma_nome',
            'dt_status_homologacao', 'dt_nomeado_por', 'dt_data_nomeacao',
            'dt_homologado_por', 'dt_data_homologacao', 'codigo_director_turma', 'codigo_director_turma_previsto',
            'director_classe', 'director_classe_id', 'director_classe_nome',
            'dc_status_homologacao', 'dc_nomeado_por', 'dc_data_nomeacao',
            'dc_homologado_por', 'dc_data_homologacao', 'codigo_director_classe', 'codigo_director_classe_previsto',
            'codigo_aluno_padrao_turma',
            'total_alunos', '_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_alunos(self, obj):
        return obj.alunos.filter(status='ATIVO').count()

    def get__count(self, obj):
        return {
            'alunos': obj.alunos.filter(status='ATIVO').count()
        }

    def get_codigo_director_turma_previsto(self, obj):
        from common.utils.geografia_mocambique import gerar_codigo_director_turma
        return gerar_codigo_director_turma(obj)

    def get_codigo_director_classe_previsto(self, obj):
        from common.utils.geografia_mocambique import gerar_codigo_director_classe
        return gerar_codigo_director_classe(obj)

    def get_codigo_aluno_padrao_turma(self, obj):
        from common.utils.geografia_mocambique import gerar_codigo_aluno_oficial
        return gerar_codigo_aluno_oficial(
            escola=obj.escola,
            classe=obj.grau_ano,
            turma=obj,
            ano=obj.ano_letivo,
            area=obj.area,
        )

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
                'codigo': instance.director_turma.codigo or '',
                'nome': instance.director_turma.nome,
                'status_homologacao': instance.dt_status_homologacao,
                'codigo_funcao': instance.codigo_director_turma or '',
            }
        if instance.director_classe:
            data['director_classe'] = {
                'id': str(instance.director_classe.id),
                'codigo': instance.director_classe.codigo or '',
                'nome': instance.director_classe.nome,
                'status_homologacao': instance.dc_status_homologacao,
                'codigo_funcao': instance.codigo_director_classe or '',
            }
        return data



from .models import HorarioEscolar

class HorarioEscolarSerializer(serializers.ModelSerializer):
    turma_nome = serializers.CharField(source='turma.nome', read_only=True)
    disciplina_nome = serializers.CharField(source='disciplina.nome', read_only=True)
    professor_nome = serializers.CharField(source='professor.nome', read_only=True, allow_null=True)
    dia_semana_display = serializers.CharField(source='get_dia_semana_display', read_only=True)

    class Meta:
        model = HorarioEscolar
        fields = [
            'id', 'escola', 'turma', 'turma_nome', 'disciplina', 'disciplina_nome',
            'professor', 'professor_nome', 'dia_semana', 'dia_semana_display',
            'tempo', 'hora_inicio', 'hora_fim', 'sala', 'status_aprovacao',
            'elaborado_por', 'aprovado_por', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
