import logging
import sys
from pathlib import Path
from typing import Optional


LOG_FORMAT = "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    verbose: bool = False
) -> None:
    """Настроить логирование."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=log_level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=handlers,
        force=True
    )
    
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)


def get_logger(name: str) -> logging.Logger:
    """Получить логгер."""
    return logging.getLogger(name)
