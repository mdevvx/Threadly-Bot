"""
Embed building utilities for creating rich Discord embeds
"""

import discord
from typing import Optional, List, Dict, Any
from datetime import datetime
from config.settings import DEFAULT_EMBED_COLOR


class EmbedBuilder:
    """Utility class for building Discord embeds"""

    def __init__(self, color: int = DEFAULT_EMBED_COLOR):
        """
        Initialize embed builder

        Args:
            color: Default embed color (hex integer)
        """
        self.color = color
        self.embed = discord.Embed(color=self.color)

    def set_title(self, title: str) -> "EmbedBuilder":
        """
        Set embed title

        Args:
            title: Embed title (max 256 characters)

        Returns:
            Self for method chaining
        """
        self.embed.title = title[:256]
        return self

    def set_description(self, description: str) -> "EmbedBuilder":
        """
        Set embed description

        Args:
            description: Embed description (max 4096 characters)

        Returns:
            Self for method chaining
        """
        self.embed.description = description[:4096]
        return self

    def set_color(self, color: int) -> "EmbedBuilder":
        """
        Set embed color

        Args:
            color: Color as hex integer

        Returns:
            Self for method chaining
        """
        self.embed.color = color
        return self

    def set_author(
        self, name: str, icon_url: Optional[str] = None, url: Optional[str] = None
    ) -> "EmbedBuilder":
        """
        Set embed author

        Args:
            name: Author name
            icon_url: Author icon URL
            url: Author URL

        Returns:
            Self for method chaining
        """
        self.embed.set_author(name=name, icon_url=icon_url, url=url)
        return self

    def set_footer(self, text: str, icon_url: Optional[str] = None) -> "EmbedBuilder":
        """
        Set embed footer

        Args:
            text: Footer text (max 2048 characters)
            icon_url: Footer icon URL

        Returns:
            Self for method chaining
        """
        self.embed.set_footer(text=text[:2048], icon_url=icon_url)
        return self

    def set_thumbnail(self, url: str) -> "EmbedBuilder":
        """
        Set embed thumbnail

        Args:
            url: Thumbnail image URL

        Returns:
            Self for method chaining
        """
        self.embed.set_thumbnail(url=url)
        return self

    def set_image(self, url: str) -> "EmbedBuilder":
        """
        Set embed image

        Args:
            url: Image URL

        Returns:
            Self for method chaining
        """
        self.embed.set_image(url=url)
        return self

    def add_field(self, name: str, value: str, inline: bool = True) -> "EmbedBuilder":
        """
        Add a field to the embed

        Args:
            name: Field name (max 256 characters)
            value: Field value (max 1024 characters)
            inline: Whether field should be inline

        Returns:
            Self for method chaining
        """
        self.embed.add_field(name=name[:256], value=value[:1024], inline=inline)
        return self

    def add_fields(self, fields: List[Dict[str, Any]]) -> "EmbedBuilder":
        """
        Add multiple fields to the embed

        Args:
            fields: List of field dictionaries with 'name', 'value', and optional 'inline'

        Returns:
            Self for method chaining
        """
        for field in fields:
            self.add_field(
                name=field.get("name", "Field"),
                value=field.get("value", "Value"),
                inline=field.get("inline", True),
            )
        return self

    def set_timestamp(self, timestamp: Optional[datetime] = None) -> "EmbedBuilder":
        """
        Set embed timestamp

        Args:
            timestamp: Datetime object (defaults to current time)

        Returns:
            Self for method chaining
        """
        self.embed.timestamp = timestamp or datetime.utcnow()
        return self

    def build(self) -> discord.Embed:
        """
        Build and return the embed

        Returns:
            Completed Discord embed
        """
        return self.embed


class QuickEmbeds:
    """Pre-built embed templates for common use cases"""

    @staticmethod
    def success(
        title: str, description: str, footer: Optional[str] = None
    ) -> discord.Embed:
        """
        Create a success embed (green)

        Args:
            title: Embed title
            description: Embed description
            footer: Optional footer text

        Returns:
            Success embed
        """
        embed = discord.Embed(
            title=f"✅ {title}", description=description, color=discord.Color.green()
        )
        if footer:
            embed.set_footer(text=footer)
        return embed

    @staticmethod
    def error(
        title: str, description: str, footer: Optional[str] = None
    ) -> discord.Embed:
        """
        Create an error embed (red)

        Args:
            title: Embed title
            description: Embed description
            footer: Optional footer text

        Returns:
            Error embed
        """
        embed = discord.Embed(
            title=f"❌ {title}", description=description, color=discord.Color.red()
        )
        if footer:
            embed.set_footer(text=footer)
        return embed

    @staticmethod
    def warning(
        title: str, description: str, footer: Optional[str] = None
    ) -> discord.Embed:
        """
        Create a warning embed (yellow)

        Args:
            title: Embed title
            description: Embed description
            footer: Optional footer text

        Returns:
            Warning embed
        """
        embed = discord.Embed(
            title=f"⚠️ {title}", description=description, color=discord.Color.yellow()
        )
        if footer:
            embed.set_footer(text=footer)
        return embed

    @staticmethod
    def info(
        title: str, description: str, footer: Optional[str] = None
    ) -> discord.Embed:
        """
        Create an info embed (blue)

        Args:
            title: Embed title
            description: Embed description
            footer: Optional footer text

        Returns:
            Info embed
        """
        embed = discord.Embed(
            title=f"ℹ️ {title}", description=description, color=discord.Color.blue()
        )
        if footer:
            embed.set_footer(text=footer)
        return embed

    @staticmethod
    def loading(
        title: str = "Processing", description: str = "Please wait..."
    ) -> discord.Embed:
        """
        Create a loading embed

        Args:
            title: Embed title
            description: Embed description

        Returns:
            Loading embed
        """
        embed = discord.Embed(
            title=f"⏳ {title}", description=description, color=discord.Color.blurple()
        )
        return embed


class PaginatedEmbed:
    """Helper for creating paginated embeds"""

    def __init__(
        self,
        title: str,
        items: List[str],
        items_per_page: int = 10,
        color: int = DEFAULT_EMBED_COLOR,
    ):
        """
        Initialize paginated embed

        Args:
            title: Embed title
            items: List of items to paginate
            items_per_page: Number of items per page
            color: Embed color
        """
        self.title = title
        self.items = items
        self.items_per_page = items_per_page
        self.color = color
        self.total_pages = (len(items) + items_per_page - 1) // items_per_page

    def get_page(self, page: int) -> discord.Embed:
        """
        Get a specific page

        Args:
            page: Page number (0-indexed)

        Returns:
            Discord embed for the page
        """
        # Ensure page is within bounds
        page = max(0, min(page, self.total_pages - 1))

        # Calculate start and end indices
        start = page * self.items_per_page
        end = start + self.items_per_page

        # Get items for this page
        page_items = self.items[start:end]

        # Create embed
        embed = discord.Embed(
            title=self.title, description="\n".join(page_items), color=self.color
        )

        # Add page footer
        embed.set_footer(text=f"Page {page + 1}/{self.total_pages}")

        return embed
