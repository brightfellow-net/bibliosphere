-- `id` is a librarian-assigned membership number (e.g. "20260814001" — date +
-- daily sequence), supplied by the application at insert time, not autoincremented.
-- username/password_hash/password_salt are nullable: required for librarians (who
-- must log in) but optional for patrons, who may have no self-service login. SQLite's
-- UNIQUE treats each NULL as distinct, so multiple username-less patrons are fine.
CREATE TABLE IF NOT EXISTS members (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('librarian', 'patron')),
    password_hash TEXT,
    password_salt TEXT,
    birthdate TEXT,
    email TEXT,
    phone TEXT,
    join_date TEXT,
    expiry_date TEXT,
    address TEXT
);

-- Column set follows data/migration/v1_biblio.sql (legacy `biblio` table), trimmed to
-- the core cataloging fields; OPAC/admin-audit columns (opac_hide, promoted, uid, image,
-- file_att, labels, spec_detail_info, source, frequency_id, input_date/last_update) are
-- out of v1 scope. `gmd_id`, `publisher_id`, `publish_place_id`, `content_type_id`,
-- `media_type_id`, `carrier_type_id` are stored as plain nullable ids with no FK/lookup
-- table yet. Author is normalized out to `authors` + `bibliography_authors` rather than
-- the legacy `sor` free-text field, though `sor` is kept for the literal title-page
-- statement of responsibility.
CREATE TABLE IF NOT EXISTS bibliographies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    isbn_issn TEXT,
    sor TEXT,
    edition TEXT,
    publish_year TEXT,
    collation TEXT,
    series_title TEXT,
    call_number TEXT NOT NULL,
    classification TEXT,
    notes TEXT,
    language_id TEXT NOT NULL DEFAULT 'en',
    gmd_id INTEGER,
    publisher_id INTEGER,
    publish_place_id INTEGER,
    content_type_id INTEGER,
    media_type_id INTEGER,
    carrier_type_id INTEGER
);

CREATE TABLE IF NOT EXISTS authors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Follows data/migration/v2__author.sql (legacy `biblio_author` table). `level`
-- is the author's order/rank on this bibliography (1 = main author, higher =
-- additional/co-author); no lookup table for level values yet, plain integer.
CREATE TABLE IF NOT EXISTS bibliography_authors (
    bibliography_id INTEGER NOT NULL REFERENCES bibliographies (id),
    author_id INTEGER NOT NULL REFERENCES authors (id),
    level INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (bibliography_id, author_id)
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bibliography_id INTEGER NOT NULL REFERENCES bibliographies (id)
);

CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL REFERENCES items (id),
    member_id TEXT NOT NULL REFERENCES members (id),
    checkout_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    return_date TEXT
);

-- Back CatalogFilters/list_page's prefix (LIKE 'text%') filtering and sorting, so the
-- catalog stays fast as bibliographies grows into the thousands.
CREATE INDEX IF NOT EXISTS idx_bibliographies_title ON bibliographies (title);
CREATE INDEX IF NOT EXISTS idx_bibliographies_call_number ON bibliographies (call_number);
CREATE INDEX IF NOT EXISTS idx_bibliographies_isbn_issn ON bibliographies (isbn_issn);

CREATE INDEX IF NOT EXISTS idx_bibliography_authors_author_id ON bibliography_authors (author_id);
CREATE INDEX IF NOT EXISTS idx_items_bibliography_id ON items (bibliography_id);
CREATE INDEX IF NOT EXISTS idx_loans_item_id ON loans (item_id);
CREATE INDEX IF NOT EXISTS idx_loans_member_id ON loans (member_id);
-- Matches the ORDER BY in SqliteLoanRepository.list_history_page, so paginating the
-- loan history view stays an index walk instead of a full sort at any data volume.
CREATE INDEX IF NOT EXISTS idx_loans_checkout_date ON loans (checkout_date DESC, id DESC);

