from pathlib import Path
from typing import Optional

from fastapi.responses import (
    FileResponse,
    JSONResponse,
)
from starlette.background import BackgroundTask

from bot.interfaces.responder import AbstractResponder


class RestResponder(AbstractResponder):
    def __init__(self):
        self.responses = []
        self._response_given = False

    async def send_text(self, text: str):
        if self._response_given:
            return
        self.responses.append({"type": "text", "content": text})
        self._response_given = True

    async def send_markdown(self, text: str):
        if self._response_given:
            return
        self.responses.append({"type": "markdown", "content": text})
        self._response_given = True

    async def send_photo(self, image_bytes: bytes, image_path: Path, caption: str, background: Optional[BackgroundTask] = None):
        if self._response_given:
            return
        self.responses.append({
            "type": "photo",
            "caption": caption,
            "filename": str(image_path),
            "background": background,
        })
        self._response_given = True

    async def send_video(self, file_path: Path, delete_after_send: bool = True):
        if self._response_given:
            return
        task = BackgroundTask(file_path.unlink) if delete_after_send else None
        self.responses.append({
            "type": "video",
            "filename": str(file_path),
            "background": task,
        })
        self._response_given = True

    async def send_document(self, file_path: Path, caption: str, background: Optional[BackgroundTask] = None):
        if self._response_given:
            return
        self.responses.append({
            "type": "document",
            "caption": caption,
            "filename": str(file_path),
            "background": background,
        })
        self._response_given = True

    async def send_json(self, data: dict):
        if self._response_given:
            return
        self.responses.append({
            "type": "json",
            "content": data,
        })
        self._response_given = True

    def get_response(self):
        for item in self.responses:
            if item["type"] in {"video", "photo", "document"}:
                media_type = {
                    "video": "video/mp4",
                    "photo": "image/jpeg",
                    "document": "application/octet-stream",
                }[item["type"]]
                return FileResponse(
                    path=item["filename"],
                    media_type=media_type,
                    filename=Path(item["filename"]).name,
                    background=item.get("background"),
                )

        for item in self.responses:
            if item["type"] == "json":
                return JSONResponse(item["content"])

        return JSONResponse(self.responses)
