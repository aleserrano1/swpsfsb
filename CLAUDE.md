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

## Git workflow requirements

Before making any code change for a bug fix or new feature, you must first create and switch to a new git branch.

Required steps:
1. Determine whether the task is a bug fix or feature.
2. Create a branch before editing any file.
3. Stay on that branch for the rest of the session.
4. Do not make code changes on main.

Branch naming:
- bug fixes: fix/<short-description>
- features: feat/<short-description>

Before editing files, run:
- git rev-parse --abbrev-ref HEAD
- git checkout -b <branch-name>

If already on main when a bug fix or feature request starts, create the branch immediately before any edits.

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
