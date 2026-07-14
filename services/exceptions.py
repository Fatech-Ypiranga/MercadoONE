class BusinessRuleException(Exception):
    pass


class ResourceNotFoundException(BusinessRuleException):
    pass


class ValidationError(BusinessRuleException):
    pass


class InsufficientStockException(BusinessRuleException):
    pass


class ConflictException(BusinessRuleException):
    pass


class UnauthorizedException(BusinessRuleException):
    pass


class ForbiddenException(BusinessRuleException):
    pass
