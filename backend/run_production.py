"""
Script de Inicialização do Backend SIGE em Modo de Produção (WSGI / Waitress).
Executa migrações, checagens e inicializa o servidor de produção multi-thread.
"""
import os
import sys
from pathlib import Path

# Diretório base do backend
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / 'apps'))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / '.env')

# Garantir ambiente de produção e DEBUG desativado
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.production'

import django
django.setup()

from django.core.management import call_command
from waitress import serve
from config.wsgi import application

def main():
    print("=" * 65)
    print("   SIGE - INICIANDO BACKEND EM MODO PRODUCAO (WSGI / Waitress)    ")
    print("=" * 65)
    from django.conf import settings
    print(f"[*] DJANGO_SETTINGS_MODULE : {os.environ.get('DJANGO_SETTINGS_MODULE')}")
    print(f"[*] DEBUG                  : {settings.DEBUG}")
    print(f"[*] BASE DE DADOS          : {settings.DATABASES['default']['ENGINE']}")
    print(f"[*] HOST DB                : {settings.DATABASES['default'].get('HOST')}")
    print(f"[*] ALLOWED_HOSTS          : {settings.ALLOWED_HOSTS}")
    print(f"[*] CORS ORIGINS           : {settings.CORS_ALLOWED_ORIGINS}")
    print("-" * 65)
    
    # 1. Executar checagem de sistema do Django
    print("[*] Executando verificacao de integridade do Django...")
    call_command('check')
    
    # 2. Executar migracoes se necessario
    print("[*] Verificando migracoes de base de dados...")
    try:
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            print(f"[*] Aplicando {len(plan)} migracao(oes) pendente(s)...")
            call_command('migrate', interactive=False)
        else:
            print("[OK] Base de dados 100% atualizada (sem migracoes pendentes).")
    except Exception as e:
        print(f"[AVISO] Nao foi possivel verificar migracoes pendentes: {e}")
    
    # 3. Coletar estaticos
    print("[*] Coletando arquivos estaticos para producao...")
    call_command('collectstatic', interactive=False, clear=False)
    
    port = int(os.environ.get('PORT', 8000))
    host = os.environ.get('HOST', '0.0.0.0')
    threads = int(os.environ.get('THREADS', 8))
    
    print("-" * 65)
    print(f"[OK] Servidor WSGI de Producao ATIVO em: http://{host}:{port}")
    print(f"[OK] Conexoes simultaneas (Threads): {threads}")
    print(f"[OK] Documentacao Swagger: http://localhost:{port}/api/docs/")
    print(f"[OK] Health Check: http://localhost:{port}/health/")
    print("=" * 65)
    
    serve(application, host=host, port=port, threads=threads)

if __name__ == '__main__':
    main()
