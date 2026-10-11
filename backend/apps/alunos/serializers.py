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
    classe = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    area = serializers.CharField(required=False, default='Geral', allow_blank=True, allow_null=True)
    ano_ingresso = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    matricula = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    nuit = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Aluno
        fields = [
            'id', 'matricula', 'ano_ingresso', 'nome', 'apelido', 'classe', 'area', 'turma', 'turma_id', 'turma_nome', 'turma_grau',
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
        ano_ingresso = validated_data.get('ano_ingresso')
        turma = validated_data.get('turma')
        if not ano_ingresso and turma and getattr(turma, 'ano_letivo', None):
            validated_data['ano_ingresso'] = turma.ano_letivo
            ano_ingresso = turma.ano_letivo

        if turma:
            if getattr(turma, 'grau_ano', None):
                validated_data['classe'] = turma.grau_ano
            area_in = validated_data.get('area')
            if not area_in or str(area_in).strip().lower() in ['', 'geral', 'ensino geral', 'tronco comum', 'none']:
                if getattr(turma, 'area', None) and str(turma.area).strip().lower() not in ['', 'geral', 'ensino geral']:
                    validated_data['area'] = turma.area

        escola = validated_data.get('escola')
        validated_data['matricula'] = gerar_proxima_matricula(
            escola=escola,
            ano_ingresso=ano_ingresso,
            classe=validated_data.get('classe'),
            turma=turma,
            area=validated_data.get('area'),
        )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('matricula', None)
        turma = validated_data.get('turma')
        if turma:
            if getattr(turma, 'grau_ano', None):
                validated_data['classe'] = turma.grau_ano
            area_in = validated_data.get('area')
            if area_in is not None:
                if not area_in or str(area_in).strip().lower() in ['', 'geral', 'ensino geral', 'tronco comum', 'none']:
                    if getattr(turma, 'area', None) and str(turma.area).strip().lower() not in ['', 'geral', 'ensino geral']:
                        validated_data['area'] = turma.area
            elif getattr(turma, 'area', None) and str(turma.area).strip().lower() not in ['', 'geral', 'ensino geral']:
                if not instance.area or str(instance.area).strip().lower() in ['', 'geral', 'ensino geral']:
                    validated_data['area'] = turma.area
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['classe'] = instance.classe or (instance.turma.grau_ano if instance.turma else None)
        aluno_area = instance.area
        turma_area = instance.turma.area if instance.turma else None

        def is_especifica(a):
            return bool(a and str(a).strip().lower() not in ['', 'geral', 'ensino geral', 'tronco comum', 'none'])

        if is_especifica(aluno_area):
            area_final = aluno_area
        elif is_especifica(turma_area):
            area_final = turma_area
        else:
            cls_str = str(instance.classe or (instance.turma.grau_ano if instance.turma else '')).lower()
            if '11' in cls_str or '12' in cls_str:
                from apps.disciplinas.models import Disciplina
                disc_area = Disciplina.objects.filter(
                    escola=instance.escola,
                    classe__icontains='11' if '11' in cls_str else '12'
                ).exclude(area__in=['', 'Geral', 'Ensino Geral']).values_list('area', flat=True).first()
                area_final = disc_area or 'Ciências com Geografia'
            else:
                area_final = 'Ensino Geral'

        ret['area'] = area_final
        ret['grupo'] = area_final
        ret['turma_area'] = turma_area or area_final

        # Garantir que o código do aluno exibido segue sempre o formato oficial (ex: 0101S0001.12.01.2026.cg)
        from common.utils.geografia_mocambique import gerar_codigo_aluno_oficial
        ret['matricula'] = gerar_codigo_aluno_oficial(
            escola=instance.escola,
            classe=ret['classe'],
            turma=instance.turma,
            ano=instance.ano_ingresso,
            area=area_final,
        )

        if instance.turma:
            ret['turma'] = {
                'id': str(instance.turma.id),
                'nome': instance.turma.nome,
                'grau_ano': instance.turma.grau_ano,
                'turno': getattr(instance.turma, 'turno', ''),
                'area': getattr(instance.turma, 'area', 'Geral'),
            }
            ret['turma_id'] = str(instance.turma.id)
            ret['turma_nome'] = instance.turma.nome
            ret['turma_grau'] = instance.turma.grau_ano
        else:
            ret['turma'] = None
            ret['turma_id'] = None
            ret['turma_nome'] = None
            ret['turma_grau'] = None
        return ret

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
