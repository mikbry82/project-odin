import logging
import os
from pathlib import Path


def configure_logging() -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    log_file = os.getenv("ODIN_LOG_FILE")
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=handlers,
    )
