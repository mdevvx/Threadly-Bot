"""
Guild configuration model
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from config.settings import WELCOME_MODE_THREAD


@dataclass
class GuildConfig:
    """Configuration model for each guild"""

    guild_id: str
    enabled: bool = True
    welcome_mode: str = WELCOME_MODE_THREAD  # 'thread' or 'channel'
    target_channel_id: Optional[str] = None  # Channel ID where threads are created
    target_category_id: Optional[str] = None  # Category ID where channels are created

    # Welcome embed configuration
    embed_enabled: bool = False
    embed_title: Optional[str] = None
    embed_description: Optional[str] = None
    embed_color: Optional[int] = None
    embed_thumbnail: Optional[str] = None
    embed_image: Optional[str] = None
    embed_footer: Optional[str] = None

    # Additional settings
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GuildConfig":
        """Create GuildConfig from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

    def is_configured(self) -> bool:
        """Check if guild is properly configured"""
        if self.welcome_mode == WELCOME_MODE_THREAD:
            return self.target_channel_id is not None
        else:  # channel mode
            return self.target_category_id is not None

    def get_embed_dict(self) -> Optional[Dict[str, Any]]:
        """Get embed configuration as dictionary"""
        if not self.embed_enabled:
            return None

        embed_data = {}

        if self.embed_title:
            embed_data["title"] = self.embed_title
        if self.embed_description:
            embed_data["description"] = self.embed_description
        if self.embed_color:
            embed_data["color"] = self.embed_color
        if self.embed_thumbnail:
            embed_data["thumbnail"] = {"url": self.embed_thumbnail}
        if self.embed_image:
            embed_data["image"] = {"url": self.embed_image}
        if self.embed_footer:
            embed_data["footer"] = {"text": self.embed_footer}

        return embed_data if embed_data else None
