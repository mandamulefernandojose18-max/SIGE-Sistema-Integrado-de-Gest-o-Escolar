import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';
import QRCode from 'qrcode';

const prisma = new PrismaClient();

async function main() {
  console.log('🌱 Iniciando carga de dados (Seed) - Sistema Integrado de Gestão Escolar (Moçambique)...');

  // Limpar tabelas para carga idempotente
  await prisma.logImpressao.deleteMany().catch(() => {});
  await prisma.certificado.deleteMany().catch(() => {});
  await prisma.pagamento.deleteMany().catch(() => {});
  await prisma.nota.deleteMany().catch(() => {});
  await prisma.professorDisciplinaTurma.deleteMany().catch(() => {});
  await prisma.pauta.deleteMany().catch(() => {});
  await prisma.disciplina.deleteMany().catch(() => {});
  await prisma.aluno.deleteMany().catch(() => {});
  await prisma.professor.deleteMany().catch(() => {});
  await prisma.turma.deleteMany().catch(() => {});
  await prisma.usuario.deleteMany({ where: { role: { not: 'SUPERADMIN' } } }).catch(() => {});

  // 1. Criar Planos de Assinatura (Mensal, Trimestral, Semestral, Anual) em MZN
  const planoMensal = await prisma.plano.upsert({
    where: { nome: 'MENSAL' },
    update: { preco: 1500.0, duracao_dias: 30 },
    create: {
      nome: 'MENSAL',
      descricao: 'Plano Mensal - Licença básica com suporte padrão',
      preco: 1500.0,
      duracao_dias: 30,
      max_alunos: 300,
      max_professores: 25,
      ativo: true
    }
  });

  const planoTrimestral = await prisma.plano.upsert({
    where: { nome: 'TRIMESTRAL' },
    update: { preco: 4200.0, duracao_dias: 90 },
    create: {
      nome: 'TRIMESTRAL',
      descricao: 'Plano Trimestral - Ideal para períodos letivos trimestrais',
      preco: 4200.0,
      duracao_dias: 90,
      max_alunos: 800,
      max_professores: 60,
      ativo: true
    }
  });

  const planoSemestral = await prisma.plano.upsert({
    where: { nome: 'SEMESTRAL' },
    update: { preco: 7800.0, duracao_dias: 180 },
    create: {
      nome: 'SEMESTRAL',
      descricao: 'Plano Semestral - Flexibilidade com desconto semestral',
      preco: 7800.0,
      duracao_dias: 180,
      max_alunos: 1500,
      max_professores: 100,
      ativo: true
    }
  });

  const planoAnual = await prisma.plano.upsert({
    where: { nome: 'ANUAL' },
    update: { preco: 14500.0, duracao_dias: 365 },
    create: {
      nome: 'ANUAL',
      descricao: 'Plano Anual Institucional - Suporte 24/7 e gestão ilimitada',
      preco: 14500.0,
      duracao_dias: 365,
      max_alunos: 3000,
      max_professores: 200,
      ativo: true
    }
  });

  console.log('✅ Planos configurados em Meticais (MZN): Mensal, Trimestral, Semestral, Anual.');

  const hashAdmin123 = await bcrypt.hash('admin123', 10);
  const hashEscola123 = await bcrypt.hash('escola123', 10);
  const hashProf123 = await bcrypt.hash('professor123', 10);
  const hashAluno123 = await bcrypt.hash('aluno123', 10);

  // 2. SuperAdmin do SaaS
  const superAdmin = await prisma.usuario.upsert({
    where: { email: 'admin.master@sige.com' },
    update: {},
    create: {
      nome: 'Eng. Fernando Mandamule',
      email: 'admin.master@sige.com',
      senha_hash: hashAdmin123,
      role: 'SUPERADMIN',
      ativo: true,
      telefone: '+258 84 100 2000'
    }
  });

  console.log(`✅ SuperAdmin criado: ${superAdmin.email}`);

  // 3. Escola 1: "Escola Secundária Central" (ATIVA)
  const agora = new Date();
  const validadeAtiva = new Date(agora);
  validadeAtiva.setDate(validadeAtiva.getDate() + 365);

  const escola1 = await prisma.escola.upsert({
    where: { nif_cnpj: '5001234567' },
    update: {
      status: 'ATIVA',
      provincia: 'Maputo',
      distrito: 'Cidade de Maputo',
      director_nome: 'Prof. Dr. António Costa',
      director_carreira: 'Professor Doutor',
      dap_nome: 'Prof. João Baptista',
      chefe_secretaria_nome: 'Dra. Maria Eunice'
    },
    create: {
      nome: 'Escola Secundária Central',
      nif_cnpj: '5001234567',
      email: 'secretaria@escola.edu.mz',
      telefone: '+258 84 111 2222',
      endereco: 'Av. Eduardo Mondlane, Maputo',
      status: 'ATIVA',
      ano_letivo_ativo: '2026',
      trimestre_ativo: '1_TRIMESTRE',
      plano_id: planoAnual.id,
      provincia: 'Maputo',
      distrito: 'Cidade de Maputo',
      director_nome: 'Prof. Dr. António Costa',
      director_carreira: 'Professor Doutor',
      dap_nome: 'Prof. João Baptista',
      chefe_secretaria_nome: 'Dra. Maria Eunice',
      usar_emblema_nacional: true
    }
  });

  // Assinatura Ativa
  await prisma.assinaturaEscola.create({
    data: {
      escola_id: escola1.id,
      plano_id: planoAnual.id,
      data_inicio: agora,
      data_fim: validadeAtiva,
      valor: planoAnual.preco,
      status: 'ATIVA',
      metodo_pagamento: 'TRANSFERENCIA'
    }
  });

  // Pessoal Administrativo da Escola
  // Director
  await prisma.usuario.upsert({
    where: { email: 'director@escola.edu.mz' },
    update: {},
    create: {
      escola_id: escola1.id,
      nome: 'Prof. Dr. António Costa',
      email: 'director@escola.edu.mz',
      senha_hash: hashAdmin123,
      role: 'DIRECTOR_ESCOLA',
      telefone: '+258 84 222 3333',
      ativo: true
    }
  });

  // DAP (Director Adjunto Pedagógico)
  await prisma.usuario.upsert({
    where: { email: 'dap@escola.edu.mz' },
    update: {},
    create: {
      escola_id: escola1.id,
      nome: 'Prof. João Baptista',
      email: 'dap@escola.edu.mz',
      senha_hash: hashAdmin123,
      role: 'DAP',
      telefone: '+258 84 333 4444',
      ativo: true
    }
  });

  // Chefe da Secretaria
  await prisma.usuario.upsert({
    where: { email: 'secretaria@escola.edu.mz' },
    update: {},
    create: {
      escola_id: escola1.id,
      nome: 'Dra. Maria Eunice',
      email: 'secretaria@escola.edu.mz',
      senha_hash: hashAdmin123,
      role: 'CHEFE_SECRETARIA',
      telefone: '+258 84 444 5555',
      ativo: true
    }
  });

  // Administrador da Escola
  await prisma.usuario.upsert({
    where: { email: 'admin.escola@escola.edu.mz' },
    update: {},
    create: {
      escola_id: escola1.id,
      nome: 'Administrador Local',
      email: 'admin.escola@escola.edu.mz',
      senha_hash: hashEscola123,
      role: 'ADMIN_ESCOLA',
      ativo: true
    }
  });

  await prisma.usuario.upsert({
    where: { email: 'admin@escola.edu.mz' },
    update: {},
    create: {
      escola_id: escola1.id,
      nome: 'Administrador Escola',
      email: 'admin@escola.edu.mz',
      senha_hash: hashEscola123,
      role: 'ADMIN_ESCOLA',
      ativo: true
    }
  });

  // Turmas
  const turma10A = await prisma.turma.create({
    data: {
      escola_id: escola1.id,
      nome: '10ª Classe A',
      grau_ano: '10ª Classe',
      turno: 'MANHA',
      sala: 'Sala 01',
      ano_letivo: '2026'
    }
  });

  const turma12B = await prisma.turma.create({
    data: {
      escola_id: escola1.id,
      nome: '12ª Classe B',
      grau_ano: '12ª Classe',
      turno: 'TARDE',
      sala: 'Sala 05',
      ano_letivo: '2026'
    }
  });

  // Professores com Perfil Oficial
  const prof1User = await prisma.usuario.upsert({
    where: { email: 'professor@escola.edu.mz' },
    update: {},
    create: {
      escola_id: escola1.id,
      nome: 'Prof. Manuel Silva',
      email: 'professor@escola.edu.mz',
      senha_hash: hashProf123,
      role: 'PROFESSOR',
      ativo: true
    }
  });

  const prof1 = await prisma.professor.create({
    data: {
      escola_id: escola1.id,
      nome: 'Manuel',
      apelido: 'Silva',
      genero: 'M',
      email: 'professor@escola.edu.mz',
      telefone: '+258 84 555 6666',
      tipo_documento: 'Bilhete de Identidade',
      numero_documento: '080123456789A',
      nuit: '109876543',
      nacionalidade: 'Moçambicana',
      provincia: 'Maputo',
      distrito: 'Cidade de Maputo',
      carreira: 'DN1',
      especialidade: 'Matemática e Estatística',
      carga_horaria_semanal: 24,
      ativo: true
    }
  });

  await prisma.usuario.update({
    where: { id: prof1User.id },
    data: { professor_id: prof1.id }
  });

  const prof2User = await prisma.usuario.upsert({
    where: { email: 'teresa.santos@escola.edu.mz' },
    update: {},
    create: {
      escola_id: escola1.id,
      nome: 'Profª. Teresa Santos',
      email: 'teresa.santos@escola.edu.mz',
      senha_hash: hashProf123,
      role: 'PROFESSOR',
      ativo: true
    }
  });

  const prof2 = await prisma.professor.create({
    data: {
      escola_id: escola1.id,
      nome: 'Teresa',
      apelido: 'Santos',
      genero: 'F',
      email: 'teresa.santos@escola.edu.mz',
      telefone: '+258 84 777 8888',
      tipo_documento: 'Bilhete de Identidade',
      numero_documento: '080987654321B',
      nuit: '108765432',
      nacionalidade: 'Moçambicana',
      provincia: 'Maputo',
      distrito: 'Cidade de Maputo',
      carreira: 'Mestre',
      especialidade: 'Física',
      carga_horaria_semanal: 20,
      ativo: true
    }
  });

  await prisma.usuario.update({
    where: { id: prof2User.id },
    data: { professor_id: prof2.id }
  });

  // Atualizar Turma com Directores de Turma e Classe
  await prisma.turma.update({
    where: { id: turma10A.id },
    data: {
      director_turma_id: prof1.id,
      director_classe_id: prof2.id
    }
  });

  // Disciplinas Oficiais
  const disciplinasLista = [
    { nome: 'Língua Portuguesa', codigo: 'PORT' },
    { nome: 'Inglês', codigo: 'ING' },
    { nome: 'Francês', codigo: 'FRAN' },
    { nome: 'História', codigo: 'HIST' },
    { nome: 'Geografia', codigo: 'GEO' },
    { nome: 'Biologia', codigo: 'BIO' },
    { nome: 'Química', codigo: 'QUIM' },
    { nome: 'Física', codigo: 'FIS' },
    { nome: 'Matemática', codigo: 'MAT' },
    { nome: 'Educação Visual', codigo: 'EV' },
    { nome: 'Agropecuária', codigo: 'AGRO' },
    { nome: 'Noções de Empreendedorismo', codigo: 'EMP' },
    { nome: 'Educação Física', codigo: 'EF' },
    { nome: 'TIC\'s', codigo: 'TIC' }
  ];

  const discCriadas: any[] = [];
  for (const d of disciplinasLista) {
    const disc = await prisma.disciplina.create({
      data: {
        escola_id: escola1.id,
        nome: d.nome,
        codigo: d.codigo,
        carga_horaria: 60,
        ano_letivo: '2026'
      }
    });
    discCriadas.push(disc);
  }

  // Alocações dos Professores
  const matDisc = discCriadas.find(d => d.codigo === 'MAT');
  const fisDisc = discCriadas.find(d => d.codigo === 'FIS');

  if (matDisc) {
    await prisma.professorDisciplinaTurma.create({
      data: {
        escola_id: escola1.id,
        professor_id: prof1.id,
        disciplina_id: matDisc.id,
        turma_id: turma10A.id
      }
    });
  }

  if (fisDisc) {
    await prisma.professorDisciplinaTurma.create({
      data: {
        escola_id: escola1.id,
        professor_id: prof2.id,
        disciplina_id: fisDisc.id,
        turma_id: turma10A.id
      }
    });
  }

  // Alunos com Dados Pessoais Oficiais de Moçambique
  const alunosBase = [
    { nome: 'Carlos', apelido: 'Mandamule', genero: 'M', nasc: '2008-04-12', doc: '110293847586A', nuit: '201928374', pai: 'Alberto Mandamule', mae: 'Ana Chissano', status: 'ATIVO' },
    { nome: 'Beatriz', apelido: 'Machel', genero: 'F', nasc: '2008-09-21', doc: '110293847587B', nuit: '201928375', pai: 'Samora Machel Jr.', mae: 'Graça Simbine', status: 'ATIVO' },
    { nome: 'Daniel', apelido: 'Couto', genero: 'M', nasc: '2007-11-05', doc: '110293847588C', nuit: '201928376', pai: 'Mia Couto', mae: 'Patrícia Silva', status: 'ATIVO' },
    { nome: 'Esperança', apelido: 'Chissano', genero: 'F', nasc: '2008-02-18', doc: '110293847589D', nuit: '201928377', pai: 'Joaquim Chissano', mae: 'Marcelina Chissano', status: 'ATIVO' },
    { nome: 'Fernando', apelido: 'Guebuza', genero: 'M', nasc: '2009-01-30', doc: '110293847590E', nuit: '201928378', pai: 'Armando Guebuza', mae: 'Maria da Luz', status: 'ATIVO' },
    { nome: 'Graça', apelido: 'Mondlane', genero: 'F', nasc: '2008-07-09', doc: '110293847591F', nuit: '201928379', pai: 'Eduardo Mondlane Jr.', mae: 'Janet Mondlane', status: 'ATIVO' }
  ];

  const alunosCriados: any[] = [];
  let seq = 1001;

  for (const ab of alunosBase) {
    const mat = `MAT-2026-${seq++}`;
    const aluno = await prisma.aluno.create({
      data: {
        escola_id: escola1.id,
        turma_id: turma10A.id,
        matricula: mat,
        nome: `${ab.nome} ${ab.apelido}`,
        apelido: ab.apelido,
        data_nascimento: new Date(ab.nasc),
        genero: ab.genero,
        tipo_documento: 'Bilhete de Identidade',
        numero_documento: ab.doc,
        nuit: ab.nuit,
        nacionalidade: 'Moçambicana',
        provincia: 'Maputo',
        distrito: 'Cidade de Maputo',
        pai: ab.pai,
        mae: ab.mae,
        nome_responsavel: ab.pai,
        contato_responsavel: '+258 84 999 0000',
        status: ab.status
      }
    });

    alunosCriados.push(aluno);

    // Criar credenciais de acesso individuais para cada Aluno
    const emailAluno = alunosCriados.length === 1
      ? 'aluno@escola.edu.mz'
      : `${ab.nome.toLowerCase()}.${ab.apelido.toLowerCase()}@aluno.escola.edu.mz`;
    await prisma.usuario.create({
      data: {
        escola_id: escola1.id,
        aluno_id: aluno.id,
        nome: `${ab.nome} ${ab.apelido}`,
        email: emailAluno,
        senha_hash: hashAluno123,
        role: 'ALUNO',
        ativo: true
      }
    });

    // Lançamento das 6 Avaliações para cada disciplina
    for (const disc of discCriadas) {
      // Notas com variações realistas (positivas e algumas negativas)
      const t1 = Number((8 + Math.random() * 10).toFixed(1));
      const t2 = Number((9 + Math.random() * 10).toFixed(1));
      const t3 = Math.random() > 0.5 ? Number((10 + Math.random() * 8).toFixed(1)) : null;
      const t4 = null;
      const trab = Number((12 + Math.random() * 6).toFixed(1));
      const at = Number((8 + Math.random() * 10).toFixed(1));

      // Cálculo de MAC e MT
      const testes = [t1, t2, trab];
      if (t3 !== null) testes.push(t3);
      const mac = testes.reduce((a, b) => a + b, 0) / testes.length;
      const mediaFinal = Math.round((mac + at) / 2);

      const aprovado = mediaFinal >= 9.5;
      const resultado = aprovado ? 'Aprovado' : 'Reprovado';
      let comp = 'S';
      if (mediaFinal >= 17.5) comp = 'E';
      else if (mediaFinal >= 15.5) comp = 'MB';
      else if (mediaFinal >= 13.5) comp = 'B';
      else if (mediaFinal >= 9.5) comp = 'S';
      else comp = 'NS';

      await prisma.nota.create({
        data: {
          escola_id: escola1.id,
          aluno_id: aluno.id,
          disciplina_id: disc.id,
          turma_id: turma10A.id,
          periodo: '1_TRIMESTRE',
          teste1: t1,
          teste2: t2,
          teste3: t3,
          teste4: t4,
          trabalho: trab,
          avaliacao_trimestral: at,
          media_final: mediaFinal,
          faltas: Math.floor(Math.random() * 3),
          comportamento: comp,
          resultado: resultado
        }
      });
    }

    // Pagamentos em Meticais (MZN)
    await prisma.pagamento.create({
      data: {
        escola_id: escola1.id,
        aluno_id: aluno.id,
        descricao: 'Mensalidade de Março / 2026',
        mes_referencia: '2026-03',
        valor: 1200.0,
        valor_pago: 1200.0,
        status: 'PAGO',
        data_vencimento: new Date('2026-03-10'),
        data_pagamento: new Date('2026-03-08'),
        metodo_pagamento: 'MPESA',
        recibo_numero: `REC-MZN-${Math.floor(10000 + Math.random() * 90000)}`
      }
    });

    await prisma.pagamento.create({
      data: {
        escola_id: escola1.id,
        aluno_id: aluno.id,
        descricao: 'Mensalidade de Abril / 2026',
        mes_referencia: '2026-04',
        valor: 1200.0,
        valor_pago: 0,
        status: 'PENDENTE',
        data_vencimento: new Date('2026-04-10')
      }
    });
  }

  // Pauta da Turma 10A
  await prisma.pauta.create({
    data: {
      escola_id: escola1.id,
      turma_id: turma10A.id,
      ano_letivo: '2026',
      periodo: '1_TRIMESTRE',
      status: 'FECHADA',
      data_fechamento: new Date(),
      homologado_por: 'Prof. Dr. António Costa (Director)'
    }
  });

  // Certificado Oficial com QR Code para o primeiro aluno
  const alunoDestaque = alunosCriados[0];
  const certUuid = '550e8400-e29b-41d4-a716-446655440000';
  const qrDataUrl = await QRCode.toDataURL(`http://localhost:3000/verificar-certificado.html?codigo=${certUuid}`);

  await prisma.certificado.create({
    data: {
      escola_id: escola1.id,
      aluno_id: alunoDestaque.id,
      tipo: 'DECLARACAO',
      codigo_autenticidade: certUuid,
      qrcode_data: qrDataUrl,
      emitido_por: 'Secretaria da Escola Secundária Central'
    }
  });

  // 4. Escola 2: "Instituto Educacional Progresso" (EXPIRADA - Para teste de HTTP 402)
  const dataInicioExpirada = new Date();
  dataInicioExpirada.setDate(dataInicioExpirada.getDate() - 90);
  const dataFimExpirada = new Date();
  dataFimExpirada.setDate(dataFimExpirada.getDate() - 15);

  const escola2 = await prisma.escola.upsert({
    where: { nif_cnpj: '5009876543' },
    update: { status: 'EXPIRADA' },
    create: {
      nome: 'Instituto Educacional Progresso (Expirado)',
      nif_cnpj: '5009876543',
      email: 'secretaria@colegioprogresso.edu.mz',
      telefone: '+258 84 999 8888',
      status: 'EXPIRADA',
      ano_letivo_ativo: '2026',
      trimestre_ativo: '1_TRIMESTRE',
      plano_id: planoMensal.id,
      provincia: 'Cidade de Maputo',
      distrito: 'KaMpfumo'
    }
  });

  await prisma.assinaturaEscola.create({
    data: {
      escola_id: escola2.id,
      plano_id: planoMensal.id,
      data_inicio: dataInicioExpirada,
      data_fim: dataFimExpirada,
      valor: planoMensal.preco,
      status: 'EXPIRADA',
      metodo_pagamento: 'TRANSFERENCIA'
    }
  });

  await prisma.usuario.upsert({
    where: { email: 'admin.progresso@sige.com' },
    update: {},
    create: {
      escola_id: escola2.id,
      nome: 'Director Manuel Bento',
      email: 'admin.progresso@sige.com',
      senha_hash: hashEscola123,
      role: 'ADMIN_ESCOLA',
      ativo: true
    }
  });

  console.log('🌟 Seed oficial de Moçambique concluído com sucesso!');
}

main()
  .catch((e) => {
    console.error('Erro no Seed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
