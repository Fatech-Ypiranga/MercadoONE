from enum import Enum as PyEnum

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum


def enum_column(enum_class):
    return Column(
        SAEnum(enum_class, values_callable=lambda choices: [choice.value for choice in choices])
    )


class CustomerType(str, PyEnum):
    FISICA = "F"
    JURIDICA = "J"


class StateRegistrationIndicator(str, PyEnum):
    CONTRIBUINTE = "1"
    ISENTO = "2"
    NAO_CONTRIBUINTE = "9"


class MovementType(str, PyEnum):
    ENTRADA = "E"
    SAIDA = "S"


class MovementReason(str, PyEnum):
    VENDA = "venda"
    COMPRA = "compra"
    AJUSTE_INVENTARIO = "ajuste"
    DEVOLUCAO = "devolucao"


class UserProfile(str, PyEnum):
    ADMIN = "admin"
    GERENTE = "gerente"
    SUPERVISOR = "supervisor"
    OPERADOR = "operador"
    CONFERENTE = "conferente"
    COLABORADOR = "colaborador"


class AuditAction(str, PyEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    STOCK_MOVE = "STOCK_MOVE"
    ROLE_CHANGE = "ROLE_CHANGE"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"


class PurchaseStatus(str, PyEnum):
    RASCUNHO = "Rascunho"
    CONFIRMADO = "Confirmado"
    CANCELADO = "Cancelado"
