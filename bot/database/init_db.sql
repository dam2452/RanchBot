SET TIME ZONE 'GMT-2';

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id BIGINT PRIMARY KEY,
    username TEXT UNIQUE,
    full_name TEXT,
    subscription_end DATE DEFAULT NULL,
    note TEXT DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles (user_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_username ON user_profiles (username);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id BIGINT PRIMARY KEY REFERENCES user_profiles(user_id),
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    is_moderator BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_admin ON user_roles (is_admin);
CREATE INDEX IF NOT EXISTS idx_user_roles_moderator ON user_roles (is_moderator);

CREATE TABLE IF NOT EXISTS user_logs (
    id SERIAL,
    user_id BIGINT,
    command TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

CREATE TABLE IF NOT EXISTS user_logs_2023 PARTITION OF user_logs
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');

CREATE TABLE IF NOT EXISTS user_logs_2024 PARTITION OF user_logs
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE IF NOT EXISTS user_logs_2025 PARTITION OF user_logs
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

CREATE TABLE IF NOT EXISTS user_logs_2026 PARTITION OF user_logs
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

CREATE TABLE IF NOT EXISTS user_logs_2027 PARTITION OF user_logs
    FOR VALUES FROM ('2027-01-01') TO ('2028-01-01');

CREATE TABLE IF NOT EXISTS user_logs_2028 PARTITION OF user_logs
    FOR VALUES FROM ('2028-01-01') TO ('2029-01-01');

CREATE TABLE IF NOT EXISTS user_logs_2029 PARTITION OF user_logs
    FOR VALUES FROM ('2029-01-01') TO ('2030-01-01');

CREATE TABLE IF NOT EXISTS user_logs_2030 PARTITION OF user_logs
    FOR VALUES FROM ('2030-01-01') TO ('2031-01-01');

CREATE INDEX IF NOT EXISTS idx_user_logs_user_id ON user_logs(user_id);

CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    log_level TEXT NOT NULL,
    log_message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp);

CREATE TABLE IF NOT EXISTS video_clips (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    clip_name TEXT NOT NULL,
    video_data BYTEA NOT NULL,
    start_time FLOAT,
    end_time FLOAT,
    duration FLOAT,
    season INT,
    episode_number INT,
    is_compilation BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_video_clips_user_id ON video_clips(user_id);
CREATE INDEX IF NOT EXISTS idx_video_clips_clip_name ON video_clips(clip_name);

CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    report TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reports_user_id ON reports(user_id);

CREATE TABLE IF NOT EXISTS search_history (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    quote TEXT NOT NULL,
    segments JSONB NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_search_history_timestamp ON search_history(timestamp);

CREATE TABLE IF NOT EXISTS last_clips (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    segment JSONB,
    compiled_clip BYTEA,
    type TEXT,
    adjusted_start_time FLOAT NULL,
    adjusted_end_time FLOAT NULL,
    is_adjusted BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_last_clips_timestamp ON last_clips(timestamp);
CREATE INDEX IF NOT EXISTS idx_last_clips_id ON last_clips(id);
CREATE INDEX IF NOT EXISTS idx_last_clips_chat_id ON last_clips(chat_id);

CREATE TABLE IF NOT EXISTS user_command_limits (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_command_limits_user_id ON user_command_limits(user_id);
CREATE INDEX IF NOT EXISTS idx_user_command_limits_timestamp ON user_command_limits(timestamp);

CREATE TABLE IF NOT EXISTS subscription_keys (
    id SERIAL PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    days INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_subscription_keys_key ON subscription_keys(key);
CREATE INDEX IF NOT EXISTS idx_subscription_keys_is_active ON subscription_keys(is_active);


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

CREATE OR REPLACE FUNCTION clean_old_system_logs() RETURNS trigger AS $$
BEGIN
    DELETE FROM system_logs WHERE timestamp < NOW() - INTERVAL '365 days';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_clean_system_logs'
    ) THEN
        CREATE TRIGGER trigger_clean_system_logs
        AFTER INSERT ON system_logs
        FOR EACH ROW EXECUTE FUNCTION clean_old_system_logs();
    END IF;
END $$;

CREATE OR REPLACE FUNCTION clean_old_user_logs() RETURNS trigger AS $$
BEGIN
    DELETE FROM user_logs WHERE timestamp < NOW() - INTERVAL '365 days';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_clean_user_logs'
    ) THEN
        CREATE TRIGGER trigger_clean_user_logs
        AFTER INSERT ON user_logs
        FOR EACH ROW EXECUTE FUNCTION clean_old_user_logs();
    END IF;
END $$;

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

-- --- ---

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    ip_address VARCHAR(45),
    user_agent VARCHAR(255)
);


CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

CREATE TABLE IF NOT EXISTS user_credentials (
    user_id BIGINT PRIMARY KEY REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    hashed_password VARCHAR(255) NOT NULL,
    auth_provider TEXT DEFAULT 'local',
    last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_credentials_user_id ON user_credentials(user_id);

CREATE TABLE IF NOT EXISTS user_series_context (
    user_id BIGINT PRIMARY KEY REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    active_series VARCHAR(50) NOT NULL DEFAULT 'ranczo',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_series_name CHECK (active_series ~ '^[a-z0-9_-]+$')
);

CREATE INDEX IF NOT EXISTS idx_user_series_context_user_id
    ON user_series_context(user_id);
CREATE INDEX IF NOT EXISTS idx_user_series_context_active_series
    ON user_series_context(active_series);

CREATE OR REPLACE FUNCTION update_series_context_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_series_context_timestamp
BEFORE UPDATE ON user_series_context
FOR EACH ROW
EXECUTE FUNCTION update_series_context_timestamp();

CREATE OR REPLACE FUNCTION ensure_user_series_context()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_series_context (user_id, active_series)
    VALUES (NEW.user_id, 'ranczo')
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_ensure_user_series_context
AFTER INSERT ON user_profiles
FOR EACH ROW
EXECUTE FUNCTION ensure_user_series_context();

INSERT INTO user_series_context (user_id, active_series)
SELECT user_id, 'ranczo'
FROM user_profiles
ON CONFLICT (user_id) DO NOTHING;
