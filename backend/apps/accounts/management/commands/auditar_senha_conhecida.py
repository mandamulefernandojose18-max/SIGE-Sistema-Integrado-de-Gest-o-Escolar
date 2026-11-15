"""Procura (e, com --aplicar, neutraliza) contas cuja senha é uma senha que esteve exposta no repositório.

A antiga "senha mestra" ficou pública e, ao ser usada, gravava-se como senha real da conta. Este comando
lista as contas ainda afectadas. Por omissão NÃO altera nada (dry-run).

- Contas não-SUPERADMIN: com --aplicar, a senha passa a ser o código oficial (`codigo_acesso`) com
  `senha_redefinida=False` (o utilizador volta ao 1.º acesso e escolhe uma nova); sem código, fica inutilizável.
- Contas SUPERADMIN: NUNCA são alteradas aqui (evita ficar sem acesso). São listadas para o titular mudar já
  a senha (Minha senha) ou definir SUPERADMIN_PASSWORD no .env e reiniciar.
Não imprime senhas nem hashes.
"""
from django.core.management.base import BaseCommand

from apps.accounts.models import Usuario

SENHAS_EXPOSTAS = ('Deusamo8', 'Deusamo8Mandamule')


class Command(BaseCommand):
    help = 'Lista/neutraliza contas com senhas que estiveram expostas no repositório (dry-run por omissão).'

    def add_arguments(self, parser):
        parser.add_argument('--aplicar', action='store_true', help='Aplica a neutralização (contas não-SUPERADMIN).')

    def handle(self, *args, **options):
        aplicar = options['aplicar']
        afectadas, superadmins, neutralizadas = 0, 0, 0
        for u in Usuario.objects.exclude(password='').iterator():
            if not u.has_usable_password():
                continue
            if not any(u.check_password(s) for s in SENHAS_EXPOSTAS):
                continue
            afectadas += 1
            rotulo = f'{u.email or u.username} [{u.role}]'
            if u.role == 'SUPERADMIN':
                superadmins += 1
                self.stdout.write(self.style.ERROR(f'  SUPERADMIN com senha exposta (altere JÁ): {rotulo}'))
                continue
            self.stdout.write(f'  senha exposta: {rotulo}')
            if aplicar:
                cod = (u.codigo_acesso or '').strip()
                if cod:
                    u.set_password(cod)
                    u.senha_redefinida = False
                    u.save(update_fields=['password', 'senha_redefinida'])
                else:
                    u.set_unusable_password()
                    u.save(update_fields=['password'])
                neutralizadas += 1
        self.stdout.write(self.style.NOTICE(
            f'Contas afectadas: {afectadas} (SUPERADMIN: {superadmins}); neutralizadas: {neutralizadas}'
            + ('' if aplicar else ' — dry-run, nada foi alterado (use --aplicar).')))
