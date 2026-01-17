"""Common dependencies and services."""

from app.core.services.log import get_log_service

# Singleton logger
logger = get_log_service()
