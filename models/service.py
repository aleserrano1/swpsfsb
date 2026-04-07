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


def add_service(project_db_id: int, description: str, amount: float,
                service_type: str = "original_service") -> Service:
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
