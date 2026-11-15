from django.core.management.base import BaseCommand
import os
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
        # A senha NUNCA fica no código. Regras:
        #  - conta nova: senha inicial vem de SUPERADMIN_PASSWORD; sem ela, a conta fica sem senha utilizável
        #    (defina SUPERADMIN_PASSWORD no .env e reinicie, ou use `manage.py changepassword`);
        #  - conta existente: a senha só é alterada se SUPERADMIN_PASSWORD estiver definida (rotação explícita).
        #    Sem a variável, o arranque do contentor NÃO repõe nenhuma senha.
        senha_env = os.environ.get('SUPERADMIN_PASSWORD', '').strip()
        if senha_env and len(senha_env) < 12:
            self.stdout.write(self.style.WARNING('[AVISO] SUPERADMIN_PASSWORD ignorada: use pelo menos 12 caracteres.'))
            senha_env = ''

        super_admins = [
            {'email': 'mandamulefj@sige.com', 'nome': 'Eng. Fernando Mandamule'},
            {'email': 'admin.master@sige.com', 'nome': 'Eng. Fernando Mandamule (Master)'},
        ]
        for sa in super_admins:
            email_valido = sa['email'].replace('.@sige.com', '@sige.com')
            try:
                conta_antiga = Usuario.objects.filter(email='mandamulefj.@sige.com').first()
                if conta_antiga and email_valido == 'mandamulefj@sige.com':
                    conta_antiga.email = 'mandamulefj@sige.com'
                    conta_antiga.username = 'mandamulefj@sige.com'
                    conta_antiga.save()
            except Exception:
                pass

            u = Usuario.objects.filter(email=email_valido).first()
            nova = u is None
            if nova:
                u = Usuario(email=email_valido, username=email_valido)
            u.nome = sa['nome']
            u.username = email_valido
            u.email = email_valido
            u.role = 'SUPERADMIN'
            u.is_superuser = True
            u.is_staff = True
            u.escola = None  # SuperAdmin não pertence a uma escola específica (gerencia a plataforma)
            if senha_env:
                u.set_password(senha_env)
            elif nova:
                u.set_unusable_password()
                self.stdout.write(self.style.WARNING(
                    f'[AVISO] SuperAdmin {email_valido} criado SEM senha: defina SUPERADMIN_PASSWORD e reinicie.'))
            try:
                u.save()
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'[AVISO] Falha ao salvar SuperAdmin {email_valido}: {e}'))
        self.stdout.write(self.style.SUCCESS('[OK] SuperAdmins configurados.'))

        self.stdout.write(self.style.SUCCESS('[OK] Inicialização concluída. Nenhum dado fictício foi inserido no sistema.'))