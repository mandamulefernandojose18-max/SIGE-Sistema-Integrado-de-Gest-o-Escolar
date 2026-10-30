from rest_framework import serializers
from .models import Professor, AlocacaoDocente
from apps.disciplinas.models import Disciplina
from apps.turmas.models import Turma

class AlocacaoDocenteSerializer(serializers.ModelSerializer):
    professor_nome = serializers.CharField(source='professor.nome', read_only=True)
    disciplina_nome = serializers.CharField(source='disciplina.nome', read_only=True)
    disciplina_codigo = serializers.CharField(source='disciplina.codigo', read_only=True)
    turma_nome = serializers.CharField(source='turma.nome', read_only=True)
    turma_grau = serializers.CharField(source='turma.grau_ano', read_only=True)
    turma_area = serializers.CharField(source='turma.area', read_only=True, allow_null=True)
    turma_turno = serializers.CharField(source='turma.turno', read_only=True, allow_null=True)
    turma_sala = serializers.CharField(source='turma.sala', read_only=True, allow_null=True)
    turma_ano_letivo = serializers.CharField(source='turma.ano_letivo', read_only=True, allow_null=True)
    professor_telefone = serializers.CharField(source='professor.telefone', read_only=True, allow_null=True)
    professor_especialidade = serializers.CharField(source='professor.especialidade', read_only=True, allow_null=True)
    director_turma_nome = serializers.CharField(source='turma.director_turma.nome', read_only=True, allow_null=True)

    class Meta:
        model = AlocacaoDocente
        fields = [
            'id', 'professor', 'professor_nome', 'disciplina', 'disciplina_nome',
            'disciplina_codigo', 'turma', 'turma_nome', 'turma_grau', 'turma_area',
            'turma_turno', 'turma_sala', 'turma_ano_letivo', 'professor_telefone', 'professor_especialidade',
            'director_turma_nome', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        turma = instance.turma
        if turma:
            data['turma'] = {
                'id': str(turma.id),
                'nome': turma.nome,
                'grau_ano': turma.grau_ano,
                'area': turma.area or 'Ensino Geral',
                'turno': turma.turno or 'MANHA',
                'sala': turma.sala or '',
                'ano_letivo': turma.ano_letivo or '2026',
                'director_turma_nome': turma.director_turma.nome if turma.director_turma else None,
            }
            data['turma_area'] = turma.area or 'Ensino Geral'
            data['turma_turno'] = turma.turno or 'MANHA'
        prof = instance.professor
        if prof:
            data['professor'] = {
                'id': str(prof.id),
                'codigo': prof.codigo or '',
                'nome': f"{prof.nome} {prof.apelido or ''}".strip(),
                'telefone': prof.telefone or '',
                'email': prof.email or '',
                'especialidade': prof.especialidade or prof.carreira or 'Ensino Geral',
            }
            data['professor_telefone'] = prof.telefone or ''
            data['professor_especialidade'] = prof.especialidade or prof.carreira or 'Ensino Geral'
        disc = instance.disciplina
        if disc:
            data['disciplina'] = {
                'id': str(disc.id),
                'nome': disc.nome,
                'codigo': disc.codigo or getattr(disc, 'abreviatura', '') or '',
                'carga_horaria': getattr(disc, 'carga_horaria', 0),
                'classe': getattr(disc, 'classe', ''),
                'area': getattr(disc, 'area', ''),
            }
            data['disciplina_carga_horaria'] = getattr(disc, 'carga_horaria', 0)
        return data

class ProfessorSerializer(serializers.ModelSerializer):
    codigo = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    alocacoes = AlocacaoDocenteSerializer(many=True, read_only=True)
    total_carga_alocada = serializers.SerializerMethodField()
    horas_normais = serializers.SerializerMethodField()
    horas_extras = serializers.SerializerMethodField()
    resumo_por_classe = serializers.SerializerMethodField()
    codigos_direccao_turma = serializers.SerializerMethodField()
    codigos_direccao_classe = serializers.SerializerMethodField()

    class Meta:
        model = Professor
        fields = [
            'id', 'codigo', 'nome', 'apelido', 'genero', 'email', 'telefone',
            'tipo_documento', 'numero_documento', 'nuit', 'nacionalidade',
            'provincia', 'distrito', 'carreira', 'especialidade',
            'carga_horaria_semanal', 'carga_maxima_por_classe', 'ativo',
            'total_carga_alocada', 'horas_normais', 'horas_extras', 'resumo_por_classe',
            'codigos_direccao_turma', 'codigos_direccao_classe',
            'alocacoes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_nuit(self, value):
        if value is None or str(value).strip() == '':
            return None
        import re
        nuit_str = str(value).strip()
        if not re.match(r'^\d{1,9}$', nuit_str):
            raise serializers.ValidationError("O NUIT do docente deve conter apenas números (no máximo 9 dígitos). Não aceita letras.")
        return nuit_str

    def validate_telefone(self, value):
        if value:
            import re
            tel_str = str(value).strip()
            if re.search(r'[a-zA-Z\u00C0-\u017F]', tel_str):
                raise serializers.ValidationError("O telefone do docente não pode aceitar letras. Insira apenas números.")
        return value

    def validate_carga_horaria_semanal(self, value):
        if value is not None:
            import re
            ch_str = str(value).strip()
            if re.search(r'[a-zA-Z\u00C0-\u017F]', ch_str):
                raise serializers.ValidationError("A carga horária deve ser um valor numérico.")
        return value

    def get_codigos_direccao_turma(self, obj):
        res = []
        for t in obj.turmas_como_director_turma.all():
            res.append({
                'turma_id': str(t.id),
                'turma_nome': t.nome,
                'grau_ano': t.grau_ano,
                'area': t.area,
                'codigo': getattr(t, 'codigo_director_turma', '') or '',
                'status_homologacao': getattr(t, 'dt_status_homologacao', 'NAO_DEFINIDO'),
                'nomeado_por': getattr(t, 'dt_nomeado_por', '') or '',
                'homologado_por': getattr(t, 'dt_homologado_por', '') or '',
            })
        return res

    def get_codigos_direccao_classe(self, obj):
        res = []
        vistos = set()
        for t in obj.turmas_como_director_classe.all():
            cod = getattr(t, 'codigo_director_classe', '') or ''
            chave = (t.grau_ano, t.ano_letivo, cod)
            if chave in vistos:
                continue
            vistos.add(chave)
            res.append({
                'turma_id': str(t.id),
                'grau_ano': t.grau_ano,
                'ano_letivo': t.ano_letivo,
                'codigo': cod,
                'status_homologacao': getattr(t, 'dc_status_homologacao', 'NAO_DEFINIDO'),
                'nomeado_por': getattr(t, 'dc_nomeado_por', '') or '',
                'homologado_por': getattr(t, 'dc_homologado_por', '') or '',
            })
        return res

    def get_total_carga_alocada(self, obj):
        total = 0
        for a in obj.alocacoes.all():
            if a.disciplina and getattr(a.disciplina, 'carga_horaria', None):
                total += a.disciplina.carga_horaria
        return total

    def get_horas_normais(self, obj):
        total = self.get_total_carga_alocada(obj)
        max_sem = obj.carga_horaria_semanal or 20
        return min(total, max_sem)

    def get_horas_extras(self, obj):
        total = self.get_total_carga_alocada(obj)
        max_sem = obj.carga_horaria_semanal or 20
        return max(0, total - max_sem)

    def get_resumo_por_classe(self, obj):
        resumo = {}
        max_por_classe = obj.carga_maxima_por_classe or {}
        for a in obj.alocacoes.all():
            turma = a.turma
            classe = (turma.grau_ano if turma else (a.disciplina.classe if a.disciplina else 'Geral')) or 'Geral'
            classe = classe.strip()
            if classe not in resumo:
                max_c = (
                    max_por_classe.get(classe) or
                    max_por_classe.get(classe.replace(' ', '')) or
                    obj.carga_horaria_semanal or 20
                )
                resumo[classe] = {
                    'classe': classe,
                    'carga_alocada': 0,
                    'carga_maxima': int(max_c),
                    'horas_normais': 0,
                    'horas_extras': 0,
                    'turmas': []
                }
            ch = a.disciplina.carga_horaria if (a.disciplina and getattr(a.disciplina, 'carga_horaria', None)) else 0
            resumo[classe]['carga_alocada'] += ch
            if turma:
                resumo[classe]['turmas'].append({
                    'turma_id': str(turma.id),
                    'turma_nome': turma.nome,
                    'area': turma.area or 'Geral',
                    'disciplina_nome': a.disciplina.nome if a.disciplina else '',
                    'carga_horaria': ch
                })

        for c_data in resumo.values():
            c_data['horas_normais'] = min(c_data['carga_alocada'], c_data['carga_maxima'])
            c_data['horas_extras'] = max(0, c_data['carga_alocada'] - c_data['carga_maxima'])

        return resumo

class CriarAlocacaoSerializer(serializers.Serializer):
    professor_id = serializers.UUIDField()
    disciplina_id = serializers.UUIDField()
    turma_id = serializers.UUIDField()
    carga_maxima_classe = serializers.IntegerField(required=False, allow_null=True)
