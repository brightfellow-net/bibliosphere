# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

The v1 MVP is implemented: all four Clean Architecture layers, a working PySide6 GUI,
SQLite persistence, and a pytest suite covering domain/application logic plus the SQLite
repositories. `docs/requirements.md` and `docs/architecture.md` remain the source of truth
for scope and layering — read them before changing behavior or adding new use cases.

## Commands

```bash
source .venv/bin/activate        # or: pip install -e ".[dev]" into a fresh venv

pytest                            # run the full test suite
pytest tests/application/test_loans.py::test_checkout_item_enforces_loan_limit  # single test

python scripts/seed_admin.py      # one-time: create the first librarian account
python main.py                    # run the app (uses data/bibliosphere.db, created on first run)
```

There is no lint/format tool configured yet — add one (e.g. ruff) if the codebase grows
enough to warrant it.

## Architecture (from docs/requirements.md)

Bibliosphere is a **desktop GUI app** (Python + PySide6) for library management, with
local **SQLite** storage and no server/network component (single-computer deployment).

- **Two roles in one app, gated by login:** Librarian (full catalog/member/loan management)
  and Patron (search catalog, view own loans only). The UI and available actions must adapt
  based on the logged-in user's role — this is a routing/permissions concern that spans the
  auth layer and every screen, not something isolated to one module.
- **Data model:** `Bibliography` (title-level metadata) has many `Item` records (physical
  instances, each with its own `available`/`checked_out` status); a `Loan` links one `Item`
  to one `Member` with checkout/due/return dates. An item is considered checked out exactly
  when it has an open loan (no `return_date`) — there is no separate status flag to keep in
  sync manually, so derive availability from loan state rather than duplicating it.
- **Loan rules are fixed defaults for v1** (14-day loan period, max 5 books/patron) and are
  intentionally not user-configurable yet. They live as named constants in
  `application/config.py` (see below) so a future settings screen can surface them.
- Checkout/return is **librarian-mediated only** — patrons cannot self-checkout in v1.
- No barcode scanning, no external ISBN lookups, no reservations, no fines, no
  notifications/reporting, and no patron self-registration in v1 (see
  `docs/requirements.md` §7 for the full deferred list). Do not build toward these
  speculatively.

### Mandatory: Clean Architecture

All implementation follows Clean Architecture under `src/bibliosphere/`. Full detail (port
example, testing implications) is in `docs/architecture.md` — read it before adding a new
use case or changing layer boundaries. Summary:

- Four layers: `domain/` (entities + `typing.Protocol` repository ports, zero framework
  deps) → `application/` (use cases, one per user action, depend only on domain; also
  `config.py` for the fixed loan-rule constants, `security.py` for password hashing, and
  `container.py`'s `UseCases` dataclass that bundles every use case instance for injection
  into the GUI) → `infrastructure/sqlite/` (adapters implementing domain ports) →
  `presentation/qt/` (PySide6 views, depend only on application + domain).
- **Dependency Rule:** dependencies point inward only — `presentation → application →
  domain`, `infrastructure → domain`. Nothing depends on `infrastructure`.
  **No SQLite import and no PySide import anywhere under `domain/` or `application/`.**
- Only `main.py` (composition root) and `scripts/seed_admin.py` (a second, minimal
  composition root) are allowed to know about both `infrastructure` and `presentation`/use
  cases together — they wire concrete repositories into use cases.
- `Item` has no stored status column — availability is always derived by checking for an
  open `Loan` (`return_date IS NULL`) referencing that item, enforced at the DB level by a
  partial unique index (`idx_loans_one_open_per_item` in `schema.sql`). Don't add a
  `status` field to `Item`; extend the loan-derivation logic in the relevant use case
  instead (see `SearchCatalog`, `CheckoutItem`).

## Methodology note

This repo has the `stream-coding` skill installed (`.claude-plugin/`,
`.claude/skills/stream-coding/`) — a documentation-first methodology where specs are
clarified to completeness before code generation. It activates automatically on triggers
like "build"/"create"/"implement"/"spec out"; no need to duplicate its instructions here.
