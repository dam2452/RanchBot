import logging
from typing import List


class ErrorHandlingLogger:
    class LoggerNotFinalizedException(Exception):
        def __init__(self):
            super().__init__("Logger destroyed without finalize() being called.")


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
                self.__logger.error("Logged errors:")
                for error in self.__errors:
                    self.__logger.error(f"- {error}")
            raise self.LoggerNotFinalizedException

    def __setup_logger(self, level: int) -> None:
        logging.basicConfig(
            format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            level=level,
        )
        self.__logger: logging.Logger = logging.getLogger(self.__class_name)

    def log(self, level: int, message: str) -> None:
        if level == logging.ERROR:
            self.__logger.error(message)
        elif level == logging.INFO:
            self.__logger.info(message)
        else:
            raise RuntimeError(f"Logging level {level} is not supported.")

    def info(self, message: str) -> None:
        self.__logger.info(message)

    def error(self, message: str) -> None:
        self.__logger.error(message)
        self.__errors.append(message)

    def warning(self, message: str) -> None:
        self.__logger.warning(message)

    def finalize(self) -> int:
        self.__is_finalized = True
        if self.__errors:
            self.__logger.error(f"Processing for '{self.__class_name}' completed with errors:")
            for error in self.__errors:
                self.__logger.error(f"- {error}")
            return self.__error_exit_code
        self.__logger.info(f"Processing for '{self.__class_name}' completed successfully.")
        return 0
