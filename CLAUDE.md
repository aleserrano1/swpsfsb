# Construction Project Manager

Desktop app for two construction companies (Santa Fe Style Builders, Southwest Plastering Co.) to track projects, record services/payments, and generate PDF documents (proposals, invoices, quotes, master files).

## Tech Stack

| Layer | Technology |
|-------|-----------|
| GUI | CustomTkinter (CTk) |
| Database | SQLite3 — WAL mode, thread-local connections |
| PDF | ReportLab (Platypus) |
| Config | JSON at `~/.swpsfsb/config.json` |

No ORM. No web framework. No logging library.

## Project Structure

```
SWPSFSB/
├── main.py              # Entry point; startup/DB connection logic
├── config.py            # JSON config I/O (db_path, base_output_dir)
├── database/
│   ├── connection.py    # Thread-local SQLite manager; query/transaction helpers
│   └── schema.py        # CREATE TABLE statements; initialize() called on DB open
├── models/              # Data access + business logic; one file per entity
│   ├── project.py       # Includes get_financials() — the financial aggregation hub
│   ├── client.py        # Multi-valued fields (names, emails, phones, addresses)
│   ├── service.py       # original_service / order_change types
│   ├── payment.py       # paid / unpaid; enforces payment-total ceiling
│   └── settings.py      # Key-value store for PIN, company info
├── pdf/
│   ├── base.py          # Shared builders: header, client block, totals, footer
│   ├── proposal.py      # Proposal + Quote (is_quote=True flag)
│   ├── invoice.py       # Invoice + PAID receipt (is_receipt=True flag)
│   └── master.py        # Chronological summary PDF
├── ui/
│   ├── app.py           # Root window; sidebar nav; content-area swapping
│   ├── startup.py       # DB connect/create screen; PIN dialogs
│   ├── theme.py         # COLOR_THEMES, COMPANY_LABELS, STATUS_COLORS constants
│   ├── widgets.py       # label/entry/button/show_error helper factories
│   ├── project_list.py  # Searchable card list
│   ├── project_form.py  # Create project form; ClientBlock dynamic sub-forms
│   ├── project_detail.py# Tabbed detail: Overview / Services / Payments
│   ├── service_form.py  # Add service/change-order dialog
│   ├── payment_form.py  # Add payment + auto-generate invoice dialog
│   ├── quote_form.py    # Generate quote dialog (no DB write)
│   └── settings_screen.py
└── assets/
    ├── sfsb_logo.png    # Replace with real logo
    └── swp_logo.png     # Replace with real logo
```

## Adding New Features or Fixing Bugs
**IMPORTANT** When the user clicks on the calendar in weekly view to add a new chore, the time of the new chore doesn’t reflect the cell the user clicked.

## Run

```bash
python main.py
```

First run shows `StartupWindow` to create or connect to a `.db` file. Subsequent runs auto-connect to the last-used path stored in `~/.swpsfsb/config.json`.

## Key Domain Rules (enforce in models, not UI)

- **Payment ceiling** — `models/payment.py:48–69`: raises `ValueError` if payment would exceed project total.
- **Proposal PIN protection** — `ui/project_detail.py:319–329`: checks for existing proposal file; prompts PIN before regenerating.
- **Project ID** — `models/project.py:29–32`: `PRJ-{COUNT(*)+1:04d}` — sequential, not UUID.
- **Financial source of truth** — `models/project.py:134–157` (`get_financials()`): always recompute from DB; never cache totals.
- **Quotes not persisted** — `ui/quote_form.py:68–69`: project object mutated temporarily; no DB write.

## Additional Documentation

Check these files when working on the relevant area:

| Topic | File |
|-------|------|
| Architectural patterns & design decisions | `.claude/docs/architectural_patterns.md` |
