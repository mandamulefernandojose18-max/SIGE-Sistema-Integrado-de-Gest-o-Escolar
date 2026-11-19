# Guia: confirmação automática de pagamentos por SMS (M-Pesa / e-Mola)

Quem usa: **SuperAdmin**. Custo: zero (aplicação gratuita no telemóvel + a infraestrutura que já existe).

## Como funciona

1. A escola paga a assinatura para a conta M-Pesa/e-Mola oficial da plataforma e **submete o comprovativo** no SIGE,
   indicando como *referência* o **código da transacção** que vem na SMS de confirmação.
2. O telemóvel da plataforma recebe a SMS do M-Pesa/e-Mola e uma aplicação reencaminha-a para o SIGE.
3. O SIGE lê o **valor** e o **código** da SMS. Só confirma o pagamento se existir um comprovativo *pendente* com
   **o mesmo código e exactamente o mesmo valor**. Em qualquer dúvida, não confirma nada e fica para validação manual.

O sistema **nunca cria pagamentos** a partir de SMS: só confirma comprovativos já submetidos pela escola.

## Passo 1: criar o token (no SIGE)

1. Entre como SuperAdmin → **Assinaturas & Pagamentos** → botão **SMS automático**.
2. Escreva um nome (ex.: *Telemóvel M-Pesa da sede*) e clique **Criar token**.
3. **Copie o token agora**: só é mostrado uma vez (o SIGE guarda apenas uma impressão digital, não o valor).
4. Anote também o endereço mostrado na janela:

```
https://sigesaas.duckdns.org/api/v1/saas/webhook/sms/
```

## Passo 2: configurar a aplicação no telemóvel (Android)

Use uma aplicação de reencaminhamento de SMS que consiga **enviar um pedido HTTP (webhook) com cabeçalhos e corpo
personalizados**. Existem várias gratuitas (por exemplo, aplicações do tipo *SMS Forwarder*, ou o Tasker/MacroDroid
com a acção *HTTP Request*). Os nomes dos menus variam por aplicação e versão, mas os campos são sempre estes:

| Campo | Valor |
|---|---|
| Endereço (URL) | `https://sigesaas.duckdns.org/api/v1/saas/webhook/sms/` |
| Método | `POST` |
| Cabeçalho 1 | `Content-Type: application/json` |
| Cabeçalho 2 | `X-Webhook-Token: <o token copiado no passo 1>` |
| Corpo (JSON) | `{"message": "<texto da SMS>"}` |
| Filtro | só SMS do remetente do M-Pesa/e-Mola (o nome que aparece no telemóvel) |

No corpo, no lugar de `<texto da SMS>` use o **marcador do texto da mensagem** da própria aplicação. Costuma ser
`%text%`, `{{text}}` ou semelhante (veja a ajuda da aplicação). Exemplo: `{"message": "%text%"}`.

Também é preciso:
- dar à aplicação a **permissão de SMS**;
- **desactivar a optimização de bateria** para ela, senão o Android pode adormecê-la e perder SMS;
- manter o telemóvel com **internet** (dados ou Wi-Fi).

> iPhone: o iOS não permite reencaminhar SMS automaticamente de forma fiável. Use um telemóvel Android para esta função.

## Passo 3: testar

Envie um pedido de teste a partir do computador (PowerShell). Substitua `COLE_AQUI_O_TOKEN` pelo token:

```powershell
curl.exe -X POST "https://sigesaas.duckdns.org/api/v1/saas/webhook/sms/" -H "Content-Type: application/json" -H "X-Webhook-Token: COLE_AQUI_O_TOKEN" -d "{\"message\": \"Confirmado PP261118.1023.A12345. Recebeu 3,000.00MT de 841234567 aos 18/11/26\"}"
```

Para um teste completo: peça a uma escola (ou use uma escola de teste) para submeter um comprovativo com a referência
`PP261118.1023.A12345` e o valor `3000.00`, e depois envie o pedido acima.

## O que o SIGE responde

| `status` | Significado | O que fazer |
|---|---|---|
| `CONFIRMADO` | Pagamento confirmado e aplicado à fatura | Nada |
| `DUPLICADO` | Esse código já foi confirmado | Nada (a SMS chegou duas vezes) |
| `SEM_CORRESPONDENCIA` | Nenhum comprovativo pendente com esse código | Aguardar que a escola submeta o comprovativo; a SMS pode ser reenviada depois |
| `VALOR_DIVERGENTE` | O código existe mas o valor é diferente | Validar manualmente (pode ser pagamento parcial) |
| `AMBIGUO` | Mais de um comprovativo corresponde | Validar manualmente |
| `NAO_RECONHECIDA` | Não foi possível ler valor e código na SMS | Validar manualmente; verifique o formato da SMS |
| HTTP `401` | Token inválido ou revogado | Confirmar o token na aplicação / criar outro |

Cada confirmação automática fica registada na ficha da instituição como **PAGAMENTO_CONFIRMADO_SMS**, com o nome do token.

## Segurança

- O token **só serve para este endereço**; não dá acesso a mais nada no SIGE.
- Há um limite de 60 pedidos por minuto por origem e um máximo de 10 tokens activos.
- **Telemóvel perdido ou token exposto?** Em *SMS automático*, clique **Revogar**: deixa de funcionar de imediato. Crie outro.
- Não partilhe o token por mensagem ou e-mail; trate-o como uma palavra-passe.
- Use um token por telemóvel, com o nome do telemóvel, para saber qual foi usado e quando.

## Limitações

- Só confirma quando **código e valor coincidem exactamente**. Pagamentos parciais, em excesso ou com código diferente
  seguem para validação manual.
- A escola tem de usar como referência o código da transacção da SMS. Se escrever outra coisa, a reconciliação não encontra o comprovativo.
- Os formatos das SMS dos operadores podem mudar. Se uma SMS real não for reconhecida, envie o texto à equipa técnica
  (sem o token) para ajustar o leitor.
