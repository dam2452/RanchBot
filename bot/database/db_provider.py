from bot.database.database_protocol import DatabaseInterface
from typing import Optional

_db_instance: Optional[DatabaseInterface] = None


def get_db() -> DatabaseInterface:
    global _db_instance
    if _db_instance is None:
        from bot.database.database_manager import DatabaseManager
        _db_instance = DatabaseManager
    return _db_instance


def set_db(db_implementation: DatabaseInterface) -> None:
    global _db_instance
    _db_instance = db_implementation


def reset_db() -> None:
    global _db_instance
    _db_instance = None


class DBProxy:
    def __getattr__(self, name):
        return getattr(get_db(), name)


db = DBProxy()
