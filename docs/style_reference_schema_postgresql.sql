-- PostgreSQL-compatible schema for an optional external PythonSoundHelix style reference database.
-- The shipped app uses local SQLite for zero-install Windows operation, but this schema can be used later
-- for a central updateable reference database.
CREATE TABLE IF NOT EXISTS reference_entries (
  id BIGSERIAL PRIMARY KEY,
  reference_type TEXT NOT NULL CHECK (reference_type IN ('style','style_alias','trait','artist','artist_alias','song','user')),
  alias TEXT NOT NULL,
  normalized_alias TEXT NOT NULL UNIQUE,
  canonical_name TEXT NOT NULL,
  style_id TEXT,
  style_name TEXT,
  style_family TEXT NOT NULL,
  bpm_min INTEGER,
  bpm_max INTEGER,
  mode TEXT,
  drum_feel TEXT,
  bass_feel TEXT,
  groove TEXT,
  instruments_json JSONB DEFAULT '{}'::jsonb,
  intensity INTEGER DEFAULT 0,
  tags TEXT,
  traits TEXT,
  no_copy BOOLEAN DEFAULT TRUE,
  confidence INTEGER DEFAULT 70,
  source TEXT DEFAULT 'seed',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_reference_entries_normalized_alias ON reference_entries(normalized_alias);
CREATE INDEX IF NOT EXISTS idx_reference_entries_family ON reference_entries(style_family);
CREATE INDEX IF NOT EXISTS idx_reference_entries_type ON reference_entries(reference_type);
