import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production' if os.environ.get('SIGE_ENV') == 'production' else 'config.settings.development')
django.setup()

from apps.tenants.models import Escola, Plano, AssinaturaEscola
from apps.accounts.models import Usuario
from apps.turmas.models import Turma
from apps.disciplinas.models import Disciplina
from apps.alunos.models import Aluno
from apps.professores.models import Professor, AlocacaoDocente
from apps.notas.models import Nota
from apps.pagamentos.models import Pagamento
from apps.material_escolar.models import MaterialEscolar
from apps.certificados.models import Certificado

print("=" * 80)
print("INVENTÁRIO COMPLETO E DETALHADO - DATAS E CAMPOS")
print("=" * 80)

print("\n--- ESCOLAS ---")
for e in Escola.objects.all():
    print(f"ID: {e.id}")
    print(f"  Nome: {e.nome}")
    print(f"  NIF: {e.nif_cnpj} | Email: {e.email} | Telefone: {e.telefone}")
    print(f"  Data Adesão: {e.data_adesao}")
    print(f"  Diretor: '{e.director_nome}' | DAP: '{e.dap_nome}' | Secr: '{e.chefe_secretaria_nome}'")
    print(f"  Código: {e.codigo_escola} | Prov: {e.provincia} | Dist: {e.distrito}")
    ass = AssinaturaEscola.objects.filter(escola=e).first()
    if ass:
        print(f"  Assinatura: Plano {ass.plano.nome} | Fim: {ass.data_fim} | Status: {ass.status}")

print("\n--- USUÁRIOS ---")
for u in Usuario.objects.all().order_by('role', 'email'):
    esc_nome = u.escola.nome if u.escola else "Sem Escola"
    print(f"  [{u.role}] {u.email} | Nome: '{u.nome}' | Escola: {esc_nome} | Cod: {u.codigo_acesso} | Ingressou: {u.date_joined}")

print("\n--- DISCIPLINAS POR ESCOLA ---")
for d in Disciplina.objects.all():
    notas_count = Nota.objects.filter(disciplina=d).count()
    aloc_count = AlocacaoDocente.objects.filter(disciplina=d).count()
    print(f"  {d.escola.nome} | {d.codigo} - {d.nome} ({d.classe}) | Notas: {notas_count} | Alocações: {aloc_count} | Criado: {d.created_at}")

print("=" * 80)
