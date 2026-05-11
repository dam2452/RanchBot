-- ============================================================================
-- Database setup
-- ============================================================================

SET TIME ZONE 'GMT-2';

CREATE SEQUENCE IF NOT EXISTS rest_user_id_seq
    START WITH -1
    INCREMENT BY -1
    MINVALUE -999999999999;


-- ============================================================================
-- User profiles & roles
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id          BIGINT PRIMARY KEY,
    username         TEXT UNIQUE,
    full_name        TEXT,
    subscription_end DATE DEFAULT NULL,
    note             TEXT DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id  ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_username ON user_profiles(username);


CREATE TABLE IF NOT EXISTS user_roles (
    user_id      BIGINT PRIMARY KEY REFERENCES user_profiles(user_id),
    is_admin     BOOLEAN NOT NULL DEFAULT FALSE,
    is_moderator BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_user_roles_user_id   ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_admin     ON user_roles(is_admin);
CREATE INDEX IF NOT EXISTS idx_user_roles_moderator ON user_roles(is_moderator);


-- ============================================================================
-- Authentication: credentials, refresh & verification tokens
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_credentials (
    user_id         BIGINT PRIMARY KEY REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    hashed_password VARCHAR(255) NOT NULL,
    auth_provider   TEXT DEFAULT 'local',
    last_updated    TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_credentials_user_id ON user_credentials(user_id);


CREATE TABLE IF NOT EXISTS refresh_tokens (
    id         SERIAL PRIMARY KEY,
    user_id    BIGINT REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    token      VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    ip_address VARCHAR(45),
    user_agent VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);


CREATE TABLE IF NOT EXISTS verification_tokens (
    id         SERIAL PRIMARY KEY,
    user_id    BIGINT REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    token      VARCHAR(32) NOT NULL,
    purpose    TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_verification_tokens_token      ON verification_tokens(token);
CREATE INDEX IF NOT EXISTS idx_verification_tokens_user_id    ON verification_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_verification_tokens_expires_at ON verification_tokens(expires_at);


-- ============================================================================
-- Series & user series context
-- ============================================================================

CREATE TABLE IF NOT EXISTS series (
    id          SERIAL PRIMARY KEY,
    series_name VARCHAR(50) UNIQUE NOT NULL,
    CONSTRAINT valid_series_name CHECK (series_name ~ '^[a-z0-9_-]+$')
);

CREATE INDEX IF NOT EXISTS idx_series_series_name ON series(series_name);


CREATE TABLE IF NOT EXISTS user_series_context (
    user_id          BIGINT PRIMARY KEY REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    active_series_id INT REFERENCES series(id) ON DELETE SET NULL,
    last_updated     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_series_context_user_id
    ON user_series_context(user_id);
CREATE INDEX IF NOT EXISTS idx_user_series_context_active_series_id
    ON user_series_context(active_series_id);

-- Migration: add JSONB column for multiple active series and backfill from
-- the legacy single-value active_series_id column.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_series_context' AND column_name = 'active_series'
    ) THEN
        ALTER TABLE user_series_context ADD COLUMN active_series JSONB DEFAULT NULL;
    END IF;
END $$;

UPDATE user_series_context u
SET active_series = jsonb_build_array(s.series_name)
FROM series s
WHERE u.active_series IS NULL AND u.active_series_id = s.id;

UPDATE user_series_context
SET active_series = '[]'::jsonb
WHERE active_series IS NULL;

ALTER TABLE user_series_context ALTER COLUMN active_series SET DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_user_series_context_active_series
    ON user_series_context USING gin (active_series);


-- ============================================================================
-- Video clips, search history, last clips, search filters
-- ============================================================================

CREATE TABLE IF NOT EXISTS video_clips (
    id             SERIAL PRIMARY KEY,
    chat_id        BIGINT NOT NULL,
    user_id        BIGINT NOT NULL,
    clip_name      TEXT NOT NULL,
    video_data     BYTEA NOT NULL,
    start_time     FLOAT,
    end_time       FLOAT,
    duration       FLOAT,
    season         INT,
    episode_number INT,
    is_compilation BOOLEAN NOT NULL DEFAULT FALSE,
    thumbnail_data BYTEA NULL
);

CREATE INDEX IF NOT EXISTS idx_video_clips_user_id   ON video_clips(user_id);
CREATE INDEX IF NOT EXISTS idx_video_clips_clip_name ON video_clips(clip_name);

-- Safety migration for instances created before thumbnail_data was part of the schema.
ALTER TABLE video_clips ADD COLUMN IF NOT EXISTS thumbnail_data BYTEA NULL;


CREATE TABLE IF NOT EXISTS search_history (
    id        SERIAL PRIMARY KEY,
    chat_id   BIGINT NOT NULL,
    quote     TEXT NOT NULL,
    segments  JSONB NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_search_history_timestamp ON search_history(timestamp);


CREATE TABLE IF NOT EXISTS last_clips (
    id                  SERIAL PRIMARY KEY,
    chat_id             BIGINT NOT NULL,
    segment             JSONB,
    compiled_clip       BYTEA,
    type                TEXT,
    adjusted_start_time FLOAT NULL,
    adjusted_end_time   FLOAT NULL,
    is_adjusted         BOOLEAN DEFAULT FALSE,
    timestamp           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_last_clips_timestamp ON last_clips(timestamp);
CREATE INDEX IF NOT EXISTS idx_last_clips_id        ON last_clips(id);
CREATE INDEX IF NOT EXISTS idx_last_clips_chat_id   ON last_clips(chat_id);


CREATE TABLE IF NOT EXISTS user_search_filters (
    id           SERIAL PRIMARY KEY,
    chat_id      BIGINT NOT NULL UNIQUE,
    filters      JSONB  NOT NULL DEFAULT '{}',
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_search_filters_chat_id ON user_search_filters(chat_id);


-- ============================================================================
-- Logging: user_logs (partitioned), system_logs, user_command_limits
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_logs (
    id        SERIAL,
    user_id   BIGINT,
    command   TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Yearly partitions 2023..2030
DO $$
DECLARE
    year_part INT;
BEGIN
    FOR year_part IN 2023..2030 LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS user_logs_%s PARTITION OF user_logs '
            'FOR VALUES FROM (''%s-01-01'') TO (''%s-01-01'')',
            year_part, year_part, year_part + 1
        );
    END LOOP;
END $$;

CREATE INDEX IF NOT EXISTS idx_user_logs_user_id ON user_logs(user_id);


CREATE TABLE IF NOT EXISTS system_logs (
    id          SERIAL PRIMARY KEY,
    log_level   TEXT NOT NULL,
    log_message TEXT NOT NULL,
    timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp);


CREATE TABLE IF NOT EXISTS user_command_limits (
    id        SERIAL PRIMARY KEY,
    user_id   BIGINT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_command_limits_user_id   ON user_command_limits(user_id);
CREATE INDEX IF NOT EXISTS idx_user_command_limits_timestamp ON user_command_limits(timestamp);


-- ============================================================================
-- Reports & subscription keys
-- ============================================================================

CREATE TABLE IF NOT EXISTS reports (
    id        SERIAL PRIMARY KEY,
    user_id   BIGINT NOT NULL,
    report    TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reports_user_id ON reports(user_id);


CREATE TABLE IF NOT EXISTS subscription_keys (
    id        SERIAL PRIMARY KEY,
    key       TEXT UNIQUE NOT NULL,
    days      INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_subscription_keys_key       ON subscription_keys(key);
CREATE INDEX IF NOT EXISTS idx_subscription_keys_is_active ON subscription_keys(is_active);


-- ============================================================================
-- series_id columns added retroactively to existing tables
-- ============================================================================

ALTER TABLE user_logs      ADD COLUMN IF NOT EXISTS series_id INT REFERENCES series(id) ON DELETE SET NULL;
ALTER TABLE video_clips    ADD COLUMN IF NOT EXISTS series_id INT REFERENCES series(id) ON DELETE SET NULL;
ALTER TABLE search_history ADD COLUMN IF NOT EXISTS series_id INT REFERENCES series(id) ON DELETE SET NULL;
ALTER TABLE last_clips     ADD COLUMN IF NOT EXISTS series_id INT REFERENCES series(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_user_logs_series_id      ON user_logs(series_id);
CREATE INDEX IF NOT EXISTS idx_video_clips_series_id    ON video_clips(series_id);
CREATE INDEX IF NOT EXISTS idx_search_history_series_id ON search_history(series_id);
CREATE INDEX IF NOT EXISTS idx_last_clips_series_id     ON last_clips(series_id);


-- ============================================================================
-- Cleanup triggers: purge rows older than 24h on each insert
-- ============================================================================

-- last_clips
CREATE OR REPLACE FUNCTION clean_old_last_clips() RETURNS trigger AS $$
BEGIN
    DELETE FROM last_clips WHERE timestamp < NOW() - INTERVAL '24 hours';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_clean_last_clips'
    ) THEN
        CREATE TRIGGER trigger_clean_last_clips
        AFTER INSERT ON last_clips
        FOR EACH ROW EXECUTE FUNCTION clean_old_last_clips();
    END IF;
END $$;


-- search_history
CREATE OR REPLACE FUNCTION clean_old_search_history() RETURNS trigger AS $$
BEGIN
    DELETE FROM search_history WHERE timestamp < NOW() - INTERVAL '24 hours';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_clean_search_history'
    ) THEN
        CREATE TRIGGER trigger_clean_search_history
        AFTER INSERT ON search_history
        FOR EACH ROW EXECUTE FUNCTION clean_old_search_history();
    END IF;
END $$;


-- user_command_limits
CREATE OR REPLACE FUNCTION clean_old_user_command_limits() RETURNS trigger AS $$
BEGIN
    DELETE FROM user_command_limits WHERE timestamp < NOW() - INTERVAL '24 hours';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_clean_user_command_limits'
    ) THEN
        CREATE TRIGGER trigger_clean_user_command_limits
        AFTER INSERT ON user_command_limits
        FOR EACH ROW EXECUTE FUNCTION clean_old_user_command_limits();
    END IF;
END $$;


-- Drop deprecated cleanup triggers (system_logs and user_logs are kept long-term).
DROP TRIGGER  IF EXISTS trigger_clean_system_logs ON system_logs;
DROP FUNCTION IF EXISTS clean_old_system_logs() CASCADE;

DROP TRIGGER  IF EXISTS trigger_clean_user_logs ON user_logs;
DROP FUNCTION IF EXISTS clean_old_user_logs() CASCADE;


-- ============================================================================
-- user_series_context triggers
-- ============================================================================

-- Refresh last_updated on every update.
CREATE OR REPLACE FUNCTION update_series_context_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_update_series_context_timestamp'
    ) THEN
        CREATE TRIGGER trigger_update_series_context_timestamp
        BEFORE UPDATE ON user_series_context
        FOR EACH ROW
        EXECUTE FUNCTION update_series_context_timestamp();
    END IF;
END $$;


-- Ensure every new user_profiles row gets a matching user_series_context row.
CREATE OR REPLACE FUNCTION ensure_user_series_context()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_series_context (user_id)
    VALUES (NEW.user_id)
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_ensure_user_series_context'
    ) THEN
        CREATE TRIGGER trigger_ensure_user_series_context
        AFTER INSERT ON user_profiles
        FOR EACH ROW
        EXECUTE FUNCTION ensure_user_series_context();
    END IF;
END $$;

-- Backfill user_series_context rows for users that existed before the trigger.
INSERT INTO user_series_context (user_id)
SELECT user_id
FROM user_profiles
ON CONFLICT (user_id) DO NOTHING;
