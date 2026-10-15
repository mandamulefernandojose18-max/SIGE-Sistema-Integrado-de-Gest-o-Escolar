from django.core.management.base import BaseCommand
from decimal import Decimal

from apps.tenants.models import Plano
from apps.accounts.models import Usuario

class Command(BaseCommand):
    help = 'Carga inicial limpa (Seed) do SIGE: apenas Planos do SaaS e SuperAdmin oficial (sem dados fictícios)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('[SEED] Configurando parâmetros essenciais do sistema...'))

        # 1. Planos oficiais do SaaS em Meticais (MZN)
        planos_dados = [
            {'nome': 'MENSAL', 'descricao': 'Plano Mensal - Licença básica', 'preco': Decimal('1500.00'), 'duracao_dias': 30, 'max_alunos': 300, 'max_professores': 25},
            {'nome': 'TRIMESTRAL', 'descricao': 'Plano Trimestral - Períodos letivos', 'preco': Decimal('4200.00'), 'duracao_dias': 90, 'max_alunos': 800, 'max_professores': 60},
            {'nome': 'SEMESTRAL', 'descricao': 'Plano Semestral com desconto', 'preco': Decimal('7800.00'), 'duracao_dias': 180, 'max_alunos': 1500, 'max_professores': 100},
            {'nome': 'ANUAL', 'descricao': 'Plano Anual Institucional - Suporte 24/7', 'preco': Decimal('14500.00'), 'duracao_dias': 365, 'max_alunos': 3000, 'max_professores': 200},
        ]
        for p in planos_dados:
            Plano.objects.update_or_create(
                nome=p['nome'],
                defaults=p
            )
        self.stdout.write(self.style.SUCCESS('[OK] Planos do SaaS configurados em MZN.'))

        # 2. SuperAdmin do SaaS
        super_admins = [
            {'email': 'mandamulefj.@sige.com', 'nome': 'Eng. Fernando Mandamule', 'pass': 'Deusamo8'},
            {'email': 'admin.master@sige.com', 'nome': 'Eng. Fernando Mandamule (Master)', 'pass': 'Deusamo8'},
        ]
        for sa in super_admins:
            u, created = Usuario.objects.get_or_create(
                email=sa['email'],
                defaults={'nome': sa['nome'], 'username': sa['email'], 'role': 'SUPERADMIN'}
            )
            u.nome = sa['nome']
            u.username = sa['email']
            u.role = 'SUPERADMIN'
            u.is_superuser = True
            u.is_staff = True
            u.escola = None  # SuperAdmin não pertence a uma escola específica (gerencia a plataforma)
            u.set_password(sa['pass'])
            u.save()
        self.stdout.write(self.style.SUCCESS('[OK] SuperAdmins configurados.'))

        self.stdout.write(self.style.SUCCESS('[OK] Inicialização concluída. Nenhum dado fictício foi inserido no sistema.'))
