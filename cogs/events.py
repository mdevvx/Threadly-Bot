"""
Events - Member join handler and welcome system
"""

import discord
from discord.ext import commands
from utils.logger import logger
from utils.layout_builder import ContainerLayout
from models.guild_config import GuildConfig
from config.settings import WELCOME_MODE_THREAD, WELCOME_MODE_CHANNEL


async def delete_thread_created_message(channel: discord.TextChannel, thread: discord.Thread):
    """
    Delete Discord's auto-generated "X started a thread: Y" system
    message from the parent channel. Threads created without a starter
    message get one of these automatically; shared by the real welcome
    flow and /threadly testwelcome so both stay clutter-free the same
    way. Requires Manage Messages; if the bot doesn't have it, this is
    skipped rather than failing the caller.
    """
    if not channel.permissions_for(channel.guild.me).manage_messages:
        logger.debug(
            f"Missing Manage Messages in channel {channel.id}; "
            "can't hide the 'started a thread' system message."
        )
        return

    try:
        async for msg in channel.history(limit=5):
            if msg.type == discord.MessageType.thread_created and msg.content == thread.name:
                await msg.delete()
                break
    except discord.HTTPException as e:
        logger.debug(f"Could not delete thread-created system message: {e}")


class Events(commands.Cog):
    """Event handlers for the bot"""

    def __init__(self, bot: commands.Bot):
        """Initialize the Events cog"""
        self.bot = bot
        logger.info("Events cog initialized")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Handle new member joins - Create thread or channel with optional embed

        Args:
            member: The member who joined
        """
        try:
            guild = member.guild
            guild_id = guild.id

            logger.info(
                f"Member {member.name} ({member.id}) joined guild {guild.name} ({guild_id})"
            )

            # Get guild configuration
            config_data = await self.bot.db.get_guild_config(guild_id)

            if not config_data:
                logger.debug(f"No configuration found for guild {guild_id}")
                return

            config = GuildConfig.from_dict(config_data)

            # Check if bot is enabled
            if not config.enabled:
                logger.debug(f"Bot is disabled in guild {guild_id}")
                return

            # Check if properly configured
            if not config.is_configured():
                logger.warning(f"Guild {guild_id} is not properly configured")
                return

            # Update cache
            self.bot.guild_configs[guild_id] = config

            # Create thread or channel based on mode
            if config.welcome_mode == WELCOME_MODE_THREAD:
                await self._create_welcome_thread(member, config)
            else:  # WELCOME_MODE_CHANNEL
                await self._create_welcome_channel(member, config)

        except Exception as e:
            logger.error(
                f"Error handling member join for {member.id} in guild {member.guild.id}: {e}"
            )

    async def _create_welcome_thread(self, member: discord.Member, config: GuildConfig):
        """
        Create a welcome thread for the new member

        Args:
            member: The member who joined
            config: Guild configuration
        """
        try:
            guild = member.guild

            # Get target channel
            channel = guild.get_channel(int(config.target_channel_id))
            if not channel:
                logger.error(
                    f"Target channel {config.target_channel_id} not found in guild {guild.id}"
                )
                return

            # Check permissions
            permissions = channel.permissions_for(guild.me)
            if not permissions.create_public_threads:
                logger.error(
                    f"Missing permission to create threads in channel {channel.id}"
                )
                return

            # Create thread name (username)
            thread_name = member.name[
                :100
            ]  # Discord thread name limit is 100 characters

            # Create the thread
            thread = await channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.public_thread,
                reason=f"Welcome thread for {member.name}",
            )

            logger.info(
                f"Created thread {thread.id} for member {member.id} in guild {guild.id}"
            )

            # Threads created without a starter message get an automatic
            # "X started a thread: Y" system message in the parent channel;
            # clean it up so the channel doesn't fill up with one line per join.
            await delete_thread_created_message(channel, thread)

            # Send welcome message/embed
            await self._send_welcome_message(thread, member, config)

        except discord.Forbidden:
            logger.error(f"Forbidden: Cannot create thread in guild {member.guild.id}")
        except discord.HTTPException as e:
            logger.error(f"HTTP error creating thread: {e}")
        except Exception as e:
            logger.error(f"Error creating welcome thread: {e}")

    async def _create_welcome_channel(
        self, member: discord.Member, config: GuildConfig
    ):
        """
        Create a welcome channel for the new member

        Args:
            member: The member who joined
            config: Guild configuration
        """
        try:
            guild = member.guild

            # Get target category
            category = guild.get_channel(int(config.target_category_id))
            if not category:
                logger.error(
                    f"Target category {config.target_category_id} not found in guild {guild.id}"
                )
                return

            # Check permissions
            permissions = category.permissions_for(guild.me)
            if not permissions.manage_channels:
                logger.error(
                    f"Missing permission to create channels in category {category.id}"
                )
                return

            # Create channel name (username, sanitized)
            channel_name = self._sanitize_channel_name(member.name)

            # Create the channel
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                reason=f"Welcome channel for {member.name}",
                topic=f"Welcome channel for {member.mention}",
            )

            logger.info(
                f"Created channel {channel.id} for member {member.id} in guild {guild.id}"
            )

            # Send welcome message/embed
            await self._send_welcome_message(channel, member, config)

        except discord.Forbidden:
            logger.error(f"Forbidden: Cannot create channel in guild {member.guild.id}")
        except discord.HTTPException as e:
            logger.error(f"HTTP error creating channel: {e}")
        except Exception as e:
            logger.error(f"Error creating welcome channel: {e}")

    async def _send_welcome_message(
        self,
        destination: discord.abc.Messageable,
        member: discord.Member,
        config: GuildConfig,
    ):
        """
        Send the welcome message to the destination as a Components V2
        layout. Note that Components V2 messages can't mix a `content`
        field with components, so the member/role mentions live inside
        the container's text instead (mentions still ping from there,
        as long as allowed_mentions permits it).

        Args:
            destination: Channel or thread to send message to
            member: The member who joined
            config: Guild configuration
        """
        try:
            if config.embed_enabled and config.get_embed_dict():
                layout = self._create_welcome_layout(member, config)
                logger.info(
                    f"Sent welcome layout to {destination.id} for member {member.id}"
                )
            else:
                layout = ContainerLayout(
                    description=(
                        f"Welcome {member.mention}! This is your personal welcome space. "
                        f"Feel free to introduce yourself!"
                    ),
                )
                logger.info(
                    f"Sent welcome message to {destination.id} for member {member.id}"
                )

            await destination.send(
                view=layout,
                allowed_mentions=discord.AllowedMentions(users=True, roles=True),
            )

        except discord.Forbidden:
            logger.error(f"Forbidden: Cannot send message to {destination.id}")
        except discord.HTTPException as e:
            logger.error(f"HTTP error sending welcome message: {e}")
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")

    def _create_welcome_layout(
        self, member: discord.Member, config: GuildConfig
    ) -> ContainerLayout:
        """
        Build the welcome container layout from guild config.

        The {user}/{roles} placeholders can be placed anywhere the admin
        wants (title, description, or footer, e.g. a quieter mention in
        the footer instead of the top of the description). If the
        template doesn't use {user} anywhere, it's appended to the
        description as a fallback so joins still get pinged. Likewise,
        if roles are configured via /threadly setroles but {roles}
        isn't used anywhere, it's appended to the footer.

        Args:
            member: The member who joined
            config: Guild configuration

        Returns:
            A ContainerLayout ready to be sent with `destination.send(view=...)`
        """
        # No fallback text here: by the time this runs the admin has
        # already configured and enabled the container, so a field left
        # blank is a deliberate choice to omit it, not a first-time default.
        raw_title = config.embed_title or ""
        raw_description = config.embed_description or ""
        raw_footer = config.embed_footer or ""

        title = self._replace_placeholders(raw_title, member, config)
        description = self._replace_placeholders(raw_description, member, config)
        footer = self._replace_placeholders(raw_footer, member, config) if raw_footer else None

        combined_raw = raw_title + raw_description + raw_footer

        if "{user}" not in combined_raw:
            description = f"{member.mention}\n\n{description}"

        roles_mention = config.mention_roles_text()
        if roles_mention and "{roles}" not in combined_raw:
            footer = f"{footer}  {roles_mention}" if footer else roles_mention

        return ContainerLayout(
            heading=title,
            description=description,
            thumbnail_url=config.embed_thumbnail,
            image_url=config.embed_image,
            footer=footer,
            color=config.embed_color,
        )

    def _replace_placeholders(
        self, text: str, member: discord.Member, config: GuildConfig
    ) -> str:
        """
        Replace placeholders with actual member/guild/role data

        Args:
            text: Text containing placeholders
            member: Member who joined
            config: Guild configuration (for {roles})

        Returns:
            Text with replaced placeholders
        """
        replacements = {
            "{user}": member.mention,
            "{username}": member.name,
            "{server}": member.guild.name,
            "{member_count}": str(member.guild.member_count),
            "{roles}": config.mention_roles_text(),
        }

        for placeholder, value in replacements.items():
            text = text.replace(placeholder, value)

        return text

    def _sanitize_channel_name(self, name: str) -> str:
        """
        Sanitize username for channel name (Discord requirements)

        Args:
            name: Original username

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
            sanitized = "welcome-channel"

        return sanitized[:100]


async def setup(bot: commands.Bot):
    """Setup function to add this cog to the bot"""
    await bot.add_cog(Events(bot))
