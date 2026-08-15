# Library Management System — Requirements

## 1. Overview

Bibliosphere is a desktop application for managing a physical library's catalog,
membership, and book lending. It provides two roles — Librarian and Patron —
in a single application: librarians manage the catalog, members, and loans;
patrons can search the catalog and track their own borrowed books. The v1
goal is a solid MVP covering catalog management and checkout/return, running
as a single-computer desktop app with local storage — no server, no network
dependency.

## 2. Users & Roles

| Role | Description |
|---|---|
| **Librarian** | Full access: manage catalog (bibliographies & items), manage member accounts, check items out to members, process returns, view all loans. |
| **Patron** | Restricted access: search/browse the catalog, view their own current loans and due dates. Cannot check books out to themselves or edit catalog/member data. |

- Access is controlled via a **login screen**. Each user (librarian or patron)
  has an account; the UI and available actions adapt based on the logged-in
  user's role.
- Patron accounts are created by librarians only — there is no self-registration
  flow in v1.

## 3. Scope

### In scope (v1 / MVP)
- Bibliography catalog management (add, edit, search)
- Multi-item tracking per bibliography
- Member account management (librarian-created)
- Checkout and return, librarian-mediated
- Due-date tracking with fixed default loan rules
- Patron self-service search/browse + view of own loans
- Login screen with role-based access

### Out of scope (v1)
See [Section 7](#7-out-of-scope--future-considerations) for the full deferred list.

## 4. Functional Requirements

### 4.1 Catalog Management (Librarian)
- Add a new bibliography with: ISBN/ISSN, title, author(s), and other manually
  entered metadata fields (no external lookup or barcode scanning in v1).
- Edit existing bibliography details.
- Search the catalog (by title, author, or ISBN).
- Add/remove physical **items** of a bibliography; each item has its own item
  ID and status (`available` / `checked out`).

### 4.2 Member Management (Librarian)
- Create a new patron account.
- Edit existing member details.
- View a member's current loans.

### 4.3 Checkout / Return (Librarian)
- Check out an available item to a member, recording checkout date and
  computed due date.
- Process a return, marking the item `available` again and recording the
  return date.
- Default loan rules (v1, fixed, not yet configurable via UI):
  - Loan period: **14 days**
  - Max concurrent loans per patron: **5 books**
- These defaults should live in one clearly identified place in the code
  (e.g. a constants/config module) so they're easy to surface in a future
  settings screen.

### 4.4 Patron Self-Service
- Search/browse the catalog (read-only) and see item availability.
- View their own current loans and due dates.
- Cannot check out, return, or reserve books themselves in v1.

### 4.5 Authentication
- Login screen (username/password) for both roles.
- Role-based UI: librarians see catalog/member/checkout management tools;
  patrons see search and "my loans" only.
- Passwords are hashed with PBKDF2-HMAC (stdlib `hashlib`), salted via
  `secrets.token_bytes` — no third-party hashing dependency.
- **Bootstrap:** since patron/librarian accounts can only be created by a
  librarian in-app, the very first librarian account is created out-of-band
  by a standalone seed script (not via the GUI), run once during setup.

## 5. Data Model (Conceptual)

```
Member       (id, name, ..., role: librarian | patron)
Author       (id, name)
Bibliography (id, isbn_issn, title, sor, edition, publish_year, ...)
BibliographyAuthor (bibliography_id -> Bibliography, author_id -> Author, level)
Item         (id, bibliography_id -> Bibliography,
              item_status: available | checked_out)
Loan         (id, item_id -> Item, member_id -> Member,
              checkout_date, due_date, return_date)
```

- A **Bibliography** (title-level record) has many **Items** (1:many).
- A **Bibliography** has many **Authors**, and an **Author** may be credited on
  many Bibliographies (many-to-many, via `BibliographyAuthor`). `level` records
  each author's order/rank on that bibliography (1 = main author, higher =
  additional/co-author).
- A **Loan** links one **Item** to one **Member** with checkout/due/return
  dates; an item is `checked_out` while it has an open loan (no `return_date`).

## 6. Tech Stack

- **Language:** Python (project already has a `.venv`)
- **GUI:** PySide6
- **Storage:** SQLite, local file
- **Deployment:** Single computer, single app instance — no networked or
  shared-database architecture in v1
- **Architecture:** Clean Architecture (mandatory) — see `docs/architecture.md` for the
  full layering, dependency rule, and folder layout implementation must follow

## 6.1 Non-Functional: Scale

Bibliosphere replaces a predecessor app that became unusable as its data volume grew.
Views over tables that accumulate without bound over the library's lifetime (loan
history first; catalog and membership lists eventually) must stay responsive at
**1,000,000+ rows**: paginate and filter at the database layer rather than loading a
full table into memory or into a GUI widget, and avoid N+1 query patterns (resolve
related records with joins or batched lookups, not one query per row).

## 7. Out of Scope / Future Considerations

Deferred, not rejected — candidates for later versions:

- Reservations / holds queue
- Fines / overdue penalty calculation
- Notifications & due-date reminders
- Reporting & analytics (most popular books, overdue lists, etc.)
- Barcode scanner support for check-in/out and cataloging
- External ISBN metadata lookup (auto-fill title/author/cover)
- Patron self-registration
- Multi-computer / shared-database deployment (would require moving off
  plain SQLite to a client-server setup)
- Librarian-configurable loan rule settings screen (loan period, max books)
- Patron self-checkout/return (kiosk mode)

## 8. Open Questions

None outstanding. The loan-rule defaults (14 days / 5 items) are placeholders
and should be sanity-checked before implementation begins.
