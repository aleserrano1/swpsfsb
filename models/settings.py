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


def get_company_address(company: str) -> dict:
    """Returns the structured address dict for a company."""
    return {
        "line1":    get(f"{company}_address_line1"),
        "line2":    get(f"{company}_address_line2"),
        "city":     get(f"{company}_address_city"),
        "state":    get(f"{company}_address_state"),
        "zip_code": get(f"{company}_address_zip"),
    }


def format_address(addr: dict) -> str:
    """Formats a structured address dict into a display string (ReportLab <br/> for newlines)."""
    parts = []
    if addr.get("line1"):
        parts.append(addr["line1"])
    if addr.get("line2"):
        parts.append(addr["line2"])
    city_state_zip = ", ".join(filter(None, [addr.get("city"), addr.get("state")]))
    if addr.get("zip_code"):
        city_state_zip = f"{city_state_zip} {addr['zip_code']}".strip()
    if city_state_zip:
        parts.append(city_state_zip)
    return "<br/>".join(parts)


def get_company_info(company: str) -> dict:
    """Returns dict with president, address, phone, logo_path for 'sfsb' or 'swp'."""
    addr = get_company_address(company)
    return {
        "name": "Santa Fe Style Builders" if company == "sfsb" else "Southwest Plastering Co.",
        "president": get(f"{company}_president"),
        "address": format_address(addr),
        "phone": get(f"{company}_phone"),
        "logo_path": get(f"{company}_logo"),
    }


def verify_pin(pin: str) -> bool:
    stored = get("pin")
    return stored == pin


def set_pin(pin: str) -> None:
    set_value("pin", pin)


def pin_is_set() -> bool:
    return bool(get("pin"))
