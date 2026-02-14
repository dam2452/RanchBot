from typing import Optional

from bot.database.database_protocol import DatabaseInterface

_db_instance: Optional[DatabaseInterface] = None


def get_db() -> DatabaseInterface:
    global _db_instance  # pylint: disable=global-statement
    if _db_instance is None:
        from bot.database.database_manager import DatabaseManager  # pylint: disable=import-outside-toplevel
        _db_instance = DatabaseManager
    return _db_instance


def set_db(db_implementation: DatabaseInterface) -> None:
    global _db_instance  # pylint: disable=global-statement
    _db_instance = db_implementation


def reset_db() -> None:
    global _db_instance  # pylint: disable=global-statement
    _db_instance = None


class DBProxy:
    def __getattr__(self, name):
        return getattr(get_db(), name)


db = DBProxy()
