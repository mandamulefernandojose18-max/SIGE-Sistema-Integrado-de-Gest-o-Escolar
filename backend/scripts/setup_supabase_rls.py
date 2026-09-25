"""
Script para Habilitar Row Level Security (RLS) e Criar Políticas no Supabase.
Garante isolamento multi-tenant por escola, acesso público controlado e permissão total para a API backend.
"""
import psycopg
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

conn_str = "postgresql://postgres.pkokhrdsffwqsmscirrl:Deusamo8Mandamule@aws-0-us-west-2.pooler.supabase.com:5432/postgres?sslmode=require"

TENANT_TABLES = [
    'sige_alunos',
    'sige_professores',
    'sige_turmas',
    'sige_disciplinas',
    'sige_notas',
    'sige_pautas',
    'sige_pagamentos',
    'sige_assinaturas_escolas',
    'sige_documentos_salvos',
    'sige_logs_impressao',
    'sige_logs_acesso',
    'sige_permissoes_edicao_notas',
    'sige_professor_disciplina_turma'
]

DJANGO_SYSTEM_TABLES = [
    'django_session',
    'django_migrations',
    'django_content_type',
    'django_admin_log',
    'auth_group',
    'auth_group_permissions',
    'auth_permission',
    'sige_usuarios_groups',
    'sige_usuarios_user_permissions'
]

def generate_and_apply_rls():
    sql_commands = []

    sql_commands.append("-- =====================================================")
    sql_commands.append("-- SIGE: Políticas de Segurança e RLS para o Supabase")
    sql_commands.append("-- =====================================================\n")

    # 1. Habilitar RLS em todas as tabelas
    all_tables = TENANT_TABLES + DJANGO_SYSTEM_TABLES + [
        'sige_escolas', 'sige_planos', 'sige_certificados', 'sige_material_escolar', 'sige_usuarios'
    ]

    for table in all_tables:
        sql_commands.append(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;")

    # 2. Política Universal para postgres e service_role (Backend Django)
    for table in all_tables:
        pol_name = f"service_all_{table}"
        sql_commands.append(f"""
DROP POLICY IF EXISTS "{pol_name}" ON public.{table};
CREATE POLICY "{pol_name}" ON public.{table}
    FOR ALL
    USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    )
    WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role')
    );
""")

    # 3. Políticas Públicas
    sql_commands.append("""
-- Catálogo de Planos (Leitura Pública)
DROP POLICY IF EXISTS "public_read_planos" ON public.sige_planos;
CREATE POLICY "public_read_planos" ON public.sige_planos
    FOR SELECT USING (true);

-- Escolas Ativas (Leitura Pública de Informações Institucionais)
DROP POLICY IF EXISTS "public_read_escolas" ON public.sige_escolas;
CREATE POLICY "public_read_escolas" ON public.sige_escolas
    FOR SELECT USING (status = 'ATIVA');

-- Validação Pública de Certificados e Diplomas com QR Code
DROP POLICY IF EXISTS "public_read_certificados" ON public.sige_certificados;
CREATE POLICY "public_read_certificados" ON public.sige_certificados
    FOR SELECT USING (true);

-- Catálogo de Materiais Escolares e Livros
DROP POLICY IF EXISTS "public_read_material_escolar" ON public.sige_material_escolar;
CREATE POLICY "public_read_material_escolar" ON public.sige_material_escolar
    FOR SELECT USING (true);
""")

    # 4. Políticas de Isolamento Multi-Tenant para as tabelas vinculadas a escola_id
    for table in TENANT_TABLES:
        sql_commands.append(f"""
-- Isolamento Multi-Tenant: {table}
DROP POLICY IF EXISTS "tenant_select_{table}" ON public.{table};
CREATE POLICY "tenant_select_{table}" ON public.{table}
    FOR SELECT USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_insert_{table}" ON public.{table};
CREATE POLICY "tenant_insert_{table}" ON public.{table}
    FOR INSERT WITH CHECK (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_update_{table}" ON public.{table};
CREATE POLICY "tenant_update_{table}" ON public.{table}
    FOR UPDATE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );

DROP POLICY IF EXISTS "tenant_delete_{table}" ON public.{table};
CREATE POLICY "tenant_delete_{table}" ON public.{table}
    FOR DELETE USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN')
    );
""")

    # 5. Política para Usuários
    sql_commands.append("""
-- Usuários: Leitura de membros da mesma escola ou SuperAdmin
DROP POLICY IF EXISTS "usuarios_tenant_select" ON public.sige_usuarios;
CREATE POLICY "usuarios_tenant_select" ON public.sige_usuarios
    FOR SELECT USING (
        current_user = 'postgres' OR
        (current_setting('request.jwt.claim.role', true) = 'service_role') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'role' = 'SUPERADMIN') OR
        (current_setting('request.jwt.claims', true)::jsonb ->> 'escola_id')::uuid = escola_id
    );
""")

    full_sql = "\n".join(sql_commands)
    
    # Salvar script SQL para referência e auditoria
    sql_file = BASE_DIR / 'supabase_schema_rls.sql'
    sql_file.write_text(full_sql, encoding='utf-8')
    print(f"[OK] Script SQL gerado com sucesso em: {sql_file}")

    print("[APPLY] Conectando ao Supabase para aplicar RLS e Políticas...")
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute(full_sql)
            conn.commit()
            print("[OK] Todas as configurações e políticas foram aplicadas com sucesso no Supabase!")

            # Consulta de verificação
            cur.execute("""
                SELECT schemaname, tablename, policyname, permissive, cmd
                FROM pg_policies
                WHERE schemaname = 'public'
                ORDER BY tablename, policyname;
            """)
            policies = cur.fetchall()
            print(f"\n[VERIFICAÇÃO] Total de Políticas Criadas: {len(policies)}")
            for p in policies[:10]:
                print(f"  - Tabela: {p[1]} | Política: {p[2]} ({p[4]})")
            if len(policies) > 10:
                print(f"  - ... e mais {len(policies) - 10} políticas configuradas.")

if __name__ == '__main__':
    generate_and_apply_rls()
