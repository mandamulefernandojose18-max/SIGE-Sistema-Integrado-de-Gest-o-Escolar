"""
Cobertura do Assistente: perguntas reais, escritas de formas variadas (informais, sem acentos, com erros), por perfil.
Cada uma tem de cair na capacidade certa PERMITIDA a esse perfil. É a rede de segurança para acrescentar capacidades sem partir as outras.
"""
import pytest
from apps.assistente.engine import classificar

# (perfil, pergunta, capacidade esperada)
CASOS = [
    # ---- Aluno
    ('ALUNO', 'quais sao as minhas notas', 'notas'), ('ALUNO', 'tenho negativas?', 'notas'), ('ALUNO', 'qual e a minha media', 'notas'),
    ('ALUNO', 'quantas faltas eu tenho', 'faltas'), ('ALUNO', 'tenho faltas por justificar?', 'faltas'), ('ALUNO', 'devo propinas?', 'propinas'),
    ('ALUNO', 'quanto devo da propina', 'propinas'), ('ALUNO', 'quando e o proximo teste', 'calendario'), ('ALUNO', 'que aulas tenho amanha', 'horario'),
    ('ALUNO', 'qual o meu horario de segunda', 'horario'), ('ALUNO', 'qual a minha turma', 'perfil_aluno'), ('ALUNO', 'quem e o meu director de turma', 'perfil_aluno'),
    ('ALUNO', 'qual o meu numero de matricula', 'perfil_aluno'), ('ALUNO', 'quanto preciso para passar a matematica', 'quanto_preciso'),
    ('ALUNO', 'como estou', 'resumo_aluno'), ('ALUNO', 'quando sao os exames', 'exames_calendario'), ('ALUNO', 'ha exames este mes?', 'exames_calendario'),
    ('ALUNO', 'quais os comunicados', 'comunicados'), ('ALUNO', 'contacto da escola', 'contactos_escola'), ('ALUNO', 'quando comeca o 2 trimestre', 'trimestres'),
    ('ALUNO', 'como justifico uma falta', 'guia_justificar_falta'), ('ALUNO', 'como pago a propina por mpesa', 'guia_pagar_propina'),
    ('ALUNO', 'preciso de uma declaracao', 'guia_pedir_documentos'), ('ALUNO', 'esqueci a senha', 'guia_recuperar_acesso'),
    ('ALUNO', 'material de matematica', 'material'), ('ALUNO', 'que disciplinas tenho', 'plano_curricular'), ('ALUNO', 'como se calcula a media trimestral', 'faq_mt'),
    ('ALUNO', 'o que sao as siglas ppf', 'faq_siglas'), ('ALUNO', 'regras para passar de classe', 'faq_aprovacao'), ('ALUNO', 'o que posso perguntar', 'guia_assistente_guia'),
    # ---- Encarregado
    ('ENCARREGADO', 'como esta o meu filho', 'resumo_aluno'), ('ENCARREGADO', 'quantas faltas tem o meu filho', 'faltas'),
    ('ENCARREGADO', 'o meu filho tem propinas em atraso', 'propinas'), ('ENCARREGADO', 'notas do meu filho', 'notas'), ('ENCARREGADO', 'o meu filho esta a passar?', 'quanto_preciso'),
    ('ENCARREGADO', 'quando e a reuniao de pais', 'calendario'), ('ENCARREGADO', 'ultimos avisos da escola', 'comunicados'), ('ENCARREGADO', 'telefone da escola', 'contactos_escola'),
    ('ENCARREGADO', 'como justifico as faltas do meu filho', 'guia_justificar_falta'), ('ENCARREGADO', 'como pago a mensalidade', 'guia_pagar_propina'),
    ('ENCARREGADO', 'em que turma esta o meu educando', 'perfil_aluno'), ('ENCARREGADO', 'preciso de um certificado', 'guia_pedir_documentos'),
    # ---- Professor
    ('PROFESSOR', 'como lanco as notas', 'guia_lancar_notas'), ('PROFESSOR', 'que turmas tenho', 'turmas_professor'), ('PROFESSOR', 'quantos alunos tenho', 'turmas_professor'),
    ('PROFESSOR', 'que aulas tenho hoje', 'horario'), ('PROFESSOR', 'qual o meu horario de quarta', 'horario'), ('PROFESSOR', 'minhas actividades de cargo', 'cargos'),
    ('PROFESSOR', 'alunos com negativa nas minhas turmas', 'aproveitamento'), ('PROFESSOR', 'como esta o aproveitamento', 'aproveitamento'),
    ('PROFESSOR', 'como registo as presencas', 'guia_registar_presencas'), ('PROFESSOR', 'como faco o sumario da aula', 'guia_sumarios'),
    ('PROFESSOR', 'como protejo uma prova contra ia', 'guia_antiia'), ('PROFESSOR', 'como gero a folha de resposta', 'guia_folha_resposta'),
    ('PROFESSOR', 'como se calcula a mfd', 'faq_mfd'), ('PROFESSOR', 'o que e a acs', 'faq_mac'), ('PROFESSOR', 'como lanco notas de exame', 'guia_exames'),
    ('PROFESSOR', 'o que faz o director de turma', 'guia_cargos_guia'), ('PROFESSOR', 'ultimos comunicados', 'comunicados'), ('PROFESSOR', 'datas dos trimestres', 'trimestres'),
    ('PROFESSOR', 'como registo uma ocorrencia disciplinar', 'guia_ocorrencias'), ('PROFESSOR', 'quando termina o trimestre', 'trimestres'),
    # ---- Secretaria
    ('SECRETARIA', 'quantos alunos temos', 'alunos_resumo'), ('SECRETARIA', 'ha transferencias pendentes', 'transferencias'), ('SECRETARIA', 'como faco uma transferencia', 'guia_transferencia'),
    ('SECRETARIA', 'como emito uma declaracao', 'guia_certificados'), ('SECRETARIA', 'como faco uma matricula', 'guia_matricula'), ('SECRETARIA', 'alunos devedores da 8 classe', 'devedores'),
    ('SECRETARIA', 'quem deve propinas', 'devedores'), ('SECRETARIA', 'ha atendimentos abertos', 'crm'), ('SECRETARIA', 'como registo um contacto com o encarregado', 'guia_crm_guia'),
    ('SECRETARIA', 'como imprimo um boletim', 'guia_impressao'), ('SECRETARIA', 'horario da 7 classe turma a', 'horario'), ('SECRETARIA', 'quantos professores temos', 'professores_resumo'),
    ('SECRETARIA', 'em que turma esta o joao', 'perfil_aluno'), ('SECRETARIA', 'ha alunos em risco', 'risco'), ('SECRETARIA', 'como liquido uma propina', 'guia_cobrar_propina'),
    # ---- DAP (Direcção Pedagógica / Área Pedagógica)
    ('DAP', 'como esta o aproveitamento', 'aproveitamento'), ('DAP', 'que pautas estao por fechar', 'pautas'), ('DAP', 'turmas sem director de turma', 'turmas'),
    ('DAP', 'professores sem turma', 'professores_resumo'), ('DAP', 'alunos em risco por faltas', 'risco'), ('DAP', 'como desbloqueio um trimestre', 'guia_desbloqueio'),
    ('DAP', 'como crio turmas em lote', 'guia_turmas'), ('DAP', 'como atribuo disciplinas a um professor', 'guia_alocacao_docente'), ('DAP', 'que disciplinas tem a 11 classe', 'plano_curricular'),
    ('DAP', 'actividades de cargo em atraso', 'cargos'), ('DAP', 'como emito a pauta e a acta', 'guia_pautas'), ('DAP', 'como vejo a estatistica de aproveitamento', 'guia_estatistica'),
    ('DAP', 'ha atendimentos abertos', 'crm'), ('DAP', 'como elaboro o horario', 'guia_horarios'), ('DAP', 'quando sao os exames', 'exames_calendario'),
    # ---- Director / Administrador
    ('DIRECTOR_ESCOLA', 'resumo da escola', 'resumo_escola'), ('DIRECTOR_ESCOLA', 'quando termina a assinatura', 'assinatura'), ('DIRECTOR_ESCOLA', 'qual o saldo de caixa', 'caixa'),
    ('DIRECTOR_ESCOLA', 'quem deve propinas', 'devedores'), ('DIRECTOR_ESCOLA', 'como redefino uma senha', 'guia_senhas'), ('DIRECTOR_ESCOLA', 'como vejo quem alterou uma nota', 'guia_auditoria'),
    ('DIRECTOR_ESCOLA', 'como pago a assinatura', 'guia_assinatura_guia'), ('DIRECTOR_ESCOLA', 'como aprovo uma despesa', 'guia_despesas'), ('DIRECTOR_ESCOLA', 'como esta a escola', 'resumo_escola'),
    ('DIRECTOR_ESCOLA', 'como esta o aproveitamento', 'aproveitamento'), ('DIRECTOR_ESCOLA', 'quantos alunos temos', 'alunos_resumo'), ('DIRECTOR_ESCOLA', 'como publico um comunicado', 'guia_comunicados'),
    ('ADMIN_ESCOLA', 'quando expira a assinatura', 'assinatura'), ('ADMIN_ESCOLA', 'ha transferencias pendentes', 'transferencias'), ('ADMIN_ESCOLA', 'esqueci a senha', 'guia_recuperar_acesso'),
    ('CHEFE_SECRETARIA', 'como emito um certificado', 'guia_certificados'), ('CHEFE_SECRETARIA', 'ha transferencias pendentes', 'transferencias'),
    # ---- Financeiro
    ('FINANCEIRO', 'qual o saldo de caixa', 'caixa'), ('FINANCEIRO', 'quem nao pagou a propina', 'devedores'), ('FINANCEIRO', 'como gero as cobrancas', 'guia_cobrar_propina'),
    ('FINANCEIRO', 'como registo uma despesa', 'guia_despesas'), ('FINANCEIRO', 'como envio sms aos encarregados', 'guia_gateway'), ('FINANCEIRO', 'como imprimo um recibo', 'guia_impressao'),
    ('FINANCEIRO', 'contacto da escola', 'contactos_escola'),
    # ---- Super Admin (plataforma)
    ('SUPERADMIN', 'quantas escolas temos', 'plat_resumo'), ('SUPERADMIN', 'ha comprovativos por validar', 'plat_pagamentos'), ('SUPERADMIN', 'faturas em atraso', 'plat_faturas'),
    ('SUPERADMIN', 'qual o mrr', 'plat_mrr'), ('SUPERADMIN', 'quantas assinaturas estao em atraso', 'plat_assinaturas'), ('SUPERADMIN', 'que planos temos', 'plat_planos'),
    ('SUPERADMIN', 'como cadastro uma escola', 'guia_saas_cadastrar'), ('SUPERADMIN', 'como inspeciono uma escola', 'guia_saas_inspeccionar'),
    ('SUPERADMIN', 'como renovo a assinatura de uma escola', 'guia_saas_renovar'), ('SUPERADMIN', 'como valido um comprovativo', 'guia_pagamentos_saas'),
    ('SUPERADMIN', 'como esta a correr o assistente', 'plat_assistente'), ('SUPERADMIN', 'o que posso perguntar', 'guia_assistente_guia'),
]


@pytest.mark.parametrize('role,pergunta,esperado', CASOS, ids=[f'{r}:{p}' for r, p, _ in CASOS])
def test_pergunta_cai_na_capacidade_certa(role, pergunta, esperado):
    assert classificar(pergunta, role=role)[0] == esperado


def test_banco_de_perguntas_cobre_todos_os_perfis():
    assert {r for r, _p, _e in CASOS} == {'ALUNO', 'ENCARREGADO', 'PROFESSOR', 'SECRETARIA', 'DAP', 'DIRECTOR_ESCOLA', 'ADMIN_ESCOLA', 'CHEFE_SECRETARIA',
                                          'FINANCEIRO', 'SUPERADMIN'}
    assert len(CASOS) >= 120
