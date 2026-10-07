"""
Status command - Display bot status and information
"""

import discord
from discord import app_commands
from discord.ext import commands
import platform
import psutil
from datetime import datetime, timezone
from utils.logger import logger
from utils.database import DatabaseError
from utils.layout_builder import ContainerLayout
from models.guild_config import GuildConfig
from config.settings import DEFAULT_EMBED_COLOR
from utils.command_group import threadly_group


class Status(commands.Cog):
    """Status and information commands"""

    def __init__(self, bot: commands.Bot):
        """Initialize the Status cog"""
        self.bot = bot
        self.start_time = datetime.now(timezone.utc)
        logger.info("Status cog initialized")

    async def status(self, interaction: discord.Interaction):
        """
        Show comprehensive bot status including:
        - Uptime
        - Server count
        - Memory usage
        - Latency
        - System info
        """
        try:
            await interaction.response.defer()

            # Calculate uptime
            uptime = datetime.now(timezone.utc) - self.start_time
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

            # System info
            memory = psutil.virtual_memory()
            memory_used = memory.used / (1024**2)  # MB
            memory_total = memory.total / (1024**2)
            cpu_percent = psutil.cpu_percent(interval=1)

            # Guild info
            total_guilds = len(self.bot.guilds)
            total_members = sum(guild.member_count for guild in self.bot.guilds)

            stat_blocks = [
                "**Bot Statistics**\n"
                f"Servers: {total_guilds}\n"
                f"Total Members: {total_members:,}\n"
                f"Latency: {round(self.bot.latency * 1000)}ms\n"
                f"Uptime: {uptime_str}",
                "**System Info**\n"
                f"Python: {platform.python_version()}\n"
                f"discord.py: {discord.__version__}\n"
                f"OS: {platform.system()} {platform.release()}\n"
                f"CPU Usage: {cpu_percent}%",
                "**Memory Usage**\n"
                f"Used: {memory_used:.2f} MB\n"
                f"Total: {memory_total:.2f} MB\n"
                f"Percentage: {memory.percent}%",
            ]

            # Guild-specific config, only shown when run inside a server
            if interaction.guild:
                try:
                    config_data = await self.bot.db.get_guild_config(interaction.guild.id)
                except DatabaseError:
                    config_data = None
                    stat_blocks.append("**Server Configuration**\nDatabase unreachable")
                if config_data:
                    config = GuildConfig.from_dict(config_data)
                    configured = "Yes" if config.is_configured() else "No"
                    stat_blocks.append(
                        "**Server Configuration**\n"
                        f"Status: {'Enabled' if config.enabled else 'Disabled'}\n"
                        f"Mode: {config.welcome_mode.capitalize()}\n"
                        f"Configured: {configured}\n"
                        f"Welcome Container: "
                        f"{'Enabled' if config.embed_enabled else 'Disabled'}"
                    )

            layout = ContainerLayout(
                heading="Bot Status",
                description="Current bot statistics and system information.",
                thumbnail_url=self.bot.user.display_avatar.url,
                extra_text=stat_blocks,
                footer=f"Requested by {interaction.user.name}",
                color=DEFAULT_EMBED_COLOR,
            )

            await interaction.followup.send(view=layout)
            logger.info(
                f"Status command used by {interaction.user.id} in guild "
                f"{interaction.guild.id if interaction.guild else 'DM'}"
            )

        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await interaction.followup.send(
                f"An error occurred while fetching status: {str(e)}", ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Setup function to add this cog to the bot"""
    cog = Status(bot)
    await bot.add_cog(cog)

    threadly_group.add_command(
        app_commands.Command(
            name="status",
            description="Display bot status and information",
            callback=cog.status,
        )
    )
