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

## 🚫 Regra Inquebrável: Proibição Absoluta de Dados Fictícios (Zero Mock/Fake Data)
- **NUNCA** gerar, cadastrar, simular ou introduzir cadernetas, turmas, notas, alunos, professores ou dados fictícios no sistema.
- O sistema lida com dados oficiais da educação e deve operar **100% com registros reais** persistidos no banco de dados. Caso não existam dados alocados, deve-se apresentar exclusivamente o estado vazio explicativo real.

## 📐 Regra de Interface: Escalabilidade Teórica sem Limite ($n$ Cadernetas)
- Considerar sempre a escala como **$n$ cadernetas** ($n$ sem limite fixo ou pré-definido).
- **NUNCA** renderizar cadernetas, turmas ou registos em listas abertas de botões ou chips que possam encher a tela e explodir visualmente conforme $n$ cresce.
- O acesso a cadernetas deve ser feito **estritamente por filtros em cascata** (`Classe` &rarr; `Secção / Área` &rarr; `Turma da Secção` &rarr; `Trimestre`), mantendo a altura da interface compacta e constante $\mathcal{O}(1)$ para qualquer valor de $n$.

## 🔄 Regra Mandatória: Sincronização Contínua de Documentação e Auto-Deploy
- **SEMPRE** que qualquer actualização for realizada no sistema (código, modelo de dados, regra de negócio, endpoint, telas ou infraestrutura):
  1. **Atualizar a documentação** correspondente na suite de manuais em `docs/` (`DOCUMENTACAO_COMPLETA_DO_SISTEMA.md`, `README.md`, etc.).
  2. **Executar git commit semântico** com mensagem descritiva.
  3. **Executar git push** para o repositório remoto.
  4. **Executar o deploy desacoplado** na VM de produção (`sigesaas.duckdns.org`), validando o funcionamento dos serviços e os atalhos locais `sige`.
