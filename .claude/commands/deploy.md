---
description: Executa o ciclo de deploy do SIGE (commit semântico, git push e deploy desacoplado na VM de produção).
---

# Fluxo de Deploy do SIGE

Para executar o deploy completo do SIGE respeitando todas as regras:

1. Verifique os arquivos modificados com `git status`.
2. Se houver alterações em funcionalidades, regras de negócio ou telas, certifique-se de que a documentação em `docs/` foi atualizada primeiro.
3. Execute o script de automação de deploy:
   ```powershell
   .\scripts\sige-git-deploy.ps1 -Message "$ARGUMENTS"
   ```
   Caso não seja fornecido argumento de mensagem, utilize uma mensagem semântica apropriada (ex: `fix: ajustes operacionais no sistema`).
4. Valide a integridade dos serviços:
   - Aplicação Web: `https://sigesaas.duckdns.org/`
   - API REST: `https://sigesaas.duckdns.org/api/v1/`
   - Atalho local: `sige`
