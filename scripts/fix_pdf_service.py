# -*- coding: utf-8 -*-
with open('backend/apps/documentos/services/pdf_service.py', 'r', encoding='utf-8') as f:
    c = f.read()

target = '''    txt_resumo = (
        f"Total Inscritos: <b>{tot_al}</b> (H: {h_n} | M: {m_n}) | "
        f"Avaliados: <b>{tot_al}</b> | "
        f"<font color="#059669">Aprovados: <b>{aprov_n}</b> ({pct_aprov}%)</font> | "
        f"<font color="#dc2626">Reprovados: <b>{reprov_n}</b> ({pct_reprov}%)</font>"
    )'''

replacement = '''    txt_resumo = (
        f"Total Inscritos: <b>{tot_al}</b> (H: {h_n} | M: {m_n}) | "
        f"Avaliados: <b>{tot_al}</b> | "
        f"<font color='#059669'>Aprovados: <b>{aprov_n}</b> ({pct_aprov}%)</font> | "
        f"<font color='#dc2626'>Reprovados: <b>{reprov_n}</b> ({pct_reprov}%)</font>"
    )'''

c_norm = c.replace('\r\n', '\n')
t_norm = target.replace('\r\n', '\n')
r_norm = replacement.replace('\r\n', '\n')

if t_norm in c_norm:
    c_norm = c_norm.replace(t_norm, r_norm)
    with open('backend/apps/documentos/services/pdf_service.py', 'w', encoding='utf-8') as f:
        f.write(c_norm)
    print('Fixed pdf_service.py successfully!')
else:
    print('Target not found')
