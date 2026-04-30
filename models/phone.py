import re


def sanitize(value: str) -> str:
    """Strip all non-digit characters from a phone string."""
    return re.sub(r'\D', '', value)


def format_display(value: str) -> str:
    """Format a stored phone number for display.

    10-digit numbers become (XXX) XXX-XXXX. Other lengths are returned as-is.
    """
    digits = sanitize(value)
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return digits
