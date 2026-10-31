---
description: Executa a bateria de testes automatizados do backend Django e verifica integridade dos endpoints.
---

# Testes Automatizados do SIGE

Comandos para execução dos testes:

```powershell
cd d:\SIGE\backend
.\venv\Scripts\activate
pytest
```

Para executar testes de um módulo específico:
```powershell
pytest core/tests/test_auth.py
pytest core/tests/test_notas.py
pytest core/tests/test_pautas.py
```
