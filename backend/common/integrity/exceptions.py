"""
Exceções canônicas de violação de integridade do SIGE.
"""
from django.core.exceptions import ValidationError

class IntegrityRuleViolation(ValidationError):
    """Exceção base para qualquer quebra de integridade de negócio do SIGE."""
    def __init__(self, message, code=None, params=None):
        super().__init__(message, code=code or 'integrity_violation', params=params)

class CrossTenantViolation(IntegrityRuleViolation):
    """Lançada quando há tentativa de associar dados de escolas (tenants) distintas."""
    def __init__(self, message="Violação de isolamento multi-tenant: registros pertencem a escolas distintas."):
        super().__init__(message, code='cross_tenant_violation')

class ImmutableRecordViolation(IntegrityRuleViolation):
    """Lançada quando há tentativa de modificar dados em pauta fechada ou registro imutável."""
    def __init__(self, message="Operação bloqueada: o registro ou a pauta associada encontra-se fechada e imutável."):
        super().__init__(message, code='immutable_record_violation')

class InvalidDomainValueViolation(IntegrityRuleViolation):
    """Lançada quando um valor numérico ou categórico excede o domínio regulamentar."""
    def __init__(self, message="Valor fora dos limites regulamentares estabelecidos pelo MINEDH/SIGE."):
        super().__init__(message, code='invalid_domain_value')
