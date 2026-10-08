from __future__ import annotations

import logging
import sys
import re

SENSITIVE_PATTERNS = [
    re.compile(r'(token\s*[:=]\s*)[^\s,]+', re.IGNORECASE),
    re.compile(r'(api[_-]?key\s*[:=]\s*)[^\s,]+', re.IGNORECASE),
    re.compile(r'(password\s*[:=]\s*)[^\s,]+', re.IGNORECASE),
    re.compile(r'(bearer\s+)[a-zA-Z0-9_\-\.]+', re.IGNORECASE),
]


class SanitizingFormatter(logging.Formatter):
    """Logging formatter that masks sensitive data such as API keys and bot tokens."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        sanitized = original
        for pattern in SENSITIVE_PATTERNS:
            sanitized = pattern.sub(r'\1[REDACTED]', sanitized)
        return sanitized


def setup_logger(name: str = "lockin", log_level: str = "INFO") -> logging.Logger:
    """Configures and returns a structured logger."""
    logger = logging.getLogger(name)
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        fmt = "[%(asctime)s] [%(levelname)s] [%(name)s:%(module)s] %(message)s"
        formatter = SanitizingFormatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
