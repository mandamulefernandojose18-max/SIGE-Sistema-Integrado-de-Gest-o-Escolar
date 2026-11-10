from rest_framework import serializers
from .models import Disciplina


class DisciplinaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disciplina
        fields = '__all__'
        read_only_fields = ['id', 'escola', 'created_at', 'updated_at']

    def validate(self, attrs):
        """A disciplina só pode ser cadastrada numa Classe/Nível que exista no Plano Curricular da escola."""
        classe = attrs.get('classe')
        if classe is None:
            return attrs
        if self.instance is not None and classe == self.instance.classe:
            return attrs
        from common.utils.tenant import get_tenant_escola
        from . import plano
        escola = get_tenant_escola(self.context.get('request')) or (self.instance.escola if self.instance else None)
        if escola and plano.classes_configuradas(escola):
            oficial = plano.nome_classe_oficial(escola, classe)
            if not oficial:
                raise serializers.ValidationError({
                    'classe': f"A classe/nível '{classe}' não está cadastrada no Plano Curricular. Cadastre-a primeiro."
                })
            attrs['classe'] = oficial
        return attrs

    def update(self, instance, validated_data):
        classe_mudou = 'classe' in validated_data and validated_data['classe'] != instance.classe
        if classe_mudou:
            instance.vinculos_area.all().delete()
            validated_data.setdefault('area', 'Geral')
        return super().update(instance, validated_data)
