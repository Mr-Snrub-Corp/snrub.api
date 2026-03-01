def validate_ines_severity(v: int) -> int:
    if not 1 <= v <= 7:
        raise ValueError("Severity must be 1-7 (INES scale)")
    return v


def validate_ines_severity_optional(v: int | None) -> int | None:
    if v is not None and not 1 <= v <= 7:
        raise ValueError("Severity must be 1-7 (INES scale)")
    return v
