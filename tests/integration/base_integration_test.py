import json
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from bot.database import db
from bot.interfaces.message import AbstractMessage
from bot.interfaces.responder import AbstractResponder

logger = logging.getLogger(__name__)


class FakeMessage(AbstractMessage):
    def __init__(
        self,
        text: str,
        user_id: int,
        chat_id: Optional[int] = None,
        username: str = "test_user",
        full_name: str = "Test User",
        reply_json: bool = False,
    ):
        self._text = text
        self._user_id = user_id
        self._chat_id = chat_id or user_id
        self._username = username
        self._full_name = full_name
        self._reply_json = reply_json

    def get_user_id(self) -> int:
        return self._user_id

    def get_username(self) -> str:
        return self._username

    def get_text(self) -> str:
        return self._text

    def get_chat_id(self) -> int:
        return self._chat_id

    def get_sender_id(self) -> int:
        return self._user_id

    def get_full_name(self) -> str:
        return self._full_name

    def should_reply_json(self) -> bool:
        return self._reply_json


class FakeResponder(AbstractResponder):
    def __init__(self):
        self.texts: List[str] = []
        self.markdowns: List[str] = []
        self.videos: List[Dict[str, Any]] = []
        self.documents: List[Dict[str, Any]] = []
        self.photos: List[Dict[str, Any]] = []
        self.json_data: List[Any] = []

    async def send_text(self, text: str) -> None:
        self.texts.append(text)
        logger.debug(f"FakeResponder.send_text: {text}")

    async def send_markdown(self, text: str) -> None:
        self.markdowns.append(text)
        logger.debug(f"FakeResponder.send_markdown: {text}")

    async def send_photo(self, image_bytes: bytes, image_path: Path, caption: str) -> None:
        self.photos.append({
            'image_bytes': image_bytes,
            'image_path': image_path,
            'caption': caption,
        })
        logger.debug(f"FakeResponder.send_photo: {image_path}")

    async def send_video(
        self,
        file_path: Path,
        delete_after_send: bool = True,
        width: Optional[int] = None,
        height: Optional[int] = None,
        duration: Optional[float] = None,
        suggestions: Optional[List[str]] = None,
    ) -> None:
        self.videos.append({
            'file_path': file_path,
            'delete_after_send': delete_after_send,
            'width': width,
            'height': height,
            'duration': duration,
            'suggestions': suggestions,
        })
        logger.debug(f"FakeResponder.send_video: {file_path}")

    async def send_document(
        self,
        file_path: Path,
        caption: str,
        delete_after_send: bool = True,
        cleanup_dir: Optional[Path] = None,
    ) -> None:
        self.documents.append({
            'file_path': file_path,
            'caption': caption,
            'delete_after_send': delete_after_send,
            'cleanup_dir': cleanup_dir,
        })
        logger.debug(f"FakeResponder.send_document: {file_path}")

    async def send_json(self, data: json) -> None:
        self.json_data.append(data)
        logger.debug(f"FakeResponder.send_json: {data}")

    def get_all_text_responses(self) -> List[str]:
        return self.texts + self.markdowns

    def has_sent_video(self) -> bool:
        return len(self.videos) > 0

    def has_sent_text(self) -> bool:
        return len(self.texts) > 0 or len(self.markdowns) > 0


class BaseIntegrationTest:
    logger = logging.getLogger(__name__)
    admin_id: int = 123

    def setup_method(self):
        pass

    def create_message(
        self,
        text: str,
        user_id: Optional[int] = None,
        chat_id: Optional[int] = None,
        **kwargs,
    ) -> FakeMessage:
        return FakeMessage(
            text=text,
            user_id=user_id or self.admin_id,
            chat_id=chat_id,
            **kwargs,
        )

    def create_responder(self) -> FakeResponder:
        return FakeResponder()

    async def add_test_user(
        self,
        user_id: int,
        username: str = "test_user",
        full_name: str = "Test User",
        subscription_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        await db.add_user(
            user_id=user_id,
            username=username,
            full_name=full_name,
            note=None,
            subscription_days=subscription_days,
        )
        return {
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "subscription_days": subscription_days,
        }

    async def make_user_subscriber(self, user_id: int, days: int = 365) -> None:
        await db.add_subscription(user_id, days)

    async def make_user_admin(self, user_id: int) -> None:
        await db.add_admin(user_id)

    async def make_user_moderator(self, user_id: int) -> None:
        await db.add_moderator(user_id)

    async def remove_admin(self, user_id: int) -> None:
        await db.remove_admin(user_id)
