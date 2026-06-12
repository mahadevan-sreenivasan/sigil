CREATE TABLE IF NOT EXISTS geolocation_history (
    id          BIGSERIAL PRIMARY KEY,
    visitor_id  TEXT NOT NULL,
    account_id  TEXT,
    ip_address  INET NOT NULL,
    latitude    DOUBLE PRECISION,
    longitude   DOUBLE PRECISION,
    country     TEXT,
    city        TEXT,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_geo_visitor  ON geolocation_history(visitor_id);
CREATE INDEX IF NOT EXISTS idx_geo_account  ON geolocation_history(account_id);
CREATE INDEX IF NOT EXISTS idx_geo_ip       ON geolocation_history(ip_address);
CREATE INDEX IF NOT EXISTS idx_geo_captured ON geolocation_history(captured_at);
