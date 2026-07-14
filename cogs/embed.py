"""
Embed commands - Create and configure welcome containers (Components V2)

Discord's classic Embed is being phased out in favor of Components V2
containers, so this cog builds and previews a ContainerLayout instead
of a discord.Embed. The stored config fields keep their old
"embed_" names for database compatibility, they just render as a
Container now instead of an Embed.
"""

import discord
from discord import app_commands
from discord.ext import commands
from utils.logger import logger
from utils.check import is_bot_enabled
from utils.layout_builder import ContainerLayout, QuickLayouts
from models.guild_config import GuildConfig
from config.settings import DEFAULT_EMBED_COLOR


def replace_placeholders(text: str, user: discord.abc.User) -> str:
    """
    Replace {user}/{username}/{server}/{member_count} placeholders.

    Shared by the creation modal and the preview command so the two
    can never drift out of sync with each other.

    Args:
        text: Text containing placeholders
        user: User to pull mention/name data from (guild data uses
            sample values since a modal submission has no "new member")

    Returns:
        Text with placeholders replaced
    """
    replacements = {
        "{user}": user.mention,
        "{username}": user.name,
        "{server}": user.guild.name if getattr(user, "guild", None) else "Sample Server",
        "{member_count}": (
            str(user.guild.member_count) if getattr(user, "guild", None) else "100"
        ),
    }
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, str(value))
    return text


def build_preview_layout(config: GuildConfig, user: discord.abc.User) -> ContainerLayout:
    """
    Build a preview ContainerLayout from guild config, using the
    invoking user as sample placeholder data.

    Args:
        config: Guild configuration
        user: User to preview placeholders with

    Returns:
        A ContainerLayout ready to be sent with `followup.send(view=...)`
    """
    title = replace_placeholders(config.embed_title or "Welcome!", user)
    description = replace_placeholders(
        config.embed_description or "Welcome to the server!", user
    )
    footer = replace_placeholders(config.embed_footer, user) if config.embed_footer else None

    return ContainerLayout(
        heading=title,
        description=description,
        thumbnail_url=config.embed_thumbnail,
        image_url=config.embed_image,
        footer=footer,
        color=config.embed_color or DEFAULT_EMBED_COLOR,
    )


def is_valid_url(url: str) -> bool:
    """Basic scheme check, good enough to catch pasted-wrong-thing mistakes."""
    return url.startswith(("http://", "https://"))


