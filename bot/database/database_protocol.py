from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
import json

from bot.database.models import (
    ClipType,
    LastClip,
    RefreshToken,
    SearchHistory,
    Series,
    SubscriptionKey,
    UserCredentials,
    UserProfile,
    VideoClip,
)


class DatabaseInterface(ABC):
    """Abstract base class defining the interface that all database implementations must follow."""

    @staticmethod
    @abstractmethod
    async def init_pool(
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> None: pass

    @staticmethod
    @abstractmethod
    async def init_db() -> None: pass

    @staticmethod
    @abstractmethod
    async def close() -> None: pass

    @staticmethod
    @abstractmethod
    async def clear_test_db(tables: List[str], schema: str) -> None: pass

    @staticmethod
    @abstractmethod
    async def set_default_admin(
        user_id: int,
        username: str,
        full_name: str,
        password: str,
    ) -> None: pass

    @staticmethod
    @abstractmethod
    async def add_user(
        user_id: int,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
        note: Optional[str] = None,
        subscription_days: Optional[int] = None,
    ) -> None: pass

    @staticmethod
    @abstractmethod
    async def add_admin(user_id: int) -> None: pass

    @staticmethod
    @abstractmethod
    async def add_moderator(user_id: int) -> None: pass

    @staticmethod
    @abstractmethod
    async def remove_admin(user_id: int) -> None: pass

    @staticmethod
    @abstractmethod
    async def is_admin_or_moderator(user_id: int) -> bool: pass

    @staticmethod
    @abstractmethod
    async def is_user_admin(user_id: int) -> Optional[bool]: pass

    @staticmethod
    @abstractmethod
    async def is_user_moderator(user_id: int) -> Optional[bool]: pass

    @staticmethod
    @abstractmethod
    async def get_admin_users() -> Optional[List[UserProfile]]: pass

    @staticmethod
    @abstractmethod
    async def get_moderator_users() -> Optional[List[UserProfile]]: pass

    @staticmethod
    @abstractmethod
    async def get_all_users() -> Optional[List[UserProfile]]: pass

    @staticmethod
    @abstractmethod
    async def is_user_in_db(user_id: int) -> bool: pass

    @staticmethod
    @abstractmethod
    async def remove_user(user_id: int) -> None: pass

    @staticmethod
    @abstractmethod
    async def add_subscription(user_id: int, days: int) -> Optional[date]: pass

    @staticmethod
    @abstractmethod
    async def remove_subscription(user_id: int) -> None: pass

    @staticmethod
    @abstractmethod
    async def get_user_subscription(user_id: int) -> Optional[date]: pass

    @staticmethod
    @abstractmethod
    async def is_user_subscribed(user_id: int) -> bool: pass

    @staticmethod
    @abstractmethod
    async def update_user_note(user_id: int, note: str) -> None: pass

    @staticmethod
    @abstractmethod
    async def log_command_usage(user_id: int) -> None: pass

    @staticmethod
    @abstractmethod
    async def is_command_limited(user_id: int, limit: int, duration_seconds: int) -> bool: pass

    @staticmethod
    @abstractmethod
    async def get_command_usage_count(user_id: int, duration_seconds: int) -> int: pass

    @staticmethod
    @abstractmethod
    async def create_subscription_key(days: int, key: str) -> None: pass

    @staticmethod
    @abstractmethod
    async def get_subscription_days_by_key(key: str) -> Optional[int]: pass

    @staticmethod
    @abstractmethod
    async def get_all_subscription_keys() -> List[SubscriptionKey]: pass

    @staticmethod
    @abstractmethod
    async def remove_subscription_key(key: str) -> bool: pass

    @staticmethod
    @abstractmethod
    async def add_report(user_id: int, report: str) -> None: pass

    @staticmethod
    @abstractmethod
    async def get_saved_clips(user_id: int, series_id: Optional[int] = None) -> List[VideoClip]: pass

    @staticmethod
    @abstractmethod
    async def save_clip(
        chat_id: int,
        user_id: int,
        clip_name: str,
        video_data: bytes,
        start_time: float,
        end_time: float,
        duration: float,
        is_compilation: bool,
        season: Optional[int] = None,
        episode_number: Optional[int] = None,
        series_id: Optional[int] = None,
    ) -> None: pass

    @staticmethod
    @abstractmethod
    async def get_clip_by_name(user_id: int, clip_name: str) -> Optional[VideoClip]: pass

    @staticmethod
    @abstractmethod
    async def delete_clip(user_id: int, clip_name: str) -> str: pass

    @staticmethod
    @abstractmethod
    async def is_clip_name_unique(chat_id: int, clip_name: str) -> bool: pass

    @staticmethod
    @abstractmethod
    async def get_user_clip_count(chat_id: int) -> int: pass

    @staticmethod
    @abstractmethod
    async def insert_last_clip(
        chat_id: int,
        segment: json,
        compiled_clip: Optional[bytes],
        clip_type: ClipType,
        adjusted_start_time: Optional[float],
        adjusted_end_time: Optional[float],
        is_adjusted: bool,
        series_id: Optional[int] = None,
    ) -> None: pass

    @staticmethod
    @abstractmethod
    async def get_last_clip_by_chat_id(chat_id: int, series_id: Optional[int] = None) -> Optional[LastClip]: pass

    @staticmethod
    @abstractmethod
    async def insert_last_search(chat_id: int, quote: str, segments: str, series_id: Optional[int] = None) -> None: pass

    @staticmethod
    @abstractmethod
    async def get_last_search_by_chat_id(chat_id: int, series_id: Optional[int] = None) -> Optional[SearchHistory]: pass

    @staticmethod
    @abstractmethod
    async def log_system_message(log_level: str, log_message: str) -> None: pass

    @staticmethod
    @abstractmethod
    async def get_or_create_series(series_name: str) -> int: pass

    @staticmethod
    @abstractmethod
    async def get_all_series() -> List[Series]: pass

    @staticmethod
    @abstractmethod
    async def get_user_active_series(user_id: int) -> Optional[int]: pass

    @staticmethod
    @abstractmethod
    async def set_user_active_series(user_id: int, series_id: int) -> None: pass
