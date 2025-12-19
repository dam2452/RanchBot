import logging
import sys
from typing import List

from rich.logging import RichHandler
from rich.panel import Panel

from preprocessor.utils.console import console


class LoggerNotFinalizedException(Exception):
    def __init__(self):
        super().__init__("Logger destroyed without finalize() being called.")


class ErrorHandlingLogger:
    def __init__(self, class_name: str, loglevel: int, error_exit_code: int) -> None:
        self.__class_name: str = class_name
        self.__error_exit_code: int = error_exit_code
        self.__errors: List[str] = []
        self.__is_finalized: bool = False

        self.__setup_logger(loglevel)

    def __del__(self) -> None:
        if not self.__is_finalized:
            self.__logger.error(
                f"ErrorHandlingLogger for '{self.__class_name}' destroyed without finalize().",
            )
            if self.__errors:
                self.__logger.error("Logged errors:")
                for error in self.__errors:
                    self.__logger.error(f"- {error}")
            raise LoggerNotFinalizedException

    def __setup_logger(self, level: int) -> None:
        logging.basicConfig(
            level=level,
            format="%(message)s",
            stream=sys.stderr,
            handlers=[
                RichHandler(
                    console=console,
                    rich_tracebacks=True,
                    show_time=True,
                    show_path=False,
                ),
            ],
            force=True,
        )
        self.__logger: logging.Logger = logging.getLogger(self.__class_name)

    def log(self, level: int, message: str) -> None:
        if level == logging.ERROR:
            self.__logger.error(message)
        elif level == logging.INFO:
            self.__logger.info(message)
        elif level == logging.WARNING:
            self.__logger.warning(message)
        elif level == logging.DEBUG:
            self.__logger.debug(message)
        else:
            raise RuntimeError(f"Logging level {level} is not supported.")

    def info(self, message: str) -> None:
        self.__logger.info(message)

    def error(self, message: str) -> None:
        self.__logger.error(message)
        self.__errors.append(message)

    def warning(self, message: str) -> None:
        self.__logger.warning(message)

    def debug(self, message: str) -> None:
        self.__logger.debug(message)

    def finalize(self) -> int:
        self.__is_finalized = True
        if self.__errors:
            console.print(
                Panel(
                    f"[bold red]Processing for '{self.__class_name}' completed with {len(self.__errors)} error(s)[/bold red]",
                    title="Errors Occurred",
                    border_style="red",
                ),
            )
            return self.__error_exit_code

        console.print(
            Panel(
                f"[bold green]Processing for '{self.__class_name}' completed successfully[/bold green]",
                title="Success",
                border_style="green",
            ),
        )
        return 0
