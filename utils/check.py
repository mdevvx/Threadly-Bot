"""
Custom checks and decorators for commands
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Callable
from utils.logger import logger
from utils.layout_builder import QuickLayouts
from utils.database import DatabaseError


def is_bot_enabled():
    """
    Check if the bot is enabled in the current guild

    Usage:
        @is_bot_enabled()
        async def my_command(self, interaction: discord.Interaction):
            ...
    """

    async def predicate(interaction: discord.Interaction) -> bool:
        """Check predicate function"""
        if not interaction.guild:
            return False

        # Get bot instance
        bot = interaction.client

        # Get guild config
        try:
            config_data = await bot.db.get_guild_config(interaction.guild.id)
        except DatabaseError as e:
            await interaction.response.send_message(
                view=QuickLayouts.error("Database Unavailable", str(e)),
                ephemeral=True,
            )
            return False

        if not config_data:
            return True  # Allow if no config exists yet

        from models.guild_config import GuildConfig

        config = GuildConfig.from_dict(config_data)

        if not config.enabled:
            await interaction.response.send_message(
                view=QuickLayouts.error(
                    "Bot Disabled",
                    "The bot is currently disabled in this server. "
                    "An administrator can enable it using `/threadly toggle enable`.",
                ),
                ephemeral=True,
            )
            return False

        return True

    return app_commands.check(predicate)


def is_guild_configured():
    """
    Check if the guild has been properly configured

    Usage:
        @is_guild_configured()
        async def my_command(self, interaction: discord.Interaction):
            ...
    """

    async def predicate(interaction: discord.Interaction) -> bool:
        """Check predicate function"""
        if not interaction.guild:
            return False

        # Get bot instance
        bot = interaction.client

        # Get guild config
        try:
            config_data = await bot.db.get_guild_config(interaction.guild.id)
        except DatabaseError as e:
            await interaction.response.send_message(
                view=QuickLayouts.error("Database Unavailable", str(e)),
                ephemeral=True,
            )
            return False

        if not config_data:
            await interaction.response.send_message(
                view=QuickLayouts.warning(
                    "Server Not Configured",
                    "This server hasn't been configured yet. Please use the "
                    "setup commands first:\n"
                    "`/threadly setmode` - Choose thread or channel mode\n"
                    "`/threadly setchannel` or `/threadly setcategory` - Set target location",
                ),
                ephemeral=True,
            )
            return False

        from models.guild_config import GuildConfig

        config = GuildConfig.from_dict(config_data)

        if not config.is_configured():
            mode = config.welcome_mode
            if mode == "thread":
                missing = "Use `/threadly setchannel` to set the target channel."
            else:
                missing = "Use `/threadly setcategory` to set the target category."

            await interaction.response.send_message(
                view=QuickLayouts.warning("Server Not Fully Configured", missing),
                ephemeral=True,
            )
            return False

        return True

    return app_commands.check(predicate)


def has_manage_guild():
    """
    Check if user has Manage Guild permission

    Usage:
        @has_manage_guild()
        async def my_command(self, interaction: discord.Interaction):
            ...
    """

    async def predicate(interaction: discord.Interaction) -> bool:
        """Check predicate function"""
        if not interaction.guild:
            return False

        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ You need the **Manage Server** permission to use this command.",
                ephemeral=True,
            )
            return False

        return True

    return app_commands.check(predicate)


def is_owner_or_admin():
    """
    Check if user is bot owner or server administrator

    Usage:
        @is_owner_or_admin()
        async def my_command(self, interaction: discord.Interaction):
            ...
    """

    async def predicate(interaction: discord.Interaction) -> bool:
        """Check predicate function"""
        bot = interaction.client

        # Check if bot owner
        if await bot.is_owner(interaction.user):
            return True

        # Check if server admin
        if interaction.guild and interaction.user.guild_permissions.administrator:
            return True

        await interaction.response.send_message(
            "❌ You must be a server administrator to use this command.", ephemeral=True
        )
        return False

    return app_commands.check(predicate)


class BotChecks:
    """Collection of reusable check methods"""

    @staticmethod
    async def check_bot_permissions(
        channel: discord.abc.GuildChannel, *permissions: str
    ) -> tuple[bool, list[str]]:
        """
        Check if bot has required permissions in a channel

        Args:
            channel: Channel to check permissions in
            *permissions: Permission names to check (e.g., 'send_messages', 'manage_channels')

        Returns:
            Tuple of (has_all_permissions, list_of_missing_permissions)
        """
        if not isinstance(channel, discord.abc.GuildChannel):
            return False, []

        bot_member = channel.guild.me
        channel_perms = channel.permissions_for(bot_member)

        missing = []
        for perm in permissions:
            if not getattr(channel_perms, perm, False):
                missing.append(perm)

        return len(missing) == 0, missing

    @staticmethod
    async def check_user_permissions(
        member: discord.Member, *permissions: str
    ) -> tuple[bool, list[str]]:
        """
        Check if user has required permissions

        Args:
            member: Member to check permissions for
            *permissions: Permission names to check

        Returns:
            Tuple of (has_all_permissions, list_of_missing_permissions)
        """
        user_perms = member.guild_permissions

        missing = []
        for perm in permissions:
            if not getattr(user_perms, perm, False):
                missing.append(perm)

        return len(missing) == 0, missing

    @staticmethod
    def format_permissions(permissions: list[str]) -> str:
        """
        Format permission names for display

        Args:
            permissions: List of permission names

        Returns:
            Formatted string with permission names
        """
        formatted = []
        for perm in permissions:
            # Convert snake_case to Title Case
            readable = perm.replace("_", " ").title()
            formatted.append(f"• {readable}")

        return "\n".join(formatted)


# Decorator for prefix commands (legacy support)
def is_bot_owner():
    """Check if user is the bot owner (for prefix commands)"""

    async def predicate(ctx: commands.Context) -> bool:
        return await ctx.bot.is_owner(ctx.author)

    return commands.check(predicate)


def has_admin_perms():
    """Check if user has administrator permissions (for prefix commands)"""

    async def predicate(ctx: commands.Context) -> bool:
        return ctx.author.guild_permissions.administrator

    return commands.check(predicate)
