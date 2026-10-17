# Diretrizes do Projeto SIGE para Agentes de IA

## 🛡️ Regra Inquebrável: Ocultação Total de Endereços IP
- **NUNCA mostrar ou expor endereços IP** (nem na forma bruta nem em subdomínios derivados de IP) em links, documentos, atalhos, mensagens ou documentação.
- Todos os links oficiais e públicos devem usar exclusivamente:
  - **Aplicação Web:** `https://sigesaas.duckdns.org/`
  - **API REST (HTTPS):** `https://sigesaas.duckdns.org/api/v1/`
  - **Documentação Swagger:** `https://sigesaas.duckdns.org/api/docs/`
- Os atalhos locais (`sige.url`, `sige.cmd` e atalho do Desktop) devem apontar exclusivamente para `https://sigesaas.duckdns.org/`.

## 💰 Regra de Orçamento (Guardrail)
- Manter o custo total de infraestrutura e serviços estritamente dentro do limite de US$ 6/mês.

## 🔄 Regra Mandatória: Sincronização Contínua de Documentação e Auto-Deploy
- **SEMPRE** que qualquer actualização for realizada no sistema (código, modelo de dados, regra de negócio, endpoint, telas ou infraestrutura):
  1. **Atualizar a documentação** correspondente na suite de manuais em `docs/` (`DOCUMENTACAO_COMPLETA_DO_SISTEMA.md`, `README.md`, etc.).
  2. **Executar git commit semântico** com mensagem descritiva.
  3. **Executar git push** para o repositório remoto.
  4. **Executar o deploy desacoplado** na VM de produção (`sigesaas.duckdns.org`), validando o funcionamento dos serviços e os atalhos locais `sige`.
