import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from apps.disciplinas.models import Disciplina

# Obter todas as escolas que têm disciplinas ou existem
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT id, nome FROM sige_escolas")
    escolas = cursor.fetchall()

print(f"Total de escolas encontradas: {len(escolas)}")

CURRICULO = [
    # 7ª Classe
    {"classe": "7ª Classe", "area": "Ensino Geral", "disciplinas": [
        ("LP-07", "Língua Portuguesa", 5),
        ("MAT-07", "Matemática", 5),
        ("ING-07", "Língua Inglesa", 3),
        ("FIS-07", "Física", 3),
        ("QUI-07", "Química", 3),
        ("BIO-07", "Biologia", 3),
        ("GEO-07", "Geografia", 3),
        ("HIS-07", "História", 3),
        ("EV-07", "Educação Visual", 2),
        ("EF-07", "Educação Física", 2),
        ("AGRO-07", "Agropecuária", 2),
    ]},
    # 8ª Classe
    {"classe": "8ª Classe", "area": "Ensino Geral", "disciplinas": [
        ("LP-08", "Língua Portuguesa", 5),
        ("MAT-08", "Matemática", 5),
        ("ING-08", "Língua Inglesa", 3),
        ("FIS-08", "Física", 3),
        ("QUI-08", "Química", 3),
        ("BIO-08", "Biologia", 3),
        ("GEO-08", "Geografia", 3),
        ("HIS-08", "História", 3),
        ("EV-08", "Educação Visual", 2),
        ("EF-08", "Educação Física", 2),
        ("AGRO-08", "Agropecuária", 2),
    ]},
    # 9ª Classe
    {"classe": "9ª Classe", "area": "Ensino Geral", "disciplinas": [
        ("LP-09", "Língua Portuguesa", 5),
        ("MAT-09", "Matemática", 5),
        ("ING-09", "Língua Inglesa", 3),
        ("FIS-09", "Física", 3),
        ("QUI-09", "Química", 3),
        ("BIO-09", "Biologia", 3),
        ("GEO-09", "Geografia", 3),
        ("HIS-09", "História", 3),
        ("EV-09", "Educação Visual", 2),
        ("EF-09", "Educação Física", 2),
        ("AGRO-09", "Agropecuária", 2),
    ]},
    # 10ª Classe
    {"classe": "10ª Classe", "area": "Ensino Geral", "disciplinas": [
        ("LP-10", "Língua Portuguesa", 5),
        ("MAT-10", "Matemática", 5),
        ("ING-10", "Língua Inglesa", 3),
        ("FIS-10", "Física", 3),
        ("QUI-10", "Química", 3),
        ("BIO-10", "Biologia", 3),
        ("GEO-10", "Geografia", 3),
        ("HIS-10", "História", 3),
        ("FILO-10", "Filosofia", 2),
        ("EF-10", "Educação Física", 2),
        ("AGRO-10", "Agropecuária", 2),
    ]},
    # 11ª Classe - Ciências com Biologia
    {"classe": "11ª Classe", "area": "Ciências com Biologia", "disciplinas": [
        ("LP-11CB", "Língua Portuguesa", 4),
        ("ING-11CB", "Língua Inglesa", 3),
        ("FILO-11CB", "Filosofia", 3),
        ("EF-11CB", "Educação Física", 2),
        ("MAT-11CB", "Matemática", 5),
        ("BIO-11CB", "Biologia", 5),
        ("QUI-11CB", "Química", 4),
        ("FIS-11CB", "Física", 4),
    ]},
    # 11ª Classe - Ciências com Desenho
    {"classe": "11ª Classe", "area": "Ciências com Desenho", "disciplinas": [
        ("LP-11CD", "Língua Portuguesa", 4),
        ("ING-11CD", "Língua Inglesa", 3),
        ("FILO-11CD", "Filosofia", 3),
        ("EF-11CD", "Educação Física", 2),
        ("MAT-11CD", "Matemática", 5),
        ("FIS-11CD", "Física", 5),
        ("DGD-11CD", "Desenho e Geometria Descritiva", 5),
        ("QUI-11CD", "Química", 3),
    ]},
    # 11ª Classe - Ciências com Geografia
    {"classe": "11ª Classe", "area": "Ciências com Geografia", "disciplinas": [
        ("LP-11CG", "Língua Portuguesa", 4),
        ("ING-11CG", "Língua Inglesa", 4),
        ("FILO-11CG", "Filosofia", 3),
        ("EF-11CG", "Educação Física", 2),
        ("MAT-11CG", "Matemática", 5),
        ("GEO-11CG", "Geografia", 5),
        ("FIS-11CG", "Física", 4),
        ("QUI-11CG", "Química", 3),
        ("AGRO-11CG", "Agropecuária", 3),
    ]},
    # 11ª Classe - Letras com Geografia
    {"classe": "11ª Classe", "area": "Letras com Geografia", "disciplinas": [
        ("LP-11LG", "Língua Portuguesa", 5),
        ("ING-11LG", "Língua Inglesa", 4),
        ("FRAN-11LG", "Língua Francesa", 3),
        ("FILO-11LG", "Filosofia", 3),
        ("HIS-11LG", "História", 4),
        ("GEO-11LG", "Geografia", 5),
        ("MATA-11LG", "Matemática Aplicada", 3),
        ("EF-11LG", "Educação Física", 2),
    ]},
    # 11ª Classe - Letras com História
    {"classe": "11ª Classe", "area": "Letras com História", "disciplinas": [
        ("LP-11LH", "Língua Portuguesa", 5),
        ("ING-11LH", "Língua Inglesa", 4),
        ("FRAN-11LH", "Língua Francesa", 3),
        ("FILO-11LH", "Filosofia", 3),
        ("HIS-11LH", "História", 5),
        ("GEO-11LH", "Geografia", 4),
        ("LIT-11LH", "Introdução à Literatura", 3),
        ("EF-11LH", "Educação Física", 2),
    ]},
    # 12ª Classe - Ciências com Biologia
    {"classe": "12ª Classe", "area": "Ciências com Biologia", "disciplinas": [
        ("LP-12CB", "Língua Portuguesa", 4),
        ("ING-12CB", "Língua Inglesa", 3),
        ("FILO-12CB", "Filosofia", 3),
        ("EF-12CB", "Educação Física", 2),
        ("MAT-12CB", "Matemática", 5),
        ("BIO-12CB", "Biologia", 5),
        ("QUI-12CB", "Química", 4),
        ("FIS-12CB", "Física", 4),
    ]},
    # 12ª Classe - Ciências com Desenho
    {"classe": "12ª Classe", "area": "Ciências com Desenho", "disciplinas": [
        ("LP-12CD", "Língua Portuguesa", 4),
        ("ING-12CD", "Língua Inglesa", 3),
        ("FILO-12CD", "Filosofia", 3),
        ("EF-12CD", "Educação Física", 2),
        ("MAT-12CD", "Matemática", 5),
        ("FIS-12CD", "Física", 5),
        ("DGD-12CD", "Desenho e Geometria Descritiva", 5),
        ("QUI-12CD", "Química", 3),
    ]},
    # 12ª Classe - Ciências com Geografia
    {"classe": "12ª Classe", "area": "Ciências com Geografia", "disciplinas": [
        ("LP-12CG", "Língua Portuguesa", 4),
        ("ING-12CG", "Língua Inglesa", 4),
        ("FILO-12CG", "Filosofia", 3),
        ("EF-12CG", "Educação Física", 2),
        ("MAT-12CG", "Matemática", 5),
        ("GEO-12CG", "Geografia", 5),
        ("FIS-12CG", "Física", 4),
        ("QUI-12CG", "Química", 3),
        ("AGRO-12CG", "Agropecuária", 3),
    ]},
    # 12ª Classe - Letras com Geografia
    {"classe": "12ª Classe", "area": "Letras com Geografia", "disciplinas": [
        ("LP-12LG", "Língua Portuguesa", 5),
        ("ING-12LG", "Língua Inglesa", 4),
        ("FRAN-12LG", "Língua Francesa", 3),
        ("FILO-12LG", "Filosofia", 3),
        ("HIS-12LG", "História", 4),
        ("GEO-12LG", "Geografia", 5),
        ("MATA-12LG", "Matemática Aplicada", 3),
        ("EF-12LG", "Educação Física", 2),
    ]},
    # 12ª Classe - Letras com História
    {"classe": "12ª Classe", "area": "Letras com História", "disciplinas": [
        ("LP-12LH", "Língua Portuguesa", 5),
        ("ING-12LH", "Língua Inglesa", 4),
        ("FRAN-12LH", "Língua Francesa", 3),
        ("FILO-12LH", "Filosofia", 3),
        ("HIS-12LH", "História", 5),
        ("GEO-12LH", "Geografia", 4),
        ("LIT-12LH", "Introdução à Literatura", 3),
        ("EF-12LH", "Educação Física", 2),
    ]},
]

from apps.tenants.models import Escola

# Buscar disciplinas existentes para não duplicar
existing_keys = set(Disciplina.objects.filter(ano_letivo='2026').values_list('escola_id', 'codigo'))
print(f"Disciplinas existentes no banco com ano 2026: {len(existing_keys)}")

novos_objetos = []
for esc_id, esc_nome in escolas:
    print(f"Avaliando escola: {esc_nome} ({esc_id})...")
    for bloco in CURRICULO:
        classe = bloco["classe"]
        area = bloco["area"]
        for codigo, nome, carga in bloco["disciplinas"]:
            if (esc_id, codigo) not in existing_keys:
                novos_objetos.append(Disciplina(
                    escola_id=esc_id,
                    codigo=codigo,
                    nome=nome,
                    classe=classe,
                    area=area,
                    carga_horaria=carga,
                    ano_letivo="2026"
                ))
                existing_keys.add((esc_id, codigo))

print(f"Total de novas disciplinas a criar em lote: {len(novos_objetos)}")
if novos_objetos:
    Disciplina.objects.bulk_create(novos_objetos, batch_size=500)
    print("Bulk create concluído com sucesso!")

print(f"Total final de disciplinas no sistema: {Disciplina.objects.count()}")
