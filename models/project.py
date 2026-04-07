from datetime import datetime
from dataclasses import dataclass, field
from database import connection as db


@dataclass
class Project:
    id: int
    project_id: str
    company: str
    job_site: str
    tax_rate: float
    down_payment: float
    status: str
    color_theme: str
    proposal_description: str
    proposal_note: str
    master_description: str
    master_note: str
    created_at: str


def _row_to_project(row) -> Project:
    return Project(
        id=row["id"],
        project_id=row["project_id"],
        company=row["company"],
        job_site=row["job_site"],
        tax_rate=row["tax_rate"],
        down_payment=row["down_payment"],
        status=row["status"],
        color_theme=row["color_theme"],
        proposal_description=row["proposal_description"] or "",
        proposal_note=row["proposal_note"] or "",
        master_description=row["master_description"] or "",
        master_note=row["master_note"] or "",
        created_at=row["created_at"],
    )


def create(
    company: str,
    job_site: str,
    tax_rate: float,
    color_theme: str = "blue",
    down_payment: float = 0.0,
) -> Project:
    now = datetime.now().isoformat(timespec="seconds")
    with db.transaction() as cur:
        # Determine next sequential ID
        cur.execute("SELECT COUNT(*) as cnt FROM projects")
        count = cur.fetchone()["cnt"]
        new_num = count + 1
        project_id = f"PRJ-{new_num:04d}"
        cur.execute(
            """INSERT INTO projects
               (project_id, company, job_site, tax_rate, down_payment, status,
                color_theme, created_at)
               VALUES (?,?,?,?,?,'non_binding',?,?)""",
            (project_id, company, job_site, tax_rate, down_payment, color_theme, now),
        )
        row_id = cur.lastrowid
    return get_by_id(row_id)


def get_by_id(project_db_id: int) -> Project | None:
    row = db.query_one("SELECT * FROM projects WHERE id=?", (project_db_id,))
    return _row_to_project(row) if row else None


def get_by_project_id(project_id: str) -> Project | None:
    row = db.query_one("SELECT * FROM projects WHERE project_id=?", (project_id,))
    return _row_to_project(row) if row else None


def all_projects() -> list[Project]:
    rows = db.query("SELECT * FROM projects ORDER BY id DESC")
    return [_row_to_project(r) for r in rows]


def search(term: str) -> list[Project]:
    """Search by project_id, job_site, or any client name."""
    like = f"%{term}%"
    rows = db.query(
        """SELECT DISTINCT p.* FROM projects p
           LEFT JOIN clients c ON c.project_id = p.id
           LEFT JOIN client_names cn ON cn.client_id = c.id
           WHERE p.project_id LIKE ?
              OR p.job_site LIKE ?
              OR cn.value LIKE ?
           ORDER BY p.id DESC""",
        (like, like, like),
    )
    return [_row_to_project(r) for r in rows]


def set_binding(project_db_id: int) -> None:
    with db.transaction() as cur:
        cur.execute(
            "UPDATE projects SET status='binding' WHERE id=?", (project_db_id,)
        )


def update_proposal_texts(project_db_id: int, description: str, note: str) -> None:
    with db.transaction() as cur:
        cur.execute(
            "UPDATE projects SET proposal_description=?, proposal_note=? WHERE id=?",
            (description, note, project_db_id),
        )


def update_master_texts(project_db_id: int, description: str, note: str) -> None:
    with db.transaction() as cur:
        cur.execute(
            "UPDATE projects SET master_description=?, master_note=? WHERE id=?",
            (description, note, project_db_id),
        )


def update_down_payment(project_db_id: int, amount: float) -> None:
    with db.transaction() as cur:
        cur.execute(
            "UPDATE projects SET down_payment=? WHERE id=?", (amount, project_db_id)
        )


def update_color(project_db_id: int, color: str) -> None:
    with db.transaction() as cur:
        cur.execute(
            "UPDATE projects SET color_theme=? WHERE id=?", (color, project_db_id)
        )


def get_financials(project_db_id: int) -> dict:
    """Return subtotal, tax, total, paid, balance for a project."""
    from models.service import services_for_project
    from models.payment import payments_for_project

    project = get_by_id(project_db_id)
    svcs = services_for_project(project_db_id)
    pmts = payments_for_project(project_db_id)

    subtotal = sum(s.amount for s in svcs)
    tax = subtotal * (project.tax_rate / 100)
    total = subtotal + tax
    paid = sum(p.amount for p in pmts if p.status == "paid")
    balance = total - paid

    return {
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "paid": paid,
        "balance": balance,
        "tax_rate": project.tax_rate,
        "down_payment": project.down_payment,
    }
