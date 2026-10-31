# frontend/ — Convenções SPA/PWA (SIGE)

- Vanilla JS ES6+ modular em `js/`, páginas em `pages/`; Bootstrap 5.3.3, Bootstrap Icons, Chart.js 4.4.4. Sem frameworks pesados.
- Cadernetas/turmas: apenas por filtros em cascata (Classe → Secção/Área → Turma da Secção → Trimestre). Nunca listas abertas de botões ou chips; a altura da UI é constante para qualquer n.
- Sem dados fictícios: sem registos reais mostrar apenas o estado vazio explicativo.
- Mobile-first e responsivo; manter suporte offline/PWA (`service-worker.js`, `manifest.json`); alterar `version.json` ao mudar assets em cache.
- Tipografia de pautas/relatórios: Times New Roman; notas negativas a vermelho.
- Chamadas à API via `https://sigesaas.duckdns.org/api/v1/`; nunca usar IPs.
- Respeitar o RBAC por departamento: cada painel só mostra o que o perfil pode ver.
