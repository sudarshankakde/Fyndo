def mask_phone(phone: str | None) -> str:
    """Return a public-safe phone label without exposing contact details."""
    if not phone:
        return "Fyndo member"
    digits = "".join(character for character in phone if character.isdigit())
    if len(digits) < 4:
        return "Fyndo member"
    return f"+{digits[:2]} ••••••{digits[-2:]}"
