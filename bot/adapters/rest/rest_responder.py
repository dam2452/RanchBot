from pathlib import Path
from typing import Optional

from fastapi.responses import (
    FileResponse,
    JSONResponse,
)
from starlette.background import BackgroundTask

from bot.adapters.rest.response_type import ResponseType
from bot.interfaces.responder import AbstractResponder


class RestResponder(AbstractResponder):
    def __init__(self):
        self.responses = []

    async def send_text(self, text: str) -> None:
        self.responses.append({"type": ResponseType.TEXT, "content": text})

    async def send_markdown(self, text: str) -> None:
        self.responses.append({"type": ResponseType.MARKDOWN, "content": text})

    async def send_photo(
        self,
        image_bytes: bytes,
        image_path: Path,
        caption: str,
        background: Optional[BackgroundTask] = None,
    ) -> None:
        self.responses.append({
            "type": ResponseType.PHOTO,
            "caption": caption,
            "filename": str(image_path),
            "background": background,
        })

    async def send_video(self, file_path: Path, delete_after_send: bool = True) -> None:
        task = BackgroundTask(file_path.unlink) if delete_after_send else None
        self.responses.append({
            "type": ResponseType.VIDEO,
            "filename": str(file_path),
            "background": task,
        })

    async def send_document(
        self,
        file_path: Path,
        caption: str,
        background: Optional[BackgroundTask] = None,
    ) -> None:
        self.responses.append({
            "type": ResponseType.DOCUMENT,
            "caption": caption,
            "filename": str(file_path),
            "background": background,
        })

    async def send_json(self, data: dict) -> None:
        self.responses.append({
            "type": ResponseType.JSON,
            "content": data,
        })

    def get_response(self):
        for item in self.responses:
            if item["type"] in {ResponseType.VIDEO, ResponseType.PHOTO, ResponseType.DOCUMENT}:
                media_type = {
                    ResponseType.VIDEO: "video/mp4",
                    ResponseType.PHOTO: "image/jpeg",
                    ResponseType.DOCUMENT: "application/octet-stream",
                }[item["type"]]
                return FileResponse(
                    path=item["filename"],
                    media_type=media_type,
                    filename=Path(item["filename"]).name,
                    background=item.get("background"),
                )

        for item in self.responses:
            if item["type"] == ResponseType.JSON:
                return JSONResponse(item["content"])

        return JSONResponse(self.responses)
