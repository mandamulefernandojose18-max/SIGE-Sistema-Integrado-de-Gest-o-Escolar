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
