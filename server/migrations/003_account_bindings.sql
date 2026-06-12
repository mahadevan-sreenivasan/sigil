CREATE TABLE IF NOT EXISTS account_bindings (
    visitor_id    TEXT NOT NULL,
    account_id    TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'observed' CHECK (status IN ('observed', 'verified')),
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verified_at   TIMESTAMPTZ,
    PRIMARY KEY (visitor_id, account_id)
);

CREATE INDEX IF NOT EXISTS idx_bindings_account ON account_bindings(account_id);
