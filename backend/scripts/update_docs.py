"""
Script de Geração e Atualização Automática de Documentação — SIGE Backend (DRF)
Executa a introspecção de rotas, modelos e schemas OpenAPI.
"""
import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / 'apps'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.urls import get_resolver
from django.apps import apps
from drf_spectacular.generators import SchemaGenerator
import yaml

def gerar_modelos_markdown():
    output = ["# Catálogo de Modelos de Dados — SIGE (Django ORM)\n"]
    output.append("> Gerado automaticamente via introspecção do Django ORM.\n\n---\n")

    app_configs = apps.get_app_configs()
    for app in app_configs:
        if not app.name.startswith('apps.'):
            continue
        models = app.get_models()
        if not list(models):
            continue

        output.append(f"## Aplicação: `{app.name}`\n")
        for model in app.get_models():
            output.append(f"### Modelo: `{model.__name__}`\n")
            doc = model.__doc__ or "Sem descrição."
            output.append(f"{doc.strip()}\n")
            output.append("| Campo | Tipo | Nulo / Opcional | Descrição / Relação |")
            output.append("| :--- | :--- | :---: | :--- |")
            for field in model._meta.get_fields():
                if field.is_relation and field.auto_created:
                    continue
                tipo = field.get_internal_type() if hasattr(field, 'get_internal_type') else type(field).__name__
                null_str = "Sim" if getattr(field, 'null', False) else "Não"
                rel = ""
                if field.is_relation and hasattr(field, 'related_model') and field.related_model:
                    rel = f" -> `{field.related_model.__name__}`"
                output.append(f"| `{field.name}` | `{tipo}` | {null_str} | {rel} |")
            output.append("\n")

    docs_dir = BASE_DIR / 'docs'
    docs_dir.mkdir(exist_ok=True)
    target = docs_dir / 'DATABASE_MODELS.md'
    target.write_text('\n'.join(output), encoding='utf-8')
    print(f"[OK] Catálogo de modelos gerado em: {target}")

def extrair_rotas(url_patterns, prefix=''):
    routes = []
    for pattern in url_patterns:
        if hasattr(pattern, 'url_patterns'):
            new_prefix = prefix + str(pattern.pattern)
            routes.extend(extrair_rotas(pattern.url_patterns, new_prefix))
        elif hasattr(pattern, 'pattern'):
            path = prefix + str(pattern.pattern)
            # Normalizar
            path = '/' + path.lstrip('/')
            callback = getattr(pattern, 'callback', None)
            cb_name = getattr(callback, '__name__', str(callback))
            cls = getattr(callback, 'cls', None)
            if cls:
                cb_name = f"{cls.__module__}.{cls.__name__}"
            routes.append({'path': path, 'name': getattr(pattern, 'name', ''), 'handler': cb_name})
    return routes

def gerar_api_reference_markdown():
    resolver = get_resolver()
    rotas = extrair_rotas(resolver.url_patterns)

    # Filtrar rotas da API
    api_rotas = [r for r in rotas if r['path'].startswith('/api/v1/') or r['path'].startswith('/health/')]
    api_rotas.sort(key=lambda x: x['path'])

    output = ["# Referência Oficial de Endpoints da API — SIGE RESTful\n"]
    output.append("> Gerado automaticamente via introspecção das URLs e ViewSets do Django REST Framework.\n")
    output.append(f"**Total de Rotas Registadas:** {len(api_rotas)}\n\n---\n")
    output.append("| Rota da API | Nome da Rota | Controlador / View | Autenticação / Tenant |")
    output.append("| :--- | :--- | :--- | :--- |")

    for r in api_rotas:
        auth_note = "Pública" if any(p in r['path'] for p in ['/auth/login', '/auth/refresh', '/health', '/certificados/verificar']) else "Requer JWT (Escola)"
        output.append(f"| `{r['path']}` | `{r['name']}` | `{r['handler']}` | {auth_note} |")

    docs_dir = BASE_DIR / 'docs'
    docs_dir.mkdir(exist_ok=True)
    target = docs_dir / 'API_REFERENCE.md'
    target.write_text('\n'.join(output), encoding='utf-8')
    print(f"[OK] Referência de endpoints gerada em: {target}")

def atualizar_openapi_schema():
    generator = SchemaGenerator(title="SIGE API", description="API RESTful SaaS Multi-Tenant Moçambique")
    schema = generator.get_schema()
    schema_file = BASE_DIR / 'schema.yml'
    with open(schema_file, 'w', encoding='utf-8') as f:
        yaml.dump(schema, f, allow_unicode=True, sort_keys=False)
    print(f"[OK] OpenAPI Schema 3.0 sincronizado em: {schema_file}")

if __name__ == '__main__':
    print("[DOCS] Iniciando atualização automática da documentação do Backend...")
    gerar_modelos_markdown()
    gerar_api_reference_markdown()
    atualizar_openapi_schema()
    print("[DOCS] Todas as documentações do Backend foram sincronizadas com sucesso!")
