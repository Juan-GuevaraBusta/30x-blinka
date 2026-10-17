"""HTTP API (T4.1). Importing this package does not read .env or open sockets."""

from app.api.app import create_app

__all__ = ["create_app"]
