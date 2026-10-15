import os
import sys
import django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from django.db import transaction
from apps.tenants.models import Escola
from apps.disciplinas.models import Disciplina
from apps.turmas.models import Turma
from apps.alunos.models import Aluno
from apps.professores.models import Professor, AlocacaoDocente
from apps.notas.models import Nota
from apps.material_escolar.models import MaterialEscolar
from apps.accounts.models import Usuario
from apps.certificados.models import Certificado

print("=" * 70)
print("INICIANDO LIMPEZA DE DADOS FICTÍCIOS E CORREÇÃO DE DUPLICAÇÕES NO SIGE")
print("=" * 70)

with transaction.atomic():
    # -------------------------------------------------------------
    # 1. REMOVER ESCOLAS FICTÍCIAS E TODOS OS SEUS REGISTOS ASSOCIADOS
    # -------------------------------------------------------------
    escolas_ficticias = Escola.objects.filter(nif_cnpj__in=['5001234567', '5009876543'])
    nomes_ficticios = list(escolas_ficticias.values_list('nome', flat=True))
    ficticias_ids = list(escolas_ficticias.values_list('id', flat=True))
    
    print(f"\n[1] Removendo escolas fictícias de demonstração: {nomes_ficticios}...")
    
    # Remover utilizadores explicitamente associados às escolas fictícias
    users_ficticios = Usuario.objects.filter(escola_id__in=ficticias_ids)
    u_count = users_ficticios.count()
    users_ficticios.delete()
    print(f"    - {u_count} utilizadores fictícios removidos.")
    
    # Remover emails de teste seed remanescentes
    emails_seed = [
        'costa@sige.com', 'baptista@sige.com', 'eunice@sige.com',
        'admin@escola.sige.com', 'admin.expirada@sige.com',
        'silva@sige.com', 'santos@sige.com', 'mandamule@sige.com'
    ]
    u_seed_count = Usuario.objects.filter(email__in=emails_seed).delete()[0]
    if u_seed_count:
        print(f"    - {u_seed_count} utilizadores seed com emails fictícios eliminados.")

    # Excluir as escolas fictícias (cascata limpa turmas, alunos, notas, disciplinas de demonstração)
    for esc in escolas_ficticias:
        nome_e = esc.nome
        esc.delete()
        print(f"    - Escola fictícia '{nome_e}' eliminada com sucesso!")

    # -------------------------------------------------------------
    # 2. REMOVER DISCIPLINAS EM ESCOLAS ONDE O USUÁRIO NÃO CADASTROU
    # -------------------------------------------------------------
    print("\n[2] Removendo disciplinas em escolas não cadastradas pelo utilizador...")
    # Escola de Massinga: usuário não cadastrou disciplinas (foram injetadas em lote)
    massinga = Escola.objects.filter(id='413ddf8a-ed24-4ef5-b5c4-009ed71c9e1a').first()
    if massinga:
        disc_m = Disciplina.objects.filter(escola=massinga)
        count_m = disc_m.count()
        disc_m.delete()
        print(f"    - Escola Secundária de Massinga: {count_m} disciplinas não cadastradas removidas (total agora: 0).")
        
        # Remover turmas duplicadas terminadas em '(1)' em Massinga
        t_dup = Turma.objects.filter(escola=massinga, nome__contains='(1)')
        count_t_dup = t_dup.count()
        t_dup.delete()
        print(f"    - Escola Secundária de Massinga: {count_t_dup} turmas duplicadas com sufixo (1) removidas.")

    # -------------------------------------------------------------
    # 3. LIMPAR DISCIPLINAS INJETADAS EM LOTE EM CAMBINE (MANTER APENAS AS REAIS)
    # -------------------------------------------------------------
    cambine = Escola.objects.filter(id='da662d05-dc31-4206-8e08-48fe1a6b54e7').first()
    if cambine:
        print("\n[3] Ajustando disciplinas na Escola Secundária de Cambine...")
        qs_c = Disciplina.objects.filter(escola=cambine)
        
        # Identificar disciplinas que estão em uso real
        em_uso_ids = set()
        for n in Nota.objects.filter(escola=cambine).values_list('disciplina_id', flat=True):
            if n: em_uso_ids.add(n)
        for a in AlocacaoDocente.objects.filter(escola=cambine).values_list('disciplina_id', flat=True):
            if a: em_uso_ids.add(a)
        for m in MaterialEscolar.objects.filter(escola=cambine).values_list('disciplina_id', flat=True):
            if m: em_uso_ids.add(m)
            
        # Disciplinas manuais cadastradas pelo usuário
        manuais = [d for d in qs_c if not (d.created_at.month == 10 and d.created_at.day == 5 and d.created_at.hour == 10 and d.created_at.minute == 39)]
        manuais_ids = {d.id for d in manuais}
        
        manter_ids = em_uso_ids.union(manuais_ids)
        a_remover_c = qs_c.exclude(id__in=manter_ids)
        count_rem_c = a_remover_c.count()
        a_remover_c.delete()
        print(f"    - Removidas {count_rem_c} disciplinas fictícias/injetadas em lote de Cambine.")
        print(f"    - Disciplinas mantidas em Cambine ({Disciplina.objects.filter(escola=cambine).count()}):")
        for d in Disciplina.objects.filter(escola=cambine).order_by('nome'):
            print(f"        * {d.codigo} - {d.nome} ({d.classe})")

    # -------------------------------------------------------------
    # 4. RESOLVER DUPLICAÇÕES DE CÓDIGOS E MATRÍCULAS DE ALUNOS
    # -------------------------------------------------------------
    if cambine:
        print("\n[4] Atribuindo números sequenciais únicos a cada aluno (eliminando duplicatas de código)...")
        turmas_cambine = Turma.objects.filter(escola=cambine).order_by('nome')
        for t in turmas_cambine:
            alunos_t = Aluno.objects.filter(escola=cambine, turma=t).order_by('created_at')
            for idx, a in enumerate(alunos_t, start=1):
                partes = (a.matricula or '').split('.')
                base = '.'.join(partes[:5]) if len(partes) >= 5 else a.matricula
                nova_mat = f"{base}.{idx:02d}"
                
                if a.matricula != nova_mat:
                    print(f"    - Aluno '{a.nome}': {a.matricula} -> {nova_mat}")
                    Aluno.objects.filter(id=a.id).update(matricula=nova_mat)
                    
                    # Atualizar conta Usuario associada
                    u = Usuario.objects.filter(aluno_id=a.id).first()
                    if u:
                        u.codigo_acesso = nova_mat
                        if not u.senha_redefinida:
                            u.set_password(nova_mat)
                        u.save(update_fields=['codigo_acesso', 'password'])

    # -------------------------------------------------------------
    # 5. ATUALIZAR QR CODES COM DOMÍNIO OFICIAL (SEM EXPOR IP)
    # -------------------------------------------------------------
    print("\n[5] Normalizando links de verificação de certificados para sigesaas.duckdns.org...")
    certs = Certificado.objects.all()
    c_updated = 0
    for c in certs:
        novo_qr = f"https://sigesaas.duckdns.org/verificar-certificado.html?codigo={c.codigo_autenticidade}"
        if c.qrcode_data != novo_qr:
            c.qrcode_data = novo_qr
            c.save(update_fields=['qrcode_data'])
            c_updated += 1
    print(f"    - {c_updated} certificados normalizados com o domínio oficial.")

print("\n" + "=" * 70)
print("LIMPEZA E HIGIENIZAÇÃO DE DADOS CONCLUÍDA COM SUCESSO!")
print("=" * 70)
