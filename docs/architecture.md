# Bibliosphere — Architecture

This document defines the mandatory code structure for implementing Bibliosphere. See
`docs/requirements.md` for what is being built; this document covers how the code must be
organized.

## Why Clean Architecture

Business rules — loan limits, item availability, role permissions — must be understandable
and testable on their own, independent of the PySide GUI and the SQLite database. Clean
Architecture achieves this by keeping those rules in a layer that knows nothing about
frameworks, so either the GUI toolkit or the storage engine could be swapped later without
touching business logic.

## Layers & responsibilities

### `domain/`
- **Entities**: `Bibliography`, `Item`, `Member`, `Loan`, `Role` — plain dataclasses with
  zero framework dependencies (no SQLite, no PySide).
- **Domain exceptions**: e.g. `ItemNotAvailable`, `LoanLimitExceeded`.
- **Ports**: repository interfaces defined as `typing.Protocol` classes
  (`BibliographyRepository`, `MemberRepository`, `LoanRepository`), expressed purely in
  domain terms. Ports live here, not in `application/`, because they describe domain
  persistence contracts, not use-case orchestration. `Item` is managed as part of the
  `Bibliography` aggregate (add/remove/lookup item methods live on `BibliographyRepository`)
  rather than getting its own repository, since an item never exists without its parent
  bibliography.

### `application/`
- **Use cases**, one per user action: `CheckoutItem`, `ReturnItem`, `AddBibliography`,
  `AddItem`, `SearchCatalog`, `CreateMember`, `AuthenticateUser`, `ListMemberLoans`, etc.
- Each use case depends only on domain ports and entities, received via constructor
  injection. A use case must never import PySide or SQLite.
- **Config**: the fixed v1 loan-rule defaults — `LOAN_PERIOD_DAYS = 14`,
  `MAX_LOANS_PER_MEMBER = 5` — live here as named constants, since they parameterize use
  cases. This is the single place a future settings screen would need to change.
- **Security**: password hashing (PBKDF2-HMAC via stdlib `hashlib`, salted with
  `secrets.token_bytes`) lives here too — it's pure stdlib with no framework dependency, so
  it doesn't violate the dependency rule, and `CreateMember`/`AuthenticateUser` use cases
  call it directly.

### `infrastructure/`
- Concrete adapters implementing the domain ports: `SqliteBibliographyRepository`,
  `SqliteMemberRepository`, `SqliteLoanRepository`, plus DB connection and schema setup.
- Depends inward on `domain` (to implement its ports). Nothing else in the project depends
  on `infrastructure`.

### `presentation/`
- PySide windows/views and view-models/controllers that call use cases and render results.
- Depends on `application` (use cases) and `domain` (types). Never imports
  `infrastructure` directly — it only ever talks to use cases.

### Composition root (`main.py`)
The one place allowed to know about both `infrastructure` and `presentation`: it
constructs concrete repositories, injects them into use cases, and wires those use cases
into the GUI at startup.

### Seed script (`scripts/seed_admin.py`)
A second, minimal composition root, separate from `main.py`, used once during setup to
create the first librarian account (see `docs/requirements.md` §4.5 — in-app account
creation requires an existing librarian, so the first one can't be created through the
GUI). It wires up `SqliteMemberRepository` and calls the `CreateMember` use case directly
— it does not import `presentation`.

## Dependency Rule

Source-code dependencies point only inward:

```
presentation → application → domain
infrastructure → domain   (implements ports; nothing depends on infrastructure)
```

`domain` depends on nothing else in the project. Concretely: **no SQLite import and no
PySide import anywhere under `domain/` or `application/`.**

## Folder layout

```
src/bibliosphere/
  domain/
    entities.py       # Bibliography, Item, Member, Loan, Role
    ports.py           # BibliographyRepository, MemberRepository, LoanRepository (Protocols)
    exceptions.py       # ItemNotAvailable, LoanLimitExceeded, ...
  application/
    config.py          # LOAN_PERIOD_DAYS, MAX_LOANS_PER_MEMBER
    security.py         # password hashing (hashlib + secrets)
    use_cases/
      checkout_item.py
      return_item.py
      add_bibliography.py
      add_item.py
      search_catalog.py
      create_member.py
      authenticate_user.py
      list_member_loans.py
  infrastructure/
    sqlite/
      connection.py
      schema.sql
      bibliography_repository.py
      member_repository.py
      loan_repository.py
  presentation/
    qt/
      main_window.py
      login_view.py
      catalog_view.py
      ...
scripts/
  seed_admin.py          # one-off: creates the first librarian account
tests/                    # pytest; unit tests for domain/application against fake
                           # repositories, no real SQLite or Qt required
main.py                   # composition root
pyproject.toml             # packaging + dependencies (pip-installable)
```

## Port example

Ports are `typing.Protocol` classes — structural typing, no forced inheritance. A concrete
adapter satisfies a port simply by implementing matching methods, with no `class Foo(Port)`
declaration required.

```python
# domain/ports.py
from typing import Protocol
from domain.entities import Bibliography

class BibliographyRepository(Protocol):
    def add(self, bibliography: Bibliography) -> None: ...
    def get_by_isbn(self, isbn: str) -> Bibliography | None: ...
    def search(self, query: str) -> list[Bibliography]: ...
```

```python
# application/use_cases/search_catalog.py
from domain.ports import BibliographyRepository

class SearchCatalog:
    def __init__(self, bibliography_repository: BibliographyRepository):
        self._bibliography_repository = bibliography_repository

    def execute(self, query: str) -> list[Bibliography]:
        return self._bibliography_repository.search(query)
```

`SqliteBibliographyRepository` in `infrastructure/sqlite/bibliography_repository.py`
implements the same methods and satisfies `BibliographyRepository` without any explicit
inheritance.

## Testing implication

Use cases and entities must be testable with in-memory fakes that satisfy the repository
Protocols — no real SQLite database and no running Qt application required to test business
logic.
