import base64
from rest_framework import serializers
from .models import Certificado
from apps.alunos.models import Aluno

class CertificadoSerializer(serializers.ModelSerializer):
    aluno_nome = serializers.CharField(source='aluno.nome', read_only=True)
    aluno_matricula = serializers.CharField(source='aluno.matricula', read_only=True)
    escola_nome = serializers.CharField(source='escola.nome', read_only=True)
    aluno_id = serializers.PrimaryKeyRelatedField(
        queryset=Aluno.objects.all(),
        source='aluno',
        required=False
    )

    class Meta:
        model = Certificado
        fields = '__all__'
        read_only_fields = ['id', 'escola', 'codigo_autenticidade', 'qrcode_data', 'created_at', 'emitido_em']
        extra_kwargs = {
            'aluno': {'required': False}
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['aluno'] = {
            'id': str(instance.aluno.id),
            'nome': instance.aluno.nome,
            'apelido': instance.aluno.apelido or '',
            'matricula': instance.aluno.matricula
        } if instance.aluno else None

        qr_val = ret.get('qrcode_data') or ''
        if qr_val and not str(qr_val).startswith('data:image/'):
            try:
                from apps.documentos.services.pdf_service import gerar_qr_code_image
                qr_buf = gerar_qr_code_image(str(qr_val))
                b64_img = base64.b64encode(qr_buf.getvalue()).decode('ascii')
                ret['qrcode_url'] = qr_val
                ret['qrcode_data'] = f"data:image/png;base64,{b64_img}"
            except Exception:
                pass
        return ret

