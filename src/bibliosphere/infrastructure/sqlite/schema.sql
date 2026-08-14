CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('librarian', 'patron')),
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL
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
    call_number TEXT,
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
    member_id INTEGER NOT NULL REFERENCES members (id),
    checkout_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    return_date TEXT
);

CREATE INDEX IF NOT EXISTS idx_bibliography_authors_author_id ON bibliography_authors (author_id);
CREATE INDEX IF NOT EXISTS idx_items_bibliography_id ON items (bibliography_id);
CREATE INDEX IF NOT EXISTS idx_loans_item_id ON loans (item_id);
CREATE INDEX IF NOT EXISTS idx_loans_member_id ON loans (member_id);

-- An item can have at most one open (unreturned) loan at a time.
CREATE UNIQUE INDEX IF NOT EXISTS idx_loans_one_open_per_item
    ON loans (item_id) WHERE return_date IS NULL;
