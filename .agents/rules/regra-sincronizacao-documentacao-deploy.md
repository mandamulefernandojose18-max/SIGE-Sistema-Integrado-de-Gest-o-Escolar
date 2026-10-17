# Regra Mandatória: Sincronização Contínua de Documentação, Commit, Push e Deploy

> [!IMPORTANT]
> **OBRIGATORIEDADE DE CICLO FECHADO EM TODA E QUALQUER ACTUALIZAÇÃO**  
> Nenhuma tarefa ou modificação no código, modelos, endpoints, regras de negócio ou interface é considerada concluída sem a sincronização da documentação correspondente, commit semântico, git push e deploy desacoplado na VM de produção.

## 🔄 Fluxo Operacional Obrigatório

Sempre que qualquer actualização for realizada no SIGE:

1. **Sincronização da Documentação (`docs/*`):**
   - Atualizar os manuais específicos afetados (`ARQUITETURA_E_SEGURANCA.md`, `MANUAL_DE_MODULOS_E_OPERACAO.md`, `REGRAS_PEDAGOGICAS_MEC.md`, `DICIONARIO_DE_DADOS.md`, `REFERENCIA_COMPLETA_API.md`, `GUIA_DE_IMPLANTACAO_E_DEVOPS.md` e o documento mestre `DOCUMENTACAO_COMPLETA_DO_SISTEMA.md`).
2. **Git Commit Semântico:**
   - Realizar `git add .` e `git commit -m "tipo: mensagem descritiva"` com tipos semânticos (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:`).
3. **Git Push:**
   - Enviar as alterações para a branch ativa no GitHub (`git push origin <branch>`).
4. **Deploy Desacoplado na VM de Produção:**
   - Disparar o deploy isolado (API primeiro, depois Web) na VM (`sigesaas.duckdns.org`) através de `scripts/sige-git-deploy.ps1` ou execução remota via SSH do `scripts/deploy-separated.sh`.
   - Validar que a API, a Web e a ligação integrada respondem com HTTP 200 OK.
   - Garantir que os atalhos locais (`sige.url`, `sige.cmd` e atalho do Desktop) apontam para `https://sigesaas.duckdns.org/`.
