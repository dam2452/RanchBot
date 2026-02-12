import logging
from typing import List

from rich.logging import RichHandler
from rich.panel import Panel

from preprocessor.services.ui.console import console


class LoggerNotFinalizedException(Exception):

    def __init__(self) -> None:
        super().__init__('Logger destroyed without finalize() being called.')

class ErrorHandlingLogger:
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    def __init__(self, class_name: str, loglevel: int, error_exit_code: int) -> None:
        self.__class_name: str = class_name
        self.__error_exit_code: int = error_exit_code
        self.__errors: List[str] = []
        self.__is_finalized: bool = False
        self.__setup_logger(loglevel)

    def __del__(self) -> None:
        if not self.__is_finalized:
            self.__logger.error(f"ErrorHandlingLogger for '{self.__class_name}' destroyed without finalize().")
            if self.__errors:
                self.__logger.error('Logged errors:')
                for error in self.__errors:
                    self.__logger.error(f'- {error}')
            raise LoggerNotFinalizedException

    def debug(self, message: str) -> None:
        self.__logger.debug(message)

    def error(self, message: str) -> None:
        self.__logger.error(message)
        self.__errors.append(message)

    def finalize(self) -> int:
        self.__is_finalized = True
        if self.__errors:
            console.print(
                Panel(
                    f"[bold red]Processing for '{self.__class_name}' "
                    f"completed with {len(self.__errors)} error(s)[/bold red]",
                    title='Errors Occurred',
                    border_style='red',
                ),
            )
            return self.__error_exit_code
        console.print(
            Panel(
                f"[bold green]Processing for '{self.__class_name}' "
                "completed successfully[/bold green]",
                title='Success',
                border_style='green',
            ),
        )
        return 0

    def info(self, message: str) -> None:
        self.__logger.info(message)

    def warning(self, message: str) -> None:
        self.__logger.warning(message)

    def __setup_logger(self, level: int) -> None:
        logging.basicConfig(
            level=level,
            format='%(message)s',
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
