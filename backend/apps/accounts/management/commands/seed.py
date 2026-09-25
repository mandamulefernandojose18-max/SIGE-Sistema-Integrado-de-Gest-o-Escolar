from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.tenants.models import Plano, Escola, AssinaturaEscola
from apps.accounts.models import Usuario
from apps.turmas.models import Turma
from apps.disciplinas.models import Disciplina
from apps.professores.models import Professor, AlocacaoDocente
from apps.alunos.models import Aluno
from apps.notas.models import Nota
from apps.material_escolar.models import MaterialEscolar

class Command(BaseCommand):
    help = 'Carga inicial e idempotente de dados (Seed) para o SIGE (Moambique)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('[SEED] Iniciando carga de dados (Seed)...'))

        # 1. Planos do SaaS
        planos_dados = [
            {'nome': 'MENSAL', 'descricao': 'Plano Mensal - Licena bsica', 'preco': Decimal('1500.00'), 'duracao_dias': 30, 'max_alunos': 300, 'max_professores': 25},
            {'nome': 'TRIMESTRAL', 'descricao': 'Plano Trimestral - Perodos letivos', 'preco': Decimal('4200.00'), 'duracao_dias': 90, 'max_alunos': 800, 'max_professores': 60},
            {'nome': 'SEMESTRAL', 'descricao': 'Plano Semestral com desconto', 'preco': Decimal('7800.00'), 'duracao_dias': 180, 'max_alunos': 1500, 'max_professores': 100},
            {'nome': 'ANUAL', 'descricao': 'Plano Anual Institucional - Suporte 24/7', 'preco': Decimal('14500.00'), 'duracao_dias': 365, 'max_alunos': 3000, 'max_professores': 200},
        ]
        planos = {}
        for p in planos_dados:
            plano, _ = Plano.objects.update_or_create(
                nome=p['nome'],
                defaults=p
            )
            planos[p['nome']] = plano
        self.stdout.write(self.style.SUCCESS(' Planos configurados em MZN.'))

        # 2. SuperAdmin do SaaS
        super_admins = [
            {'email': 'mandamulefj.@sige.com', 'nome': 'Eng. Fernando Mandamule', 'pass': 'Deusamo8'},
            {'email': 'admin.master@sige.com', 'nome': 'Eng. Fernando Mandamule (Master)', 'pass': 'Deusamo8'},
        ]
        for sa in super_admins:
            u, created = Usuario.objects.get_or_create(email=sa['email'], defaults={'nome': sa['nome'], 'username': sa['email'], 'role': 'SUPERADMIN'})
            u.nome = sa['nome']
            u.username = sa['email']
            u.role = 'SUPERADMIN'
            u.is_superuser = True
            u.is_staff = True
            u.set_password(sa['pass'])
            u.save()
        self.stdout.write(self.style.SUCCESS('[OK] SuperAdmins criados.'))

        # 3. Escola 1: "Escola Secundria Central" (ATIVA)
        agora = timezone.now()
        escola1, _ = Escola.objects.update_or_create(
            nif_cnpj='5001234567',
            defaults={
                'nome': 'Escola Secundria Central',
                'email': 'central@escola.sige.com',
                'status': 'ATIVA',
                'provincia': 'Maputo',
                'distrito': 'Cidade de Maputo',
                'director_nome': 'Prof. Dr. Antnio Costa',
                'director_carreira': 'Professor Doutor',
                'dap_nome': 'Prof. Joo Baptista',
                'chefe_secretaria_nome': 'Dra. Maria Eunice',
                'plano': planos['ANUAL'],
                'ano_letivo_ativo': '2026',
                'trimestre_ativo': '1_TRIMESTRE'
            }
        )
        AssinaturaEscola.objects.get_or_create(
            escola=escola1,
            plano=planos['ANUAL'],
            defaults={
                'data_inicio': agora,
                'data_fim': agora + timedelta(days=365),
                'valor': Decimal('14500.00'),
                'status': 'ATIVA'
            }
        )

        # 4. Escola 2: "Escola Secundria do Dondo" (EXPIRADA para testes de isolamento/bloqueio 402)
        escola_expirada, _ = Escola.objects.update_or_create(
            nif_cnpj='5009876543',
            defaults={
                'nome': 'Escola Secundria do Dondo',
                'email': 'dondo@escola.sige.com',
                'status': 'EXPIRADA',
                'provincia': 'Sofala',
                'distrito': 'Dondo',
                'director_nome': 'Prof. Mateus Simango',
                'dap_nome': 'Prof. Gabriel Tembe',
                'chefe_secretaria_nome': 'Dra. Elsa Cossa',
                'plano': planos['MENSAL'],
                'ano_letivo_ativo': '2026',
                'trimestre_ativo': '1_TRIMESTRE'
            }
        )
        AssinaturaEscola.objects.get_or_create(
            escola=escola_expirada,
            plano=planos['MENSAL'],
            defaults={
                'data_inicio': agora - timedelta(days=60),
                'data_fim': agora - timedelta(days=1),
                'valor': Decimal('1500.00'),
                'status': 'EXPIRADA'
            }
        )
        self.stdout.write(self.style.SUCCESS(' Escolas configuradas (ATIVA e EXPIRADA).'))

        # 5. Utilizadores Administrativos da Escola 1
        staff = [
            {'email': 'costa@sige.com', 'nome': 'Prof. Dr. Antnio Costa', 'role': 'DIRECTOR_ESCOLA', 'pass': 'costa123'},
            {'email': 'baptista@sige.com', 'nome': 'Prof. Joo Baptista', 'role': 'DAP', 'pass': 'baptista123'},
            {'email': 'eunice@sige.com', 'nome': 'Dra. Maria Eunice', 'role': 'CHEFE_SECRETARIA', 'pass': 'eunice123'},
            {'email': 'admin@escola.sige.com', 'nome': 'Admin Central', 'role': 'ADMIN_ESCOLA', 'pass': 'admin123'},
        ]
        for s in staff:
            u, _ = Usuario.objects.get_or_create(email=s['email'], defaults={'nome': s['nome'], 'username': s['email'], 'role': s['role'], 'escola': escola1})
            u.nome = s['nome']
            u.username = s['email']
            u.role = s['role']
            u.escola = escola1
            u.set_password(s['pass'])
            u.save()

        # Usuário para a Escola Expirada
        u_exp, _ = Usuario.objects.get_or_create(email='admin.expirada@sige.com', defaults={'nome': 'Admin Expirada', 'username': 'admin.expirada@sige.com', 'role': 'ADMIN_ESCOLA', 'escola': escola_expirada})
        u_exp.username = 'admin.expirada@sige.com'
        u_exp.set_password('expirada123')
        u_exp.escola = escola_expirada
        u_exp.save()

        # 6. Turmas
        turma10a, _ = Turma.objects.get_or_create(
            escola=escola1,
            nome='10 Classe A',
            defaults={'grau_ano': '10 Classe', 'turno': 'MANHA', 'ano_letivo': '2026', 'area': 'Geral', 'sala': 'Sala 01'}
        )
        turma12a, _ = Turma.objects.get_or_create(
            escola=escola1,
            nome='12 Classe A',
            defaults={'grau_ano': '12 Classe', 'turno': 'MANHA', 'ano_letivo': '2026', 'area': 'Cincias', 'sala': 'Sala 05'}
        )

        # 7. Disciplinas
        disciplinas_nomes = [
            ('Matemtica', 'MAT-10', '10 Classe'),
            ('Lngua Portuguesa', 'POR-10', '10 Classe'),
            ('Fsica', 'FIS-10', '10 Classe'),
            ('Qumica', 'QUI-10', '10 Classe'),
            ('Biologia', 'BIO-10', '10 Classe'),
            ('Histria', 'HIS-10', '10 Classe'),
            ('Geografia', 'GEO-10', '10 Classe'),
            ('Ingls', 'ING-10', '10 Classe'),
        ]
        disciplinas = {}
        for nome, cod, cls in disciplinas_nomes:
            disc, _ = Disciplina.objects.get_or_create(
                escola=escola1,
                codigo=cod,
                defaults={'nome': nome, 'classe': cls, 'area': 'Geral', 'ano_letivo': '2026'}
            )
            disciplinas[cod] = disc

        # 8. Professores
        prof1, _ = Professor.objects.get_or_create(
            escola=escola1,
            email='silva@sige.com',
            defaults={'nome': 'Carlos Silva', 'especialidade': 'Matemtica', 'carreira': 'DN1', 'telefone': '+258 84 200 3000'}
        )
        u_prof1, _ = Usuario.objects.get_or_create(email='silva@sige.com', defaults={'nome': 'Carlos Silva', 'username': 'silva@sige.com', 'role': 'PROFESSOR', 'escola': escola1, 'professor_id': prof1.id})
        u_prof1.username = 'silva@sige.com'
        u_prof1.set_password('silva123')
        u_prof1.professor_id = prof1.id
        u_prof1.save()

        prof2, _ = Professor.objects.get_or_create(
            escola=escola1,
            email='santos@sige.com',
            defaults={'nome': 'Ana Santos', 'especialidade': 'Língua Portuguesa', 'carreira': 'DN1', 'telefone': '+258 84 300 4000'}
        )
        u_prof2, _ = Usuario.objects.get_or_create(email='santos@sige.com', defaults={'nome': 'Ana Santos', 'username': 'santos@sige.com', 'role': 'PROFESSOR', 'escola': escola1, 'professor_id': prof2.id})
        u_prof2.username = 'santos@sige.com'
        u_prof2.set_password('santos123')
        u_prof2.professor_id = prof2.id
        u_prof2.save()

        # Alocações Docentes
        AlocacaoDocente.objects.get_or_create(escola=escola1, professor=prof1, disciplina=disciplinas['MAT-10'], turma=turma10a)
        AlocacaoDocente.objects.get_or_create(escola=escola1, professor=prof2, disciplina=disciplinas['POR-10'], turma=turma10a)

        # 9. Alunos
        aluno1, _ = Aluno.objects.get_or_create(
            escola=escola1,
            matricula='2026001',
            defaults={
                'nome': 'Fernando José Mandamule',
                'turma': turma10a,
                'data_nascimento': '2009-05-18',
                'genero': 'M',
                'provincia': 'Maputo',
                'distrito': 'Cidade de Maputo',
                'status': 'ATIVO'
            }
        )
        u_aluno, _ = Usuario.objects.get_or_create(email='mandamule@sige.com', defaults={'nome': 'Fernando José Mandamule', 'username': 'mandamule@sige.com', 'role': 'ALUNO', 'escola': escola1, 'aluno_id': aluno1.id})
        u_aluno.username = 'mandamule@sige.com'
        u_aluno.set_password('mandamule123')
        u_aluno.aluno_id = aluno1.id
        u_aluno.save()

        aluno2, _ = Aluno.objects.get_or_create(
            escola=escola1,
            matricula='2026002',
            defaults={
                'nome': 'Maria Manuela Cossa',
                'turma': turma10a,
                'data_nascimento': '2009-08-22',
                'genero': 'F',
                'provincia': 'Maputo',
                'distrito': 'Cidade de Maputo',
                'status': 'ATIVO'
            }
        )

        # 10. Notas Iniciais
        Nota.objects.update_or_create(
            escola=escola1, aluno=aluno1, disciplina=disciplinas['MAT-10'], turma=turma10a, periodo='1_TRIMESTRE',
            defaults={'teste1': 16.0, 'teste2': 17.0, 'trabalho': 18.0, 'avaliacao_trimestral': 16.0, 'media_final': 17.0, 'resultado': 'Aprovado', 'comportamento': 'MB'}
        )
        Nota.objects.update_or_create(
            escola=escola1, aluno=aluno1, disciplina=disciplinas['POR-10'], turma=turma10a, periodo='1_TRIMESTRE',
            defaults={'teste1': 14.0, 'teste2': 15.0, 'trabalho': 16.0, 'avaliacao_trimestral': 15.0, 'media_final': 15.0, 'resultado': 'Aprovado', 'comportamento': 'B'}
        )

        # 11. Material Escolar
        MaterialEscolar.objects.get_or_create(
            escola=escola1,
            titulo='Manual Oficial de Matemtica - 10 Classe',
            defaults={
                'classe': '10 Classe',
                'disciplina': disciplinas['MAT-10'],
                'descricao': 'Manual oficial aprovado pelo MINEDH para o ensino secundrio geral.',
                'tipo': 'MANUAL',
                'nome_arquivo': 'manual_matematica_10a.pdf',
                'extensao': 'pdf',
                'tamanho_bytes': 1542000,
                'publicado_por': 'Direco Pedaggica'
            }
        )

        self.stdout.write(self.style.SUCCESS(' Carga de dados (Seed) concluda com sucesso!'))

