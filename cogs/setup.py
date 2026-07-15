"""
Setup commands - Configure welcome system (channels, categories, mode)
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from utils.logger import logger
from utils.check import is_bot_enabled
from utils.layout_builder import ContainerLayout, QuickLayouts
from models.guild_config import GuildConfig
from config.settings import WELCOME_MODE_THREAD, WELCOME_MODE_CHANNEL, DEFAULT_EMBED_COLOR
from utils.command_group import threadly_group


class Setup(commands.Cog):
    """Setup commands for configuring the welcome system"""

    def __init__(self, bot: commands.Bot):
        """Initialize the Setup cog"""
        self.bot = bot
        logger.info("Setup cog initialized")

    @app_commands.describe(mode="Choose between thread or channel creation")
    @app_commands.default_permissions(administrator=True)
    @is_bot_enabled()
    async def set_mode(
        self, interaction: discord.Interaction, mode: Literal["thread", "channel"]
    ):
        """
        Set the welcome mode for new members

        Args:
            mode: 'thread' (creates threads) or 'channel' (creates channels)
        """
        try:
            await interaction.response.defer(ephemeral=True)

            guild_id = interaction.guild.id
            config_data = await self.bot.db.get_guild_config(guild_id)
            config = (
                GuildConfig.from_dict(config_data)
                if config_data
                else GuildConfig(guild_id=str(guild_id))
            )

            config.welcome_mode = mode
            await self.bot.db.upsert_guild_config(guild_id, config.to_dict())
            self.bot.guild_configs[guild_id] = config

            next_step = (
                "Use `/threadly setchannel` to set the channel where threads will be created."
                if mode == WELCOME_MODE_THREAD
                else "Use `/threadly setcategory` to set the category where channels will be created."
            )

            await interaction.followup.send(
                view=QuickLayouts.success(
                    "Welcome Mode Updated",
                    f"Welcome mode set to **{mode}**.\n\n{next_step}",
                    footer=f"Changed by {interaction.user.name}",
                ),
                ephemeral=True,
            )
            logger.info(f"Welcome mode set to {mode} in guild {guild_id}")

        except Exception as e:
            logger.error(f"Error in setmode command: {e}")
            await interaction.followup.send(
                view=QuickLayouts.error("Something Went Wrong", str(e)),
                ephemeral=True,
            )

    @app_commands.describe(channel="The channel where welcome threads will be created")
    @app_commands.default_permissions(administrator=True)
    @is_bot_enabled()
    async def set_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        """
        Set the target channel for creating welcome threads

        Args:
            channel: Discord text channel where threads will be created
        """
        try:
            await interaction.response.defer(ephemeral=True)

            guild_id = interaction.guild.id

            permissions = channel.permissions_for(interaction.guild.me)
            if not permissions.create_public_threads:
                await interaction.followup.send(
                    view=QuickLayouts.error(
                        "Missing Permission",
                        f"I don't have permission to create threads in {channel.mention}.\n"
                        f"Grant me the **Create Public Threads** permission.",
                    ),
                    ephemeral=True,
                )
                return

            config_data = await self.bot.db.get_guild_config(guild_id)
            config = (
                GuildConfig.from_dict(config_data)
                if config_data
                else GuildConfig(guild_id=str(guild_id))
            )

            config.target_channel_id = str(channel.id)
            await self.bot.db.upsert_guild_config(guild_id, config.to_dict())
            self.bot.guild_configs[guild_id] = config

            description = f"Welcome threads will be created in {channel.mention}."
            if config.welcome_mode != WELCOME_MODE_THREAD:
                description += (
                    f"\n\n**Note:** Current mode is **{config.welcome_mode}**. "
                    f"Use `/threadly setmode thread` to enable thread creation."
                )

            await interaction.followup.send(
                view=QuickLayouts.success(
                    "Thread Channel Set",
                    description,
                    footer=f"Changed by {interaction.user.name}",
                ),
                ephemeral=True,
            )
            logger.info(f"Thread channel set to {channel.id} in guild {guild_id}")

        except Exception as e:
            logger.error(f"Error in setchannel command: {e}")
            await interaction.followup.send(
                view=QuickLayouts.error("Something Went Wrong", str(e)),
                ephemeral=True,
            )

    @app_commands.describe(
        category="The category where welcome channels will be created"
    )
    @app_commands.default_permissions(administrator=True)
    @is_bot_enabled()
    async def set_category(
        self, interaction: discord.Interaction, category: discord.CategoryChannel
    ):
        """
        Set the target category for creating welcome channels

        Args:
            category: Discord category where channels will be created
        """
        try:
            await interaction.response.defer(ephemeral=True)

            guild_id = interaction.guild.id

            permissions = category.permissions_for(interaction.guild.me)
            if not permissions.manage_channels:
                await interaction.followup.send(
                    view=QuickLayouts.error(
                        "Missing Permission",
                        f"I don't have permission to create channels in "
                        f"**{category.name}**.\nGrant me the **Manage Channels** permission.",
                    ),
                    ephemeral=True,
                )
                return

            config_data = await self.bot.db.get_guild_config(guild_id)
            config = (
                GuildConfig.from_dict(config_data)
                if config_data
                else GuildConfig(guild_id=str(guild_id))
            )

            config.target_category_id = str(category.id)
            await self.bot.db.upsert_guild_config(guild_id, config.to_dict())
            self.bot.guild_configs[guild_id] = config

            description = f"Welcome channels will be created in **{category.name}**."
            if config.welcome_mode != WELCOME_MODE_CHANNEL:
                description += (
                    f"\n\n**Note:** Current mode is **{config.welcome_mode}**. "
                    f"Use `/threadly setmode channel` to enable channel creation."
                )

            await interaction.followup.send(
                view=QuickLayouts.success(
                    "Channel Category Set",
                    description,
                    footer=f"Changed by {interaction.user.name}",
                ),
                ephemeral=True,
            )
            logger.info(f"Channel category set to {category.id} in guild {guild_id}")

        except Exception as e:
            logger.error(f"Error in setcategory command: {e}")
            await interaction.followup.send(
                view=QuickLayouts.error("Something Went Wrong", str(e)),
                ephemeral=True,
            )

    @app_commands.default_permissions(administrator=True)
    @is_bot_enabled()
    async def view_config(self, interaction: discord.Interaction):
        """Display current guild configuration"""
        try:
            await interaction.response.defer(ephemeral=True)

            guild_id = interaction.guild.id
            config_data = await self.bot.db.get_guild_config(guild_id)

            if not config_data:
                await interaction.followup.send(
                    view=QuickLayouts.warning(
                        "No Configuration Found",
                        "Use the setup commands to configure the bot:\n"
                        "`/threadly setmode`, then `/threadly setchannel` or `/threadly setcategory`.",
                    ),
                    ephemeral=True,
                )
                return

            config = GuildConfig.from_dict(config_data)

            if config.target_channel_id:
                channel = interaction.guild.get_channel(int(config.target_channel_id))
                channel_text = (
                    channel.mention if channel else f"ID: {config.target_channel_id} (not found)"
                )
            else:
                channel_text = "Not set"

            if config.target_category_id:
                category = interaction.guild.get_channel(int(config.target_category_id))
                category_text = (
                    category.name if category else f"ID: {config.target_category_id} (not found)"
                )
            else:
                category_text = "Not set"

            details = (
                f"**Status:** {'Enabled' if config.enabled else 'Disabled'}\n"
                f"**Welcome Mode:** {config.welcome_mode.capitalize()}\n"
                f"**Configured:** {'Yes' if config.is_configured() else 'No'}\n"
                f"**Thread Channel:** {channel_text}\n"
                f"**Channel Category:** {category_text}\n"
                f"**Welcome Container:** "
                f"{'Enabled' if config.embed_enabled else 'Disabled'}"
            )

            layout = ContainerLayout(
                heading="Current Configuration",
                description=details,
                footer=f"Requested by {interaction.user.name}",
                color=DEFAULT_EMBED_COLOR,
            )

            await interaction.followup.send(view=layout, ephemeral=True)
            logger.info(f"Config viewed by {interaction.user.id} in guild {guild_id}")

        except Exception as e:
            logger.error(f"Error in viewconfig command: {e}")
            await interaction.followup.send(
                view=QuickLayouts.error("Something Went Wrong", str(e)),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    """Setup function to add this cog to the bot"""
    cog = Setup(bot)
    await bot.add_cog(cog)

    threadly_group.add_command(
        app_commands.Command(
            name="setmode",
            description="Set welcome mode (thread or channel)",
            callback=cog.set_mode,
        )
    )
    threadly_group.add_command(
        app_commands.Command(
            name="setchannel",
            description="Set channel for thread creation",
            callback=cog.set_channel,
        )
    )
    threadly_group.add_command(
        app_commands.Command(
            name="setcategory",
            description="Set category for channel creation",
            callback=cog.set_category,
        )
    )
    threadly_group.add_command(
        app_commands.Command(
            name="viewconfig",
            description="View current welcome system configuration",
            callback=cog.view_config,
        )
    )
