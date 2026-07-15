"""
Shared top-level slash command group.

Every slash command in the bot is registered as a subcommand of this
single "/threadly" group instead of as its own top-level command, e.g.
"/threadly createembed" instead of "/createembed". Cogs live in
separate files, so this Group is defined once here and imported by
each cog's setup() function, which adds its own commands to it.
It's registered on the bot's CommandTree exactly once, in bot.py.
"""

from discord import app_commands

threadly_group = app_commands.Group(
    name="threadly",
    description="Threadly bot commands",
)
