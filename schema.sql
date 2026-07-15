-- ============================================
-- Discord Welcome Bot - Supabase Database Schema
-- ============================================
-- This schema creates the necessary tables for the Discord bot
-- Run this in your Supabase SQL Editor

-- Create threadly_guild_configs table
CREATE TABLE IF NOT EXISTS threadly_guild_configs (
    -- Primary identification
    id BIGSERIAL PRIMARY KEY,
    guild_id TEXT UNIQUE NOT NULL,
    
    -- Bot settings
    enabled BOOLEAN DEFAULT true,
    welcome_mode TEXT DEFAULT 'thread' CHECK (welcome_mode IN ('thread', 'channel')),
    
    -- Target locations
    target_channel_id TEXT,  -- For thread creation
    target_category_id TEXT, -- For channel creation
    
    -- Welcome embed configuration
    embed_enabled BOOLEAN DEFAULT false,
    embed_title TEXT,
    embed_description TEXT,
    embed_color INTEGER,
    embed_thumbnail TEXT,
    embed_image TEXT,
    embed_footer TEXT,
    mention_role_ids TEXT[], -- Roles pinged via the {roles} placeholder

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Migration: run this manually if the table already existed before the
-- mention_role_ids column was added (CREATE TABLE IF NOT EXISTS above
-- won't add columns to an existing table).
-- ALTER TABLE threadly_guild_configs ADD COLUMN IF NOT EXISTS mention_role_ids TEXT[];

-- Create index on guild_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_threadly_guild_configs_guild_id ON threadly_guild_configs(guild_id);

-- Create index on enabled status for filtering
CREATE INDEX IF NOT EXISTS idx_threadly_guild_configs_enabled ON threadly_guild_configs(enabled);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc', NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to call the function before update
DROP TRIGGER IF EXISTS update_threadly_guild_configs_updated_at ON threadly_guild_configs;
CREATE TRIGGER update_threadly_guild_configs_updated_at
    BEFORE UPDATE ON threadly_guild_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Optional: Insert sample data for testing
-- ============================================
-- INSERT INTO threadly_guild_configs (guild_id, enabled, welcome_mode, target_channel_id, embed_enabled, embed_title, embed_description, embed_color)
-- VALUES 
--     ('123456789012345678', true, 'thread', '987654321098765432', true, 'Welcome to the Server!', 'We are glad to have you here, {user}!', 5865074);

-- ============================================
-- Row Level Security (RLS) - Optional but recommended
-- ============================================
-- Enable RLS on the table
ALTER TABLE threadly_guild_configs ENABLE ROW LEVEL SECURITY;

-- Create policy to allow service role full access
CREATE POLICY "Service role has full access"
    ON threadly_guild_configs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Create policy for anon key (if you want to restrict access)
CREATE POLICY "Anon can read own guild"
    ON threadly_guild_configs
    FOR SELECT
    TO anon
    USING (true);

CREATE POLICY "Anon can insert/update own guild"
    ON threadly_guild_configs
    FOR INSERT
    TO anon
    WITH CHECK (true);

CREATE POLICY "Anon can update own guild"
    ON threadly_guild_configs
    FOR UPDATE
    TO anon
    USING (true)
    WITH CHECK (true);

-- ============================================
-- Utility Queries
-- ============================================

-- View all guild configurations
-- SELECT * FROM threadly_guild_configs ORDER BY created_at DESC;

-- Count enabled guilds
-- SELECT COUNT(*) FROM threadly_guild_configs WHERE enabled = true;

-- Find guilds with thread mode
-- SELECT guild_id, target_channel_id FROM threadly_guild_configs WHERE welcome_mode = 'thread';

-- Find guilds with embeds enabled
-- SELECT guild_id, embed_title FROM threadly_guild_configs WHERE embed_enabled = true;

-- Delete a specific guild configuration
-- DELETE FROM threadly_guild_configs WHERE guild_id = 'YOUR_GUILD_ID';

-- Clear all configurations (use with caution!)
-- TRUNCATE TABLE threadly_guild_configs;