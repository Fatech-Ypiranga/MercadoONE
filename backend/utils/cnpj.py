from shared.exceptions import ValidationError


def normalize_cnpj(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def is_valid_cnpj(value: str) -> bool:
    document = normalize_cnpj(value)
    if len(document) != 14 or document == document[0] * 14:
        return False

    digits = [int(character) for character in document]
    first_digit = _calculate_check_digit(digits[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    second_digit = _calculate_check_digit(
        digits[:12] + [first_digit],
        [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2],
    )
    return digits[-2:] == [first_digit, second_digit]


def _calculate_check_digit(digits: list[int], weights: list[int]) -> int:
    remainder = sum(digit * weight for digit, weight in zip(digits, weights)) % 11
    return 0 if remainder < 2 else 11 - remainder


def require_valid_cnpj(document: str, *, entity: str = "document") -> str:
    """Normalize and validate a CNPJ, raising ValidationError if invalid."""
    normalized = normalize_cnpj(document)
    if not is_valid_cnpj(normalized):
        raise ValidationError(f"{entity} must be a valid CNPJ.")
    return normalized
