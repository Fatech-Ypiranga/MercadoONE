class BusinessRuleException(Exception):
    """Exceção base para regras de negócio"""
    pass

class ResourceNotFoundException(BusinessRuleException):
    """Lançada quando um ID ou recurso não existe"""
    pass

class ValidationError(BusinessRuleException):
    """Lançada quando dados falham na validação (valores negativos, strings vazias, etc)"""
    pass

class InsufficientStockException(BusinessRuleException):
    """Lançada quando não há estoque suficiente para uma saída ou venda"""
    pass