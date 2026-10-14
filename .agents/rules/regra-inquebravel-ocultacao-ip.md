# Regra Inquebrável: Proibição de Exposição de Endereços IP

> [!CRITICAL]
> **NUNCA MOSTRAR OU EXPOR ENDEREÇOS IP** em links, mensagens de chat, documentações, atalhos, relatórios ou terminais.

## Diretrizes Obrigatórias:
1. **Links Públicos e Documentação:**
   - **Aplicação Web:** `https://sigesaas.duckdns.org/`
   - **API REST (HTTPS):** `https://sigesaas.duckdns.org/api/v1/`
   - **Documentação Swagger:** `https://sigesaas.duckdns.org/api/docs/`
2. **Proibição Absoluta:**
   - É terminantemente proibido exibir o IP bruto (ex: `139.84.x.x`) ou qualquer subdomínio que contenha números de IP (ex: `sige.139-84-x-x.sslip.io`) para o usuário, em atalhos (`sige.url`, `sige.cmd`), em arquivos de documentação ou nas respostas da conversa.
   - Qualquer comunicação sobre o sistema em produção deve utilizar exclusivamente o domínio oficial seguro `sigesaas.duckdns.org`.
3. **Nginx e Redirecionamento:**
   - Qualquer tentativa de acesso direto via IP deve ser redirecionada imediatamente (301) pelo Nginx para `https://sigesaas.duckdns.org/`.
