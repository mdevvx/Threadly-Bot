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
from typing import Optional
from utils.logger import logger
from utils.check import is_bot_enabled
from utils.layout_builder import ContainerLayout, QuickLayouts
from models.guild_config import GuildConfig
from config.settings import DEFAULT_EMBED_COLOR
from utils.command_group import threadly_group


def replace_placeholders(text: str, user: discord.abc.User, roles_mention: str = "") -> str:
    """
    Replace {user}/{username}/{server}/{member_count}/{roles} placeholders.

    Shared by the creation modal and the preview command so the two
    can never drift out of sync with each other.

    Args:
        text: Text containing placeholders
        user: User to pull mention/name data from (guild data uses
            sample values since a modal submission has no "new member")
        roles_mention: Pre-built role mention string for {roles}

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
        "{roles}": roles_mention,
    }
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, str(value))
    return text


def build_preview_layout(
    config: GuildConfig, user: discord.abc.User, author_name: Optional[str] = None
) -> ContainerLayout:
    """
    Build a preview ContainerLayout from guild config, using the
    invoking user as sample placeholder data.

    This is the single source of truth for turning a GuildConfig into a
    rendered container: /threadly previewembed, /threadly testwelcome,
    and the post-submit preview after /threadly createembed all call
    this instead of keeping their own copies, so they can't drift apart.

    Args:
        config: Guild configuration
        user: User to preview placeholders with
        author_name: Optional small tag shown above the heading (e.g.
            "[TEST MODE]" for /threadly testwelcome)

    Returns:
        A ContainerLayout ready to be sent with `followup.send(view=...)`
    """
    roles_mention = config.mention_roles_text()
    # No fallback text: a field left blank should preview exactly as it
    # will actually be sent, i.e. omitted, not filled with placeholder copy.
    raw_title = config.embed_title or ""
    raw_description = config.embed_description or ""
    raw_footer = config.embed_footer or ""
    combined_raw = raw_title + raw_description + raw_footer

    title = replace_placeholders(raw_title, user, roles_mention) if raw_title else None
    description = replace_placeholders(raw_description, user, roles_mention) if raw_description else ""
    footer = replace_placeholders(raw_footer, user, roles_mention) if raw_footer else ""

    # Mirrors the fallback placement rules used for the real welcome
    # message, so the preview matches what members will actually see.
    if "{user}" not in combined_raw:
        description = f"{user.mention}\n\n{description}" if description else user.mention

    if roles_mention and "{roles}" not in combined_raw:
        footer = f"{footer}  {roles_mention}" if footer else roles_mention

    description = description or None
    footer = footer or None

    return ContainerLayout(
        heading=title,
        description=description,
        thumbnail_url=config.embed_thumbnail,
        image_url=config.embed_image,
        footer=footer,
        color=config.embed_color or DEFAULT_EMBED_COLOR,
        author_name=author_name,
    )


class EmbedCreationModal(discord.ui.Modal, title="Create Welcome Container"):
    """Modal for creating the welcome container's text content. Thumbnail
    and image live in a separate modal (see ImageUploadModal) since
    Discord caps modals at 5 fields and images need room of their own."""

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
        max_length=4000,  # Discord's modal TextInput cap (embed descriptions allow 4096, modals don't)
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

    def __init__(self, bot: commands.Bot, existing_config: Optional[GuildConfig] = None):
        super().__init__(
            title="Edit Welcome Container" if existing_config else "Create Welcome Container"
        )
        self.bot = bot

        if existing_config:
            self.embed_title.default = existing_config.embed_title
            self.embed_description.default = existing_config.embed_description
            self.embed_color.default = (
                f"#{existing_config.embed_color:06X}" if existing_config.embed_color else None
            )
            self.embed_footer.default = existing_config.embed_footer

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
                    "Welcome Container Saved",
                    "Your welcome container has been configured successfully!\n\n"
                    "**Placeholders:** `{user}` `{username}` `{server}` `{member_count}` `{roles}`\n\n"
                    "Use `/threadly setimages` to upload a thumbnail and/or image."
                    + (
                        " Use `/threadly setroles` to choose which roles `{roles}` mentions."
                        if not config.mention_role_ids
                        else ""
                    ),
                    footer=f"Saved by {interaction.user.name}",
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


async def get_or_create_asset_channel(
    bot: commands.Bot, guild: discord.Guild, config: GuildConfig
) -> discord.TextChannel:
    """
    Get (or create) the hidden channel used to permanently host uploaded
    thumbnail/image files. A modal file upload's own URL is signed and
    expires, so uploads get re-sent as a message in this channel and we
    keep that message's attachment URL instead, which stays valid for as
    long as the message exists.

    Raises discord.Forbidden if the bot lacks Manage Channels to create it.
    """
    if config.asset_channel_id:
        channel = guild.get_channel(int(config.asset_channel_id))
        if isinstance(channel, discord.TextChannel):
            return channel

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, attach_files=True
        ),
    }
    channel = await guild.create_text_channel(
        name="threadly-assets",
        overwrites=overwrites,
        reason="Storage for Threadly welcome container images",
        topic="Used by Threadly to permanently host welcome container images. Don't delete.",
    )

    config.asset_channel_id = str(channel.id)
    await bot.db.upsert_guild_config(guild.id, config.to_dict())
    bot.guild_configs[guild.id] = config

    logger.info(f"Created asset storage channel {channel.id} in guild {guild.id}")
    return channel


class ImageUploadModal(discord.ui.Modal, title="Set Container Images"):
    """Modal for uploading the welcome container's thumbnail and image.
    Uses discord.ui.FileUpload instead of URL text fields so images are
    uploaded directly rather than pasted as links."""

    thumbnail_label = discord.ui.Label(
        text="Thumbnail (blank = keep existing)",
        description="Upload a replacement thumbnail. Hosted permanently.",
        component=discord.ui.FileUpload(required=False, min_values=0, max_values=1),
    )

    image_label = discord.ui.Label(
        text="Image (blank = keep existing)",
        description="Upload a replacement image. Hosted permanently.",
        component=discord.ui.FileUpload(required=False, min_values=0, max_values=1),
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)

            guild_id = interaction.guild.id
            config_data = await self.bot.db.get_guild_config(guild_id)
            config = (
                GuildConfig.from_dict(config_data)
                if config_data
                else GuildConfig(guild_id=str(guild_id))
            )

            thumbnail_attachments = self.thumbnail_label.component.values
            image_attachments = self.image_label.component.values

            if not thumbnail_attachments and not image_attachments:
                await interaction.followup.send(
                    view=QuickLayouts.warning(
                        "Nothing Uploaded",
                        "Both fields were left blank, so nothing changed.",
                    ),
                    ephemeral=True,
                )
                return

            try:
                storage_channel = await get_or_create_asset_channel(
                    self.bot, interaction.guild, config
                )
            except discord.Forbidden:
                await interaction.followup.send(
                    view=QuickLayouts.error(
                        "Missing Permission",
                        "I need the **Manage Channels** permission to create a private "
                        "channel to permanently host uploaded images.",
                    ),
                    ephemeral=True,
                )
                return

            if thumbnail_attachments:
                config.embed_thumbnail = await self._store_attachment(
                    storage_channel, thumbnail_attachments[0]
                )
            if image_attachments:
                config.embed_image = await self._store_attachment(
                    storage_channel, image_attachments[0]
                )

            await self.bot.db.upsert_guild_config(guild_id, config.to_dict())
            self.bot.guild_configs[guild_id] = config

            await interaction.followup.send(
                view=QuickLayouts.success(
                    "Images Updated", "Container images updated successfully!"
                ),
                ephemeral=True,
            )
            await interaction.followup.send(
                view=build_preview_layout(config, interaction.user),
                ephemeral=True,
            )
            logger.info(f"Container images updated in guild {guild_id} by {interaction.user.id}")

        except Exception as e:
            logger.error(f"Error in image upload modal submission: {e}")
            await interaction.followup.send(
                view=QuickLayouts.error("Something Went Wrong", str(e)),
                ephemeral=True,
            )

    @staticmethod
    async def _store_attachment(channel: discord.TextChannel, attachment: discord.Attachment) -> str:
        """Re-upload an attachment into the storage channel and return its permanent URL."""
        file = await attachment.to_file()
        message = await channel.send(file=file)
        return message.attachments[0].url


class RoleMentionView(discord.ui.View):
    """Role picker for the welcome container's {roles} placeholder."""

    def __init__(self, bot: commands.Bot, existing_role_ids: Optional[list] = None):
        super().__init__(timeout=180)
        self.bot = bot

        select = discord.ui.RoleSelect(
            placeholder="Select roles to mention (e.g. Team roles)",
            min_values=0,
            max_values=10,
            default_values=[discord.Object(id=int(rid)) for rid in (existing_role_ids or [])],
        )
        select.callback = self.on_select
        self.add_item(select)

    async def on_select(self, interaction: discord.Interaction):
        try:
            select: discord.ui.RoleSelect = self.children[0]
            role_ids = [str(role.id) for role in select.values]

            guild_id = interaction.guild.id
            config_data = await self.bot.db.get_guild_config(guild_id)
            config = (
                GuildConfig.from_dict(config_data)
                if config_data
                else GuildConfig(guild_id=str(guild_id))
            )
            config.mention_role_ids = role_ids or None

            await self.bot.db.upsert_guild_config(guild_id, config.to_dict())
            self.bot.guild_configs[guild_id] = config

            mention_text = config.mention_roles_text() or "*(none selected)*"
            await interaction.response.send_message(
                view=QuickLayouts.success(
                    "Mention Roles Updated",
                    f"`{{roles}}` will now mention: {mention_text}\n\n"
                    "They'll be auto-added to the footer of your welcome container. "
                    "To place them somewhere else instead (title, description, or a "
                    "custom spot in the footer), add `{roles}` there yourself with "
                    "`/threadly createembed`.",
                ),
                ephemeral=True,
            )
            logger.info(f"Mention roles updated in guild {guild_id} by {interaction.user.id}")

        except Exception as e:
            logger.error(f"Error in role mention select: {e}")
            await interaction.response.send_message(
                view=QuickLayouts.error("Something Went Wrong", str(e)),
                ephemeral=True,
            )


