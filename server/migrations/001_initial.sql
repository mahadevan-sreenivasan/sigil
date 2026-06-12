CREATE TABLE IF NOT EXISTS visitors (
    visitor_id    TEXT PRIMARY KEY,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS signal_sets (
    id              BIGSERIAL PRIMARY KEY,
    visitor_id      TEXT NOT NULL REFERENCES visitors(visitor_id) ON DELETE CASCADE,
    captured_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    canvas_hash     TEXT,
    webgl_renderer  TEXT,
    audio_hash      TEXT,
    font_hash       TEXT,
    signals_extra   JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_signal_sets_visitor  ON signal_sets(visitor_id);
CREATE INDEX IF NOT EXISTS idx_signal_sets_canvas   ON signal_sets(canvas_hash);
CREATE INDEX IF NOT EXISTS idx_signal_sets_webgl    ON signal_sets(webgl_renderer);
CREATE INDEX IF NOT EXISTS idx_signal_sets_audio    ON signal_sets(audio_hash);
CREATE INDEX IF NOT EXISTS idx_signal_sets_font     ON signal_sets(font_hash);
CREATE INDEX IF NOT EXISTS idx_signal_sets_captured ON signal_sets(captured_at);
