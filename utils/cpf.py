def normalize_cpf(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def is_valid_cpf(value: str) -> bool:
    document = normalize_cpf(value)
    if len(document) != 11 or document == document[0] * 11:
        return False

    digits = [int(character) for character in document]
    first_digit = _calculate_check_digit(digits[:9], list(range(10, 1, -1)))
    second_digit = _calculate_check_digit(digits[:9] + [first_digit], list(range(11, 1, -1)))
    return digits[-2:] == [first_digit, second_digit]


def build_cpf(sequence: int) -> str:
    """Build a valid CPF from a numeric sequence (useful for tests/seeds)."""
    base = f"{abs(sequence) % 10**9:09d}"
    if base == base[0] * 9:
        base = f"{(abs(sequence) + 1) % 10**9:09d}"
    digits = [int(character) for character in base]
    first_digit = _calculate_check_digit(digits, list(range(10, 1, -1)))
    second_digit = _calculate_check_digit(digits + [first_digit], list(range(11, 1, -1)))
    return f"{base}{first_digit}{second_digit}"


def _calculate_check_digit(digits: list[int], weights: list[int]) -> int:
    remainder = sum(digit * weight for digit, weight in zip(digits, weights)) % 11
    return 0 if remainder < 2 else 11 - remainder
