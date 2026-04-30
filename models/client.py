from dataclasses import dataclass, field
from database import connection as db
from models.phone import sanitize as sanitize_phone


@dataclass
class Client:
    id: int
    project_id: int
    names: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    addresses: list[dict] = field(default_factory=list)


def _load_fields(client_id: int) -> tuple:
    names = [r["value"] for r in db.query("SELECT value FROM client_names WHERE client_id=? ORDER BY id", (client_id,))]
    emails = [r["value"] for r in db.query("SELECT value FROM client_emails WHERE client_id=? ORDER BY id", (client_id,))]
    phones = [r["value"] for r in db.query("SELECT value FROM client_phones WHERE client_id=? ORDER BY id", (client_id,))]
    rows = db.query(
        "SELECT address_line1, address_line2, city, state, zip_code "
        "FROM client_addresses WHERE client_id=? ORDER BY id",
        (client_id,),
    )
    addresses = [
        {
            "line1": r["address_line1"],
            "line2": r["address_line2"],
            "city": r["city"],
            "state": r["state"],
            "zip_code": r["zip_code"],
        }
        for r in rows
    ]
    return names, emails, phones, addresses


def clients_for_project(project_db_id: int) -> list[Client]:
    rows = db.query("SELECT * FROM clients WHERE project_id=? ORDER BY id", (project_db_id,))
    clients = []
    for row in rows:
        names, emails, phones, addresses = _load_fields(row["id"])
        clients.append(Client(
            id=row["id"],
            project_id=row["project_id"],
            names=names,
            emails=emails,
            phones=phones,
            addresses=addresses,
        ))
    return clients


def _insert_addresses(cur, client_id: int, addresses: list[dict]) -> None:
    for addr in addresses:
        line1 = addr.get("line1", "").strip()
        if not line1:
            continue
        cur.execute(
            "INSERT INTO client_addresses (client_id, address_line1, address_line2, city, state, zip_code) "
            "VALUES (?,?,?,?,?,?)",
            (
                client_id,
                line1,
                addr.get("line2", "").strip(),
                addr.get("city", "").strip(),
                addr.get("state", "").strip(),
                addr.get("zip_code", "").strip(),
            ),
        )


def add_client(project_db_id: int, names: list[str], emails: list[str],
               phones: list[str], addresses: list[dict]) -> Client:
    with db.transaction() as cur:
        cur.execute("INSERT INTO clients (project_id) VALUES (?)", (project_db_id,))
        client_id = cur.lastrowid
        for v in names:
            if v.strip():
                cur.execute("INSERT INTO client_names (client_id, value) VALUES (?,?)", (client_id, v.strip()))
        for v in emails:
            if v.strip():
                cur.execute("INSERT INTO client_emails (client_id, value) VALUES (?,?)", (client_id, v.strip()))
        for v in phones:
            cleaned = sanitize_phone(v)
            if cleaned:
                cur.execute("INSERT INTO client_phones (client_id, value) VALUES (?,?)", (client_id, cleaned))
        _insert_addresses(cur, client_id, addresses)

    names_out, emails_out, phones_out, addresses_out = _load_fields(client_id)
    return Client(id=client_id, project_id=project_db_id,
                  names=names_out, emails=emails_out,
                  phones=phones_out, addresses=addresses_out)


def update_client(client_id: int, names: list[str], emails: list[str],
                  phones: list[str], addresses: list[dict]) -> None:
    with db.transaction() as cur:
        cur.execute("DELETE FROM client_names WHERE client_id=?", (client_id,))
        cur.execute("DELETE FROM client_emails WHERE client_id=?", (client_id,))
        cur.execute("DELETE FROM client_phones WHERE client_id=?", (client_id,))
        cur.execute("DELETE FROM client_addresses WHERE client_id=?", (client_id,))
        for v in names:
            if v.strip():
                cur.execute("INSERT INTO client_names (client_id, value) VALUES (?,?)", (client_id, v.strip()))
        for v in emails:
            if v.strip():
                cur.execute("INSERT INTO client_emails (client_id, value) VALUES (?,?)", (client_id, v.strip()))
        for v in phones:
            cleaned = sanitize_phone(v)
            if cleaned:
                cur.execute("INSERT INTO client_phones (client_id, value) VALUES (?,?)", (client_id, cleaned))
        _insert_addresses(cur, client_id, addresses)


def delete_client(client_id: int) -> None:
    with db.transaction() as cur:
        cur.execute("DELETE FROM clients WHERE id=?", (client_id,))
