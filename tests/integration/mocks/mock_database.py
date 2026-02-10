from datetime import (
    datetime,
    timedelta,
)
import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
)


class MockDatabase:
    _users: Dict[int, Dict[str, Any]] = {}
    _roles: Dict[int, List[str]] = {}
    _subscriptions: Dict[int, datetime] = {}
    _last_clips: Dict[int, Dict[str, Any]] = {}
    _search_history: List[Dict[str, Any]] = []
    _command_usage: Dict[int, int] = {}
    _call_log: List[Dict[str, Any]] = []

    @classmethod
    def reset(cls):
        cls._users = {}
        cls._roles = {}
        cls._subscriptions = {}
        cls._last_clips = {}
        cls._search_history = []
        cls._command_usage = {}
        cls._call_log = []

    @classmethod
    async def init_pool(cls, *args, **kwargs):
        cls._call_log.append({
            'method': 'init_pool',
            'args': args,
            'kwargs': kwargs,
        })

    @classmethod
    async def init_db(cls):
        cls._call_log.append({'method': 'init_db'})

    @classmethod
    async def close(cls):
        cls._call_log.append({'method': 'close'})

    @classmethod
    async def clear_test_db(cls, tables: List[str], schema: str):
        cls.reset()
        cls._call_log.append({
            'method': 'clear_test_db',
            'tables': tables,
            'schema': schema,
        })

    @classmethod
    async def set_default_admin(
        cls,
        user_id: int,
        username: str,
        full_name: str,
        password: str,
    ):
        cls._users[user_id] = {
            'user_id': user_id,
            'username': username,
            'full_name': full_name,
            'password': password,
        }
        if user_id not in cls._roles:
            cls._roles[user_id] = []
        if 'admin' not in cls._roles[user_id]:
            cls._roles[user_id].append('admin')

        cls._call_log.append({
            'method': 'set_default_admin',
            'user_id': user_id,
        })

    @classmethod
    async def add_user(
        cls,
        user_id: int,
        username: str,
        full_name: str,
        note: Optional[str] = None,
        subscription_days: Optional[int] = None,
    ):
        cls._users[user_id] = {
            'user_id': user_id,
            'username': username,
            'full_name': full_name,
            'note': note,
        }
        if subscription_days:
            cls._subscriptions[user_id] = datetime.now() + timedelta(days=subscription_days)

        cls._call_log.append({
            'method': 'add_user',
            'user_id': user_id,
        })

    @classmethod
    async def add_subscription(cls, user_id: int, days: int):
        cls._subscriptions[user_id] = datetime.now() + timedelta(days=days)
        cls._call_log.append({
            'method': 'add_subscription',
            'user_id': user_id,
            'days': days,
        })

    @classmethod
    async def add_admin(cls, user_id: int):
        if user_id not in cls._roles:
            cls._roles[user_id] = []
        if 'admin' not in cls._roles[user_id]:
            cls._roles[user_id].append('admin')

        cls._call_log.append({
            'method': 'add_admin',
            'user_id': user_id,
        })

    @classmethod
    async def remove_admin(cls, user_id: int):
        if user_id in cls._roles and 'admin' in cls._roles[user_id]:
            cls._roles[user_id].remove('admin')

        cls._call_log.append({
            'method': 'remove_admin',
            'user_id': user_id,
        })

    @classmethod
    async def is_admin_or_moderator(cls, user_id: int) -> bool:
        if user_id not in cls._roles:
            return False
        return 'admin' in cls._roles[user_id] or 'moderator' in cls._roles[user_id]

    @classmethod
    async def insert_last_clip(
        cls,
        chat_id: int,
        segment: Dict[str, Any],
        clip_type: str,
        adjusted_start_time: float,
        adjusted_end_time: float,
        **kwargs,
    ):
        cls._last_clips[chat_id] = {
            'chat_id': chat_id,
            'segment': segment,
            'clip_type': clip_type,
            'adjusted_start_time': adjusted_start_time,
            'adjusted_end_time': adjusted_end_time,
            **kwargs,
        }

        cls._call_log.append({
            'method': 'insert_last_clip',
            'chat_id': chat_id,
        })

    @classmethod
    async def get_last_clip(cls, chat_id: int) -> Optional[Dict[str, Any]]:
        return cls._last_clips.get(chat_id)

    @classmethod
    async def log_command_usage(cls, user_id: int):
        if user_id not in cls._command_usage:
            cls._command_usage[user_id] = 0
        cls._command_usage[user_id] += 1

        cls._call_log.append({
            'method': 'log_command_usage',
            'user_id': user_id,
        })

    @classmethod
    async def get_or_create_series(cls, series_name: str) -> int:
        cls._call_log.append({
            'method': 'get_or_create_series',
            'series_name': series_name,
        })
        return 1

    @classmethod
    def get_call_log(cls) -> List[Dict[str, Any]]:
        return cls._call_log

    @classmethod
    def get_call_count(cls, method_name: str) -> int:
        return sum(1 for call in cls._call_log if call['method'] == method_name)

    @classmethod
    def get_user(cls, user_id: int) -> Optional[Dict[str, Any]]:
        return cls._users.get(user_id)

    @classmethod
    def get_user_roles(cls, user_id: int) -> List[str]:
        return cls._roles.get(user_id, [])

    @classmethod
    def has_subscription(cls, user_id: int) -> bool:
        if user_id not in cls._subscriptions:
            return False
        return cls._subscriptions[user_id] > datetime.now()

    @classmethod
    async def log_system_message(cls, level: str, message: str):
        cls._call_log.append({
            'method': 'log_system_message',
            'level': level,
            'message': message,
        })

    @classmethod
    def __get_db_connection(cls):
        """Mock context manager for database connection"""
        class MockConnection:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

            async def execute(self, *args, **kwargs):
                pass

            async def fetch(self, *args, **kwargs):
                return []

            async def fetchrow(self, *args, **kwargs):
                return None

        return MockConnection()

    pool = None
