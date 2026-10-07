-- ============================================
-- Threadly - copy data from the OLD project to the NEW project
-- ============================================
-- Prerequisite: schema.sql has already been run in the NEW project.
-- Stop the bot before starting so nothing is written mid-migration.


-- --------------------------------------------
-- STEP 1 - run in the OLD project's SQL Editor
-- --------------------------------------------
-- Returns a single cell containing every row as JSON.
-- Copy that cell's full value (click the cell -> copy).

SELECT json_agg(t ORDER BY t.id) AS rows_json
FROM public.threadly_guild_configs t;


-- --------------------------------------------
-- STEP 2 - run in the NEW project's SQL Editor
-- --------------------------------------------
-- Paste the copied JSON between the two $json$ markers (replace PASTE_HERE).
-- $json$ quoting means apostrophes inside welcome messages need no escaping.

INSERT INTO threadly.threadly_guild_configs (
    id, guild_id, enabled, welcome_mode, target_channel_id, target_category_id,
    embed_enabled, embed_title, embed_description, embed_color, embed_thumbnail,
    embed_image, embed_footer, mention_role_ids, asset_channel_id,
    created_at, updated_at
)
SELECT
    id, guild_id, enabled, welcome_mode, target_channel_id, target_category_id,
    embed_enabled, embed_title, embed_description, embed_color, embed_thumbnail,
    embed_image, embed_footer, mention_role_ids, asset_channel_id,
    COALESCE(created_at, updated_at, TIMEZONE('utc', NOW())),
    COALESCE(updated_at, TIMEZONE('utc', NOW()))
FROM json_populate_recordset(
    NULL::threadly.threadly_guild_configs,
    $json$PASTE_HERE$json$::json
)
ON CONFLICT (guild_id) DO NOTHING;

-- Move the id sequence past the copied ids so new guilds don't collide
SELECT setval(
    pg_get_serial_sequence('threadly.threadly_guild_configs', 'id'),
    COALESCE((SELECT MAX(id) FROM threadly.threadly_guild_configs), 0) + 1,
    false
);


-- --------------------------------------------
-- STEP 3 - verify (run in both projects, counts must match)
-- --------------------------------------------
-- OLD: SELECT COUNT(*) FROM public.threadly_guild_configs;
-- NEW: SELECT COUNT(*) FROM threadly.threadly_guild_configs;
