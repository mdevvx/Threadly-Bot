-- ============================================
-- Threadly - Supabase Database Schema
-- ============================================
-- Creates everything inside a dedicated threadly schema (not public).
-- Run this whole file once in the Supabase SQL Editor of a fresh project.
--
-- After running it:
--   1. Project Settings -> Data API -> "Exposed schemas": add  threadly
--      (lowercase) and save.
--   2. In .env set SUPABASE_URL and SUPABASE_KEY to the NEW project's URL
--      and service_role / secret key (Project Settings -> API Keys).
--      Optional: SUPABASE_SCHEMA=threadly (this is already the default).

-- --------------------------------------------
-- Schema
-- --------------------------------------------
CREATE SCHEMA IF NOT EXISTS threadly;

-- --------------------------------------------
-- Guild configuration table
-- --------------------------------------------
CREATE TABLE IF NOT EXISTS threadly.threadly_guild_configs (
    -- Primary identification
    id BIGSERIAL PRIMARY KEY,
    guild_id TEXT UNIQUE NOT NULL,

    -- Bot settings
    enabled BOOLEAN DEFAULT true,
    welcome_mode TEXT DEFAULT 'thread' CHECK (welcome_mode IN ('thread', 'channel')),

    -- Target locations
    target_channel_id TEXT,  -- For thread creation
    target_category_id TEXT, -- For channel creation

    -- Welcome container configuration
    embed_enabled BOOLEAN DEFAULT false,
    embed_title TEXT,
    embed_description TEXT,
    embed_color INTEGER,
    embed_thumbnail TEXT,
    embed_image TEXT,
    embed_footer TEXT,
    mention_role_ids TEXT[], -- Roles pinged via the {roles} placeholder
    asset_channel_id TEXT,   -- Hidden channel storing uploaded thumbnail/image files

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- guild_id already has an index through its UNIQUE constraint
CREATE INDEX IF NOT EXISTS idx_threadly_guild_configs_enabled
    ON threadly.threadly_guild_configs(enabled);

-- --------------------------------------------
-- updated_at trigger
-- --------------------------------------------
CREATE OR REPLACE FUNCTION threadly.update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc', NOW());
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS update_threadly_guild_configs_updated_at
    ON threadly.threadly_guild_configs;
CREATE TRIGGER update_threadly_guild_configs_updated_at
    BEFORE UPDATE ON threadly.threadly_guild_configs
    FOR EACH ROW
    EXECUTE FUNCTION threadly.update_updated_at_column();

-- --------------------------------------------
-- Access: the bot connects with the service_role (secret) key.
-- anon / authenticated get nothing, so the data is not reachable with
-- the public anon key even though the schema is exposed to the API.
-- --------------------------------------------
REVOKE ALL ON SCHEMA threadly FROM anon, authenticated;
GRANT USAGE ON SCHEMA threadly TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA threadly TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA threadly TO service_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA threadly TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA threadly GRANT ALL ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA threadly GRANT ALL ON SEQUENCES TO service_role;

-- RLS on: blocks every role except service_role (which bypasses RLS)
ALTER TABLE threadly.threadly_guild_configs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role has full access" ON threadly.threadly_guild_configs;
CREATE POLICY "Service role has full access"
    ON threadly.threadly_guild_configs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Make PostgREST pick up the new schema/table right away
NOTIFY pgrst, 'reload schema';

-- ============================================
-- Utility Queries
-- ============================================
-- SELECT * FROM threadly.threadly_guild_configs ORDER BY created_at DESC;
-- SELECT COUNT(*) FROM threadly.threadly_guild_configs WHERE enabled = true;
-- DELETE FROM threadly.threadly_guild_configs WHERE guild_id = 'YOUR_GUILD_ID';
