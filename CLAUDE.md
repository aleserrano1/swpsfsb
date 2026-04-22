# Construction Project Manager (SWPSFSB)

Desktop app for two construction companies — **Santa Fe Style Builders** (`sfsb`) and **Southwest Plastering Co.** (`swp`) — to manage projects, clients, services, payments, and generate PDFs (proposals, invoices, receipts, master files).

## Tech Stack

| Layer | Library / Version |
|-------|------------------|
| GUI | CustomTkinter 5.2.2 (dark mode, `ctk.CTk`) |
| Database | SQLite3 (stdlib) — WAL mode, thread-local connections |
| PDFs | ReportLab 4.4.10 + Pillow 12.2.0 |
| Config | JSON at `~/.swpsfsb/config.json` |
| Python | 3.13, venv at `venv/` |

## Key Directories

```
main.py              Entry point; DB auto-connect or startup screen
config.py            Load/save ~/.swpsfsb/config.json (db_path, base_output_dir)
database/
  connection.py      Thread-local SQLite pool; query(), query_one(), transaction()
  schema.py          Table definitions; initialize() creates all tables
models/              One file per entity: project, client, service, payment, settings
  project.py         get_financials() — single source of truth for all money calcs
  settings.py        KV store in DB; company info (name/president/address/phone), PIN
pdf/
  base.py            Shared styles, builders, make_doc(), footer_callback()
  proposal.py        Proposal + Quote PDFs
  invoice.py         Invoice + Paid Receipt PDFs
  master.py          Project Master File PDF (chronological financial activity)
ui/
  app.py             Root CTkFrame; sidebar nav; content-area swap
  theme.py           COLOR_THEMES, COMPANY_LABELS, STATUS_LABELS/COLORS
  widgets.py         label(), button(), entry(), section_label(), show_error(), etc.
  startup.py         DB selection + PIN setup on first launch
  project_detail.py  Tabbed detail view (Overview / Services / Payments)
assets/              sfsb_logo.png, swp_logo.png (used in PDF headers)
```

## Adding New Features or Fixing Bugs

**IMPORTANT**: When you work on a new feature or bug, create a git branch first. Then work on changes in that branch for the remainder of the session.

## Running the App

```bash
# Activate venv first (Windows)
venv\Scripts\activate

python main.py
```

No build step. No test suite.

## PDF Output Layout

All PDFs land in `{base_output_dir}/{project_id}/`:

| File | Trigger |
|------|---------|
| `{project_id}-proposal.pdf` | Mark as Binding |
| `QUOTE-{project_id}-{ts}.pdf` | Generate Quote |
| `INV-{project_id}-{id:04d}.pdf` | Add Payment |
| `REC-{project_id}-{id:04d}.pdf` | Mark Payment Paid |
| `MASTER-{project_id}.pdf` | Generate Master File |

## Additional Documentation

- [Architectural Patterns](.claude/docs/architectural_patterns.md) — DB access, model shape, financial aggregation, UI navigation, dialog variants, PDF pipeline, widget helpers, error handling, two-company pattern
