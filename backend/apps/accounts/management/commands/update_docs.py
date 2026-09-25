from django.core.management.base import BaseCommand
import subprocess
import sys
from pathlib import Path

class Command(BaseCommand):
    help = "Atualiza automaticamente a documentação do Backend (OpenAPI, Endpoints e Modelos)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("[DOCS] Executando gerador de documentação..."))
        base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
        script = base_dir / 'scripts' / 'update_docs.py'
        
        result = subprocess.run([sys.executable, str(script)], cwd=str(base_dir), capture_output=True, text=True)
        if result.returncode == 0:
            self.stdout.write(result.stdout)
            self.stdout.write(self.style.SUCCESS("[DOCS] Documentação atualizada com sucesso!"))
        else:
            self.stderr.write(result.stderr)
            self.stderr.write(self.style.ERROR("[DOCS] Erro ao atualizar documentação."))
