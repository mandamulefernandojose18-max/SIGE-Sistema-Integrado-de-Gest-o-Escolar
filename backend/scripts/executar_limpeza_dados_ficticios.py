import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production' if os.environ.get('SIGE_ENV') == 'production' else 'config.settings.development')
django.setup()

from django.db import transaction
from apps.tenants.models import Escola, Plano, AssinaturaEscola
from apps.disciplinas.models import Disciplina
from apps.turmas.models import Turma
from apps.alunos.models import Aluno
from apps.professores.models import Professor, AlocacaoDocente
from apps.notas.models import Nota
from apps.material_escolar.models import MaterialEscolar
from apps.accounts.models import Usuario
from apps.certificados.models import Certificado

print("=" * 75)
print("SIGE — PURIFICAÇÃO E LIMPEZA INTEGRAL DE DADOS FICTÍCIOS")
print("=" * 75)

with transaction.atomic():
    # -------------------------------------------------------------
    # 1. REMOVER ESCOLAS FICTÍCIAS, TEMPORÁRIAS E DUPLICADAS DE TESTE
    # -------------------------------------------------------------
    nifs_ficticios = ['000111222', '11224245', '5001234567', '5009876543']
    escolas_ficticias = Escola.objects.filter(nif_cnpj__in=nifs_ficticios)
    
    # Também qualquer escola temporária chamada Test Temp ou similar
    escolas_temp = Escola.objects.filter(nome__icontains='Test Temp')
    todas_ficticias = (escolas_ficticias | escolas_temp).distinct()
    
    nomes_ficticios = list(todas_ficticias.values_list('nome', flat=True))
    ficticias_ids = list(todas_ficticias.values_list('id', flat=True))
    
    print(f"\n[1] Identificadas {todas_ficticias.count()} instituições fictícias/de teste para eliminação: {nomes_ficticios}")
    
    # Remover utilizadores explicitamente associados às escolas fictícias
    users_ficticios_esc = Usuario.objects.filter(escola_id__in=ficticias_ids)
    u_count = users_ficticios_esc.count()
    users_ficticios_esc.delete()
    print(f"    - {u_count} utilizadores vinculados a instituições de teste removidos.")
    
    # Eliminar as escolas fictícias (cascata limpa turmas, assinaturas, etc.)
    for esc in todas_ficticias:
        nome_e = esc.nome
        esc.delete()
        print(f"    - Instituição fictícia '{nome_e}' eliminada com sucesso!")

    # -------------------------------------------------------------
    # 2. REMOVER UTILIZADORES FICTÍCIOS E CONTAS DE TESTE RESIDUAIS
    # -------------------------------------------------------------
    print("\n[2] Removendo contas e utilizadores fictícios...")
    emails_ficticios = [
        'costa@sige.com', 'baptista@sige.com', 'eunice@sige.com',
        'admin@escola.sige.com', 'admin.expirada@sige.com',
        'silva@sige.com', 'santos@sige.com', 'mandamule@sige.com',
        'temp@test.mz', 'colegio@sige.com', 'araujo@gmail.com',
        # Contas automáticas com nomes fictícios de demonstração
        'gd.0409s0001@sige.edu.mz', 'dp.0409s0001@sige.edu.mz', 'secr.0409s0001@sige.edu.mz',
        'dp.0411s0001@sige.edu.mz', 'secr.0411s0001@sige.edu.mz',
        'dp.0407s0001@sige.edu.mz', 'secr.0407s0001@sige.edu.mz'
    ]
    u_del = Usuario.objects.filter(email__in=emails_ficticios).delete()
    print(f"    - {u_del[0]} utilizadores fictícios eliminados.")

    # -------------------------------------------------------------
    # 3. CORRIGIR NOMES FIÉIS E REAIS DOS UTILIZADORES
    # -------------------------------------------------------------
    print("\n[3] Restaurando nomes reais e fiéis de administradores...")
    u_fernando = Usuario.objects.filter(email='mandamulefernandojose18@gmail.com').first()
    if u_fernando:
        nome_antigo = u_fernando.nome
        u_fernando.nome = 'Fernando José Mandamule'
        u_fernando.save(update_fields=['nome'])
        print(f"    - Utilizador 'mandamulefernandojose18@gmail.com': '{nome_antigo}' -> '{u_fernando.nome}'.")

    # SuperAdmins oficiais
    for sa_email in ['mandamulefj@sige.com', 'admin.master@sige.com']:
        sa = Usuario.objects.filter(email=sa_email).first()
        if sa and sa.nome != 'Eng. Fernando Mandamule':
            sa.nome = 'Eng. Fernando Mandamule'
            sa.save(update_fields=['nome'])
            print(f"    - SuperAdmin '{sa_email}' normalizado.")

    # -------------------------------------------------------------
    # 4. PURIFICAR DADOS DAS INSTITUIÇÕES OFICIAIS ATIVAS
    # -------------------------------------------------------------
    print("\n[4] Purificando cadastros das instituições ativas (sem nomes de directores fictícios)...")
    
    # A. Escola Secundária de Cambine
    cambine = Escola.objects.filter(id='da662d05-dc31-4206-8e08-48fe1a6b54e7').first()
    if cambine:
        cambine.director_nome = 'Fernando José Mandamule'
        cambine.director_carreira = 'Professor Técnico'
        cambine.dap_nome = ''
        cambine.chefe_secretaria_nome = ''
        cambine.save(update_fields=['director_nome', 'director_carreira', 'dap_nome', 'chefe_secretaria_nome'])
        print(f"    - '{cambine.nome}': Director='{cambine.director_nome}', DAP e Secretaria purificados (em branco para dados fiéis).")

        # Remover disciplina de teste 'bio-10' sem alunos nem notas em Cambine (Cambine só leciona 11ª Classe)
        bio10 = Disciplina.objects.filter(escola=cambine, codigo='bio-10', notas__isnull=True, alocacaodocente__isnull=True).first()
        if bio10:
            bio10.delete()
            print(f"    - Disciplina de teste 'bio-10' removida de Cambine.")

    # B. Escola Secundária de Massinga
    massinga = Escola.objects.filter(id='413ddf8a-ed24-4ef5-b5c4-009ed71c9e1a').first()
    if massinga:
        massinga.director_nome = ''
        massinga.director_carreira = ''
        massinga.dap_nome = ''
        massinga.chefe_secretaria_nome = ''
        massinga.save(update_fields=['director_nome', 'director_carreira', 'dap_nome', 'chefe_secretaria_nome'])
        print(f"    - '{massinga.nome}': Purificada, 100% limpa para receber os dados reais da direcção.")

    # C. Qualquer outra escola com resquícios de 'Prof. Dr. António Costa'
    escolas_com_costa = Escola.objects.filter(director_nome__icontains='Costa')
    for e in escolas_com_costa:
        e.director_nome = ''
        e.director_carreira = ''
        e.dap_nome = ''
        e.chefe_secretaria_nome = ''
        e.save(update_fields=['director_nome', 'director_carreira', 'dap_nome', 'chefe_secretaria_nome'])
        print(f"    - Instituição '{e.nome}': Resquício fictício eliminado.")

    # -------------------------------------------------------------
    # 5. GARANTIR CODIFICAÇÃO E QR CODES OFICIAIS (SEM EXPOSIÇÃO DE IP)
    # -------------------------------------------------------------
    print("\n[5] Verificando integridade e QR codes oficiais dos certificados...")
    certs = Certificado.objects.all()
    c_updated = 0
    for c in certs:
        novo_qr = f"https://sigesaas.duckdns.org/verificar-certificado.html?codigo={c.codigo_autenticidade}"
        if c.qrcode_data != novo_qr:
            c.qrcode_data = novo_qr
            c.save(update_fields=['qrcode_data'])
            c_updated += 1
    print(f"    - {c_updated} certificados garantidos com HTTPS e domínio oficial sigesaas.duckdns.org.")

print("\n" + "=" * 75)
print("SISTEMA TOTALMENTE PURIFICADO: PRONTO PARA RECEBER DADOS REAIS E FIÉIS!")
print("=" * 75)
