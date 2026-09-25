import pytest
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.tenants.models import Escola, Plano, AssinaturaEscola
from apps.turmas.models import Turma
from apps.disciplinas.models import Disciplina
from apps.alunos.models import Aluno
from apps.professores.models import Professor, AlocacaoDocente
from apps.notas.models import Nota, PermissaoEdicaoNotas
from apps.pautas.models import Pauta
from apps.pagamentos.models import Pagamento
from common.integrity.exceptions import (
    IntegrityRuleViolation,
    CrossTenantViolation,
    ImmutableRecordViolation,
    InvalidDomainValueViolation
)

@pytest.mark.django_db
class TestIntegrityRulesSIGE:
    def setup_method(self):
        self.plano = Plano.objects.create(nome='PLANO_INTEGRIDADE', preco=1500, duracao_dias=30)
        
        # Escola Primária A
        self.escola_a = Escola.objects.create(
            nome='Escola Integridade A',
            nif_cnpj='NIF_INT_A',
            email='int_a@sige.mz',
            status='ATIVA',
            plano=self.plano
        )
        self.turma_a = Turma.objects.create(
            escola=self.escola_a,
            nome='10ª A Integridade',
            grau_ano='10ª Classe',
            ano_letivo='2026'
        )
        self.disciplina_a = Disciplina.objects.create(
            escola=self.escola_a,
            nome='Matemática',
            codigo='MAT-10-INT',
            ano_letivo='2026'
        )
        self.aluno_a = Aluno.objects.create(
            escola=self.escola_a,
            turma=self.turma_a,
            matricula='MAT-INT-001',
            nome='Estudante de Integridade A',
            data_nascimento='2009-01-01',
            genero='M'
        )
        self.professor_a = Professor.objects.create(
            escola=self.escola_a,
            nome='Professor A',
            email='prof.a@sige.mz',
            especialidade='Matemática'
        )

        # Escola Primária B (Outro Tenant)
        self.escola_b = Escola.objects.create(
            nome='Escola Integridade B',
            nif_cnpj='NIF_INT_B',
            email='int_b@sige.mz',
            status='ATIVA',
            plano=self.plano
        )
        self.turma_b = Turma.objects.create(
            escola=self.escola_b,
            nome='10ª B Integridade',
            grau_ano='10ª Classe',
            ano_letivo='2026'
        )
        self.disciplina_b = Disciplina.objects.create(
            escola=self.escola_b,
            nome='Química',
            codigo='QUI-10-INT',
            ano_letivo='2026'
        )

    # -------------------------------------------------------------
    # 1. Regras de Integridade de Domínio (Normas MINEDH)
    # -------------------------------------------------------------
    def test_nota_acima_do_limite_maximo_rejeitada(self):
        """Notas > 20.0 devem ser categoricamente rejeitadas pelo sistema."""
        with pytest.raises((ValidationError, InvalidDomainValueViolation)):
            Nota.objects.create(
                escola=self.escola_a,
                aluno=self.aluno_a,
                disciplina=self.disciplina_a,
                turma=self.turma_a,
                periodo='1_TRIMESTRE',
                media_final=20.5
            )

    def test_nota_abaixo_do_limite_minimo_rejeitada(self):
        """Notas < 0.0 devem ser rejeitadas."""
        with pytest.raises((ValidationError, InvalidDomainValueViolation)):
            Nota.objects.create(
                escola=self.escola_a,
                aluno=self.aluno_a,
                disciplina=self.disciplina_a,
                turma=self.turma_a,
                periodo='1_TRIMESTRE',
                media_final=-1.0
            )

    def test_faltas_negativas_rejeitadas(self):
        """Número de faltas < 0 deve ser rejeitado."""
        with pytest.raises((ValidationError, InvalidDomainValueViolation)):
            Nota.objects.create(
                escola=self.escola_a,
                aluno=self.aluno_a,
                disciplina=self.disciplina_a,
                turma=self.turma_a,
                periodo='1_TRIMESTRE',
                media_final=14,
                faltas=-3
            )

    def test_periodo_academico_invalido_rejeitado(self):
        """Períodos não canônicos devem ser rejeitados."""
        with pytest.raises((ValidationError, InvalidDomainValueViolation)):
            Nota.objects.create(
                escola=self.escola_a,
                aluno=self.aluno_a,
                disciplina=self.disciplina_a,
                turma=self.turma_a,
                periodo='TRIMESTRE_INVENTADO',
                media_final=12
            )

    # -------------------------------------------------------------
    # 2. Regras de Integridade de Isolamento Multi-Tenant
    # -------------------------------------------------------------
    def test_aluno_turma_escolas_diferentes_bloqueado(self):
        """Tentativa de matricular Aluno da Escola A em Turma da Escola B deve falhar."""
        with pytest.raises((ValidationError, CrossTenantViolation)):
            Aluno.objects.create(
                escola=self.escola_a,
                turma=self.turma_b,  # Turma pertence à Escola B
                matricula='MAT-CROSS-01',
                nome='Aluno Cruzado',
                data_nascimento='2009-05-05',
                genero='F'
            )

    def test_nota_com_disciplina_outro_tenant_bloqueada(self):
        """Tentativa de lançar nota usando Disciplina de outro tenant deve falhar."""
        with pytest.raises((ValidationError, CrossTenantViolation)):
            Nota.objects.create(
                escola=self.escola_a,
                aluno=self.aluno_a,
                disciplina=self.disciplina_b,  # Disciplina de Escola B
                turma=self.turma_a,
                periodo='1_TRIMESTRE',
                media_final=15
            )

    def test_alocacao_docente_cruzada_bloqueada(self):
        """Alocar professor da Escola A em turma da Escola B deve falhar."""
        with pytest.raises((ValidationError, CrossTenantViolation)):
            AlocacaoDocente.objects.create(
                escola=self.escola_a,
                professor=self.professor_a,
                disciplina=self.disciplina_a,
                turma=self.turma_b  # Turma de Escola B
            )

    # -------------------------------------------------------------
    # 3. Regras de Integridade de Entidade e Unicidade
    # -------------------------------------------------------------
    def test_duplicidade_de_nota_no_mesmo_periodo_bloqueada(self):
        """Um aluno não pode ter 2 notas na mesma disciplina/turma/período."""
        Nota.objects.create(
            escola=self.escola_a,
            aluno=self.aluno_a,
            disciplina=self.disciplina_a,
            turma=self.turma_a,
            periodo='1_TRIMESTRE',
            media_final=12
        )
        with pytest.raises((ValidationError, IntegrityError)):
            Nota.objects.create(
                escola=self.escola_a,
                aluno=self.aluno_a,
                disciplina=self.disciplina_a,
                turma=self.turma_a,
                periodo='1_TRIMESTRE',
                media_final=14
            )

    def test_duplicidade_de_pauta_turma_ano_periodo_bloqueada(self):
        """Não pode existir mais de uma pauta para a mesma turma, ano e período."""
        Pauta.objects.create(
            escola=self.escola_a,
            turma=self.turma_a,
            ano_letivo='2026',
            periodo='1_TRIMESTRE',
            status='ABERTA'
        )
        with pytest.raises((ValidationError, IntegrityError)):
            Pauta.objects.create(
                escola=self.escola_a,
                turma=self.turma_a,
                ano_letivo='2026',
                periodo='1_TRIMESTRE',
                status='EM_CONSOLIDACAO'
            )

    def test_duplicidade_alocacao_docente_bloqueada(self):
        """Não pode existir alocação duplicada para o mesmo professor, disciplina e turma."""
        AlocacaoDocente.objects.create(
            escola=self.escola_a,
            professor=self.professor_a,
            disciplina=self.disciplina_a,
            turma=self.turma_a
        )
        with pytest.raises((ValidationError, IntegrityError)):
            AlocacaoDocente.objects.create(
                escola=self.escola_a,
                professor=self.professor_a,
                disciplina=self.disciplina_a,
                turma=self.turma_a
            )

    # -------------------------------------------------------------
    # 4. Regras de Imutabilidade e Ciclo de Vida (Pautas & Notas)
    # -------------------------------------------------------------
    def test_pauta_fechada_impede_alteracao_ou_insercao_de_nota(self):
        """Ao fechar a pauta, nenhuma nota daquela turma/período pode ser gravada sem permissão."""
        Pauta.objects.create(
            escola=self.escola_a,
            turma=self.turma_a,
            ano_letivo='2026',
            periodo='1_TRIMESTRE',
            status='FECHADA',
            data_fechamento=timezone.now(),
            homologado_por='Director Geral'
        )

        with pytest.raises((ValidationError, ImmutableRecordViolation)):
            Nota.objects.create(
                escola=self.escola_a,
                aluno=self.aluno_a,
                disciplina=self.disciplina_a,
                turma=self.turma_a,
                periodo='1_TRIMESTRE',
                media_final=15
            )

    def test_pauta_fechada_permite_alteracao_se_houver_permissao_ativa(self):
        """Com PermissaoEdicaoNotas ativa, o lançamento é autorizado."""
        Pauta.objects.create(
            escola=self.escola_a,
            turma=self.turma_a,
            ano_letivo='2026',
            periodo='1_TRIMESTRE',
            status='FECHADA',
            data_fechamento=timezone.now(),
            homologado_por='Director Geral'
        )

        PermissaoEdicaoNotas.objects.create(
            escola=self.escola_a,
            professor=self.professor_a,
            turma=self.turma_a,
            disciplina=self.disciplina_a,
            periodo='1_TRIMESTRE',
            autorizado_por='DAP António Costa',
            motivo='Retificação de teste após recurso',
            ativa=True
        )

        # Com permissão ativa, deve salvar com sucesso!
        nota = Nota.objects.create(
            escola=self.escola_a,
            aluno=self.aluno_a,
            disciplina=self.disciplina_a,
            turma=self.turma_a,
            periodo='1_TRIMESTRE',
            media_final=17
        )
        assert nota.id is not None
        assert nota.media_final == 17

    # -------------------------------------------------------------
    # 5. Regras de Integridade Financeira e Contratos SaaS
    # -------------------------------------------------------------
    def test_pagamento_valor_negativo_rejeitado(self):
        """Pagamentos com valores negativos devem ser rejeitados."""
        with pytest.raises((ValidationError, IntegrityRuleViolation)):
            Pagamento.objects.create(
                escola=self.escola_a,
                aluno=self.aluno_a,
                descricao='Mensalidade Março',
                mes_referencia='2026-03',
                valor=-500,
                data_vencimento=timezone.now()
            )

    def test_assinatura_data_fim_invalida_rejeitada(self):
        """Data final de assinatura anterior à data inicial deve ser rejeitada."""
        agora = timezone.now()
        with pytest.raises((ValidationError, IntegrityRuleViolation)):
            AssinaturaEscola.objects.create(
                escola=self.escola_a,
                plano=self.plano,
                data_inicio=agora,
                data_fim=agora - timedelta(days=10),
                valor=1500
            )
