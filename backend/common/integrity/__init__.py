"""
Módulo de Integridade do Sistema SIGE
Centraliza validadores, regras de negócio e asserções de consistência e isolamento.
"""
from .validators import (
    validar_escala_nota,
    validar_faltas,
    validar_nuit_mz,
    validar_periodo_academico,
    validar_comportamento,
    validar_anotacao_minedh,
)
from .exceptions import (
    IntegrityRuleViolation,
    CrossTenantViolation,
    ImmutableRecordViolation,
    InvalidDomainValueViolation,
)
from .tenant_checks import (
    validar_integridade_tenant,
    verificar_pauta_permite_edicao_nota,
)

__all__ = [
    'validar_escala_nota',
    'validar_faltas',
    'validar_nuit_mz',
    'validar_periodo_academico',
    'validar_comportamento',
    'validar_anotacao_minedh',
    'IntegrityRuleViolation',
    'CrossTenantViolation',
    'ImmutableRecordViolation',
    'InvalidDomainValueViolation',
    'validar_integridade_tenant',
    'verificar_pauta_permite_edicao_nota',
]
