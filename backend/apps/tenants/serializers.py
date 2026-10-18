from rest_framework import serializers
from .models import Plano, Escola, AssinaturaEscola, AnoLectivo

class PlanoSerializer(serializers.ModelSerializer):
    preco = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False)

    class Meta:
        model = Plano
        fields = '__all__'

class AssinaturaEscolaSerializer(serializers.ModelSerializer):
    plano_nome = serializers.CharField(source='plano.nome', read_only=True)
    valor = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False)
    valor_pago = serializers.DecimalField(source='valor', max_digits=12, decimal_places=2, coerce_to_string=False, read_only=True)

    class Meta:
        model = AssinaturaEscola
        fields = '__all__'

class EscolaSerializer(serializers.ModelSerializer):
    plano_nome = serializers.CharField(source='plano.nome', read_only=True)
    assinatura_ativa = serializers.SerializerMethodField()
    assinaturas = AssinaturaEscolaSerializer(many=True, read_only=True)
    _count = serializers.SerializerMethodField()
    logo_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    galeria_logos = serializers.JSONField(required=False, allow_null=True)
    imagem_fundo_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    galeria_fundos = serializers.JSONField(required=False, allow_null=True)
    codigo_gabinete_director = serializers.ReadOnlyField()
    codigo_direccao_pedagogica = serializers.ReadOnlyField()
    codigo_secretaria = serializers.ReadOnlyField()
    codigos_orgaos = serializers.SerializerMethodField()

    class Meta:
        model = Escola
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_codigos_orgaos(self, obj):
        from common.utils.geografia_mocambique import obter_codigos_orgaos_escola
        return obter_codigos_orgaos_escola(obj.codigo_escola or '')

    def to_internal_value(self, data):
        data = data.copy() if hasattr(data, 'copy') else dict(data)
        if 'email' in data and isinstance(data['email'], str):
            import re
            data['email'] = re.sub(r'\.+@', '@', data['email'].strip()).lower()
        return super().to_internal_value(data)

    def validate(self, attrs):
        logo_val = attrs.get('logo_url')
        if logo_val and str(logo_val).startswith('data:'):
            attrs['logo_base64'] = logo_val
            attrs['logo_url'] = None
        elif 'logo_url' in attrs and (logo_val == '' or logo_val is None):
            attrs['logo_url'] = None
            attrs['logo_base64'] = None
        galeria = attrs.get('galeria_logos')
        if galeria is not None and not isinstance(galeria, list):
            attrs['galeria_logos'] = []

        fundo_val = attrs.get('imagem_fundo_url')
        if fundo_val and str(fundo_val).startswith('data:'):
            attrs['imagem_fundo_base64'] = fundo_val
            attrs['imagem_fundo_url'] = None
        elif 'imagem_fundo_url' in attrs and (fundo_val == '' or fundo_val is None):
            attrs['imagem_fundo_url'] = None
            attrs['imagem_fundo_base64'] = None
        galeria_f = attrs.get('galeria_fundos')
        if galeria_f is not None and not isinstance(galeria_f, list):
            attrs['galeria_fundos'] = []
        cfg_exames = attrs.get('config_classes_exames')
        if cfg_exames is not None and not isinstance(cfg_exames, dict):
            attrs['config_classes_exames'] = {}
        return super().validate(attrs)

    def get_assinatura_ativa(self, obj):
        ass = obj.assinaturas.order_by('-data_fim').first()
        if ass:
            val = float(ass.valor) if ass.valor is not None else 0.0
            return {
                'id': str(ass.id),
                'plano': ass.plano.nome if ass.plano else 'MENSAL',
                'data_inicio': ass.data_inicio,
                'data_fim': ass.data_fim,
                'status': ass.status,
                'valor': val,
                'valor_pago': val
            }
        return None

    def get__count(self, obj):
        from apps.alunos.models import Aluno
        from apps.professores.models import Professor
        return {
            'alunos': Aluno.objects.filter(escola=obj).count(),
            'professores': Professor.objects.filter(escola=obj).count()
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['logo_url'] = instance.logo_url or instance.logo_base64 or None
        data['galeria_logos'] = instance.galeria_logos if isinstance(instance.galeria_logos, list) else []
        data['imagem_fundo_url'] = instance.imagem_fundo_url or instance.imagem_fundo_base64 or None
        data['galeria_fundos'] = instance.galeria_fundos if isinstance(instance.galeria_fundos, list) else []
        data['config_classes_exames'] = instance.config_classes_exames if isinstance(instance.config_classes_exames, dict) else {}
        data['codigo_gabinete_director'] = instance.codigo_gabinete_director
        data['codigo_direccao_pedagogica'] = instance.codigo_direccao_pedagogica
        data['codigo_secretaria'] = instance.codigo_secretaria
        if instance.plano:
            data['plano_id'] = str(instance.plano.id)
            data['plano'] = {
                'id': str(instance.plano.id),
                'nome': instance.plano.nome,
                'preco': float(instance.plano.preco) if instance.plano.preco is not None else 0.0,
                'duracao_dias': instance.plano.duracao_dias
            }
        else:
            data['plano_id'] = None
            data['plano'] = None
        return data

class AnoLectivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnoLectivo
        fields = ['id', 'ano', 'descricao', 'ativo', 'data_inicio', 'data_fim', 'created_at']


