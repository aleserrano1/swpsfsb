# Architectural Patterns

Patterns that appear across multiple files. Follow these when adding features.

---

## 1. Database Access

All DB reads and writes go through `database/connection.py`. Models never import `sqlite3` directly.

**Reads** — use `db.query()` / `db.query_one()`:
```
models/project.py:44      db.query_one("SELECT * FROM projects WHERE id=?", ...)
models/service.py:23      db.query("SELECT * FROM services WHERE project_id=?", ...)
```

**Writes** — use `db.transaction()` context manager; auto-commits on exit, auto-rolls back on exception:
```
models/project.py:28–37   with db.transaction() as cur: cur.execute(...)
models/payment.py:71–81   with db.transaction() as cur: cur.execute(...)
```

**Connection features** (`database/connection.py:28–33`): WAL mode, `busy_timeout=5000`, `foreign_keys=ON`, thread-local storage. All of these are set once when the connection is first opened per thread.

---

## 2. Model CRUD Structure

Every model follows the same shape. Don't deviate.

1. `@dataclass` with typed fields — `models/project.py:12–25`, `models/payment.py:12–25`
2. Private `_row_to_*(row)` converter from `sqlite3.Row` — `models/service.py:18–24`
3. `*_for_project(project_db_id)` query — `models/service.py:27–32`
4. `get_by_id(id)` returning `Entity | None` — `models/payment.py:34–36`
5. `add_*(...)` inserts, then re-queries and returns fresh object — `models/service.py:35–44`
6. Focused `update_*(id, value)` functions, one per field group — `models/project.py:91–115`

**Key**: `add_*` always returns the DB-fetched object, not the input. This ensures `id`, `created_at`, and any DB defaults are populated.

---

## 3. Financial Aggregation

`models/project.py:134–157` (`get_financials()`) is the single source for all financial figures. It is called by:
- All three tabs in `ui/project_detail.py`
- `ui/payment_form.py` (for invoice generation)
- `ui/quote_form.py`
- All PDF generators that show totals

Never compute subtotal/tax/total/paid/balance inline elsewhere. Always call `get_financials()`.

---

## 4. UI Navigation (Callback Pattern)

`ui/app.py` owns the content area. Child screens never navigate directly; they invoke callbacks passed at construction.

- `app.py:68–101`: `_show_projects`, `_new_project`, `_open_project`, `_show_settings` each call `_clear_content()` then pack a new screen.
- Screen constructors accept `on_back`, `on_save`, `on_cancel`, `on_open_project` — `ui/project_list.py:10`, `ui/project_detail.py:24`, `ui/project_form.py:11`.
- When a save callback triggers navigation, defer with `self.after(0, lambda: self.on_save(...))` to avoid destroying the widget while still inside its event handler — `ui/project_form.py:136`.

---

## 5. Modal Dialog (Two Variants)

### Callback-based (fire-and-forget)
Used when the dialog needs to trigger a parent refresh. Dialog calls `on_save()` then destroys itself.
```
ui/service_form.py:49–54    add_service(...); if self.on_save: self.on_save(); self.destroy()
ui/payment_form.py:74–88    add_payment(...); self._generate_invoice(payment); self.on_save(); self.destroy()
```

### wait_window-based (result collection)
Used when the caller needs a value back before continuing. Caller blocks on `wait_window(dialog)`, then reads an attribute.
```
ui/project_detail.py:336–341   desc_dialog = ProposalTextDialog(self, ...); self.wait_window(desc_dialog)
                                if desc_dialog.cancelled: return
ui/startup.py:60–63            dialog = PinSetupDialog(self); self.wait_window(dialog); return dialog.result
```

Result dialogs expose `.result` and/or `.cancelled` as instance attributes, set before `self.destroy()`.

All dialogs call `self.grab_set()` in `__init__` to block parent interaction.

---

## 6. PDF Building

All PDFs follow the same build sequence:

1. Call `pdf.base.make_doc(path, project_id)` — `pdf/proposal.py:16`, `pdf/invoice.py:67`, `pdf/master.py:15`
2. Call `pdf.base.get_styles()` for paragraph styles
3. Build `elements: list` by appending flowables — call shared builders from `pdf/base.py` for common sections
4. Call `doc.build(elements, onFirstPage=footer_callback, onLaterPages=footer_callback)`

**Shared builders in `pdf/base.py`** (reused by all three PDF modules):
- `build_header_elements()` line 74 — logo + company info
- `build_client_block()` line 129 — client names/emails/job site
- `build_optional_text_blocks()` line 153 — General Description / Note sections
- `build_totals_block()` line 168 — right-aligned subtotal/tax/total table
- `standard_table_style()` line 54 — consistent table header/row styling

**File naming** (`ui/payment_form.py:97`, `ui/project_detail.py:374`):
- Proposal: `{project_id}-proposal.pdf`
- Invoice: `INV-{project_id}-{payment_id:04d}.pdf`
- Receipt: `REC-{project_id}-{payment_id:04d}.pdf`
- Quote: `QUOTE-{project_id}-{timestamp}.pdf`
- Master: `MASTER-{project_id}.pdf`

All files written to `{base_output_dir}/{project_id}/`.

---

## 7. Widget Helpers

Never construct CTk widgets directly in screens — use the factories in `ui/widgets.py`. They return the widget instance so callers can chain `.pack()`.

```
ui/widgets.py:8     label(parent, text, bold, size, fg)
ui/widgets.py:15    entry(parent, placeholder, width)
ui/widgets.py:20    button(parent, text, command, width, fg_color, hover_color)
ui/widgets.py:28    section_label(parent, text)   ← gray uppercase field labels
ui/widgets.py:39    show_error(title, message)
ui/widgets.py:43    show_info(title, message)
ui/widgets.py:47    ask_yes_no(title, message) -> bool
```

---

## 8. Error Handling

**Model layer** raises `ValueError` for domain violations; all other exceptions propagate up.
- `models/payment.py:48–69`: payment ceiling check raises `ValueError` with a user-readable message.

**UI layer** catches at the call site and shows a message box. Never swallow silently.
```
ui/payment_form.py:80–83    except ValueError as e: show_error(...); return
ui/project_detail.py:352    except Exception as e: show_error("PDF Error", ...)
ui/startup.py:84            except Exception as e: show_error("Error", ...)
```

---

## 9. Two-Company Data Pattern

Company identity is stored as `'sfsb'` or `'swp'` in the DB. Display names and PDF info are resolved at runtime.

- `ui/theme.py:12–15`: `COMPANY_LABELS` maps code → display name
- `models/settings.py:22–27` (`get_company_info(company)`): returns name, president, address, phone from `settings` table
- PDF generators receive a `company_info` dict; they never query company data themselves

When adding company-specific behavior, add to `theme.py` or `models/settings.py` — not inline in UI or PDF files.