class Embed(commands.Cog):
    """Welcome container creation and configuration commands"""

    def __init__(self, bot: commands.Bot):
        """Initialize the Embed cog"""
        self.bot = bot
        logger.info("Embed cog initialized")

    @app_commands.default_permissions(administrator=True)
    @is_bot_enabled()
    async def create_embed(self, interaction: discord.Interaction):
        """Create or edit the welcome container using a modal form"""
        guild_id = interaction.guild.id
        config_data = await self.bot.db.get_guild_config(guild_id)
        existing_config = GuildConfig.from_dict(config_data) if config_data else None

        modal = EmbedCreationModal(self.bot, existing_config=existing_config)
        await interaction.response.send_modal(modal)

    @app_commands.default_permissions(administrator=True)
    @is_bot_enabled()
    async def set_images(self, interaction: discord.Interaction):
        """Upload the welcome container's thumbnail and/or image"""
        modal = ImageUploadModal(self.bot)
        await interaction.response.send_modal(modal)

    @app_commands.default_permissions(administrator=True)
    @is_bot_enabled()
    async def set_mention_roles(self, interaction: discord.Interaction):
        """Choose which roles the {roles} placeholder mentions"""
        guild_id = interaction.guild.id
        config_data = await self.bot.db.get_guild_config(guild_id)
        existing_role_ids = (
            GuildConfig.from_dict(config_data).mention_role_ids if config_data else None
        )

        await interaction.response.send_message(
            content="Select up to 10 roles to mention with the `{roles}` placeholder:",
            view=RoleMentionView(self.bot, existing_role_ids),
            ephemeral=True,
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
                        "Use `/threadly createembed` first to set up a welcome container.",
                    ),
                    ephemeral=True,
                )
                return

            config = GuildConfig.from_dict(config_data)

            if state and not config.get_embed_dict():
                await interaction.followup.send(
                    view=QuickLayouts.error(
                        "No Container Configured",
                        "Use `/threadly createembed` to create one first.",
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
                        "Use `/threadly createembed` first to set up a welcome container.",
                    ),
                    ephemeral=True,
                )
                return

            config = GuildConfig.from_dict(config_data)

            if not config.get_embed_dict():
                await interaction.followup.send(
                    view=QuickLayouts.error(
                        "No Container Configured",
                        "Use `/threadly createembed` to create one.",
                    ),
                    ephemeral=True,
                )
                return

            # Preview shows the saved content regardless of enabled/disabled
            # state, since toggling it off doesn't erase anything and admins
            # should still be able to check it before re-enabling. The tag
            # goes inside the container (not `content=`) since Components V2
            # layouts can't be combined with a message content field.
            tag = None if config.embed_enabled else "[DISABLED]"
            await interaction.followup.send(
                view=build_preview_layout(config, interaction.user, author_name=tag),
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
    cog = Embed(bot)
    await bot.add_cog(cog)

    threadly_group.add_command(
        app_commands.Command(
            name="createembed",
            description="Create or edit the welcome container",
            callback=cog.create_embed,
        )
    )
    threadly_group.add_command(
        app_commands.Command(
            name="setimages",
            description="Upload the welcome container's thumbnail and/or image",
            callback=cog.set_images,
        )
    )
    threadly_group.add_command(
        app_commands.Command(
            name="setroles",
            description="Choose which roles the {roles} placeholder mentions",
            callback=cog.set_mention_roles,
        )
    )
    threadly_group.add_command(
        app_commands.Command(
            name="toggleembed",
            description="Enable or disable the welcome container",
            callback=cog.toggle_embed,
        )
    )
    threadly_group.add_command(
        app_commands.Command(
            name="previewembed",
            description="Preview the current welcome container",
            callback=cog.preview_embed,
        )
    )
