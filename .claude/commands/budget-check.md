---
description: Valida o guardrail financeiro inquebrável de infraestrutura (máximo US$ 6/mês).
---

# Verificação do Guardrail de Orçamento ($6/mês)

Regra Inquebrável: O custo total de infraestrutura e serviços do SIGE deve permanecer estritamente dentro de **US$ 6/mês**.

Critérios de auditoria:
- Máquina Virtual (VM): Instância económica compatível com o orçamento (Free Tier / e2-micro ou VPS económica < $6/mês).
- DuckDNS: Gratuito (`sigesaas.duckdns.org`).
- Let's Encrypt / Certbot SSL: Gratuito.
- Armazenamento / Volumes adicionais: Proibido provisionar discos gerenciados ou serviços de terceiros cobrados acima da margem.
- Qualquer proposta de arquitetura ou alteração em docker-compose / nuvem deve validar a conformidade com este teto financeiro antes de ser aprovada.
