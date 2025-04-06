from pathlib import Path

from fastapi.responses import (
    FileResponse,
    JSONResponse,
)

from bot.interfaces.responder import AbstractResponder


class RestResponder(AbstractResponder):
    def __init__(self):
        self.responses = []
        self._response_given = False

    async def send_text(self, text: str):
        if self._response_given:
            return
        self.responses.append({
            "type": "text",
            "content": text,
        })
        self._response_given = True

    async def send_markdown(self, text: str):
        if self._response_given:
            return
        self.responses.append({
            "type": "markdown",
            "content": text,
        })
        self._response_given = True

    async def send_photo(self, image_bytes: bytes, image_path: Path, caption: str):
        if self._response_given:
            return
        self.responses.append({
            "type": "photo",
            "caption": caption,
            "filename": str(image_path),
        })
        self._response_given = True

    async def send_video(self, file_path: Path):
        if self._response_given:
            return
        self.responses.append({
            "type": "video",
            "filename": str(file_path),
        })
        self._response_given = True

    async def send_document(self, file_path: Path, caption: str):
        if self._response_given:
            return
        self.responses.append({
            "type": "document",
            "caption": caption,
            "filename": str(file_path),
        })
        self._response_given = True

    def get_response(self):
        for item in self.responses:
            if item["type"] == "video":
                return FileResponse(
                    path=item["filename"],
                    media_type="video/mp4",
                    filename=Path(item["filename"]).name,
                )
            if item["type"] == "photo":
                return FileResponse(
                    path=item["filename"],
                    media_type="image/jpeg",
                    filename=Path(item["filename"]).name,
                )
            if item["type"] == "document":
                return FileResponse(
                    path=item["filename"],
                    media_type="application/octet-stream",
                    filename=Path(item["filename"]).name,
                )
        return JSONResponse(self.responses)
