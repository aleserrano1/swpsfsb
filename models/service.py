from datetime import datetime
from dataclasses import dataclass, field
from database import connection as db


@dataclass
class Subfield:
    id: int
    service_id: int
    text: str
    sort_order: int


@dataclass
class Service:
    id: int
    project_id: int
    description: str
    amount: float
    type: str  # 'original_service' or 'order_change'
    is_hidden: bool
    created_at: str
    subfields: list = field(default_factory=list)


def _row_to_service(row) -> Service:
    return Service(
        id=row["id"],
        project_id=row["project_id"],
        description=row["description"],
        amount=row["amount"],
        type=row["type"],
        is_hidden=bool(row["is_hidden"]),
        created_at=row["created_at"],
    )


def _row_to_subfield(row) -> Subfield:
    return Subfield(
        id=row["id"],
        service_id=row["service_id"],
        text=row["text"],
        sort_order=row["sort_order"],
    )


def subfields_for_service(service_id: int) -> list[Subfield]:
    rows = db.query(
        "SELECT * FROM service_subfields WHERE service_id=? ORDER BY sort_order, id",
        (service_id,),
    )
    return [_row_to_subfield(r) for r in rows]


def add_subfield(service_id: int, text: str, sort_order: int = 0) -> Subfield:
    svc_row = db.query_one(
        """SELECT s.type, p.status FROM services s
           JOIN projects p ON p.id = s.project_id
           WHERE s.id=?""",
        (service_id,),
    )
    if svc_row and svc_row["type"] == "original_service" and svc_row["status"] == "binding":
        raise ValueError(
            "Sub-lines cannot be added to original service line items while the project is binding."
        )
    with db.transaction() as cur:
        cur.execute(
            "INSERT INTO service_subfields (service_id, text, sort_order) VALUES (?,?,?)",
            (service_id, text, sort_order),
        )
        row_id = cur.lastrowid
    row = db.query_one("SELECT * FROM service_subfields WHERE id=?", (row_id,))
    return _row_to_subfield(row)


def delete_subfield(subfield_id: int, authorized: bool = False) -> None:
    if not authorized:
        row = db.query_one(
            """SELECT p.status FROM service_subfields sf
               JOIN services s ON s.id = sf.service_id
               JOIN projects p ON p.id = s.project_id
               WHERE sf.id=?""",
            (subfield_id,),
        )
        if row and row["status"] == "binding":
            raise ValueError("Deleting a subfield on a binding project requires the override PIN.")
    with db.transaction() as cur:
        cur.execute("DELETE FROM service_subfields WHERE id=?", (subfield_id,))


def services_for_project(project_db_id: int) -> list[Service]:
    rows = db.query(
        "SELECT * FROM services WHERE project_id=? ORDER BY id",
        (project_db_id,),
    )
    services = [_row_to_service(r) for r in rows]
    for svc in services:
        svc.subfields = subfields_for_service(svc.id)
    return services


_ALLOWED_TYPE = {
    "non_binding": "original_service",
    "binding": "order_change",
}

_TYPE_LABELS = {
    "original_service": "Original Service",
    "order_change": "Change Order",
}

_STATUS_MESSAGES = {
    "non_binding": "Only Original Services can be added before the project is binding.",
    "binding": "Only Change Orders can be added once the project is binding.",
}


def add_service(project_db_id: int, description: str, amount: float,
                service_type: str = "original_service") -> Service:
    proj_row = db.query_one("SELECT status FROM projects WHERE id=?", (project_db_id,))
    if proj_row:
        status = proj_row["status"]
        if status == "completed":
            raise ValueError("Services cannot be added to a completed project.")
        allowed = _ALLOWED_TYPE.get(status)
        if allowed and service_type != allowed:
            raise ValueError(
                f"Cannot add a {_TYPE_LABELS.get(service_type, service_type)} — "
                f"{_STATUS_MESSAGES.get(status, 'invalid service type for current project status.')}"
            )
    now = datetime.now().isoformat(timespec="seconds")
    with db.transaction() as cur:
        cur.execute(
            "INSERT INTO services (project_id, description, amount, type, created_at) VALUES (?,?,?,?,?)",
            (project_db_id, description, amount, service_type, now),
        )
        row_id = cur.lastrowid
    row = db.query_one("SELECT * FROM services WHERE id=?", (row_id,))
    svc = _row_to_service(row)
    svc.subfields = []
    return svc


def delete_service(service_id: int, authorized: bool = False) -> None:
    if not authorized:
        row = db.query_one(
            "SELECT p.status FROM services s JOIN projects p ON p.id = s.project_id WHERE s.id=?",
            (service_id,),
        )
        if row and row["status"] == "binding":
            raise ValueError("Deleting a service on a binding project requires the override PIN.")
    with db.transaction() as cur:
        cur.execute("DELETE FROM services WHERE id=?", (service_id,))


def toggle_hidden(service_id: int) -> bool:
    """Flip is_hidden for a service; return the new is_hidden value."""
    with db.transaction() as cur:
        cur.execute(
            "UPDATE services SET is_hidden = NOT is_hidden WHERE id=?", (service_id,)
        )
    row = db.query_one("SELECT is_hidden FROM services WHERE id=?", (service_id,))
    return bool(row["is_hidden"])
