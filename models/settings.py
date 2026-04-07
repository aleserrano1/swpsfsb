from database import connection as db


def get(key: str, default: str = "") -> str:
    row = db.query_one("SELECT value FROM settings WHERE key=?", (key,))
    return row["value"] if row else default


def set_value(key: str, value: str) -> None:
    with db.transaction() as cur:
        cur.execute(
            "INSERT INTO settings (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def get_company_info(company: str) -> dict:
    """Returns dict with president, address, phone for 'sfsb' or 'swp'."""
    return {
        "name": "Santa Fe Style Builders" if company == "sfsb" else "Southwest Plastering Co.",
        "president": get(f"{company}_president"),
        "address": get(f"{company}_address"),
        "phone": get(f"{company}_phone"),
    }


def verify_pin(pin: str) -> bool:
    stored = get("pin")
    return stored == pin


def set_pin(pin: str) -> None:
    set_value("pin", pin)


def pin_is_set() -> bool:
    return bool(get("pin"))