-- An item can have at most one open (unreturned) loan at a time.
CREATE UNIQUE INDEX IF NOT EXISTS idx_loans_one_open_per_item
    ON loans (item_id) WHERE return_date IS NULL;

-- Trigram-tokenized FTS5 indexes backing CatalogFilters' substring search on
-- title/author (the other 5 filterable columns stay prefix-LIKE, see the indexes
-- above). External-content tables (content=<table>, content_rowid='id') so FTS5
-- doesn't duplicate the title/name text; the FTS rowid maps 1:1 onto the real
-- primary key. Query the FTS table via its own `rowid` column, not `id` — the
-- virtual table itself has no `id` column, content_rowid only tells FTS5 which
-- content-table column to sync against.
--
-- External-content tables do not auto-sync, hence the triggers below.
CREATE VIRTUAL TABLE IF NOT EXISTS bibliographies_title_fts USING fts5(
    title, content='bibliographies', content_rowid='id', tokenize='trigram'
);

CREATE TRIGGER IF NOT EXISTS bibliographies_title_fts_ai AFTER INSERT ON bibliographies BEGIN
    INSERT INTO bibliographies_title_fts(rowid, title) VALUES (new.id, new.title);
END;

CREATE TRIGGER IF NOT EXISTS bibliographies_title_fts_ad AFTER DELETE ON bibliographies BEGIN
    INSERT INTO bibliographies_title_fts(bibliographies_title_fts, rowid, title)
    VALUES ('delete', old.id, old.title);
END;

CREATE TRIGGER IF NOT EXISTS bibliographies_title_fts_au AFTER UPDATE ON bibliographies BEGIN
    INSERT INTO bibliographies_title_fts(bibliographies_title_fts, rowid, title)
    VALUES ('delete', old.id, old.title);
    INSERT INTO bibliographies_title_fts(rowid, title) VALUES (new.id, new.title);
END;

-- Backfill/self-heal for rows written before this index existed. NOTE: an
-- "INSERT ... SELECT ... WHERE id NOT IN (SELECT rowid FROM bibliographies_title_fts)"
-- looks like the obvious idempotent approach but is BROKEN for external-content FTS5
-- tables: a plain (non-MATCH) SELECT/COUNT against such a table reads straight through
-- to the content table for any rowid, regardless of whether that rowid has actually
-- been added to the trigram index yet — so that NOT-IN subquery is vacuously always
-- empty once bibliographies has rows, and the backfill silently never runs (confirmed
-- empirically). 'rebuild' is FTS5's documented command to fully regenerate the index
-- from the current content table; it's the only reliable way to backfill/self-heal an
-- external-content table, and running it unconditionally on every startup is safe
-- (fully idempotent) — it's a one-time, ~150ms-at-4,126-rows startup cost (scales with
-- content size, not a per-query cost), not the per-keystroke query path this feature
-- is about.
INSERT INTO bibliographies_title_fts(bibliographies_title_fts) VALUES ('rebuild');

-- authors is insert-only today (AuthorRepository/SqliteAuthorRepository expose no
-- update or remove), so only an AFTER INSERT trigger is needed here — mirrors how
-- `items` has no status column for the same "don't write untestable code for a
-- case the port can't produce" reasoning. If AuthorRepository ever grows
-- update/remove, add AU/AD triggers mirroring bibliographies_title_fts's above.
CREATE VIRTUAL TABLE IF NOT EXISTS authors_name_fts USING fts5(
    name, content='authors', content_rowid='id', tokenize='trigram'
);

CREATE TRIGGER IF NOT EXISTS authors_name_fts_ai AFTER INSERT ON authors BEGIN
    INSERT INTO authors_name_fts(rowid, name) VALUES (new.id, new.name);
END;

-- See the long comment above bibliographies_title_fts's backfill — same reasoning.
INSERT INTO authors_name_fts(authors_name_fts) VALUES ('rebuild');
