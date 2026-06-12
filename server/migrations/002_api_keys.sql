CREATE TABLE IF NOT EXISTS api_keys (
    id              BIGSERIAL PRIMARY KEY,
    key_type        TEXT NOT NULL CHECK (key_type IN ('publishable', 'secret')),
    key_hash        TEXT NOT NULL UNIQUE,
    key_prefix      TEXT NOT NULL,
    allowed_origins TEXT[] DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at      TIMESTAMPTZ
);
