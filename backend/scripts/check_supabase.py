import psycopg
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

conn_str = "postgresql://postgres.pkokhrdsffwqsmscirrl:Deusamo8Mandamule@aws-0-us-west-2.pooler.supabase.com:5432/postgres?sslmode=require"

with psycopg.connect(conn_str) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT current_database(), current_user, version();")
        db, user, ver = cur.fetchone()
        print("=== CONEXÃO EM TEMPO REAL COM O SUPABASE ===")
        print(f"Base de Dados: {db}")
        print(f"Utilizador Conectado: {user}")
        print(f"Versão PostgreSQL: {ver.split(',')[0]}")
        print("---------------------------------------------")

        cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';")
        print(f"Total de Tabelas Criadas no Schema public: {cur.fetchone()[0]}")

        cur.execute("SELECT count(*) FROM pg_policies WHERE schemaname = 'public';")
        print(f"Total de Políticas RLS Ativas: {cur.fetchone()[0]}")

        cur.execute("SELECT count(*) FROM public.sige_usuarios;")
        print(f"Total de Usuários Cadastrados: {cur.fetchone()[0]}")

        cur.execute("SELECT count(*) FROM public.sige_alunos;")
        print(f"Total de Alunos Matriculados: {cur.fetchone()[0]}")

        cur.execute("SELECT count(*) FROM public.sige_turmas;")
        print(f"Total de Turmas: {cur.fetchone()[0]}")

        cur.execute("SELECT nome, status FROM public.sige_escolas;")
        escolas = cur.fetchall()
        print(f"Escolas Cadastradas ({len(escolas)}): {escolas}")
        print("=============================================")
