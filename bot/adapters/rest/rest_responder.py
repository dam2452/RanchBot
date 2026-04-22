from pathlib import Path
import shutil
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from fastapi.responses import (
    FileResponse,
    JSONResponse,
    Response,
)
from starlette.background import BackgroundTask

from bot.adapters.rest.response_type import ResponseType
from bot.interfaces.responder import AbstractResponder


class RestResponder(AbstractResponder):
    def __init__(self, prefer_json: bool = True):
        self.__response: Optional[Union[FileResponse, JSONResponse]] = None
        self.__prefer_json = prefer_json
        self.__notices: List[Dict[str, str]] = []

    async def send_text(self, text: str) -> None:
        if self.__prefer_json:
            self.__notices.append({"type": ResponseType.TEXT, "content": text})
            return
        self.__set_response(JSONResponse({"type": ResponseType.TEXT, "content": text}))

    async def send_markdown(self, text: str) -> None:
        if self.__prefer_json:
            self.__notices.append({"type": ResponseType.MARKDOWN, "content": text})
            return
        self.__set_response(JSONResponse({"type": ResponseType.MARKDOWN, "content": text}))

    async def send_photo(
        self,
        image_bytes: bytes,
        image_path: Path,
        caption: str,
        background: Optional[BackgroundTask] = None,
    ) -> None:
        if self.__prefer_json:
            payload: Dict[str, object] = {
                "type": "photo",
                "filename": image_path.name,
                "caption": caption,
                "size_bytes": len(image_bytes),
            }
            if self.__notices:
                payload["notices"] = self.__notices
            self.__set_response(JSONResponse(payload))
            return
        self.__set_response(
            FileResponse(
                path=str(image_path),
                media_type="image/jpeg",
                filename=image_path.name,
                background=background,
            ),
        )

    async def send_video(
        self,
        file_path: Path,
        delete_after_send: bool = True,
        width: Optional[int] = None,
        height: Optional[int] = None,
        duration: Optional[float] = None,
        suggestions: Optional[List[str]] = None,
    ) -> None:
        if self.__prefer_json:
            payload: Dict[str, object] = {
                "type": "video",
                "filename": file_path.name,
                "media_type": "video/mp4",
                "duration": duration,
                "suggestions": suggestions or [],
            }
            if file_path.exists():
                payload["size_bytes"] = file_path.stat().st_size
            if self.__notices:
                payload["notices"] = self.__notices

            if delete_after_send and file_path.exists():
                file_path.unlink()

            self.__set_response(JSONResponse(payload))
            return

        background = BackgroundTask(file_path.unlink) if delete_after_send else None
        self.__set_response(
            FileResponse(
                path=str(file_path),
                media_type="video/mp4",
                filename=file_path.name,
                background=background,
            ),
        )

    async def send_document(
        self,
        file_path: Path,
        caption: str,
        delete_after_send: bool = True,
        cleanup_dir: Optional[Path] = None,
    ) -> None:
        if self.__prefer_json:
            payload: Dict[str, object] = {
                "type": "document",
                "filename": file_path.name,
                "caption": caption,
                "media_type": "application/octet-stream",
            }
            if file_path.exists():
                payload["size_bytes"] = file_path.stat().st_size
                try:
                    payload["content"] = file_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    payload["content"] = None
            else:
                payload["size_bytes"] = 0
                payload["content"] = None

            if self.__notices:
                payload["notices"] = self.__notices

            if cleanup_dir:
                shutil.rmtree(cleanup_dir, ignore_errors=True)
            elif delete_after_send and file_path.exists():
                file_path.unlink()

            self.__set_response(JSONResponse(payload))
            return

        background = None
        if cleanup_dir:
            background = BackgroundTask(shutil.rmtree, cleanup_dir, ignore_errors=True)
        elif delete_after_send:
            background = BackgroundTask(file_path.unlink)

        self.__set_response(
            FileResponse(
                path=str(file_path),
                media_type="application/octet-stream",
                filename=file_path.name,
                background=background,
            ),
        )

    async def send_json(self, data: Any) -> None:
        if self.__notices and isinstance(data, dict):
            data = {**data, "notices": self.__notices}
        self.__set_response(JSONResponse(data))

    def __set_response(self, response: Union[FileResponse, JSONResponse]) -> None:
        if self.__response is not None:
            raise RuntimeError("Response already set for this request")
        self.__response = response

    def get_response(self) -> Response:
        if self.__response is None and self.__notices:
            if len(self.__notices) == 1:
                return JSONResponse(self.__notices[0])
            return JSONResponse({"type": "messages", "messages": self.__notices})
        if self.__response is None:
            raise RuntimeError("No response has been set")
        return self.__response
