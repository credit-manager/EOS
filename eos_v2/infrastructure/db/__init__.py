"""Database infrastructure boundary.

Domain code must not import ORM/session implementation details from here.
"""

from .session import Database, DatabaseConfig

__all__ = ["Database", "DatabaseConfig"]
