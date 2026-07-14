"""
Admin commands - Sync and Toggle functionality
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal, Optional
from utils.logger import logger
from utils.layout_builder import QuickLayouts
from models.guild_config import GuildConfig


class Admin(commands.Cog):
    """Admin commands for bot management"""

    def __init__(self, bot: commands.Bot):
        """Initialize the Admin cog"""
        self.bot = bot
        logger.info("Admin cog initialized")

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync_commands(
        self,
        ctx: commands.Context,
        action: Optional[Literal["clear"]] = None,
    ):
        """
        Sync slash commands to current guild

        Usage:
            $sync - Syncs commands to current guild
            $sync clear - Clears all commands from current guild

        Args:
            action: Optional 'clear' to remove all commands
        """
        try:
            await ctx.message.add_reaction("⏳")  # Processing

            if action == "clear":
                # Clear all commands from guild
                self.bot.tree.clear_commands(guild=ctx.guild)
                await self.bot.tree.sync(guild=ctx.guild)

                await ctx.message.clear_reactions()
                await ctx.message.add_reaction("✅")
                await ctx.send(
                    f"✅ Cleared all commands from **{ctx.guild.name}**\n"
                    f"💡 Run `$sync` to re-sync commands"
                )
                logger.info(f"Cleared all commands from guild {ctx.guild.id}")

            else:
                # Sync to current guild (instant)
                self.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await self.bot.tree.sync(guild=ctx.guild)
                await ctx.message.clear_reactions()
                await ctx.message.add_reaction("✅")
                await ctx.send(
                    f"✅ Synced {len(synced)} commands to **{ctx.guild.name}**"
                )
                logger.info(f"Synced {len(synced)} commands to guild {ctx.guild.id}")

        except Exception as e:
            await ctx.message.clear_reactions()
            await ctx.message.add_reaction("❌")
            await ctx.send(f"❌ Failed to sync commands: {str(e)}")
            logger.error(f"Error syncing commands: {e}")

    @app_commands.command(
        name="toggle", description="Enable or disable the bot in this server"
    )
    @app_commands.describe(state="Enable or disable the bot")
    @app_commands.default_permissions(administrator=True)
    async def toggle_bot(
        self, interaction: discord.Interaction, state: Literal["enable", "disable"]
    ):
        """
        Toggle bot functionality in the server

        Args:
            state: 'enable' or 'disable'
        """
        try:
            await interaction.response.defer(ephemeral=True)

            guild_id = interaction.guild.id
            enabled = state == "enable"

            # Get current config
            config_data = await self.bot.db.get_guild_config(guild_id)

            if config_data:
                # Update existing config
                config = GuildConfig.from_dict(config_data)
                config.enabled = enabled
                await self.bot.db.upsert_guild_config(guild_id, config.to_dict())
            else:
                # Create new config
                config = GuildConfig(guild_id=str(guild_id), enabled=enabled)
                await self.bot.db.upsert_guild_config(guild_id, config.to_dict())

            # Update cache
            self.bot.guild_configs[guild_id] = config

            # Send response as a Components V2 container instead of an embed
            status_text = "enabled" if enabled else "disabled"
            layout = (
                QuickLayouts.success(
                    f"Bot {status_text.capitalize()}",
                    f"The bot has been **{status_text}** in this server.",
                    footer=f"Changed by {interaction.user.name}",
                )
                if enabled
                else QuickLayouts.warning(
                    f"Bot {status_text.capitalize()}",
                    f"The bot has been **{status_text}** in this server.",
                    footer=f"Changed by {interaction.user.name}",
                )
            )

            await interaction.followup.send(view=layout, ephemeral=True)
            logger.info(
                f"Bot {status_text} in guild {guild_id} by {interaction.user.id}"
            )

        except Exception as e:
            logger.error(f"Error in toggle command: {e}")
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}", ephemeral=True
            )

    @sync_commands.error
    async def sync_error(self, ctx: commands.Context, error: commands.CommandError):
        """Error handler for sync command"""
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Only the bot owner can use this command.")
            logger.warning(f"Unauthorized sync attempt by {ctx.author.id}")
        else:
            await ctx.send(f"❌ An error occurred: {str(error)}")
            logger.error(f"Sync command error: {error}")


async def setup(bot: commands.Bot):
    """Setup function to add this cog to the bot"""
    await bot.add_cog(Admin(bot))
