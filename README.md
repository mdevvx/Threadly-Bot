# Discord Welcome Bot

A scalable Discord bot that creates personalized welcome threads or channels for new members, with fully customizable welcome messages built on Discord's Components V2.

## Features

- **Dual Mode**: Create threads OR channels for new members
- **Custom Welcome Containers**: Fully customizable welcome messages using Components V2 (Discord's successor to embeds)
- **Per-Server Config**: Independent settings for each server, nothing shared or mixed between guilds
- **Permission-Based**: Administrator-only setup commands
- **Database-Backed**: Supabase integration for persistent storage
- **Comprehensive Logging**: Colored console output plus daily log files
- **Slash Commands**: Modern Discord slash command interface, synced instantly per-guild
- **Built-in Testing**: `/threadly testwelcome` lets admins verify their setup without waiting for a real member to join

## Prerequisites

- Python 3.8+
- `discord.py` 2.6.0 or newer (required for Components V2 support)
- Discord Bot Token
- Supabase Account (free tier works)

## Installation

1. **Clone the repository**

```bash
   git clone <your-repo-url>
   cd discord_bot
```

2. **Install dependencies**

```bash
   pip install -r requirements.txt
```

3. **Setup Supabase**
    - Create a new project at [supabase.com](https://supabase.com)
    - Run the SQL schema from `schema.sql` in the SQL Editor
    - Copy your Project URL and anon key

4. **Configure environment variables**
    - Copy `.env` and fill in your credentials:

```env
   DISCORD_TOKEN=your_bot_token_here
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_anon_key
   BOT_PREFIX=$
   LOG_LEVEL=INFO
```

5. **Run the bot**

```bash
   python bot.py
```

6. **Sync commands**
    - In the server you want to test in, run `$sync` (bot owner only)
    - This syncs commands to that server instantly. Run it again in every
      server the bot joins, since sync is per-guild, not global (this avoids
      the duplicate-command issue global sync can cause)
    - `$sync clear` removes all commands from the current server

## Commands

### Admin Commands

- `$sync` - Sync slash commands to the current server (bot owner only)
- `$sync clear` - Remove all commands from the current server (bot owner only)
- `/threadly toggle <enable/disable>` - Enable/disable the bot in this server

All other commands are subcommands of the single `/threadly` slash command group.

### Setup Commands

- `/threadly setmode <thread/channel>` - Set welcome mode
- `/threadly setchannel <channel>` - Set channel for threads
- `/threadly setcategory <category>` - Set category for channels
- `/threadly viewconfig` - View current configuration

### Welcome Container Commands

- `/threadly createembed` - Create or edit the welcome container: title, description, color, and footer. Pre-fills with your current values if one already exists.
- `/threadly setimages` - Upload a thumbnail and/or image directly (drag & drop or browse). Leave a field blank to keep what's already set.
  - Uploaded files are re-hosted in a hidden `#threadly-assets` channel the bot creates automatically on first use (only the bot can see it) so the links don't expire like raw upload links do. Requires the **Manage Channels** permission the first time it's used.
- `/threadly setroles` - Pick which roles the `{roles}` placeholder mentions
- `/threadly toggleembed <true/false>` - Enable/disable the welcome container
- `/threadly previewembed` - Preview the current welcome container

### Testing

- `/threadly testwelcome` - Simulate a member join to test your setup without waiting for a real one

### Status

- `/threadly status` - View bot status and statistics

## Welcome Container Placeholders

Use these in your welcome container's title/description/footer:

- `{user}` - Mentions the new member (if omitted from the template entirely, it's still added to the description so joins keep pinging)
- `{username}` - Member's username
- `{server}` - Server name
- `{member_count}` - Total member count
- `{roles}` - Mentions the roles picked with `/threadly setroles`

Place `{user}` or `{roles}` wherever fits your design, e.g. a quiet `-# Say hi, {user}!` in the footer instead of a mention up top.

## Folder Structure

```
discord_bot/
├── bot.py              # Main entry point
├── .env                # Environment variables (not committed)
├── requirements.txt    # Dependencies
├── schema.sql          # Supabase table schema
├── cogs/                # Command modules
│   ├── admin.py          # $sync, /threadly toggle
│   ├── setup.py          # /threadly setmode, setchannel, setcategory, viewconfig
│   ├── embed.py          # /threadly welcome container commands
│   ├── status.py         # /threadly status
│   ├── events.py         # on_member_join and welcome delivery
│   └── test.py           # /threadly testwelcome
├── utils/               # Utility modules
│   ├── logger.py          # Colored console + file logging
│   ├── database.py        # Supabase wrapper
│   ├── layout_builder.py  # Components V2 container helpers
│   ├── command_group.py   # Shared /threadly app_commands.Group
│   └── check.py           # Reusable app_commands checks
├── models/              # Data models
│   └── guild_config.py    # Per-guild config dataclass
└── config/               # Configuration
    └── settings.py         # Env vars and constants
```

Every package folder has an `__init__.py`, so imports work the same whether you run the bot as-is or package it later.

## Permissions Required

The bot needs these permissions:

- **Read Messages/View Channels**
- **Send Messages**
- **Create Public Threads** (for thread mode)
- **Manage Channels** (for channel mode)
- **Manage Messages** (to hide the "started a thread" system message; skipped gracefully if missing)
- **Embed Links**
- **Attach Files**

## Support

For issues or questions, please open an issue on GitHub.

## License

MIT License
