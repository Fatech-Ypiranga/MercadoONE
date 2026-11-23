"""Maximum discount (percent of the sale gross total) each profile may grant alone.

Above its limit a profile needs a Supervisor+ authorization token, and the
authorizer's own limit must also cover the discount. Today's values keep the
previous behaviour (profiles with `sales:discount` unlimited, others need an
authorization for any discount); change them here to tighten the policy.
"""

from decimal import Decimal

from utils.enums import UserProfile

MAX_DISCOUNT_PERCENT: dict[UserProfile, Decimal] = {
    UserProfile.ADMIN: Decimal("100"),
    UserProfile.GERENTE: Decimal("100"),
    UserProfile.SUPERVISOR: Decimal("100"),
    UserProfile.OPERADOR: Decimal("0"),
    UserProfile.CONFERENTE: Decimal("0"),
    UserProfile.COLABORADOR: Decimal("0"),
}


def max_discount_percent(profile: UserProfile) -> Decimal:
    return MAX_DISCOUNT_PERCENT.get(profile, Decimal("0"))


def discount_percent(discount: Decimal, gross_total: Decimal) -> Decimal:
    if gross_total <= 0:
        return Decimal("0")
    return discount * Decimal("100") / gross_total
