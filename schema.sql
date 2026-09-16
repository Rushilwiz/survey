-- Anonymous in-class survey. No PII: only a random survey token, answer slugs,
-- an optional comment, and a UTC timestamp. See docs/adr/0001-*.md.

CREATE TABLE IF NOT EXISTS submissions (
  id         INTEGER PRIMARY KEY,
  uuid       TEXT UNIQUE NOT NULL,   -- Survey token (UUIDv4); dedup key, not identity
  q1  TEXT, q2  TEXT, q3  TEXT, q4  TEXT, q5  TEXT,
  q6  TEXT, q7  TEXT, q8  TEXT, q9  TEXT, q10 TEXT,  -- q4 is comma-joined slugs
  comments   TEXT,
  created_at TEXT NOT NULL           -- UTC ISO 8601
);

CREATE TABLE IF NOT EXISTS meta (
  key   TEXT PRIMARY KEY,
  value TEXT
);
