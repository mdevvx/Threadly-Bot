"""
Supabase database handler for guild configurations
"""

from typing import Optional, Dict, Any
from supabase import create_async_client, AsyncClient
from config.settings import SUPABASE_URL, SUPABASE_KEY
from utils.logger import logger


class Database:
    """Database handler for Supabase operations"""

    def __init__(self):
        """Set up state; the actual client is created in initialize()"""
        self.client: Optional[AsyncClient] = None

    async def initialize(self):
        """
        Create the Supabase client.

        Must be awaited once (e.g. from setup_hook) before any other
        method is used. supabase-py's client creation is a coroutine,
        so it can't happen in __init__. Using the async client here
        instead of create_client() matters: the sync client's
        .execute() blocks the event loop for the whole HTTP round-trip,
        which can eat into Discord's 3-second interaction ack window
        and cause "The application did not respond" errors.
        """
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.warning(
                "Supabase credentials not configured. Database features disabled."
            )
            return

        try:
            self.client = await create_async_client(SUPABASE_URL, SUPABASE_KEY)
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
                await self.client.table("threadly_guild_configs")
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
            await self.client.table("threadly_guild_configs").upsert(
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
            await self.client.table("threadly_guild_configs").update({key: value}).eq(
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
            await self.client.table("threadly_guild_configs").delete().eq(
                "guild_id", str(guild_id)
            ).execute()
            logger.info(f"Deleted config for guild {guild_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting guild config for {guild_id}: {e}")
            return False


# Create database instance (client is created later via initialize())
db = Database()
