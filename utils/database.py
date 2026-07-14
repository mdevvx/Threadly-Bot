"""
Supabase database handler for guild configurations
"""

from typing import Optional, Dict, Any
from supabase import create_client, Client
from config.settings import SUPABASE_URL, SUPABASE_KEY
from utils.logger import logger


class Database:
    """Database handler for Supabase operations"""

    def __init__(self):
        """Initialize Supabase client"""
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.warning(
                "Supabase credentials not configured. Database features disabled."
            )
            self.client: Optional[Client] = None
        else:
            try:
                self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self.client = None

    async def get_guild_config(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve guild configuration from database

        Args:
            guild_id: Discord guild ID

        Returns:
            Guild configuration dictionary or None
        """
        if not self.client:
            return None

        try:
            response = (
                self.client.table("threadly_guild_configs")
                .select("*")
                .eq("guild_id", str(guild_id))
                .execute()
            )

            if response.data and len(response.data) > 0:
                logger.debug(f"Retrieved config for guild {guild_id}")
                return response.data[0]
            return None

        except Exception as e:
            logger.error(f"Error fetching guild config for {guild_id}: {e}")
            return None

    async def upsert_guild_config(self, guild_id: int, config: Dict[str, Any]) -> bool:
        """
        Insert or update guild configuration

        Args:
            guild_id: Discord guild ID
            config: Configuration dictionary

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False

        try:
            config["guild_id"] = str(guild_id)
            # Use on_conflict parameter to specify which column to use for conflict resolution
            self.client.table("threadly_guild_configs").upsert(
                config, on_conflict="guild_id"
            ).execute()
            logger.info(f"Updated config for guild {guild_id}")
            return True

        except Exception as e:
            logger.error(f"Error upserting guild config for {guild_id}: {e}")
            return False

    async def update_guild_setting(self, guild_id: int, key: str, value: Any) -> bool:
        """
        Update a specific setting for a guild

        Args:
            guild_id: Discord guild ID
            key: Setting key to update
            value: New value

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False

        try:
            self.client.table("threadly_guild_configs").update({key: value}).eq(
                "guild_id", str(guild_id)
            ).execute()
            logger.info(f"Updated {key} for guild {guild_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating {key} for guild {guild_id}: {e}")
            return False

    async def delete_guild_config(self, guild_id: int) -> bool:
        """
        Delete guild configuration

        Args:
            guild_id: Discord guild ID

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False

        try:
            self.client.table("threadly_guild_configs").delete().eq(
                "guild_id", str(guild_id)
            ).execute()
            logger.info(f"Deleted config for guild {guild_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting guild config for {guild_id}: {e}")
            return False


# Create database instance
db = Database()
