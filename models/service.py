from datetime import datetime
from dataclasses import dataclass
from database import connection as db


@dataclass
class Service:
    id: int
    project_id: int
    description: str
    amount: float
    type: str  # 'original_service' or 'order_change'
    created_at: str


def _row_to_service(row) -> Service:
    return Service(
        id=row["id"],
        project_id=row["project_id"],
        description=row["description"],
        amount=row["amount"],
        type=row["type"],
        created_at=row["created_at"],
    )


def services_for_project(project_db_id: int) -> list[Service]:
    rows = db.query(
        "SELECT * FROM services WHERE project_id=? ORDER BY id",
        (project_db_id,),
    )
    return [_row_to_service(r) for r in rows]


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
    return _row_to_service(row)


def delete_service(service_id: int) -> None:
    with db.transaction() as cur:
        cur.execute("DELETE FROM services WHERE id=?", (service_id,))
