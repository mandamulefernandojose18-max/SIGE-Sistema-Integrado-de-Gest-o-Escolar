from rest_framework import serializers
from .models import Disciplina


class DisciplinaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disciplina
        fields = '__all__'
        read_only_fields = ['id', 'escola', 'created_at', 'updated_at']
        extra_kwargs = {'nome': {'required': False}}

    def validate(self, attrs):
        """A disciplina só pode ser cadastrada numa Classe/Nível que exista no Plano Curricular da escola."""
        if self.instance is None and not attrs.get('catalogo') and not str(attrs.get('nome') or '').strip():
            raise serializers.ValidationError({'nome': 'Escolha a disciplina em "Todas Disciplinas de Ensino" ou indique o nome.'})
        attrs = self._validar_classe(attrs)
        cat = attrs.get('catalogo')
        if cat is not None:
            from common.utils.tenant import get_tenant_escola
            escola = get_tenant_escola(self.context.get('request')) or (self.instance.escola if self.instance else None)
            if escola and cat.escola_id != escola.id:
                raise serializers.ValidationError({'catalogo': 'Disciplina do catálogo não encontrada nesta escola.'})
            attrs['nome'] = cat.nome
        self._validar_codigo_unico(attrs)
        return attrs

    def _validar_codigo_unico(self, attrs):
        """O código é único por escola e ano lectivo: devolve 400 claro em vez de erro 500."""
        from common.utils.tenant import get_tenant_escola
        escola = get_tenant_escola(self.context.get('request')) or (self.instance.escola if self.instance else None)
        codigo = attrs.get('codigo', self.instance.codigo if self.instance else None)
        if not escola or not codigo:
            return
        ano = attrs.get('ano_letivo', self.instance.ano_letivo if self.instance else Disciplina._meta.get_field('ano_letivo').default)
        qs = Disciplina.objects.filter(escola=escola, codigo=codigo, ano_letivo=ano)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        outra = qs.first()
        if outra:
            raise serializers.ValidationError({
                'codigo': f"O código '{codigo}' já está a ser usado por '{outra.nome}' ({outra.classe}). Escolha outro código."
            })

    @staticmethod
    def _catalogo_para(escola, nome):
        """Liga a disciplina ao catálogo 'Todas Disciplinas de Ensino' (cria a entrada se ainda não existir)."""
        from .models import DisciplinaCatalogo
        from . import plano
        limpo = ' '.join(str(nome or '').split())
        return plano.achar_no_catalogo(escola, limpo) or DisciplinaCatalogo.objects.create(escola=escola, nome=limpo)

    def create(self, validated_data):
        escola = validated_data.get('escola')
        if escola is not None and validated_data.get('catalogo') is None:
            cat = self._catalogo_para(escola, validated_data.get('nome'))
            validated_data['catalogo'] = cat
        if validated_data.get('catalogo') is not None:
            validated_data['nome'] = validated_data['catalogo'].nome
        return super().create(validated_data)

    def _validar_classe(self, attrs):
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
        if validated_data.get('catalogo') is None and 'nome' in validated_data \
                and ' '.join(validated_data['nome'].split()).lower() != (instance.nome or '').lower():
            validated_data['catalogo'] = self._catalogo_para(instance.escola, validated_data['nome'])
            validated_data['nome'] = validated_data['catalogo'].nome
        classe_mudou = 'classe' in validated_data and validated_data['classe'] != instance.classe
        if classe_mudou:
            instance.vinculos_area.all().delete()
            validated_data.setdefault('area', 'Geral')
        return super().update(instance, validated_data)
