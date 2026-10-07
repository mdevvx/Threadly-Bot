"""
Private welcome ("ticket") channel helpers, shared by the real member-join
flow, /threadly testwelcome and /threadly setcategory so all three apply
the exact same permission rules.
"""

from typing import List, Optional
import discord
from utils.logger import logger
from models.guild_config import GuildConfig

# Discord hard limit on channels inside a single category
MAX_CHANNELS_PER_CATEGORY = 50

# What the bot needs in the category to create a private channel, lock it
# down with overwrites, and post the welcome layout into it. The bot can
# only grant permissions it has itself, so everything the member/roles get
# must be in this list too.
REQUIRED_BOT_PERMISSIONS = [
    "view_channel",
    "manage_channels",
    "manage_roles",
    "send_messages",
    "read_message_history",
    "embed_links",
    "attach_files",
]

MEMBER_PERMISSIONS = dict(
    view_channel=True,
    send_messages=True,
    read_message_history=True,
    embed_links=True,
    attach_files=True,
)

ROLE_PERMISSIONS = dict(
    view_channel=True,
    send_messages=True,
    read_message_history=True,
)


def missing_bot_permissions(category: discord.CategoryChannel) -> List[str]:
    """Names of required permissions the bot lacks in the category."""
    perms = category.permissions_for(category.guild.me)
    return [p for p in REQUIRED_BOT_PERMISSIONS if not getattr(perms, p, False)]


def format_permission_names(names: List[str]) -> str:
    """'manage_roles' -> 'Manage Roles', one bullet per line."""
    return "\n".join(f"• {n.replace('_', ' ').title()}" for n in names)


def is_category_full(category: discord.CategoryChannel) -> bool:
    return len(category.channels) >= MAX_CHANNELS_PER_CATEGORY


def sanitize_channel_name(name: str, fallback: str = "welcome-channel") -> str:
    """
    Sanitize a username into a valid text channel name
    (lowercase letters, digits and hyphens, max 100 characters).
    """
    sanitized = "".join(c if c.isalnum() or c == "-" else "-" for c in name.lower())

    while "--" in sanitized:
        sanitized = sanitized.replace("--", "-")

    sanitized = sanitized.strip("-")
    return (sanitized or fallback)[:100]


def welcome_channel_topic(member: discord.abc.User) -> str:
    """Topic used to recognise a member's existing welcome channel."""
    return f"Welcome channel for {member.mention}"


def find_existing_welcome_channel(
    guild: discord.Guild, member: discord.abc.User
) -> Optional[discord.TextChannel]:
    """Find a welcome channel previously created for this member (e.g. on rejoin)."""
    topic = welcome_channel_topic(member)
    for channel in guild.text_channels:
        if channel.topic == topic:
            return channel
    return None


def _build_overwrites(
    category: discord.CategoryChannel,
    member: discord.Member,
    config: GuildConfig,
) -> dict:
    """
    Start from the category's own overwrites (so staff roles that can see
    the category keep seeing new channels), then make the channel private:
    hidden from @everyone, visible to the member, the bot, and the roles
    pinged in the welcome message.

    Every overwrite is masked to the permissions the bot itself has in the
    category, because Discord rejects the whole request (403 Missing
    Permissions) if it tries to allow/deny a permission it doesn't have.
    """
    guild = category.guild
    bot_value = category.permissions_for(guild.me).value

    def merge(target, **perms):
        overwrite = overwrites.get(target, discord.PermissionOverwrite())
        overwrite.update(**perms)
        overwrites[target] = overwrite

    overwrites = dict(category.overwrites)
    merge(guild.default_role, view_channel=False)
    merge(guild.me, manage_channels=True, **MEMBER_PERMISSIONS)
    merge(member, **MEMBER_PERMISSIONS)

    for role_id in config.mention_role_ids or []:
        role = guild.get_role(int(role_id))
        if role and not role.is_default():
            merge(role, **ROLE_PERMISSIONS)

    masked = {}
    for target, overwrite in overwrites.items():
        allow, deny = overwrite.pair()
        masked[target] = discord.PermissionOverwrite.from_pair(
            discord.Permissions(allow.value & bot_value),
            discord.Permissions(deny.value & bot_value),
        )
    return masked


async def create_private_channel(
    member: discord.Member,
    category: discord.CategoryChannel,
    config: GuildConfig,
    *,
    name: str,
    topic: str,
    reason: str,
) -> discord.TextChannel:
    """
    Create a private channel for the member inside the category.

    Raises discord.Forbidden / discord.HTTPException on failure so callers
    can report them their own way.
    """
    return await category.guild.create_text_channel(
        name=name,
        category=category,
        overwrites=_build_overwrites(category, member, config),
        topic=topic,
        reason=reason,
    )


async def ensure_member_access(channel: discord.TextChannel, member: discord.Member):
    """Re-grant the member access to their existing channel (e.g. after rejoining)."""
    try:
        await channel.set_permissions(
            member, reason="Member rejoined", **MEMBER_PERMISSIONS
        )
    except discord.HTTPException as e:
        logger.warning(
            f"Could not restore access to channel {channel.id} for member {member.id}: {e}"
        )
