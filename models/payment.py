from datetime import datetime
from dataclasses import dataclass
from database import connection as db


@dataclass
class Payment:
    id: int
    project_id: int
    amount: float
    payment_type: str
    description: str
    check_number: str
    status: str  # 'paid' or 'unpaid'
    invoice_description: str
    invoice_note: str
    created_at: str


def _row_to_payment(row) -> Payment:
    return Payment(
        id=row["id"],
        project_id=row["project_id"],
        amount=row["amount"],
        payment_type=row["payment_type"],
        description=row["description"],
        check_number=row["check_number"] or "",
        status=row["status"],
        invoice_description=row["invoice_description"] or "",
        invoice_note=row["invoice_note"] or "",
        created_at=row["created_at"],
    )


def payments_for_project(project_db_id: int) -> list[Payment]:
    rows = db.query(
        "SELECT * FROM payments WHERE project_id=? ORDER BY id",
        (project_db_id,),
    )
    return [_row_to_payment(r) for r in rows]


def get_by_id(payment_id: int) -> Payment | None:
    row = db.query_one("SELECT * FROM payments WHERE id=?", (payment_id,))
    return _row_to_payment(row) if row else None


def add_payment(
    project_db_id: int,
    amount: float,
    payment_type: str,
    description: str,
    check_number: str,
    invoice_description: str = "",
    invoice_note: str = "",
) -> Payment:
    """Add a payment. Raises ValueError if amount would exceed project total."""
    from models.project import get_financials
    fin = get_financials(project_db_id)
    existing_total = sum(
        r["amount"] for r in db.query(
            "SELECT amount FROM payments WHERE project_id=?", (project_db_id,)
        )
    )
    if existing_total + amount > fin["total"] + 0.005:  # small float tolerance
        raise ValueError(
            f"Payment of ${amount:,.2f} would exceed project total of ${fin['total']:,.2f}. "
            f"Current payments: ${existing_total:,.2f}, Remaining: ${fin['total'] - existing_total:,.2f}"
        )
    now = datetime.now().isoformat(timespec="seconds")
    with db.transaction() as cur:
        cur.execute(
            """INSERT INTO payments
               (project_id, amount, payment_type, description, check_number,
                status, invoice_description, invoice_note, created_at)
               VALUES (?,?,?,?,?,'unpaid',?,?,?)""",
            (project_db_id, amount, payment_type, description,
             check_number or None, invoice_description, invoice_note, now),
        )
        row_id = cur.lastrowid
    return get_by_id(row_id)


def set_paid(payment_id: int) -> Payment:
    with db.transaction() as cur:
        cur.execute("UPDATE payments SET status='paid' WHERE id=?", (payment_id,))
    return get_by_id(payment_id)


def update_invoice_texts(payment_id: int, description: str, note: str) -> None:
    with db.transaction() as cur:
        cur.execute(
            "UPDATE payments SET invoice_description=?, invoice_note=? WHERE id=?",
            (description, note, payment_id),
        )
