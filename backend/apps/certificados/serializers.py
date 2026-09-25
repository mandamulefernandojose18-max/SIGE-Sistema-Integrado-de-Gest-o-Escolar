from rest_framework import serializers
from .models import Certificado

class CertificadoSerializer(serializers.ModelSerializer):
    aluno_nome = serializers.CharField(source='aluno.nome', read_only=True)
    aluno_matricula = serializers.CharField(source='aluno.matricula', read_only=True)
    escola_nome = serializers.CharField(source='escola.nome', read_only=True)

    class Meta:
        model = Certificado
        fields = '__all__'
        read_only_fields = ['id', 'escola', 'created_at', 'emitido_em']
