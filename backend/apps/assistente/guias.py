"""
Guias "como se faz" por módulo do SIGE. Texto fiel a docs/MANUAL_DE_MODULOS_E_OPERACAO.md e
docs/DOCUMENTACAO_COMPLETA_DO_SISTEMA.md. Quando a documentação mudar, actualizar também aqui.

Cada guia: id, chaves (palavras-chave já normalizadas, com espaço à volta), texto, destino (id do ecrã do menu) e rótulo do atalho.
"""

GUIAS = [
    {'id': 'ano_lectivo', 'destino': None,
     'chaves': [' pagina vazia', ' em branco', ' nao aparece', ' nao carrega', ' buscar ', ' escolher o ano', ' escolha o ano'],
     'texto': 'Na maioria dos módulos a página só mostra dados depois de escolher o Ano Lectivo e carregar em "Buscar". '
              'Se a página está vazia, escolha o Ano Lectivo no topo da página e clique em Buscar.'},
    {'id': 'matricula', 'destino': 'alunos', 'rotulo': 'Abrir Alunos & Matrículas',
     'chaves': [' matricula', ' matricular', ' inscrever', ' inscricao', ' cadastrar aluno', ' ficha do aluno', ' registar aluno'],
     'texto': 'Em Alunos & Matrículas faz-se o registo biográfico completo (filiação, NUIT, identificação, contactos e turma). '
              'O seletor de classe só mostra as classes do Plano Curricular; ao escolher turma, o aluno herda a classe e a área dessa turma. '
              'Usam este módulo a Chefe de Secretaria, o Administrador e o DAP.'},
    {'id': 'turmas', 'destino': 'turmas', 'rotulo': 'Abrir Turmas',
     'chaves': [' criar turma', ' criar uma turma', ' crio turma', ' crio uma turma', ' formacao automatica', ' lotacao', ' renumerar', ' capacidade da turma'],
     'texto': 'Em Turmas & Capacidade o DAP, o Director e o Administrador criam turmas (uma a uma ou em lote, capacidade padrão 50). '
              'A classe e a secção/área vêm do Plano Curricular. A barra de ocupação fica verde abaixo de 80%, amarela a partir de 80% e vermelha quando a turma está lotada. '
              'A Formação Automática distribui os alunos sem turma por ordem alfabética ou equilibrando o género.'},
    {'id': 'plano_curricular', 'destino': 'plano-curricular', 'rotulo': 'Abrir Plano Curricular',
     'chaves': [' plano curricular', ' cadastrar disciplina', ' adicionar disciplina', ' classe tem exame', ' areas e seccoes'],
     'texto': 'O Plano Curricular (Área Pedagógica) é uma só página com 4 passos: 1) Classe/Nível e se tem exame; 2) Disciplinas da classe, escolhidas do catálogo "Todas Disciplinas de Ensino"; '
              '3) Áreas/Secções; 4) Disciplinas por área (com "Tem exame?" quando a classe tem exame). Edita a Direcção, o DAP e a Chefe de Secretaria; os restantes só consultam. '
              'Este plano condiciona turmas, matrículas, pautas e exames.'},
    {'id': 'alocacao_docente', 'destino': 'professores', 'rotulo': 'Abrir Atribuição & Docentes',
     'chaves': [' alocacao', ' alocar professor', ' atribuir disciplina', ' carga horaria do professor', ' horas extras', ' carreira'],
     'texto': 'Em Atribuição & Docentes (DAP e Administrador) associa-se Professor + Turma + Disciplina; isso cria automaticamente as grelhas dos 3 trimestres da caderneta. '
              'O sistema controla a carga horária semanal e separa horas normais de horas extras.'},
    {'id': 'lancar_notas', 'destino': 'caderneta', 'rotulo': 'Abrir a Caderneta',
     'chaves': [' lancar nota', ' lancar as notas', ' lancamento de nota', ' caderneta', ' como lanco', ' registar nota'],
     'texto': 'As notas são lançadas na Caderneta pelo professor da disciplina: no ano lectivo certo aparecem as suas turmas e o botão "Lançar as notas". '
              'Só o professor lança notas e só nas suas turmas (os outros perfis consultam e exportam). A MT só é apurada com a 1.ª e 2.ª ACS e a AT. '
              'Fora do prazo, ou com a pauta fechada, a Direcção/DAP pode conceder um desbloqueio temporário.'},
    {'id': 'desbloqueio', 'destino': 'desbloqueio', 'rotulo': 'Abrir Desbloqueio de Trimestre',
     'chaves': [' desbloque', ' prazo de notas', ' prazos de lancamento', ' reabrir trimestre', ' fora do prazo'],
     'texto': 'Em Desbloqueio de Trimestre (DAP e Director) definem-se as datas de abertura e encerramento do lançamento de notas dos 3 trimestres, '
              'e pode dar-se a um professor uma autorização temporária e justificada para lançar ou corrigir notas fora do prazo ou com a pauta fechada.'},
    {'id': 'pautas', 'destino': 'pautas', 'rotulo': 'Abrir Pautas & Actas',
     'chaves': [' emitir pauta', ' pauta geral', ' acta', ' actas', ' conselho de avaliacao', ' conselho de notas', ' fechar pauta'],
     'texto': 'Em Pautas & Actas (Director de Turma, DAP e Director) há duas abas: a Pauta Geral da Turma (disciplinas com 1.º, 2.º, 3.º trimestre e MFD, negativas, média geral e resultado) '
              'e a Acta do Conselho de Avaliação (valores por extenso). Exporta-se em Excel e PDF (A4 paisagem). O Director de Turma define data, hora e presidente da sessão do conselho.'},
    {'id': 'exames', 'destino': 'exames', 'rotulo': 'Abrir Exames',
     'chaves': [' pauta de exame', ' lancar nota de exame', ' parametros do exame', ' nota final do exame'],
     'texto': 'Em Exames só aparecem as turmas de classes "Com Exame" (padrão MEC: 10.ª e 12.ª). A frequência vem das cadernetas dos 3 trimestres; em "Parâmetros do Exame" definem-se os pesos (a soma tem de ser 100%) e a nota mínima. '
              'Lançam-se as notas da 1.ª e 2.ª época e guarda-se; exporta-se em Excel ou PDF. As classificações alimentam o Certificado e a Declaração com Notas.'},
    {'id': 'juris', 'destino': 'calendario-exames', 'rotulo': 'Abrir Calendário e Júris dos Exames',
     'chaves': [' juri', ' juris', ' excluidos do exame', ' alunos excluidos'],
     'texto': 'Em Área Pedagógica → Calendário e Júris dos Exames consulta-se o calendário das provas, os júris e os alunos excluídos dos exames.'},
    {'id': 'estatistica', 'destino': 'estatisticas-aproveitamento', 'rotulo': 'Abrir Estatística de Aproveitamento',
     'chaves': [' estatistica', ' taxa de aprovacao', ' ranking de reprovacao', ' aproveitamento'],
     'texto': 'A Estatística de Aproveitamento (DAP, Director e Administrador) tem 4 níveis: resumo da escola, por classe, por turma (com o Director de Turma) e por disciplina e docente. Exporta-se em PDF e Excel.'},
    {'id': 'certificados', 'destino': 'certificados', 'rotulo': 'Abrir Certificados & Declarações',
     'chaves': [' certificado', ' declaracao', ' comprovativo de matricula', ' habilitacoes'],
     'texto': 'Em Certificados & Declarações (Chefe de Secretaria e Director) emitem-se Conclusão de Classe/Ciclo, Guia de Transferência, Declaração com Notas e Comprovativo de Matrícula, '
              'cada um com código único e QR Code de verificação. Também pode imprimir-se pela Central de Impressão (PDF, Word ou Excel).'},
    {'id': 'pagar_propina', 'destino': 'aluno-pagamentos', 'rotulo': 'Abrir As Minhas Propinas',
     'chaves': [' como pago', ' pagar propina', ' pagar a propina', ' pagamento por', ' m pesa', ' mpesa', ' e mola', ' emola', ' recibo'],
     'texto': 'Pode pagar a propina por carteira móvel (M-Pesa ou e-Mola), POS, transferência bancária ou numerário. No Espaço do Aluno → As Minhas Propinas vê as faturas pendentes e pagas; '
              'o recibo oficial (REC-...) só mostra "PAGO" depois de o pagamento ser confirmado, e até lá mostra "NÃO PAGO". Na secretaria pode liquidar-se mediante comprovativo (talão, mensagem M-Pesa/e-Mola ou dinheiro).'},
    {'id': 'cobrar_propina', 'destino': 'pagamentos', 'rotulo': 'Abrir Propinas & Mensalidades',
     'chaves': [' gerar propina', ' gerar cobranca', ' cobranca', ' cobrancas', ' faturacao em lote', ' plano de pagamento', ' tabela de propinas', ' liquidar'],
     'texto': 'Em Propinas & Mensalidades (Financeiro, Chefe de Secretaria, Director e Administrador) há duas abas: Cobranças (geração individual ou em lote por turma e mês, e liquidação multicanal com recibo) '
              'e Planos & Tabela de Propinas (valor, periodicidade, dia de vencimento e multa por atraso). O sistema bloqueia faturas duplicadas.'},
    {'id': 'despesas', 'destino': 'despesas', 'rotulo': 'Abrir Receitas & Despesas',
     'chaves': [' registar despesa', ' aprovar despesa', ' folha de salario', ' patrimonio', ' receitas e despesas'],
     'texto': 'Receitas e despesas são registadas pelo Financeiro e aprovadas exclusivamente pelo Director da Escola (separação de funções: o Financeiro não aprova). '
              'No mesmo módulo processa-se a folha de salário mensal e regista-se o património da escola.'},
    {'id': 'impressao', 'destino': 'impressao', 'rotulo': 'Abrir a Central de Impressão',
     'chaves': [' imprimir', ' impressao', ' boletim', ' ficha biografica', ' descarregar documento', ' exportar documento'],
     'texto': 'A Central de Impressão gera Boletim, Declaração com Notas, Certificado de Habilitações, Recibo, Ficha, Pauta, Pauta de Exames, Acta, Caderneta e Estatísticas, em PDF, Word ou Excel, '
              'individualmente ou em lote por turma. Os ficheiros descarregam-se como "Documento - Nome do aluno - Ano". É obrigatório ter um logótipo escolhido nas definições da escola.'},
    {'id': 'portal_aluno', 'destino': 'aluno-perfil', 'rotulo': 'Abrir O Meu Perfil',
     'chaves': [' portal do aluno', ' o meu perfil', ' espaco do aluno', ' ver as minhas notas', ' meu boletim'],
     'texto': 'O Espaço do Aluno tem o perfil e comprovativo de matrícula, as notas e o boletim (apenas os trimestres que a escola publicou), as faltas, o calendário, o horário, as propinas e o material escolar da classe.'},
    {'id': 'senhas', 'destino': 'usuarios-senhas', 'rotulo': 'Abrir Utilizadores & Permissões',
     'chaves': [' redefinir senha', ' redefino', ' redefinir', ' esqueci a senha', ' esqueci a palavra', ' palavra passe', ' criar utilizador', ' bloquear utilizador', ' codigo de acesso', ' senha do professor'],
     'texto': 'Em Utilizadores & Permissões (Administrador, Director, DAP e Chefe de Secretaria) o sistema gera as contas em falta (direcção, professores, directores de turma e alunos), '
              'mostra os códigos de acesso, redefine palavras-passe esquecidas e bloqueia ou desbloqueia utilizadores. Quem esqueceu a senha deve pedir a redefinição a esses perfis.'},
    {'id': 'auditoria', 'destino': 'auditoria', 'rotulo': 'Abrir a Auditoria',
     'chaves': [' auditoria', ' quem alterou', ' quem lancou', ' trilha', ' log de acesso', ' registo de acessos'],
     'texto': 'A Auditoria de Operações (Direcção da Escola) regista notas lançadas ou alteradas, pagamentos, transferências e alterações cadastrais, com filtros por data, utilizador e acção e o antes/depois. '
              'O registo de acessos (sessões, tentativas inválidas) está em Acessos, para o Administrador.'},
    {'id': 'assinatura_guia', 'destino': 'assinatura-escola', 'rotulo': 'Abrir Assinatura do Sistema',
     'chaves': [' renovar assinatura', ' pagar assinatura', ' fatura da assinatura', ' comprovativo da assinatura'],
     'texto': 'Em Assinatura do Sistema (Administrador e Director) vê o estado da subscrição, o plano, o próximo vencimento e as faturas, e envia o comprovativo de pagamento. '
              'Pode pagar por M-Pesa, e-Mola ou transferência bancária (Millennium BIM e BCI), com validação pelo SuperAdmin.'},
    {'id': 'gateway', 'destino': 'prompt-gateway', 'rotulo': 'Abrir o Gateway SMS',
     'chaves': [' enviar sms', ' sms', ' whatsapp', ' ussd', ' reconciliacao', ' gateway'],
     'texto': 'O Gateway (SMS e Pagamentos) permite enviar mensagens por SMS (telemóvel Android da escola), por WhatsApp (link direto) ou em modo de teste, a destinatários manuais, por turma ou a quem tem propinas pendentes, '
              'com modelos prontos (propina, recibo, convocatória, falta, pautas). Também reconcilia os SMS de M-Pesa/e-Mola sem duplicar referências.'},
    {'id': 'material', 'destino': 'material-escolar', 'rotulo': 'Abrir Material Escolar',
     'chaves': [' carregar material', ' publicar material', ' biblioteca digital', ' manual escolar'],
     'texto': 'A Biblioteca Digital de Material Escolar guarda manuais, fichas e planos organizados por classe. Aceita ficheiros até 15 MB (PDF, DOCX, XLSX, PPTX, imagens) ou ligações externas, com permissões por perfil.'},
    {'id': 'justificar_falta', 'destino': 'presencas', 'rotulo': 'Abrir Presenças dos Alunos',
     'chaves': [' justificar falta', ' justificar uma falta', ' justificacao de falta', ' pedir justificacao', ' anular justificacao'],
     'texto': 'Cada falta vale 1 (aula simples) ou 2 (aula dupla). O aluno ou encarregado pode pedir a justificação de uma falta injustificada; quem decide é a secretaria/direcção, indicando disciplina, trimestre, '
              'quantidade de faltas e motivo (as mais antigas são abatidas primeiro e a justificação pode ser anulada). As faltas efectivas são as marcadas menos as justificadas.'},
    {'id': 'registar_presencas', 'destino': 'presencas', 'rotulo': 'Abrir Presenças dos Alunos',
     'chaves': [' registar presenca', ' registo presenca', ' registo de presenca', ' marcar presenca', ' registar faltas', ' lancar faltas', ' tipo de aula'],
     'texto': 'O professor regista as presenças em Presenças dos Alunos: escolha o Ano Lectivo e Buscar, depois Classe → Secção/Área → Turma → Disciplina → Data, indique se a aula é simples ou dupla e marque Presente, '
              'Falta justificada, Falta injustificada ou Atraso. Não se aceitam datas futuras e o professor só vê as suas turmas e disciplinas.'},
    {'id': 'transferencia', 'destino': 'transferencias', 'rotulo': 'Abrir Transferências & Anulações',
     'chaves': [' transferencia', ' transferir', ' anular matricula', ' anulacao de matricula', ' guia de transferencia'],
     'texto': 'A Secretaria abre o processo (saída, entrada ou anulação de matrícula) escolhendo o aluno, o motivo e anexando o pedido do encarregado; confirma-se a quitação (biblioteca, material, documentos e propinas em aberto) '
              'e o Director homologa ou rejeita. A homologação emite a Guia de Transferência (GT-AAAA-NNNN) ou a Declaração de Anulação (DA-AAAA-NNNN), com QR de verificação. '
              'Só alunos activos e sem outro processo pendente.'},
    {'id': 'comunicados', 'destino': 'comunicados', 'rotulo': 'Abrir Comunicados',
     'chaves': [' publicar comunicado', ' publicar um comunicado', ' publico um comunicado', ' criar comunicado', ' enviar circular', ' fazer um aviso'],
     'texto': 'Em Comunicados publicam-se circulares e avisos com público-alvo (todos, professores, alunos, encarregados ou secretaria), com publicação supervisionada pela Direcção e pelo DAP.'},
    {'id': 'horarios', 'destino': 'horarios', 'rotulo': 'Abrir Horários',
     'chaves': [' criar horario', ' elaborar horario', ' aprovar horario', ' grelha de horario'],
     'texto': 'Os Horários são uma grelha semanal (2.ª a sábado) de disciplina, professor, sala e tempo lectivo. O DAP elabora (rascunho) e o Director aprova; só os horários aprovados são vistos por professores e alunos.'},
    {'id': 'sumarios', 'destino': 'sumarios', 'rotulo': 'Abrir Planos de Aula & Sumários',
     'chaves': [' plano de aula', ' planos de aula', ' sumario', ' sumarios'],
     'texto': 'Em Planos de Aula & Sumários o professor submete planos quinzenais ou mensais e regista o sumário diário de cada aula por disciplina e turma; a revisão e o parecer são do DAP.'},
    {'id': 'ocorrencias', 'destino': 'ocorrencias', 'rotulo': 'Abrir Ocorrências',
     'chaves': [' ocorrencia', ' ocorrencias', ' disciplinar', ' indisciplina'],
     'texto': 'Docentes e secretaria registam ocorrências com gravidade, descrição e medida imediata; o DAP dá o parecer pedagógico e o Director da Escola homologa a medida disciplinar.'},
    {'id': 'antiia', 'destino': 'provas-anti-ia', 'rotulo': 'Abrir a Blindagem Anti-IA',
     'chaves': [' anti ia', ' prova codificada', ' prova protegida', ' selos', ' embargo', ' qr da prova', ' escudo'],
     'texto': 'Na Blindagem Anti-IA escolha o Ano Lectivo e Buscar, carregue a prova (Word ou PDF), defina a identificação, a data de libertação (embargo) e, em "Selos e cópias", gere as cópias numeradas em PDF e/ou Word. '
              'O QR e o código de barras de cada cópia mostram "Prova sob embargo" até à data definida e registam cada leitura.'},
    {'id': 'folha_resposta', 'destino': 'folha-resposta', 'rotulo': 'Abrir a Folha de Resposta',
     'chaves': [' folha de resposta', ' grelha de respostas', ' folha personalizada'],
     'texto': 'Em Folha de Resposta Personalizada escolha o Ano Lectivo e Buscar, depois o âmbito (aluno, turma, classe ou em branco), a avaliação (tipo, disciplina, data, duração) e a grelha '
              '(perguntas, alternativas, cotação, versões, chave). Use "Pré-visualizar" e exporte em PDF ou Excel.'},
    {'id': 'cargos_guia', 'destino': 'minhas-atividades', 'rotulo': 'Abrir As Minhas Actividades',
     'chaves': [' director de turma', ' director de classe', ' delegado da disciplina', ' atividades do cargo', ' actividades do cargo', ' o que faz o delegado'],
     'texto': 'A Direcção atribui as actividades do Director de Turma, do Director de Classe e do Delegado da Disciplina em Actividades dos Cargos (com catálogo de sugestões, prazo e prioridade). '
              'O professor vê só as suas em "As Minhas Actividades de Cargo" e pode marcar Pendente, Em curso ou Concluída com uma nota.'},
    {'id': 'crm_guia', 'destino': 'crm', 'rotulo': 'Abrir o CRM Escolar',
     'chaves': [' crm', ' registar contacto', ' registar um contacto', ' registo um contacto', ' contacto com o encarregado', ' atendimento ao encarregado'],
     'texto': 'No CRM Escolar (Direcção, DAP e Secretaria), "Alertas de evasão" lista alunos com muitas faltas efectivas ou propinas em atraso, filtrando por Classe e Turma; a Ficha mostra o encarregado, as faltas, as propinas e permite registar contactos. '
              '"Atendimentos" regista pedidos e reclamações com estado e prioridade até serem resolvidos.'},
    {'id': 'calendario_guia', 'destino': 'calendario', 'rotulo': 'Abrir o Calendário Escolar',
     'chaves': [' criar evento', ' importar calendario', ' carregar calendario', ' adicionar evento'],
     'texto': 'No Calendário Escolar a Direcção e o DAP configuram os eventos lectivos (testes, exames, conselhos, feriados), por formulário ou importando um ficheiro Excel/CSV com o modelo oficial, e podem arquivar o documento oficial do calendário. '
              'Todos os outros perfis consultam.'},
    {'id': 'assistente_guia', 'destino': 'assistente', 'rotulo': 'Abrir o Assistente',
     'chaves': [' o que sabes', ' o que podes', ' ajuda ', ' como funcionas', ' para que serves'],
     'texto': 'Sou o assistente do SIGE. Respondo (só em leitura) com dados reais da escola e com os guias dos módulos. Pergunte, por exemplo, por faltas, notas, propinas, horário, calendário, exames, transferências, '
              'ou "como lanço as notas?". Para dados de um aluno, escolha-o primeiro. Se eu não souber, diga-me que a resposta não ajudou.'},
]

