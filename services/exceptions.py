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


class ExternalServiceException(Exception):
    """Raised when an upstream/external service call fails (maps to 502/503)."""

    def __init__(self, message: str, *, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code
