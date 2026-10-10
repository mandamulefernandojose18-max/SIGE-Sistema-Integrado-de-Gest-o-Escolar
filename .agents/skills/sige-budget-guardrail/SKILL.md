---
name: sige-budget-guardrail
description: >-
  Regra inquebrável de infraestrutura que proíbe terminantemente qualquer custo ou plano de Máquina Virtual (VM) ou serviços extras que ultrapassem 6 dólares americanos por mês ($6/mês). Ative sempre que qualquer ação de provisionamento, redimensionamento, upgrade, configuração de serviços em nuvem ou deploy na VM for executada.
---

# 🛑 SIGE — Budget Guardrail: Limite Estrito de $6/mês para a VM

Esta skill estabelece uma **política inquebrável de orçamento** para qualquer infraestrutura, provisionamento, deploy ou manutenção da Máquina Virtual de produção do **SIGE** (Sistema Integrado de Gestão Escolar).

---

## 📌 1. Regra de Ouro do Orçamento

> **REGRA MANDATÓRIA:**
> O custo total mensal acumulado da VM e de quaisquer serviços associados em nuvem **NUNCA PODE ULTRAPASSAR 6 DÓLARES AMERICANOS (\$6.00 USD / MÊS)**.

Nenhum agente, script ou procedimento está autorizado a alterar planos, contratar add-ons ou provisionar recursos adicionais que violem este teto financeiro.

---

## ⛔ 2. Proibições Absolutas (Custo Zero Adicional)

É expressamente proibido ativar:
1. **Upgrades de Plano:** Não fazer upgrade para instâncias superiores a \$6/mês (ex: planos de \$10, \$12, \$20 da Vultr/DigitalOcean são proibidos sem aval explícito do usuário).
2. **Backups Automáticos Pagos:** Proibido marcar *Auto Backups* da Vultr (+20% de acréscimo, \$1.20/mês). Backups devem ser gerados via script próprio, Git ou exportação gratuita.
3. **Block Storage Adicional:** Proibido anexar volumes de disco externos pagos por GB. Todo o storage deve utilizar o disco SSD local já incluído no plano base (ex: 25 GB NVMe).
4. **IPs Flutuantes / Reservados Pagos:** Utilizar exclusivamente o IP público IPv4 já alocado gratuitamente com a instância.
5. **DDoS Protection Avançada Paga:** Proibido contratar mitigação de DDoS extra faturada em \$10/mês.

---

## 💡 3. Estratégias Mandatórias de Otimização em 1 GB RAM

Para manter a aplicação rápida e estável dentro da VM de \$5/mês (`vc2-1c-1gb`):

### A. Memória Swap Obrigatória (2 GB a 2.5 GB)
Toda VM configurada deve ter arquivo de swap configurado e ativo permanentemente:
```bash
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
```

### B. Limpeza Automática de Imagens Docker
Após cada deploy, o script deve rodar limpeza de imagens órfãs para nunca estourar o disco de 25 GB:
```bash
docker image prune -f
```

### C. Offloading de Base de Dados (Supabase Gratuito)
Sempre que possível, apontar o `DATABASE_URL` para o PostgreSQL remoto do **Supabase** (plano gratuito), liberando a memória RAM do PostgreSQL local para o Django e Nginx.

---

## 🛡️ 4. Checklist de Verificação Antes de Executar Comandos de Nuvem

Antes de executar qualquer chamada de API ou comando de infraestrutura:
- [ ] O plano selecionado custa $\le$ \$6/mês? *(Ex: `vc2-1c-1gb` = \$5/mês)*.
- [ ] O campo `backups` está definido como `"disabled"`?
- [ ] Não há itens de `attached_block_storages` ou `floating_ip`?
- [ ] O limite de RAM está sendo compensado com swapfile?
