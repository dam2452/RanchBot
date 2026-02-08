import json
from pathlib import Path
import shutil
from typing import (
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
    def __init__(self):
        self.__response: Optional[Union[FileResponse, JSONResponse]] = None

    async def send_text(self, text: str) -> None:
        self.__set_response(JSONResponse({"type": ResponseType.TEXT, "content": text}))

    async def send_markdown(self, text: str) -> None:
        self.__set_response(JSONResponse({"type": ResponseType.MARKDOWN, "content": text}))

    async def send_photo(
        self,
        image_bytes: bytes,
        image_path: Path,
        caption: str,
        background: Optional[BackgroundTask] = None,
    ) -> None:
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
    ) -> bool:
        background = BackgroundTask(file_path.unlink) if delete_after_send else None
        self.__set_response(
            FileResponse(
                path=str(file_path),
                media_type="video/mp4",
                filename=file_path.name,
                background=background,
            ),
        )
        return True

    async def send_document(
        self,
        file_path: Path,
        caption: str,
        delete_after_send: bool = True,
        cleanup_dir: Optional[Path] = None,
    ) -> None:
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

    async def send_json(self, data: json) -> None:
        self.__set_response(JSONResponse(data))

    def __set_response(self, response: Union[FileResponse, JSONResponse]) -> None:
        if self.__response is not None:
            raise RuntimeError("Response already set for this request")
        self.__response = response

    def get_response(self) -> Response:
        if self.__response is None:
            raise RuntimeError("No response has been set")
        return self.__response
