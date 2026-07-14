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
- **Built-in Testing**: `/testwelcome` lets admins verify their setup without waiting for a real member to join

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
- `/toggle <enable/disable>` - Enable/disable the bot in this server

### Setup Commands

- `/setmode <thread/channel>` - Set welcome mode
- `/setchannel <channel>` - Set channel for threads
- `/setcategory <category>` - Set category for channels
- `/viewconfig` - View current configuration

### Welcome Container Commands

- `/createembed` - Create a custom welcome container (opens a form)
- `/setembedimages` - Set thumbnail and image URLs for the welcome container
- `/toggleembed <true/false>` - Enable/disable the welcome container
- `/previewembed` - Preview the current welcome container

### Testing

- `/testwelcome` - Simulate a member join to test your setup without waiting for a real one

### Status

- `/status` - View bot status and statistics

## Welcome Container Placeholders

Use these in your welcome container's title/description/footer:

- `{user}` - Mentions the new member
- `{username}` - Member's username
- `{server}` - Server name
- `{member_count}` - Total member count

## Folder Structure

```
discord_bot/
├── bot.py              # Main entry point
├── .env                # Environment variables (not committed)
├── requirements.txt    # Dependencies
├── schema.sql          # Supabase table schema
├── cogs/                # Command modules
│   ├── admin.py          # $sync, /toggle
│   ├── setup.py          # /setmode, /setchannel, /setcategory, /viewconfig
│   ├── embed.py          # Welcome container commands
│   ├── status.py         # /status
│   ├── events.py         # on_member_join and welcome delivery
│   └── test.py           # /testwelcome
├── utils/               # Utility modules
│   ├── logger.py          # Colored console + file logging
│   ├── database.py        # Supabase wrapper
│   ├── layout_builder.py  # Components V2 container helpers
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
- **Embed Links**
- **Attach Files**

## Support

For issues or questions, please open an issue on GitHub.

## License

MIT License
