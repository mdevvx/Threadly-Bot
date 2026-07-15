"""
Test commands - Test welcome system functionality
"""

import discord
from discord import app_commands
from discord.ext import commands
from utils.logger import logger
from utils.layout_builder import ContainerLayout
from models.guild_config import GuildConfig
from config.settings import WELCOME_MODE_THREAD, WELCOME_MODE_CHANNEL
from utils.command_group import threadly_group
from cogs.embed import build_preview_layout
from cogs.events import delete_thread_created_message


class Test(commands.Cog):
    """Test commands for the welcome system"""

    def __init__(self, bot: commands.Bot):
        """Initialize the Test cog"""
        self.bot = bot
        logger.info("Test cog initialized")

    @app_commands.default_permissions(administrator=True)
    async def test_welcome(self, interaction: discord.Interaction):
        """
        Test the welcome system by simulating a member join

        This will:
        - Create a test thread/channel based on your mode
        - Send the welcome message/embed if configured
        - Allow you to verify your setup works correctly
        """
        try:
            # Defer immediately to prevent timeout
            await interaction.response.defer(ephemeral=True)

            logger.info(
                f"Test welcome command used by {interaction.user.id} in guild {interaction.guild.id}"
            )

            guild = interaction.guild
            guild_id = guild.id
            user = interaction.user

            # Get guild configuration
            config_data = await self.bot.db.get_guild_config(guild_id)

            if not config_data:
                await interaction.followup.send(
                    "[X] No configuration found for this server!\n"
                    "Please configure the bot first using:\n"
                    "- /threadly setmode - Choose thread or channel mode\n"
                    "- /threadly setchannel or /threadly setcategory - Set target location",
                    ephemeral=True,
                )
                return

            config = GuildConfig.from_dict(config_data)

            # Check if bot is enabled
            if not config.enabled:
                await interaction.followup.send(
                    "[X] The bot is currently disabled in this server.\n"
                    "Enable it using /threadly toggle enable",
                    ephemeral=True,
                )
                return

            # Check if properly configured
            if not config.is_configured():
                mode = config.welcome_mode
                if mode == WELCOME_MODE_THREAD:
                    missing = "Use /threadly setchannel to set the target channel."
                else:
                    missing = "Use /threadly setcategory to set the target category."

                await interaction.followup.send(
                    f"[X] Server is not fully configured.\n{missing}", ephemeral=True
                )
                return

            # Send initial status
            await interaction.followup.send(
                f"[TEST] Testing Welcome System...\n"
                f"Mode: **{config.welcome_mode}**\n"
                f"Embed: **{'Enabled' if config.embed_enabled else 'Disabled'}**\n"
                f"Testing with user: {user.mention}",
                ephemeral=True,
            )

            # Create thread or channel based on mode
            result = None
            if config.welcome_mode == WELCOME_MODE_THREAD:
                result = await self._test_thread_creation(user, config, interaction)
            else:  # WELCOME_MODE_CHANNEL
                result = await self._test_channel_creation(user, config, interaction)

            if result:
                await interaction.followup.send(
                    f"[SUCCESS] Test Successful!\n"
                    f"Created: {result.mention}\n"
                    f"You can check the {'thread' if config.welcome_mode == WELCOME_MODE_THREAD else 'channel'} "
                    f"to see how the welcome message looks.\n\n"
                    f"[TIP] You can delete this test {'thread' if config.welcome_mode == WELCOME_MODE_THREAD else 'channel'} manually.",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "[X] Test failed! Check the logs for error details.", ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error in testwelcome command: {e}")
            try:
                await interaction.followup.send(
                    f"[X] An error occurred during testing: {str(e)}", ephemeral=True
                )
            except:
                logger.error("Failed to send error message to user")

    async def _test_thread_creation(
        self,
        member: discord.Member,
        config: GuildConfig,
        interaction: discord.Interaction,
    ):
        """
        Test thread creation

        Args:
            member: Member to use for testing
            config: Guild configuration
            interaction: The interaction object

        Returns:
            Created thread or None if failed
        """
        try:
            guild = interaction.guild

            # Get target channel
            channel = guild.get_channel(int(config.target_channel_id))
            if not channel:
                await interaction.followup.send(
                    f"[X] Target channel (ID: {config.target_channel_id}) not found!",
                    ephemeral=True,
                )
                return None

            # Check permissions
            permissions = channel.permissions_for(guild.me)
            if not permissions.create_public_threads:
                await interaction.followup.send(
                    f"[X] Missing permission to create threads in {channel.mention}\n"
                    f"Grant me the **Create Public Threads** permission.",
                    ephemeral=True,
                )
                return None

            # Create test thread name
            thread_name = f"test-{member.name}"[:100]

            # Create the thread
            thread = await channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.public_thread,
                reason=f"Test welcome thread for {member.name}",
            )

            logger.info(f"Created test thread {thread.id} in guild {guild.id}")

            await delete_thread_created_message(channel, thread)

            # Send welcome message/embed
            await self._send_test_welcome_message(thread, member, config)

            return thread

        except discord.Forbidden:
            logger.error(f"Forbidden: Cannot create thread in guild {guild.id}")
            await interaction.followup.send(
                "[X] Permission denied to create threads!", ephemeral=True
            )
            return None
        except discord.HTTPException as e:
            logger.error(f"HTTP error creating test thread: {e}")
            await interaction.followup.send(
                f"[X] Failed to create thread: {str(e)}", ephemeral=True
            )
            return None
        except Exception as e:
            logger.error(f"Error creating test thread: {e}")
            return None

    async def _test_channel_creation(
        self,
        member: discord.Member,
        config: GuildConfig,
        interaction: discord.Interaction,
    ):
        """
        Test channel creation

        Args:
            member: Member to use for testing
            config: Guild configuration
            interaction: The interaction object

        Returns:
            Created channel or None if failed
        """
        try:
            guild = interaction.guild

            # Get target category
            category = guild.get_channel(int(config.target_category_id))
            if not category:
                await interaction.followup.send(
                    f"[X] Target category (ID: {config.target_category_id}) not found!",
                    ephemeral=True,
                )
                return None

            # Check permissions
            permissions = category.permissions_for(guild.me)
            if not permissions.manage_channels:
                await interaction.followup.send(
                    f"[X] Missing permission to create channels in **{category.name}**\n"
                    f"Grant me the **Manage Channels** permission.",
                    ephemeral=True,
                )
                return None

            # Create test channel name
            channel_name = self._sanitize_channel_name(f"test-{member.name}")

            # Create the channel
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                reason=f"Test welcome channel for {member.name}",
                topic=f"Test welcome channel for {member.mention}",
            )

            logger.info(f"Created test channel {channel.id} in guild {guild.id}")

            # Send welcome message/embed
            await self._send_test_welcome_message(channel, member, config)

            return channel

        except discord.Forbidden:
            logger.error(f"Forbidden: Cannot create channel in guild {guild.id}")
            await interaction.followup.send(
                "[X] Permission denied to create channels!", ephemeral=True
            )
            return None
        except discord.HTTPException as e:
            logger.error(f"HTTP error creating test channel: {e}")
            await interaction.followup.send(
                f"[X] Failed to create channel: {str(e)}", ephemeral=True
            )
            return None
        except Exception as e:
            logger.error(f"Error creating test channel: {e}")
            return None

    async def _send_test_welcome_message(
        self,
        destination: discord.abc.Messageable,
        member: discord.Member,
        config: GuildConfig,
    ):
        """
        Send test welcome message or embed

        Args:
            destination: Channel or thread to send message to
            member: Member for testing (used in placeholders)
            config: Guild configuration
        """
        try:
            if config.embed_enabled and config.get_embed_dict():
                layout = build_preview_layout(config, member, author_name="[TEST MODE]")
                logger.info(f"Sent test welcome layout to {destination.id}")
            else:
                layout = ContainerLayout(
                    author_name="[TEST MODE]",
                    description=(
                        f"Welcome {member.mention}!\n\n"
                        f"This is your personal welcome space. Feel free to introduce yourself!\n\n"
                        f"*This is a test message. Real welcome messages won't have the "
                        f"[TEST MODE] tag.*"
                    ),
                )
                logger.info(f"Sent test welcome message to {destination.id}")

            await destination.send(view=layout)

        except discord.Forbidden:
            logger.error(f"Forbidden: Cannot send message to {destination.id}")
        except discord.HTTPException as e:
            logger.error(f"HTTP error sending test welcome message: {e}")
        except Exception as e:
            logger.error(f"Error sending test welcome message: {e}")

    def _sanitize_channel_name(self, name: str) -> str:
        """
        Sanitize username for channel name (Discord requirements)

        Args:
            name: Original name

        Returns:
            Sanitized channel name
        """
        # Remove invalid characters for channel names
        # Discord allows: a-z, 0-9, hyphens
        sanitized = "".join(c if c.isalnum() or c == "-" else "-" for c in name.lower())

        # Remove consecutive hyphens
        while "--" in sanitized:
            sanitized = sanitized.replace("--", "-")

        # Remove leading/trailing hyphens
        sanitized = sanitized.strip("-")

        # Ensure it's not empty and max 100 characters
        if not sanitized:
            sanitized = "test-welcome-channel"

        return sanitized[:100]


async def setup(bot: commands.Bot):
    """Setup function to add this cog to the bot"""
    cog = Test(bot)
    await bot.add_cog(cog)

    threadly_group.add_command(
        app_commands.Command(
            name="testwelcome",
            description="Test the welcome system (creates a test thread/channel)",
            callback=cog.test_welcome,
        )
    )
