from datetime import datetime
from dataclasses import dataclass, field
from database import connection as db


@dataclass
class PaymentAllocation:
    id: int
    payment_id: int
    service_id: int
    amount: float


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
    payment_description: str
    created_at: str
    allocations: list = field(default_factory=list)


def _row_to_allocation(row) -> PaymentAllocation:
    return PaymentAllocation(
        id=row["id"],
        payment_id=row["payment_id"],
        service_id=row["service_id"],
        amount=row["amount"],
    )


def allocations_for_payment(payment_id: int) -> list[PaymentAllocation]:
    rows = db.query(
        "SELECT * FROM payment_allocations WHERE payment_id=? ORDER BY id",
        (payment_id,),
    )
    return [_row_to_allocation(r) for r in rows]


def service_total_allocated(service_id: int) -> float:
    """Sum of all allocation amounts for a service across all payments (paid and unpaid)."""
    row = db.query_one(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM payment_allocations WHERE service_id=?",
        (service_id,),
    )
    return float(row["total"]) if row else 0.0


def _row_to_payment(row) -> Payment:
    p = Payment(
        id=row["id"],
        project_id=row["project_id"],
        amount=row["amount"],
        payment_type=row["payment_type"],
        description=row["description"],
        check_number=row["check_number"] or "",
        status=row["status"],
        invoice_description=row["invoice_description"] or "",
        invoice_note=row["invoice_note"] or "",
        payment_description=row["payment_description"] or "",
        created_at=row["created_at"],
    )
    p.allocations = allocations_for_payment(p.id)
    return p


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
    description: str,
    invoice_description: str = "",
    invoice_note: str = "",
    allocations: list[dict] | None = None,
) -> Payment:
    """Add a payment/invoice with line item allocations.

    allocations: list of {"service_id": int, "amount": float}
    Raises ValueError for invalid project state, amount overages, or allocation mismatches.
    """
    from models.project import get_financials, get_by_id as get_project
    from models.service import services_for_project

    proj = get_project(project_db_id)
    if proj is None:
        raise ValueError("Project not found.")
    if proj.status == "completed":
        raise ValueError("Payments cannot be added to a completed project.")
    if proj.status != "binding":
        raise ValueError("Payments can only be created after the project is marked as binding.")

    fin = get_financials(project_db_id)
    existing_total = sum(
        r["amount"] for r in db.query(
            "SELECT amount FROM payments WHERE project_id=?", (project_db_id,)
        )
    )
    if existing_total + amount > fin["total"] + 0.005:
        raise ValueError(
            f"Payment of ${amount:,.2f} would exceed project total of ${fin['total']:,.2f}. "
            f"Current payments: ${existing_total:,.2f}, Remaining: ${fin['total'] - existing_total:,.2f}"
        )

    # Validate allocations
    alloc_list = allocations or []
    if not alloc_list:
        raise ValueError("At least one line item allocation is required.")

    alloc_total = sum(a["amount"] for a in alloc_list)
    if abs(alloc_total - amount) > 0.005:
        raise ValueError(
            f"Allocation total (${alloc_total:,.2f}) must equal payment amount (${amount:,.2f})."
        )

    tax_factor = 1 + proj.tax_rate / 100
    visible_services = {
        s.id: s for s in services_for_project(project_db_id) if not s.is_hidden
    }
    for alloc in alloc_list:
        svc_id = alloc["service_id"]
        alloc_amt = alloc["amount"]
        if alloc_amt <= 0:
            raise ValueError("Allocation amounts must be greater than zero.")
        if svc_id not in visible_services:
            raise ValueError(f"Service ID {svc_id} is not available for allocation.")
        svc = visible_services[svc_id]
        svc_taxed = svc.amount * tax_factor
        already = service_total_allocated(svc_id)
        remaining = svc_taxed - already
        if alloc_amt > remaining + 0.005:
            raise ValueError(
                f"Allocation of ${alloc_amt:,.2f} to '{svc.description}' exceeds "
                f"its remaining balance of ${remaining:,.2f} (including tax)."
            )

    now = datetime.now().isoformat(timespec="seconds")
    with db.transaction() as cur:
        cur.execute(
            """INSERT INTO payments
               (project_id, amount, payment_type, description, check_number,
                status, invoice_description, invoice_note, payment_description, created_at)
               VALUES (?,?,''  ,?,NULL,'unpaid',?,?,'',?)""",
            (project_db_id, amount, description, invoice_description, invoice_note, now),
        )
        row_id = cur.lastrowid
        for alloc in alloc_list:
            cur.execute(
                "INSERT INTO payment_allocations (payment_id, service_id, amount) VALUES (?,?,?)",
                (row_id, alloc["service_id"], alloc["amount"]),
            )
    return get_by_id(row_id)


def mark_paid(payment_id: int, payment_type: str, payment_description: str) -> Payment:
    with db.transaction() as cur:
        cur.execute(
            "UPDATE payments SET status='paid', payment_type=?, payment_description=? WHERE id=?",
            (payment_type, payment_description, payment_id),
        )
    return get_by_id(payment_id)


def delete_payment(payment_id: int) -> None:
    """Delete an unpaid payment (allocations cascade automatically)."""
    payment = get_by_id(payment_id)
    if payment is None:
        raise ValueError("Payment not found.")
    if payment.status == "paid":
        raise ValueError("Paid payments cannot be deleted.")
    with db.transaction() as cur:
        cur.execute("DELETE FROM payments WHERE id=?", (payment_id,))


def update_invoice_texts(payment_id: int, description: str, note: str) -> None:
    with db.transaction() as cur:
        cur.execute(
            "UPDATE payments SET invoice_description=?, invoice_note=? WHERE id=?",
            (description, note, payment_id),
        )