# "Onde fica X?" — id do ecrã → (rótulo, palavras-chave normalizadas)
NAVEGACAO = {
    'dashboard': ('o Painel', [' painel', ' dashboard', ' inicio']),
    'alunos': ('Alunos & Matrículas', [' alunos', ' matriculas']),
    'turmas': ('Turmas', [' turmas']),
    'horarios': ('Horários', [' horario', ' horarios']),
    'professores': ('Atribuição & Docentes', [' professores', ' docentes']),
    'plano-curricular': ('o Plano Curricular', [' plano curricular', ' disciplinas']),
    'caderneta': ('a Caderneta', [' caderneta', ' lancar notas']),
    'pautas': ('Pautas & Actas', [' pautas', ' pauta', ' actas']),
    'exames': ('Exames', [' exames', ' exame']),
    'calendario-exames': ('o Calendário e Júris dos Exames', [' juris', ' calendario de exames', ' calendario dos exames']),
    'calendario': ('o Calendário Escolar', [' calendario']),
    'presencas': ('Presenças dos Alunos', [' presencas', ' faltas']),
    'transferencias': ('Transferências & Anulações', [' transferencias', ' transferencia']),
    'certificados': ('Certificados & Declarações', [' certificados', ' declaracoes', ' declaracao']),
    'impressao': ('a Central de Impressão', [' impressao', ' imprimir', ' boletim']),
    'pagamentos': ('Propinas & Mensalidades', [' propinas', ' mensalidades', ' pagamentos']),
    'despesas': ('Receitas & Despesas', [' despesas', ' receitas']),
    'comunicados': ('Comunicados', [' comunicados', ' circulares']),
    'ocorrencias': ('Ocorrências Disciplinares', [' ocorrencias', ' disciplina']),
    'sumarios': ('Planos de Aula & Sumários', [' sumarios', ' planos de aula']),
    'material-escolar': ('o Material Escolar', [' material escolar', ' manuais']),
    'estatisticas-aproveitamento': ('a Estatística de Aproveitamento', [' estatistica', ' estatisticas']),
    'atribuicoes-cargos': ('Actividades dos Cargos', [' actividades dos cargos', ' atividades dos cargos']),
    'minhas-atividades': ('As Minhas Actividades de Cargo', [' minhas atividades', ' minhas actividades']),
    'provas-anti-ia': ('a Blindagem Anti-IA', [' anti ia', ' provas']),
    'folha-resposta': ('a Folha de Resposta', [' folha de resposta']),
    'usuarios-senhas': ('Utilizadores & Permissões', [' utilizadores', ' senhas', ' permissoes']),
    'auditoria': ('a Auditoria', [' auditoria']),
    'assinatura-escola': ('a Assinatura do Sistema', [' assinatura', ' subscricao']),
    'prompt-gateway': ('o Gateway SMS', [' gateway', ' sms']),
    'crm': ('o CRM Escolar', [' crm', ' encarregados']),
    'aluno-perfil': ('O Meu Perfil', [' meu perfil']),
    'aluno-notas': ('As Minhas Notas', [' minhas notas', ' notas']),
    'aluno-faltas': ('As Minhas Faltas', [' minhas faltas']),
    'aluno-pagamentos': ('As Minhas Propinas', [' minhas propinas']),
    'aluno-calendario': ('o Calendário Académico', [' calendario academico']),
    'assistente': ('o Assistente', [' assistente']),
}
