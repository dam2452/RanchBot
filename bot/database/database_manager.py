from datetime import (
    date,
    datetime,
    timedelta,
)
import json
import logging
from pathlib import Path
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

import asyncpg
import bcrypt

from bot.database.database_protocol import DatabaseInterface
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
from bot.exceptions import TooManyActiveTokensError
from bot.settings import settings
from bot.utils.constants import DatabaseKeys

db_manager_logger = logging.getLogger(__name__)

class DatabaseManager(DatabaseInterface):
    pool: asyncpg.Pool = None
    _db_fully_initialized: bool = False

    @classmethod
    async def init_pool(
        cls,
            host: Optional[str] = None,
            port: Optional[int] = None,
            database: Optional[str] = None,
            user: Optional[str] = None,
            password: Optional[str] = None,
            schema: Optional[str] = None,
    ):
        if cls.pool is not None and not cls.pool.is_closing():
            db_manager_logger.debug("Database connection pool already exists and is active.")
            return

        config = {
            "host": host or settings.POSTGRES_HOST,
            "port": port or settings.POSTGRES_PORT,
            "database": database or settings.POSTGRES_DB,
            "user": user or settings.POSTGRES_USER,
            "password": password or settings.POSTGRES_PASSWORD.get_secret_value(),
            "server_settings": {"search_path": schema or settings.POSTGRES_SCHEMA},
        }
        db_manager_logger.info("Creating new database connection pool.")
        cls.pool = await asyncpg.create_pool(**config)

    @classmethod
    async def execute_sql_file(cls, file_path: Path) -> None:
        absolute_path = file_path if file_path.is_absolute() else Path(__file__).resolve().parent / file_path
        if not absolute_path.exists():
            db_manager_logger.error(f"SQL file not found: {absolute_path}")
            raise FileNotFoundError(f"SQL file not found: {absolute_path}")

        async with cls.__get_db_connection() as conn:
            async with conn.transaction(): # type: ignore
                with absolute_path.open("r", encoding="utf-8") as file:
                    sql_commands = file.read()
                    await conn.execute(sql_commands) # type: ignore

    @classmethod
    async def init_db(cls) -> None:
        if cls.pool is None or cls.pool.is_closing():
            db_manager_logger.error("Cannot initialize DB schema, connection pool is not available.")
            raise ConnectionError("Database connection pool is not initialized or is closed.")
        db_manager_logger.info("Initializing database schema.")
        await cls.execute_sql_file(Path("init_db.sql"))
        db_manager_logger.info("Database schema initialized.")

    @classmethod
    async def ensure_db_initialized(cls):
        if cls._db_fully_initialized:
            db_manager_logger.info("Database connection and schema already confirmed as initialized.")
            return

        db_manager_logger.info("Ensuring database connection pool and schema are initialized...")
        await cls.init_pool()
        await cls.init_db()
        cls._db_fully_initialized = True
        db_manager_logger.info("📦 Database pool and schema initialization process ensured by DatabaseManager.")

    @classmethod
    def __get_db_connection(cls):
        if cls.pool is None or cls.pool.is_closing():
            db_manager_logger.critical("Attempted to acquire connection from a non-existent or closed pool.")
            raise ConnectionError("Database connection pool is not initialized or is closed.")
        return cls.pool.acquire()

    @classmethod
    async def __resolve_series_id(cls, identifier_id: Optional[int], series_id: Optional[int]) -> Optional[int]:
        if series_id is not None:
            return series_id

        if identifier_id is not None:
            active_series_id = await cls.get_user_active_series(identifier_id)
            if active_series_id:
                return active_series_id

            return await cls.get_or_create_series(settings.DEFAULT_SERIES)

        return None

    @classmethod
    async def get_or_create_series(cls, series_name: str) -> int:
        async with cls.__get_db_connection() as conn:
            series_id = await conn.fetchval(
                "SELECT id FROM series WHERE series_name = $1",
                series_name,
            )
            if series_id is None:
                series_id = await conn.fetchval(
                    "INSERT INTO series (series_name) VALUES ($1) RETURNING id",
                    series_name,
                )
            return series_id

    @classmethod
    async def get_series_by_id(cls, series_id: int) -> Optional[str]:
        async with cls.__get_db_connection() as conn:
            series_name = await conn.fetchval(
                "SELECT series_name FROM series WHERE id = $1",
                series_id,
            )
            return series_name

    @classmethod
    async def get_series_by_name(cls, series_name: str) -> Optional[int]:
        async with cls.__get_db_connection() as conn:
            series_id = await conn.fetchval(
                "SELECT id FROM series WHERE series_name = $1",
                series_name,
            )
            return series_id

    @classmethod
    async def get_all_series(cls) -> List[Series]:
        async with cls.__get_db_connection() as conn:
            rows = await conn.fetch("SELECT id, series_name FROM series")
            return [Series(id=row[DatabaseKeys.ID], series_name=row[DatabaseKeys.SERIES_NAME]) for row in rows]

    @classmethod
    async def log_user_activity(cls, user_id: int, command: str, series_id: Optional[int] = None) -> None:
        async with cls.__get_db_connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    "INSERT INTO user_logs (user_id, command, series_id) VALUES ($1, $2, $3)",
                    user_id, command, series_id,
                )

    @classmethod
    async def log_system_message(cls, log_level: str, log_message: str) -> None:
        async with cls.__get_db_connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    "INSERT INTO system_logs (log_level, log_message) VALUES ($1, $2)",
                    log_level, log_message,
                )

    @classmethod
    async def add_user(
        cls,
                user_id: int, username: Optional[str] = None, full_name: Optional[str] = None,
                note: Optional[str] = None, subscription_days: Optional[int] = None,
    ) -> None:

        async with cls.__get_db_connection() as conn:
            subscription_end = date.today() + timedelta(days=subscription_days) if subscription_days else None
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO user_profiles (user_id, username, full_name, subscription_end, note)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (user_id) DO NOTHING
                    """,
                    user_id, username, full_name, subscription_end, note,
                )

    @classmethod
    async def update_user(
        cls,
                user_id: int, username: Optional[str] = None, full_name: Optional[str] = None, note: Optional[str] = None,
                subscription_end: Optional[int] = None,
    ) -> None:
        async with cls.__get_db_connection() as conn:
            updates = []
            params = []

            if username is not None:
                updates.append(f"username = ${len(params) + 1}")
                params.append(username)
            if full_name is not None:
                updates.append(f"full_name = ${len(params) + 1}")
                params.append(full_name)
            if note is not None:
                updates.append(f"note = ${len(params) + 1}")
                params.append(note)
            if subscription_end is not None:
                updates.append(f"subscription_end = ${len(params) + 1}")
                params.append(subscription_end)

            if updates:
                query = f"UPDATE user_profiles SET {', '.join(updates)} WHERE user_id = ${len(params) + 1}"
                params.append(user_id)
                async with conn.transaction():
                    await conn.execute(query, *params)

    @classmethod
    async def remove_user(cls, user_id: int) -> None:
        async with cls.__get_db_connection() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM user_roles WHERE user_id = $1", user_id)
                await conn.execute("DELETE FROM user_profiles WHERE user_id = $1", user_id)

    @classmethod
    async def get_all_users(cls) -> Optional[List[UserProfile]]:
        async with cls.__get_db_connection() as conn:
            rows = await conn.fetch(
                "SELECT user_id, username, full_name, subscription_end, note FROM user_profiles",
            )

        return [
            UserProfile(
                user_id=row[DatabaseKeys.USER_ID],
                username=row[DatabaseKeys.USERNAME],
                full_name=row[DatabaseKeys.FULL_NAME],
                subscription_end=row[DatabaseKeys.SUBSCRIPTION_END],
                note=row[DatabaseKeys.NOTE],
            ) for row in rows
        ] if rows else None

    @classmethod
    async def is_user_in_db(cls, user_id: int) -> bool:
        async with cls.__get_db_connection() as conn:
            result = await conn.fetchval("SELECT EXISTS (SELECT 1 FROM user_profiles WHERE user_id = $1)", user_id)
        return result

    @classmethod
    async def get_admin_users(cls) -> Optional[List[UserProfile]]:
        async with cls.__get_db_connection() as conn:
            rows = await conn.fetch(
                "SELECT user_id, username, full_name, subscription_end, note FROM user_profiles "
                "WHERE user_id IN (SELECT user_id FROM user_roles WHERE is_admin = TRUE)",
            )

        return [
            UserProfile(
                user_id=row[DatabaseKeys.USER_ID],
                username=row[DatabaseKeys.USERNAME],
                full_name=row.get(DatabaseKeys.FULL_NAME, "N/A"),
                subscription_end=row.get(DatabaseKeys.SUBSCRIPTION_END, None),
                note=row.get(DatabaseKeys.NOTE, "Brak"),
            ) for row in rows
        ] if rows else None

    @classmethod
    async def get_moderator_users(cls) -> Optional[List[UserProfile]]:
        async with cls.__get_db_connection() as conn:
            rows = await conn.fetch(
                "SELECT user_id, username, full_name, subscription_end, note FROM user_profiles "
                "WHERE user_id IN (SELECT user_id FROM user_roles WHERE is_moderator = TRUE)",
            )

        return [
            UserProfile(
                user_id=row[DatabaseKeys.USER_ID],
                username=row[DatabaseKeys.USERNAME],
                full_name=row.get(DatabaseKeys.FULL_NAME, "N/A"),
                subscription_end=row.get(DatabaseKeys.SUBSCRIPTION_END, None),
                note=row.get(DatabaseKeys.NOTE, "Brak"),
            ) for row in rows
        ] if rows else None

    @classmethod
    async def is_user_subscribed(cls, user_id: int) -> bool:
        async with cls.__get_db_connection() as conn:
            result = await conn.fetchrow(
                "SELECT ur.is_admin, ur.is_moderator, up.subscription_end "
                "FROM user_profiles up "
                "LEFT JOIN user_roles ur ON ur.user_id = up.user_id "
                "WHERE up.user_id = $1",
                user_id,
            )

        if result:
            is_admin = result[DatabaseKeys.IS_ADMIN]
            is_moderator = result[DatabaseKeys.IS_MODERATOR]
            subscription_end = result[DatabaseKeys.SUBSCRIPTION_END]
            if is_admin or is_moderator or (subscription_end and subscription_end >= date.today()):
                return True
        return False

    @classmethod
    async def is_user_admin(cls, user_id: int) -> Optional[bool]:
        async with cls.__get_db_connection() as conn:
            result = await conn.fetchval(
                "SELECT is_admin FROM user_roles WHERE user_id = $1",
                user_id,
            )
        return result

    @classmethod
    async def is_user_moderator(cls, user_id: int) -> Optional[bool]:
        async with cls.__get_db_connection() as conn:
            result = await conn.fetchval(
                "SELECT is_moderator FROM user_roles WHERE user_id = $1",
                user_id,
            )
        return result

    @classmethod
    async def set_default_admin(cls, user_id: int, username: str, full_name: str, password: Optional[str] = None) -> None:
        async with cls.__get_db_connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    "INSERT INTO user_profiles (user_id, username, full_name) "
                    "VALUES ($1, $2, $3) "
                    "ON CONFLICT (user_id) DO NOTHING",
                    user_id, username, full_name,
                )

                await conn.execute(
                    "INSERT INTO user_roles (user_id, is_admin) "
                    "VALUES ($1, TRUE) "
                    "ON CONFLICT (user_id) DO NOTHING",
                    user_id,
                )

                if password:
                    salt = bcrypt.gensalt()
                    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

                    await conn.execute(
                        """
                        INSERT INTO user_credentials (user_id, hashed_password)
                        VALUES ($1, $2)
                        ON CONFLICT (user_id) DO UPDATE SET hashed_password = EXCLUDED.hashed_password
                        """,
                        user_id, hashed_password,
                    )

    @classmethod
    def __row_to_video_clip(cls, row: asyncpg.Record) -> VideoClip:
        return VideoClip(
            id=row[DatabaseKeys.ID],
            chat_id=row["chat_id"],
            user_id=row[DatabaseKeys.USER_ID],
            name=row[DatabaseKeys.CLIP_NAME],
            video_data=row[DatabaseKeys.VIDEO_DATA],
            start_time=row[DatabaseKeys.START_TIME],
            end_time=row[DatabaseKeys.END_TIME],
            duration=row[DatabaseKeys.DURATION],
            season=row[DatabaseKeys.SEASON],
            episode_number=row[DatabaseKeys.EPISODE_NUMBER],
            is_compilation=row[DatabaseKeys.IS_COMPILATION],
            series_id=row.get(DatabaseKeys.SERIES_ID),
        )

    @classmethod
    async def get_saved_clips(cls, user_id: int, series_id: Optional[int] = None) -> List[VideoClip]:
        resolved_series_id = await cls.__resolve_series_id(user_id, series_id)

        async with cls.__get_db_connection() as conn:
            if resolved_series_id:
                rows = await conn.fetch(
                    "SELECT id, chat_id, user_id, clip_name, video_data, start_time, end_time, duration, season, episode_number, is_compilation, series_id "
                    "FROM video_clips "
                    "WHERE user_id = $1 AND series_id = $2",
                    user_id, resolved_series_id,
                )
            else:
                rows = await conn.fetch(
                    "SELECT id, chat_id, user_id, clip_name, video_data, start_time, end_time, duration, season, episode_number, is_compilation, series_id "
                    "FROM video_clips "
                    "WHERE user_id = $1",
                    user_id,
                )

        return [cls.__row_to_video_clip(row) for row in rows] if rows else []

    @classmethod
    async def save_clip(  # pylint: disable=too-many-arguments
        cls,
        chat_id: int, user_id: int, clip_name: str, video_data: bytes, start_time: float,
        end_time: float, duration: float, is_compilation: bool,
        season: Optional[int] = None, episode_number: Optional[int] = None, series_id: Optional[int] = None,
    ) -> None:
        resolved_series_id = await cls.__resolve_series_id(user_id, series_id)

        async with cls.__get_db_connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    "INSERT INTO video_clips (chat_id, user_id, clip_name, video_data, start_time, "
                    "end_time, duration, season, episode_number, is_compilation, series_id) "
                    "VALUES ($1, $2, $3, $4::bytea, $5, $6, $7, $8, $9, $10, $11)",
                    chat_id, user_id, clip_name, video_data, start_time, end_time, duration,
                    season, episode_number, is_compilation, resolved_series_id,
                )

    @classmethod
    async def get_clip_by_name(cls, user_id: int, clip_name: str) -> Optional[VideoClip]:
        async with cls.__get_db_connection() as conn:
            row = await conn.fetchrow(
                "SELECT id, chat_id, user_id, clip_name, video_data, start_time, end_time, duration, season, episode_number, is_compilation, series_id "
                "FROM video_clips "
                "WHERE user_id = $1 AND clip_name = $2",
                user_id, clip_name,
            )

        if row:
            return cls.__row_to_video_clip(row)
        return None

    @classmethod
    async def get_clip_by_index(cls, user_id: int, index: int) -> Optional[VideoClip]:
        async with cls.__get_db_connection() as conn:
            row = await conn.fetchrow(
                "SELECT id, chat_id, user_id, clip_name, video_data, start_time, end_time, duration, season, episode_number, is_compilation, series_id "
                "FROM video_clips "
                "WHERE user_id = $1 "
                "ORDER BY id "
                "LIMIT 1 OFFSET $2",
                user_id, index - 1,
            )

        if row:
            return cls.__row_to_video_clip(row)
        return None

    @classmethod
    async def get_video_data_by_name(cls, user_id: int, clip_name: str) -> Optional[bytes]:
        async with cls.__get_db_connection() as conn:
            result = await conn.fetchval(
                "SELECT video_data FROM video_clips WHERE user_id = $1 AND clip_name = $2",
                user_id, clip_name,
            )
        return result

    @classmethod
    async def add_subscription(cls, user_id: int, days: int) -> Optional[date]:
        async with cls.__get_db_connection() as conn:
            new_end_date = await conn.fetchval(
                "UPDATE user_profiles "
                "SET subscription_end = CURRENT_DATE + $2 * interval '1 day' "
                "WHERE user_id = $1 "
                "RETURNING subscription_end",
                user_id, days,
            )
        return new_end_date

    @classmethod
    async def remove_subscription(cls, user_id: int) -> None:
        async with cls.__get_db_connection() as conn:
            await conn.execute(
                "UPDATE user_profiles "
                "SET subscription_end = NULL "
                "WHERE user_id = $1",
                user_id,
            )

    @classmethod
    async def get_user_subscription(cls, user_id: int) -> Optional[date]:
        async with cls.__get_db_connection() as conn:
            subscription_end = await conn.fetchval("SELECT subscription_end FROM user_profiles WHERE user_id = $1", user_id)
        return subscription_end

    @classmethod
    async def add_report(cls, user_id: int, report: str) -> None:
        async with cls.__get_db_connection() as conn:
            await conn.execute(
                "INSERT INTO reports (user_id, report) "
                "VALUES ($1, $2)",
                user_id, report,
            )

    @classmethod
    async def get_reports(cls, user_id: int) -> List[Dict[str, Union[int, str]]]:
        async with cls.__get_db_connection() as conn:
            rows = await conn.fetch(
                "SELECT id, report FROM reports WHERE user_id = $1 ORDER BY id DESC",
                user_id,
            )
            return [{DatabaseKeys.ID: row[DatabaseKeys.ID], DatabaseKeys.REPORT: row[DatabaseKeys.REPORT]} for row in rows]

    @classmethod
    async def delete_clip(cls, user_id: int, clip_name: str) -> str:
        async with cls.__get_db_connection() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    "DELETE FROM video_clips "
                    "WHERE user_id = $1 AND clip_name = $2",
                    user_id, clip_name,
                )
        return result

    @classmethod
    async def is_clip_name_unique(cls, chat_id: int, clip_name: str) -> bool:
        async with cls.__get_db_connection() as conn:
            result = await conn.fetchval(
                "SELECT COUNT(*) FROM video_clips WHERE chat_id=$1 AND clip_name=$2",
                chat_id, clip_name,
            )
        return result == 0

    @classmethod
    async def insert_last_search(cls, chat_id: int, quote: str, segments: str, series_id: Optional[int] = None) -> None:
        resolved_series_id = await cls.__resolve_series_id(chat_id, series_id)

        async with cls.__get_db_connection() as conn:
            await conn.execute(
                "INSERT INTO search_history (chat_id, quote, segments, series_id) "
                "VALUES ($1, $2, $3::jsonb, $4)",
                chat_id, quote, segments, resolved_series_id,
            )

    @classmethod
    async def get_last_search_by_chat_id(cls, chat_id: int, series_id: Optional[int] = None) -> Optional[SearchHistory]:
        resolved_series_id = await cls.__resolve_series_id(chat_id, series_id)

        async with cls.__get_db_connection() as conn:
            if resolved_series_id:
                result = await conn.fetchrow(
                    "SELECT id, chat_id, quote, segments, series_id "
                    "FROM search_history "
                    "WHERE chat_id = $1 AND series_id = $2 "
                    "ORDER BY id DESC "
                    "LIMIT 1",
                    chat_id, resolved_series_id,
                )
            else:
                result = await conn.fetchrow(
                    "SELECT id, chat_id, quote, segments, series_id "
                    "FROM search_history "
                    "WHERE chat_id = $1 "
                    "ORDER BY id DESC "
                    "LIMIT 1",
                    chat_id,
                )

        if result:
            return SearchHistory(
                id=result[DatabaseKeys.ID],
                chat_id=result["chat_id"],
                quote=result[DatabaseKeys.QUOTE],
                segments=result[DatabaseKeys.SEGMENTS],
                series_id=result.get(DatabaseKeys.SERIES_ID),
            )
        return None

    @classmethod
    async def update_last_search(cls, search_id: int, new_quote: Optional[str] = None, new_segments: Optional[str] = None) -> None:
        async with cls.__get_db_connection() as conn:
            if new_quote:
                await conn.execute(
                    "UPDATE search_history "
                    "SET quote = $1 "
                    "WHERE id = $2",
                    new_quote, search_id,
                )
            if new_segments:
                await conn.execute(
                    "UPDATE search_history "
                    "SET segments = $1::jsonb "
                    "WHERE id = $2",
                    new_segments, search_id,
                )

    @classmethod
    async def delete_search_by_id(cls, search_id: int) -> None:
        async with cls.__get_db_connection() as conn:
            await conn.execute(
                "DELETE FROM search_history "
                "WHERE id = $1",
                search_id,
            )

    @classmethod
    async def insert_last_clip(
        cls,
                chat_id: int,
                segment: json,
                compiled_clip: Optional[bytes],
                clip_type: ClipType,
                adjusted_start_time: Optional[float],
                adjusted_end_time: Optional[float],
                is_adjusted: bool,
                series_id: Optional[int] = None,
    ) -> None:
        resolved_series_id = await cls.__resolve_series_id(chat_id, series_id)

        async with cls.__get_db_connection() as conn:
            segment_json = json.dumps(segment)
            await conn.execute(
                "INSERT INTO last_clips (chat_id, segment, compiled_clip, type, adjusted_start_time, adjusted_end_time, is_adjusted, series_id) "
                "VALUES ($1, $2::jsonb, $3::bytea, $4, $5, $6, $7, $8)",
                chat_id, segment_json, compiled_clip, clip_type.value, adjusted_start_time, adjusted_end_time, is_adjusted, resolved_series_id,
            )

    @classmethod
    async def get_last_clip_by_chat_id(cls, chat_id: int, series_id: Optional[int] = None) -> Optional[LastClip]:
        resolved_series_id = await cls.__resolve_series_id(chat_id, series_id)

        async with cls.__get_db_connection() as conn:
            if resolved_series_id:
                row = await conn.fetchrow(
                    "SELECT id, chat_id, segment, compiled_clip, type AS clip_type, "
                    "adjusted_start_time, adjusted_end_time, is_adjusted, timestamp, series_id "
                    "FROM last_clips "
                    "WHERE chat_id = $1 AND series_id = $2 "
                    "ORDER BY id DESC "
                    "LIMIT 1",
                    chat_id, resolved_series_id,
                )
            else:
                row = await conn.fetchrow(
                    "SELECT id, chat_id, segment, compiled_clip, type AS clip_type, "
                    "adjusted_start_time, adjusted_end_time, is_adjusted, timestamp, series_id "
                    "FROM last_clips "
                    "WHERE chat_id = $1 "
                    "ORDER BY id DESC "
                    "LIMIT 1",
                    chat_id,
                )

        if row:
            return LastClip(
                id=row[DatabaseKeys.ID],
                chat_id=row["chat_id"],
                segment=row[DatabaseKeys.SEGMENT],
                compiled_clip=row[DatabaseKeys.COMPILED_CLIP],
                clip_type=ClipType(row[DatabaseKeys.CLIP_TYPE]),
                adjusted_start_time=row[DatabaseKeys.ADJUSTED_START_TIME],
                adjusted_end_time=row[DatabaseKeys.ADJUSTED_END_TIME],
                is_adjusted=row[DatabaseKeys.IS_ADJUSTED],
                timestamp=row[DatabaseKeys.TIMESTAMP],
                series_id=row.get(DatabaseKeys.SERIES_ID),
            )
        return None

    @classmethod
    async def update_last_clip(
        cls,
                clip_id: int, new_segment: Optional[str] = None, new_compiled_clip: Optional[bytes] = None,
                new_type: Optional[str] = None,
    ) -> None:
        async with cls.__get_db_connection() as conn:
            if new_segment:
                await conn.execute(
                    "UPDATE last_clips "
                    "SET segment = $1::jsonb "
                    "WHERE id = $2",
                    new_segment, clip_id,
                )
            if new_compiled_clip:
                await conn.execute(
                    "UPDATE last_clips "
                    "SET compiled_clip = $1::bytea "
                    "WHERE id = $2",
                    new_compiled_clip, clip_id,
                )
            if new_type:
                await conn.execute(
                    "UPDATE last_clips "
                    "SET type = $1 "
                    "WHERE id = $2",
                    new_type, clip_id,
                )

    @classmethod
    async def delete_clip_by_id(cls, clip_id: int) -> None:
        async with cls.__get_db_connection() as conn:
            await conn.execute(
                "DELETE FROM last_clips WHERE id = $1",
                clip_id,
            )

    @classmethod
    async def update_user_note(cls, user_id: int, note: str) -> None:
        async with cls.__get_db_connection() as conn:
            await conn.execute(
                "UPDATE user_profiles SET note = $1 WHERE user_id = $2",
                note, user_id,
            )

    @classmethod
    async def log_command_usage(cls, user_id: int) -> None:
        async with cls.__get_db_connection() as conn:
            await conn.execute(
                "INSERT INTO user_command_limits (user_id, timestamp) VALUES ($1, NOW())",
                user_id,
            )

    @classmethod
    async def is_command_limited(cls, user_id: int, limit: int, duration_seconds: int) -> bool:
        usage_count = await cls.get_command_usage_count(user_id, duration_seconds)
        return usage_count >= limit

    @classmethod
    async def get_command_usage_count(cls, user_id: int, duration_seconds: int) -> int:
        async with cls.__get_db_connection() as conn:
            time_threshold = datetime.now() - timedelta(seconds=duration_seconds)
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM user_command_limits WHERE user_id = $1 AND timestamp >= $2",
                user_id, time_threshold,
            )
        return count

    @classmethod
    async def is_admin_or_moderator(cls, user_id: int) -> bool:
        async with cls.__get_db_connection() as conn:
            result = await conn.fetchrow(
                "SELECT is_admin, is_moderator "
                "FROM user_roles "
                "WHERE user_id = $1",
                user_id,
            )

        if result:
            return result[DatabaseKeys.IS_ADMIN] or result[DatabaseKeys.IS_MODERATOR]
        return False

    @classmethod
    async def get_subscription_days_by_key(cls, key: str) -> Optional[int]:
        async with cls.__get_db_connection() as conn:
            result = await conn.fetchrow(
                "SELECT days FROM subscription_keys WHERE key = $1 AND is_active = TRUE",
                key,
            )
        return result[DatabaseKeys.DAYS] if result else None

    @classmethod
    async def deactivate_subscription_key(cls, key: str) -> None:
        async with cls.__get_db_connection() as conn:
            await conn.execute(
                "UPDATE subscription_keys SET is_active = FALSE WHERE key = $1",
                key,
            )

    @classmethod
    async def create_subscription_key(cls, days: int, key: str) -> None:
        async with cls.__get_db_connection() as conn:
            await conn.execute(
                "INSERT INTO subscription_keys (key, days, is_active) VALUES ($1, $2, TRUE)",
                key, days,
            )

    @classmethod
    async def remove_subscription_key(cls, key: str) -> bool:
        async with cls.__get_db_connection() as conn:
            result = await conn.execute(
                "DELETE FROM subscription_keys WHERE key = $1",
                key,
            )
        return result == "DELETE 1"

    @classmethod
    async def get_all_subscription_keys(cls) -> List[SubscriptionKey]:
        async with cls.__get_db_connection() as conn:
            rows = await conn.fetch("SELECT * FROM subscription_keys")
        return [SubscriptionKey(**row) for row in rows]

    @classmethod
    async def get_user_clip_count(cls, chat_id: int) -> int:
        async with cls.__get_db_connection() as conn:
            result = await conn.fetchval(
                "SELECT COUNT(*) FROM video_clips WHERE chat_id = $1",
                chat_id,
            )
        return result

    @classmethod
    async def clear_test_db(cls, tables: List[str], schema: str = "public") -> None:
        if not tables:
            raise ValueError("No tables specified for truncation.")

        async with cls.__get_db_connection() as conn:
            async with conn.transaction():
                valid_schema = await conn.fetchval(
                    "SELECT COUNT(*) > 0 FROM information_schema.schemata WHERE schema_name = $1",
                    schema,
                )
                if not valid_schema:
                    raise ValueError(f"Invalid schema: {schema}")

                for table in tables:
                    valid_table = await conn.fetchval(
                        """
                        SELECT COUNT(*) > 0
                        FROM information_schema.tables
                        WHERE table_schema = $1 AND table_name = $2
                        """,
                        schema, table,
                    )
                    if not valid_table:
                        raise ValueError(f"Invalid table: {table}")

                    await conn.execute(f'TRUNCATE TABLE "{schema}"."{table}" CASCADE;')

    @classmethod
    async def set_user_as_moderator(cls, user_id: int) -> None:
        async with cls.__get_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO user_roles (user_id, is_moderator)
                VALUES ($1, TRUE)
                ON CONFLICT (user_id) DO UPDATE SET is_moderator = TRUE
                """,
                user_id,
            )

    @classmethod
    async def add_admin(cls, user_id: int) -> None:
        async with cls.__get_db_connection() as conn:
            async with conn.transaction():
                user_exists = await conn.fetchval(
                    "SELECT COUNT(*) FROM user_profiles WHERE user_id = $1",
                    user_id,
                )
                if not user_exists:
                    raise ValueError(f"User with ID {user_id} does not exist in user_profiles")

                await conn.execute(
                    """
                    INSERT INTO user_roles (user_id, is_admin)
                    VALUES ($1, TRUE)
                    ON CONFLICT (user_id) DO UPDATE SET is_admin = TRUE
                    """,
                    user_id,
                )

    @classmethod
    async def add_moderator(cls, user_id: int) -> None:
        await cls.set_user_as_moderator(user_id)

    @classmethod
    async def remove_admin(cls, user_id: int) -> None:
        async with cls.__get_db_connection() as conn:
            async with conn.transaction():
                user_in_roles = await conn.fetchval(
                    "SELECT COUNT(*) FROM user_roles WHERE user_id = $1",
                    user_id,
                )
                if not user_in_roles:
                    raise ValueError(f"User with ID {user_id} does not exist in user_roles")

                await conn.execute(
                    """
                    UPDATE user_roles
                    SET is_admin = FALSE
                    WHERE user_id = $1
                    """,
                    user_id,
                )

    @classmethod
    async def __get_message_from_message_table(
        cls,
            table: str, key: str, handler_name: str,
    ) -> Optional[str]:
        async with cls.__get_db_connection() as conn:
            query = f"""
                SELECT message
                FROM {table}
                WHERE handler_name = $1 AND key = $2
            """
            row = await conn.fetchrow(query, handler_name, key)
            return row[DatabaseKeys.MESSAGE] if row else None

    @classmethod
    async def get_message_from_specialized_table(
        cls,
            key: str, handler_name: str,
    ) -> Optional[str]:
        return await cls.__get_message_from_message_table(
            settings.SPECIALIZED_TABLE, key, handler_name,
        )

    @classmethod
    async def get_user_by_username(cls, username: str) -> Optional[Tuple[UserProfile, UserCredentials]]:
        async with cls.__get_db_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    up.user_id,
                    up.username,
                    up.full_name,
                    up.subscription_end,
                    up.note,
                    uc.hashed_password,
                    uc.created_at,
                    uc.last_updated
                FROM user_profiles up
                JOIN user_credentials uc ON up.user_id = uc.user_id
                WHERE up.username = $1
                """,
                username,
            )
            if row:
                profile = UserProfile(
                    user_id=row[DatabaseKeys.USER_ID],
                    username=row[DatabaseKeys.USERNAME],
                    full_name=row[DatabaseKeys.FULL_NAME],
                    subscription_end=row[DatabaseKeys.SUBSCRIPTION_END],
                    note=row[DatabaseKeys.NOTE],
                )
                credentials = UserCredentials(
                    user_id=row[DatabaseKeys.USER_ID],
                    hashed_password=row[DatabaseKeys.HASHED_PASSWORD],
                    created_at=row[DatabaseKeys.CREATED_AT],
                    last_updated=row[DatabaseKeys.LAST_UPDATED],
                )
                return profile, credentials
            return None

    @classmethod
    async def insert_refresh_token(
        cls,
                user_id: int,
                token: str,
                created_at: datetime,
                expires_at: datetime,
                ip_address: Optional[str],
                user_agent: Optional[str],
    ) -> None:
        async with cls.__get_db_connection() as conn:
            active_token_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM refresh_tokens
                WHERE user_id = $1 AND expires_at > NOW()
                """,
                user_id,
            )

            if active_token_count >= settings.MAX_ACTIVE_TOKENS:
                raise TooManyActiveTokensError(f"User {user_id} exceeded the max number of active refresh tokens.")

            await conn.execute(
                """
                INSERT INTO refresh_tokens (user_id, token, created_at, expires_at, ip_address, user_agent)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                user_id, token, created_at, expires_at, ip_address, user_agent,
            )

    @classmethod
    async def get_refresh_token(cls, token: str) -> Optional[RefreshToken]:
        async with cls.__get_db_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, token, created_at, expires_at, revoked_at, ip_address, user_agent
                FROM refresh_tokens
                WHERE token = $1 AND expires_at > NOW()
                """,
                token,
            )
            if row:
                return RefreshToken(
                    id=row[DatabaseKeys.ID],
                    user_id=row[DatabaseKeys.USER_ID],
                    token=row[DatabaseKeys.TOKEN],
                    created_at=row[DatabaseKeys.CREATED_AT],
                    expires_at=row[DatabaseKeys.EXPIRES_AT],
                    revoked=row[DatabaseKeys.REVOKED_AT] is not None,
                    revoked_at=row[DatabaseKeys.REVOKED_AT],
                    ip_address=row[DatabaseKeys.IP_ADDRESS],
                    user_agent=row[DatabaseKeys.USER_AGENT],
                )
            return None

    @classmethod
    async def revoke_refresh_token(cls, token: str) -> None:
        async with cls.__get_db_connection() as conn:
            await conn.execute(
                """
                UPDATE refresh_tokens
                SET revoked_at = NOW(), expires_at = NOW()
                WHERE token = $1
                """,
                token,
            )

    @classmethod
    async def revoke_all_user_tokens(cls, user_id: int) -> int:
        async with cls.__get_db_connection() as conn:
            result = await conn.execute(
                """
                UPDATE refresh_tokens
                SET revoked_at = NOW(), expires_at = NOW()
                WHERE user_id = $1 AND expires_at > NOW() AND revoked_at IS NULL
                """,
                user_id,
            )
            return int(result.split()[-1]) if result else 0

    @classmethod
    async def get_credentials_with_profile_by_username(cls, username: str) -> Optional[Tuple[UserProfile, str]]:
        async with cls.__get_db_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    up.user_id,
                    up.username,
                    up.full_name,
                    up.subscription_end,
                    up.note,
                    uc.hashed_password
                FROM user_profiles up
                JOIN user_credentials uc ON up.user_id = uc.user_id
                WHERE up.username = $1
                """,
                username,
            )
            if row:
                profile = UserProfile(
                    user_id=row[DatabaseKeys.USER_ID],
                    username=row[DatabaseKeys.USERNAME],
                    full_name=row[DatabaseKeys.FULL_NAME],
                    subscription_end=row[DatabaseKeys.SUBSCRIPTION_END],
                    note=row[DatabaseKeys.NOTE],
                )
                return profile, row[DatabaseKeys.HASHED_PASSWORD]
            return None

    @classmethod
    async def get_user_by_id(cls, user_id: int) -> Optional[UserProfile]:
        async with cls.__get_db_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT user_id, username, full_name, subscription_end, note
                FROM user_profiles
                WHERE user_id = $1
                """,
                user_id,
            )
            if row:
                return UserProfile(
                    user_id=row[DatabaseKeys.USER_ID],
                    username=row[DatabaseKeys.USERNAME],
                    full_name=row[DatabaseKeys.FULL_NAME],
                    subscription_end=row[DatabaseKeys.SUBSCRIPTION_END],
                    note=row[DatabaseKeys.NOTE],
                )
            return None

    @classmethod
    async def get_user_active_series(cls, user_id: int) -> Optional[int]:
        async with cls.__get_db_connection() as conn:
            result = await conn.fetchval(
                "SELECT active_series_id FROM user_series_context WHERE user_id = $1",
                user_id,
            )
            return result

    @classmethod
    async def set_user_active_series(cls, user_id: int, series_id: int) -> None:
        async with cls.__get_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO user_series_context (user_id, active_series_id)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE SET active_series_id = $2
                """,
                user_id, series_id,
            )