class EmbedCreationModal(discord.ui.Modal, title="Create Welcome Container"):
    """Modal for creating the welcome container's text content."""

    embed_title = discord.ui.TextInput(
        label="Title",
        placeholder="Enter a title (max 256 characters)",
        max_length=256,
        required=False,
    )

    embed_description = discord.ui.TextInput(
        label="Description",
        placeholder="Use {user}, {username}, {server}, {member_count}",
        style=discord.TextStyle.paragraph,
        max_length=4096,
        required=False,
    )

    embed_color = discord.ui.TextInput(
        label="Accent Color (Hex Code)",
        placeholder="e.g., #5865F2 or 5865F2",
        max_length=7,
        required=False,
    )

    embed_footer = discord.ui.TextInput(
        label="Footer Text",
        placeholder="Enter footer text",
        max_length=2048,
        required=False,
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission"""
        try:
            await interaction.response.defer(ephemeral=True)

            guild_id = interaction.guild.id

            config_data = await self.bot.db.get_guild_config(guild_id)
            config = (
                GuildConfig.from_dict(config_data)
                if config_data
                else GuildConfig(guild_id=str(guild_id))
            )

            # Parse the accent color, falling back to the bot default if blank.
            embed_color = None
            if self.embed_color.value:
                try:
                    embed_color = int(self.embed_color.value.lstrip("#"), 16)
                except ValueError:
                    await interaction.followup.send(
                        view=QuickLayouts.error(
                            "Invalid Color",
                            "Use a hex color code like `#5865F2` or `5865F2`.",
                        ),
                        ephemeral=True,
                    )
                    return

            config.embed_enabled = True
            config.embed_title = self.embed_title.value or None
            config.embed_description = self.embed_description.value or None
            config.embed_color = embed_color or DEFAULT_EMBED_COLOR
            config.embed_footer = self.embed_footer.value or None

            await self.bot.db.upsert_guild_config(guild_id, config.to_dict())
            self.bot.guild_configs[guild_id] = config

            await interaction.followup.send(
                view=QuickLayouts.success(
                    "Welcome Container Created",
                    "Your welcome container has been configured successfully!\n\n"
                    "**Placeholders:** `{user}` `{username}` `{server}` `{member_count}`\n\n"
                    "Use `/setembedimages` to add a thumbnail and image.",
                    footer=f"Created by {interaction.user.name}",
                ),
                ephemeral=True,
            )

            await interaction.followup.send(
                view=build_preview_layout(config, interaction.user),
                ephemeral=True,
            )

            logger.info(
                f"Welcome container created in guild {guild_id} by {interaction.user.id}"
            )

        except Exception as e:
            logger.error(f"Error in embed modal submission: {e}")
            await interaction.followup.send(
                view=QuickLayouts.error("Something Went Wrong", str(e)),
                ephemeral=True,
            )


class ImageURLModal(discord.ui.Modal, title="Set Container Images"):
    """Modal for setting the welcome container's thumbnail and image URLs."""

    thumbnail_url = discord.ui.TextInput(
        label="Thumbnail URL",
        placeholder="https://example.com/thumbnail.png",
        required=False,
    )

    image_url = discord.ui.TextInput(
        label="Main Image URL",
        placeholder="https://example.com/image.png",
        required=False,
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission"""
        try:
            await interaction.response.defer(ephemeral=True)

            guild_id = interaction.guild.id
            config_data = await self.bot.db.get_guild_config(guild_id)

            if not config_data:
                await interaction.followup.send(
                    view=QuickLayouts.error(
                        "No Configuration Found",
                        "Use `/createembed` first to set up a welcome container.",
                    ),
                    ephemeral=True,
                )
                return

            config = GuildConfig.from_dict(config_data)

            if self.thumbnail_url.value and not is_valid_url(self.thumbnail_url.value):
                await interaction.followup.send(
                    view=QuickLayouts.error(
                        "Invalid Thumbnail URL", "URLs must start with http:// or https://"
                    ),
                    ephemeral=True,
                )
                return

            if self.image_url.value and not is_valid_url(self.image_url.value):
                await interaction.followup.send(
                    view=QuickLayouts.error(
                        "Invalid Image URL", "URLs must start with http:// or https://"
                    ),
                    ephemeral=True,
                )
                return

            if self.thumbnail_url.value:
                config.embed_thumbnail = self.thumbnail_url.value
            if self.image_url.value:
                config.embed_image = self.image_url.value

            await self.bot.db.upsert_guild_config(guild_id, config.to_dict())
            self.bot.guild_configs[guild_id] = config

            await interaction.followup.send(
                view=QuickLayouts.success(
                    "Images Updated", "Container images updated successfully!"
                ),
                ephemeral=True,
            )
            logger.info(
                f"Container images updated in guild {guild_id} by {interaction.user.id}"
            )

        except Exception as e:
            logger.error(f"Error in image URL modal submission: {e}")
            await interaction.followup.send(
                view=QuickLayouts.error("Something Went Wrong", str(e)),
                ephemeral=True,
            )


class Embed(commands.Cog):
    """Welcome container creation and configuration commands"""

    def __init__(self, bot: commands.Bot):
        """Initialize the Embed cog"""
        self.bot = bot
        logger.info("Embed cog initialized")

    @app_commands.command(
        name="createembed", description="Create a custom welcome container"
    )
    @app_commands.default_permissions(administrator=True)
    @is_bot_enabled()
    async def create_embed(self, interaction: discord.Interaction):
        """Create and configure a welcome container using a modal form"""
        modal = EmbedCreationModal(self.bot)
        await interaction.response.send_modal(modal)

    @app_commands.command(
        name="setembedimages",
        description="Set thumbnail and image URLs for the welcome container",
    )
    @app_commands.default_permissions(administrator=True)
    @is_bot_enabled()
    async def set_embed_images(self, interaction: discord.Interaction):
        """Set thumbnail and image URLs for the welcome container using a modal"""
        modal = ImageURLModal(self.bot)
        await interaction.response.send_modal(modal)

    @app_commands.command(
        name="toggleembed", description="Enable or disable the welcome container"
    )
    @app_commands.describe(state="Enable or disable the welcome container")
    @app_commands.default_permissions(administrator=True)
    @is_bot_enabled()
    async def toggle_embed(self, interaction: discord.Interaction, state: bool):
        """
        Toggle the welcome container on/off

        Args:
            state: True to enable, False to disable
        """
        try:
            await interaction.response.defer(ephemeral=True)

            guild_id = interaction.guild.id
            config_data = await self.bot.db.get_guild_config(guild_id)

            if not config_data:
                await interaction.followup.send(
                    view=QuickLayouts.error(
                        "No Configuration Found",
                        "Use `/createembed` first to set up a welcome container.",
                    ),
                    ephemeral=True,
                )
                return

            config = GuildConfig.from_dict(config_data)

            if state and not config.get_embed_dict():
                await interaction.followup.send(
                    view=QuickLayouts.error(
                        "No Container Configured",
                        "Use `/createembed` to create one first.",
                    ),
                    ephemeral=True,
                )
                return

            config.embed_enabled = state
            await self.bot.db.upsert_guild_config(guild_id, config.to_dict())
            self.bot.guild_configs[guild_id] = config

            status_text = "enabled" if state else "disabled"
            layout_fn = QuickLayouts.success if state else QuickLayouts.warning
            await interaction.followup.send(
                view=layout_fn(
                    f"Welcome Container {status_text.capitalize()}",
                    f"Welcome container has been **{status_text}**.",
                    footer=f"Changed by {interaction.user.name}",
                ),
                ephemeral=True,
            )
            logger.info(f"Welcome container {status_text} in guild {guild_id}")

        except Exception as e:
            logger.error(f"Error in toggleembed command: {e}")
            await interaction.followup.send(
                view=QuickLayouts.error("Something Went Wrong", str(e)),
                ephemeral=True,
            )

    @app_commands.command(
        name="previewembed", description="Preview the current welcome container"
    )
    @app_commands.default_permissions(administrator=True)
    @is_bot_enabled()
    async def preview_embed(self, interaction: discord.Interaction):
        """Preview the configured welcome container"""
        try:
            await interaction.response.defer(ephemeral=True)

            guild_id = interaction.guild.id
            config_data = await self.bot.db.get_guild_config(guild_id)

            if not config_data:
                await interaction.followup.send(
                    view=QuickLayouts.error(
                        "No Configuration Found",
                        "Use `/createembed` first to set up a welcome container.",
                    ),
                    ephemeral=True,
                )
                return

            config = GuildConfig.from_dict(config_data)

            if not config.embed_enabled or not config.get_embed_dict():
                await interaction.followup.send(
                    view=QuickLayouts.error(
                        "No Container Configured",
                        "Use `/createembed` to create one.",
                    ),
                    ephemeral=True,
                )
                return

            await interaction.followup.send(
                view=build_preview_layout(config, interaction.user),
                ephemeral=True,
            )
            logger.info(
                f"Container preview viewed by {interaction.user.id} in guild {guild_id}"
            )

        except Exception as e:
            logger.error(f"Error in previewembed command: {e}")
            await interaction.followup.send(
                view=QuickLayouts.error("Something Went Wrong", str(e)),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    """Setup function to add this cog to the bot"""
    await bot.add_cog(Embed(bot))
