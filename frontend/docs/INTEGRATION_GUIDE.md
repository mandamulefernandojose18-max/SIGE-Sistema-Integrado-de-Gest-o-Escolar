# Guia de Integração Frontend ↔ Backend — SIGE

## 1. Configuração da URL Base da API (`js/config.js`)

O frontend detecta dinamicamente a porta e o host onde está rodando. O arquivo `js/config.js` estabelece a variável global:

```javascript
window.SIGE_CONFIG = {
  API_BASE_URL: window.ENV_API_URL || (
    (window.location.port && window.location.port !== '8000' && window.location.port !== '80')
      ? (window.location.protocol + '//' + window.location.hostname + ':8000/api/v1')
      : '/api/v1'
  )
};
```

---

## 2. Padrão de Chamada à API (`apiFetch`)

Todas as requisições HTTP do frontend passam pela função centralizada `apiFetch(endpoint, options)`:

```javascript
async function apiFetch(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${window.SIGE_CONFIG.API_BASE_URL}${endpoint}`;
    
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {})
    };

    const token = localStorage.getItem('sige_access_token');
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, { ...options, headers });
    
    // Tratamento de Expiração de Licença SaaS (HTTP 402)
    if (response.status === 402) {
        exibirAvisoSubscricaoExpirada();
        throw new Error('Subscrição expirada');
    }

    // Tratamento de Sessão Expirada (HTTP 401)
    if (response.status === 401) {
        efetuarLogout();
        throw new Error('Sessão expirada');
    }

    return response;
}
```

---

## 3. Download de Documentos Oficiais (PDF, XLSX, DOCX)

Para endpoints que devolvem arquivos binários para impressão ou download:
```javascript
async function descarregarDocumento(endpoint, nomeArquivo) {
    const res = await apiFetch(endpoint);
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = nomeArquivo;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
}
```

---

## 4. Relação de Endpoints Consumidos por Módulo

| Módulo na UI | Rota do Backend | Método | Propósito |
| :--- | :--- | :---: | :--- |
| **Login** | `/api/v1/auth/login/` | POST | Autenticação e obtenção do JWT |
| **Perfil** | `/api/v1/auth/me/` | GET | Recuperação dos dados do utilizador e papel |
| **Turmas** | `/api/v1/turmas/` | GET, POST | Listagem e registo de turmas da escola |
| **Alunos** | `/api/v1/alunos/` | GET, POST | Matrículas e gestão de dados biográficos |
| **Professores** | `/api/v1/professores/` | GET, POST | Registo docente e alocações de turmas |
| **Caderneta** | `/api/v1/professores/caderneta/:id/completa/` | GET | Lançamento e consulta de notas contínuas |
| **Pautas** | `/api/v1/pautas/turma/:id/completa/` | GET | Visualização das médias e aprovações MINEDH |
| **Pauta em PDF** | `/api/v1/pautas/turma/:id/pdf/` | GET | Download da pauta oficial em PDF com QR Code |
| **Pauta em Excel** | `/api/v1/pautas/turma/:id/export-xlsx/` | GET | Download da pauta em folha de cálculo XLSX |
| **Acta em Word** | `/api/v1/pautas/turma/:id/docx/` | GET | Download da acta de conselho em DOCX |
| **Materiais** | `/api/v1/material-escolar/` | GET, POST | Repositório digital de manuais escolares |
| **Pagamentos** | `/api/v1/pagamentos/` | GET, POST | Gestão de propinas, emolumentos e recibos |
| **Certificados** | `/api/v1/certificados/` | GET, POST | Emissão e consulta de certificados |
