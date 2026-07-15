"""
Layout building utilities for Components V2.

Discord's Components V2 replaces the old Embed object with a LayoutView
made of TextDisplay, Section, Thumbnail, MediaGallery, Separator and
Container components. A Container is the closest equivalent to an embed:
it has an accent_color for its left border and can hold text, a
thumbnail, an image, and a footer-style line.

Sending one of these is the same as sending an embed used to be:

    await interaction.response.send_message(view=QuickLayouts.success(...))
    await channel.send(view=ContainerLayout(heading="Welcome!", ...))

Requires discord.py >= 2.6.0.
"""

import discord
from typing import Optional, List
from config.settings import DEFAULT_EMBED_COLOR


def _color(value: Optional[int]) -> discord.Color:
    """Normalize an int/None color value into a discord.Color."""
    return discord.Color(value) if value else discord.Color(DEFAULT_EMBED_COLOR)


class ContainerLayout(discord.ui.LayoutView):
    """
    A single-container LayoutView, the Components V2 equivalent of a
    message with one discord.Embed. Built dynamically in __init__ so it
    can be populated from database-backed config at runtime.
    """

    def __init__(
        self,
        *,
        heading: Optional[str] = None,
        description: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        image_url: Optional[str] = None,
        footer: Optional[str] = None,
        color: Optional[int] = None,
        extra_text: Optional[List[str]] = None,
        author_name: Optional[str] = None,
    ):
        """
        Args:
            heading: Rendered as a markdown heading (like an embed title).
            description: Main body text (like an embed description).
            thumbnail_url: Small image shown beside the heading/description,
                pairs the text into a Section.
            image_url: Full-width image shown below the text.
            footer: Small muted line at the bottom, separated by a divider.
            color: Accent color for the container's left border. Falls
                back to the bot's default color if not provided.
            extra_text: Additional text blocks appended after the main
                section, each rendered as its own TextDisplay (used for
                embed "field" equivalents).
            author_name: Small bold line shown above the heading (like an
                embed author). Used sparingly, e.g. for test-mode tags.
        """
        super().__init__(timeout=None)

        children: List[discord.ui.Item] = []

        text_parts = []
        if author_name:
            text_parts.append(f"**{author_name}**")
        if heading:
            text_parts.append(f"## {heading}")
        if description:
            text_parts.append(description)

        if text_parts:
            if thumbnail_url:
                children.append(
                    discord.ui.Section(
                        *text_parts,
                        accessory=discord.ui.Thumbnail(thumbnail_url),
                    )
                )
            else:
                children.append(discord.ui.TextDisplay("\n".join(text_parts)))

        if extra_text:
            for block in extra_text:
                children.append(discord.ui.TextDisplay(block))

        if image_url:
            children.append(
                discord.ui.MediaGallery(discord.MediaGalleryItem(media=image_url))
            )

        if footer:
            children.append(discord.ui.Separator())
            children.append(discord.ui.TextDisplay(f"-# {footer}"))

        # Discord rejects an empty container, so always have at least one
        # child even if every field above was left blank.
        if not children:
            children.append(discord.ui.TextDisplay("\u200b"))

        container = discord.ui.Container(*children, accent_color=_color(color))
        self.add_item(container)


class QuickLayouts:
    """Pre-built container layouts for common status messages, mirroring
    the old QuickEmbeds helper (success/error/warning/info)."""

    @staticmethod
    def success(title: str, description: str, footer: Optional[str] = None) -> ContainerLayout:
        return ContainerLayout(
            heading=f"Success: {title}",
            description=description,
            footer=footer,
            color=discord.Color.green().value,
        )

    @staticmethod
    def error(title: str, description: str, footer: Optional[str] = None) -> ContainerLayout:
        return ContainerLayout(
            heading=f"Error: {title}",
            description=description,
            footer=footer,
            color=discord.Color.red().value,
        )

    @staticmethod
    def warning(title: str, description: str, footer: Optional[str] = None) -> ContainerLayout:
        return ContainerLayout(
            heading=f"Warning: {title}",
            description=description,
            footer=footer,
            color=discord.Color.gold().value,
        )

    @staticmethod
    def info(title: str, description: str, footer: Optional[str] = None) -> ContainerLayout:
        return ContainerLayout(
            heading=title,
            description=description,
            footer=footer,
            color=DEFAULT_EMBED_COLOR,
        )
