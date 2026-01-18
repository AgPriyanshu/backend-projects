import logging
import logging.config
from pathlib import Path
from typing import Optional

import yaml

# Load logging configuration from log_config.yaml
_config_path = Path(__file__).resolve().parent.parent / "log_config.yaml"

if _config_path.exists():
    with open(_config_path, "r") as f:
        _config = yaml.safe_load(f)
        logging.config.dictConfig(_config)


def get_logger(name: Optional[str] = "backend_projects") -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: The name of the logger. Typically __name__ of the calling module.
              If None, returns the root logger.

    Returns:
        A configured logging.Logger instance.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
        >>> logger.error("An error occurred", exc_info=True)
    """
    return logging.getLogger(name)


logger = get_logger()
