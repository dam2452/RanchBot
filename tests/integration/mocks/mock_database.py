from datetime import (
    date,
    datetime,
    timedelta,
)
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from bot.database.database_protocol import DatabaseInterface
from bot.database.models import (
    ClipType,
    LastClip,
    SearchHistory,
    SubscriptionKey,
    UserProfile,
    VideoClip,
)


class MockDatabase(DatabaseInterface):
    """
    Mock database implementing the same interface as db.
    This class has many public methods as required by the database interface,
    and private methods are used internally for mock implementation.
    """
    _users: Dict[int, Dict[str, Any]] = {}
    _roles: Dict[int, List[str]] = {}
    _subscriptions: Dict[int, datetime] = {}
    _subscription_keys: Dict[str, int] = {}
    _reports: List[Dict[str, Any]] = []
    _last_clips: Dict[int, Dict[str, Any]] = {}
    _saved_clips: Dict[int, List[Dict[str, Any]]] = {}
    _last_searches: Dict[int, Dict[str, Any]] = {}
    _search_history: List[Dict[str, Any]] = []
    _command_usage: Dict[int, int] = {}
    _call_log: List[Dict[str, Any]] = []

    @classmethod
    def reset(cls):
        cls._users = {}
        cls._roles = {}
        cls._subscriptions = {}
        cls._subscription_keys = {}
        cls._reports = []
        cls._last_clips = {}
        cls._saved_clips = {}
        cls._last_searches = {}
        cls._search_history = []
        cls._command_usage = {}
        cls._call_log = []
        cls._user_active_series = {}
        cls._series = {1: 'ranczo'}
        cls._series_by_name = {'ranczo': 1}
        cls._next_series_id = 2

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
        username: Optional[str] = None,
        full_name: Optional[str] = None,
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
        if user_id not in cls._users:
            return None
        end_date = date.today() + timedelta(days=days)
        cls._subscriptions[user_id] = datetime.combine(end_date, datetime.min.time())
        cls._call_log.append({
            'method': 'add_subscription',
            'user_id': user_id,
            'days': days,
        })
        return end_date

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
    async def add_moderator(cls, user_id: int):
        if user_id not in cls._roles:
            cls._roles[user_id] = []
        if 'moderator' not in cls._roles[user_id]:
            cls._roles[user_id].append('moderator')

        cls._call_log.append({
            'method': 'add_moderator',
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
        compiled_clip: Optional[bytes],
        clip_type: ClipType,
        adjusted_start_time: Optional[float],
        adjusted_end_time: Optional[float],
        is_adjusted: bool,
        series_id: Optional[int] = None,
    ):
        cls._last_clips[chat_id] = {
            'chat_id': chat_id,
            'segment': segment,
            'compiled_clip': compiled_clip,
            'clip_type': clip_type,
            'adjusted_start_time': adjusted_start_time,
            'adjusted_end_time': adjusted_end_time,
            'is_adjusted': is_adjusted,
            'series_id': series_id,
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
    async def log_user_activity(cls, user_id: int, command: str, series_id: Optional[int] = None):
        cls._call_log.append({
            'method': 'log_user_activity',
            'user_id': user_id,
            'command': command,
            'series_id': series_id,
        })

    @classmethod
    async def log_system_message(cls, log_level: str, log_message: str):
        cls._call_log.append({
            'method': 'log_system_message',
            'log_level': log_level,
            'log_message': log_message,
        })

    @classmethod
    async def create_subscription_key(cls, days: int, key: str):
        cls._subscription_keys[key] = days
        cls._call_log.append({
            'method': 'create_subscription_key',
            'days': days,
            'key': key,
        })

    @classmethod
    async def get_subscription_days_by_key(cls, key: str) -> Optional[int]:
        return cls._subscription_keys.get(key)

    @classmethod
    async def get_all_subscription_keys(cls):
        return [
            SubscriptionKey(id=i, key=k, days=v, is_active=True)
            for i, (k, v) in enumerate(cls._subscription_keys.items(), 1)
        ]

    @classmethod
    async def remove_subscription_key(cls, key: str) -> bool:
        if key in cls._subscription_keys:
            del cls._subscription_keys[key]
            cls._call_log.append({
                'method': 'remove_subscription_key',
                'key': key,
            })
            return True
        return False

    @classmethod
    async def get_admin_users(cls):
        admin_users = []
        for user_id, roles in cls._roles.items():
            if 'admin' in roles and user_id in cls._users:
                user = cls._users[user_id]
                admin_users.append(
                    UserProfile(
                        user_id=user['user_id'],
                        username=user.get('username', ''),
                        full_name=user.get('full_name', ''),
                        note=user.get('note'),
                    ),
                )
        return admin_users

    @classmethod
    async def get_moderator_users(cls):
        moderator_users = []
        for user_id, roles in cls._roles.items():
            if 'moderator' in roles and user_id in cls._users:
                user = cls._users[user_id]
                moderator_users.append(
                    UserProfile(
                        user_id=user['user_id'],
                        username=user.get('username', ''),
                        full_name=user.get('full_name', ''),
                        note=user.get('note'),
                    ),
                )
        return moderator_users

    @classmethod
    async def get_all_users(cls):
        return [
            UserProfile(
                user_id=user['user_id'],
                username=user.get('username', ''),
                full_name=user.get('full_name', ''),
                note=user.get('note'),
            )
            for user in cls._users.values()
        ]

    @classmethod
    async def is_user_in_db(cls, user_id: int) -> bool:
        return user_id in cls._users

    @classmethod
    async def remove_user(cls, user_id: int):
        if user_id in cls._users:
            del cls._users[user_id]
        if user_id in cls._roles:
            del cls._roles[user_id]
        if user_id in cls._subscriptions:
            del cls._subscriptions[user_id]
        cls._call_log.append({
            'method': 'remove_user',
            'user_id': user_id,
        })

    @classmethod
    async def remove_subscription(cls, user_id: int):
        if user_id in cls._subscriptions:
            del cls._subscriptions[user_id]
        cls._call_log.append({
            'method': 'remove_subscription',
            'user_id': user_id,
        })

    @classmethod
    async def get_user_subscription(cls, user_id: int) -> Optional[date]:
        if user_id in cls._subscriptions:
            return cls._subscriptions[user_id].date()
        return None

    @classmethod
    async def update_user_note(cls, user_id: int, note: str):
        if user_id in cls._users:
            cls._users[user_id]['note'] = note
        cls._call_log.append({
            'method': 'update_user_note',
            'user_id': user_id,
            'note': note,
        })

    @classmethod
    async def add_report(cls, user_id: int, report: str):
        cls._reports.append({
            'user_id': user_id,
            'report': report,
            'timestamp': datetime.now(),
        })
        cls._call_log.append({
            'method': 'add_report',
            'user_id': user_id,
        })

    @classmethod
    async def get_saved_clips(cls, user_id: int, _series_id: Optional[int] = None):
        if user_id not in cls._saved_clips:
            return []
        return [
            VideoClip(
                id=i,
                chat_id=user_id,
                user_id=user_id,
                name=clip['name'],
                video_data=clip['video_data'],
                start_time=clip['start_time'],
                end_time=clip['end_time'],
                duration=clip['duration'],
                is_compilation=clip.get('is_compilation', False),
                season=clip.get('season'),
                episode_number=clip.get('episode_number'),
                series_id=clip.get('series_id'),
            )
            for i, clip in enumerate(cls._saved_clips[user_id], 1)
        ]

    @classmethod
    async def save_clip(  # pylint: disable=too-many-arguments
        cls, chat_id: int, user_id: int, clip_name: str, video_data: bytes,
        start_time: float, end_time: float, duration: float,
        is_compilation: bool = False, season: Optional[int] = None,
        episode_number: Optional[int] = None, series_id: Optional[int] = None,
    ):
        _ = chat_id
        if user_id not in cls._saved_clips:
            cls._saved_clips[user_id] = []
        cls._saved_clips[user_id].append({
            'name': clip_name,
            'video_data': video_data,
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration,
            'is_compilation': is_compilation,
            'season': season,
            'episode_number': episode_number,
            'series_id': series_id,
        })
        cls._call_log.append({
            'method': 'save_clip',
            'user_id': user_id,
            'clip_name': clip_name,
        })

    @classmethod
    async def is_clip_name_unique(cls, chat_id: int, clip_name: str) -> bool:
        if chat_id not in cls._saved_clips:
            return True
        return not any(clip['name'] == clip_name for clip in cls._saved_clips[chat_id])

    @classmethod
    async def get_user_clip_count(cls, chat_id: int) -> int:
        if chat_id not in cls._saved_clips:
            return 0
        return len(cls._saved_clips[chat_id])

    @classmethod
    async def get_clip_by_name(cls, user_id: int, clip_name: str):
        if user_id not in cls._saved_clips:
            return None
        for i, clip in enumerate(cls._saved_clips[user_id], 1):
            if clip['name'] == clip_name:
                return VideoClip(
                    id=i,
                    chat_id=user_id,
                    user_id=user_id,
                    name=clip['name'],
                    video_data=clip['video_data'],
                    start_time=clip['start_time'],
                    end_time=clip['end_time'],
                    duration=clip['duration'],
                    is_compilation=clip.get('is_compilation', False),
                    season=clip.get('season'),
                    episode_number=clip.get('episode_number'),
                )
        return None

    @classmethod
    async def delete_clip(cls, user_id: int, clip_name: str):
        if user_id in cls._saved_clips:
            cls._saved_clips[user_id] = [
                clip for clip in cls._saved_clips[user_id]
                if clip['name'] != clip_name
            ]
        cls._call_log.append({
            'method': 'delete_clip',
            'user_id': user_id,
            'clip_name': clip_name,
        })

    @classmethod
    async def get_last_clip_by_chat_id(cls, chat_id: int, _series_id: Optional[int] = None):
        if chat_id not in cls._last_clips:
            return None

        clip_data = cls._last_clips[chat_id]
        return LastClip(
            id=1,
            chat_id=chat_id,
            segment=clip_data.get('segment', '{}'),
            clip_type=clip_data.get('clip_type', ClipType.SINGLE),
            adjusted_start_time=clip_data.get('adjusted_start_time', 0.0),
            adjusted_end_time=clip_data.get('adjusted_end_time', 0.0),
            compiled_clip=clip_data.get('compiled_clip'),
            is_adjusted=clip_data.get('is_adjusted', False),
            timestamp=date.today(),
        )

    @classmethod
    async def insert_last_search(cls, chat_id: int, quote: str, segments: str, series_id: Optional[int] = None):
        cls._last_searches[chat_id] = {
            'quote': quote,
            'segments': segments,
            'series_id': series_id,
        }
        cls._call_log.append({
            'method': 'insert_last_search',
            'chat_id': chat_id,
        })

    @classmethod
    async def get_last_search_by_chat_id(cls, chat_id: int, _series_id: Optional[int] = None):
        if chat_id not in cls._last_searches:
            return None
        search_data = cls._last_searches[chat_id]
        return SearchHistory(
            id=1,
            chat_id=chat_id,
            quote=search_data['quote'],
            segments=search_data['segments'],
        )

    _user_active_series: Dict[int, int] = {}
    _series: Dict[int, str] = {1: 'ranczo'}
    _series_by_name: Dict[str, int] = {'ranczo': 1}
    _next_series_id: int = 2

    @classmethod
    async def get_user_active_series(cls, user_id: int) -> Optional[int]:
        return cls._user_active_series.get(user_id)

    @classmethod
    async def get_series_by_id(cls, series_id: int) -> Optional[str]:
        return cls._series.get(series_id)

    @classmethod
    async def set_user_active_series(cls, user_id: int, series_id: int):
        cls._user_active_series[user_id] = series_id
        cls._call_log.append({
            'method': 'set_user_active_series',
            'user_id': user_id,
            'series_id': series_id,
        })

    pool = None
