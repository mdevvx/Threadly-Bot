"""
Discord Bot - Main Entry Point
A scalable Discord bot with welcome system (threads/channels)
"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import aiohttp
import traceback
from config.settings import DISCORD_TOKEN, BOT_PREFIX
from utils.logger import logger
from utils.database import db, DatabaseError
from utils.command_group import threadly_group


class WelcomeBot(commands.Bot):
    """Custom bot class with extended functionality and connection handling"""

    def __init__(self):
        """Initialize the bot with intents and settings"""
        # Setup intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True  # Required for member join events
        intents.guilds = True

        # Initialize bot with connection parameters
        super().__init__(
            command_prefix=BOT_PREFIX,
            intents=intents,
            help_command=None,  # Disable default help command
            max_messages=10000,  # Limit message cache to prevent memory issues
            heartbeat_timeout=60.0,  # Increase heartbeat timeout
            chunk_guilds_at_startup=False,  # Don't chunk all members at startup
        )

        # Store database instance
        self.db = db

        # Guild configs cache (guild_id: GuildConfig)
        self.guild_configs = {}

        # Connection tracking
        self.connection_lost = False
        self.reconnect_attempts = 0

        logger.info("Bot instance created")

    async def setup_hook(self):
        """Called when the bot is starting up"""
        logger.info("Running setup hook...")

        # Create aiohttp session for better connection pooling
        self.session = aiohttp.ClientSession()

        # Supabase client creation is async, so it happens here rather
        # than at import time. Must finish before cogs load since their
        # commands call bot.db methods.
        await self.db.initialize()

        # Register the shared /threadly command group; cogs add their
        # own subcommands to it as they load.
        self.tree.add_command(threadly_group)

        # Without this, an unhandled error in a command (e.g. send_modal
        # failing) leaves the interaction completely unacknowledged, and
        # Discord just shows "The application did not respond" with
        # nothing in the console to explain why.
        self.tree.on_error = self.on_app_command_error

        # Load all cogs
        await self.load_cogs()

        logger.info("Setup hook completed")

    async def load_cogs(self):
        """Load all cog extensions"""
        cogs = [
            "cogs.admin",
            "cogs.setup",
            "cogs.embed",
            "cogs.status",
            "cogs.events",
            "cogs.test",
        ]

        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")

    async def on_ready(self):
        """Called when the bot is ready"""
        if self.reconnect_attempts > 0:
            logger.info(f"Bot reconnected after {self.reconnect_attempts} attempts")
            self.reconnect_attempts = 0

        self.connection_lost = False
        logger.info(f"Logged in as {self.user.name} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        logger.info(f"Latency: {round(self.latency * 1000)}ms")
        logger.info("Bot is ready!")

    async def on_connect(self):
        """Called when the bot successfully connects to Discord"""
        logger.info("Successfully connected to Discord")
        self.connection_lost = False

    async def on_disconnect(self):
        """Called when the bot disconnects from Discord"""
        logger.warning("Disconnected from Discord")
        self.connection_lost = True
        self.reconnect_attempts += 1

    async def on_resumed(self):
        """Called when the bot resumes a session"""
        logger.info("Session resumed successfully")
        self.connection_lost = False
        self.reconnect_attempts = 0

    async def on_shard_connect(self, shard_id: int):
        """Called when a shard connects (if sharding is used)"""
        logger.info(f"Shard {shard_id} connected")

    async def on_shard_disconnect(self, shard_id: int):
        """Called when a shard disconnects (if sharding is used)"""
        logger.warning(f"Shard {shard_id} disconnected")

    async def on_guild_join(self, guild: discord.Guild):
        """Called when bot joins a new guild"""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")

        # Initialize default config for new guild
        from models.guild_config import GuildConfig

        try:
            # Only create defaults if the guild has no saved config, so
            # re-inviting the bot doesn't wipe an existing setup.
            if not await self.db.get_guild_config(guild.id):
                default_config = GuildConfig(guild_id=str(guild.id))
                await self.db.upsert_guild_config(guild.id, default_config.to_dict())
        except DatabaseError as e:
            logger.error(f"Could not initialize config for guild {guild.id}: {e}")

    async def on_guild_remove(self, guild: discord.Guild):
        """Called when bot is removed from a guild"""
        logger.info(f"Removed from guild: {guild.name} (ID: {guild.id})")

        # Remove from cache
        if guild.id in self.guild_configs:
            del self.guild_configs[guild.id]

    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        """Global error handler for prefix commands"""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore command not found errors

        logger.error(f"Command error in {ctx.command}: {error}")

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        """Global error handler for slash commands, so failures are visible
        instead of leaving the interaction unacknowledged."""
        command_name = interaction.command.qualified_name if interaction.command else "unknown"
        logger.error(
            f"App command error in /{command_name}: {error}\n"
            + "".join(traceback.format_exception(type(error), error, error.__traceback__))
        )

        original = getattr(error, "original", error)
        if isinstance(original, DatabaseError):
            message = str(original)
        else:
            message = "Something went wrong running that command. Please try again."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except discord.HTTPException:
            pass

    async def close(self):
        """Cleanup when bot shuts down"""
        logger.info("Closing bot connections...")
        if hasattr(self, "session") and self.session:
            await self.session.close()
        await super().close()


async def main():
    """Main function to run the bot with retry logic"""
    max_retries = 5
    retry_delay = 5  # seconds
    retry_count = 0

    while retry_count < max_retries:
        bot = WelcomeBot()

        try:
            logger.info(f"Starting bot... (Attempt {retry_count + 1}/{max_retries})")
            await bot.start(DISCORD_TOKEN)

        except discord.LoginFailure:
            logger.critical("Invalid token - cannot continue")
            break

        except discord.ConnectionClosed as e:
            logger.error(f"Connection closed: {e}")
            retry_count += 1
            if retry_count < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff

        except aiohttp.ClientError as e:
            logger.error(f"Network error: {e}")
            retry_count += 1
            if retry_count < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2

        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            break

        except Exception as e:
            logger.critical(f"Fatal error: {e}", exc_info=True)
            retry_count += 1
            if retry_count < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2

        finally:
            logger.info("Shutting down bot...")
            await bot.close()

    if retry_count >= max_retries:
        logger.critical("Max retry attempts reached. Bot shutting down.")


if __name__ == "__main__":
    """Entry point"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
