/**
 * SIGE — Ciclo Diário de Assinaturas e Faturação SaaS
 * Execução idempotente (Africa/Maputo):
 * 1. Chama gerar_faturas_do_dia() (ON CONFLICT DO NOTHING)
 * 2. Chama actualizar_estados_assinaturas() (em_atraso -> restrita -> suspensa)
 * Suporta execução via Node / Python / API
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

console.log('====================================================');
console.log('  SIGE SaaS — Execução do Ciclo Diário de Assinaturas');
console.log('  Fuso Horário: Africa/Maputo | Moeda: MZN');
console.log('====================================================');

const pythonScript = `
import os, sys, django
sys.path.insert(0, os.path.abspath('backend'))
sys.path.insert(0, os.path.abspath('backend/apps'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production' if os.environ.get('ENVIRONMENT') == 'production' else 'config.settings.development')
django.setup()

from django.db import connection

if connection.vendor == 'postgresql':
    with connection.cursor() as cursor:
        print('[DB] A executar gerar_faturas_do_dia() no PostgreSQL...')
        cursor.execute("SELECT public.gerar_faturas_do_dia();")
        faturas = cursor.fetchone()[0]
        print(f'[DB] Faturas abertas geradas: {faturas}')

        print('[DB] A executar actualizar_estados_assinaturas() no PostgreSQL...')
        cursor.execute("SELECT public.actualizar_estados_assinaturas();")
        estados = cursor.fetchone()[0]
        print(f'[DB] Resultado da transição de estados: {estados}')
else:
    from apps.tenants.saas_services import executar_rotina_diaria_saas_python
    res = executar_rotina_diaria_saas_python()
    print(f'[SQLITE/FALLBACK] Resultado: {res}')

print('[CONCLUÍDO] Ciclo diário de assinaturas processado com sucesso.')
`;

const venvPython = process.platform === 'win32'
  ? path.join(__dirname, '..', 'backend', 'venv', 'Scripts', 'python.exe')
  : path.join(__dirname, '..', 'backend', 'venv', 'bin', 'python');

const pythonBin = fs.existsSync(venvPython) ? venvPython : 'python';

const child = spawn(pythonBin, ['-c', pythonScript], {
  cwd: path.join(__dirname, '..'),
  env: process.env,
  stdio: 'inherit'
});

child.on('close', (code) => {
  if (code === 0) {
    console.log('[SUCESSO] Rotina diária de assinaturas concluída com êxito (Código 0).');
    process.exit(0);
  } else {
    console.error(`[ERRO] A rotina diária falhou com código de saída ${code}.`);
    process.exit(code);
  }
});
