"""CTP Configuration Package.

Provides Pydantic schemas for Board.json, Card.json, and YAML configs.
"""

from ctp.config.exceptions import ConfigError
from ctp.config.loader import ConfigLoader


__all__ = ["ConfigError", "ConfigLoader"]