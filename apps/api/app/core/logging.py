"""Configuration du logging structuré et sécurisé de l'API Life Pilot.

Règles de sécurité obligatoires : ne jamais journaliser de secrets, tokens,
contenus complets d'emails, contenus complets de documents, ni IBAN non masqués.
"""

from __future__ import annotations

import contextvars
import json
import logging
import re
import sys
import uuid
from collections.abc import Mapping, MutableMapping
from datetime import UTC, datetime
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

CORRELATION_ID_HEADER = "X-Correlation-ID"
DEFAULT_LOG_LEVEL = "INFO"
REDACTED_VALUE = "[REDACTED]"
MASKED_IBAN_VALUE = "[IBAN_MASKED]"

# Interdit explicitement les logs de secrets/tokens et autres champs sensibles.
SENSITIVE_FIELD_PATTERNS = (
    "secret",
    "token",
    "password",
    "passwd",
    "authorization",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "credential",
    "cookie",
    "session",
)
SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"(?i)(secret|token|password|api[_-]?key)=([^\s&]+)"),
)
IBAN_PATTERN = re.compile(r"\b[A-Z]{2}\d{2}(?:[\s-]?[A-Z0-9]){11,30}\b")
DOCUMENT_OR_EMAIL_CONTENT_FIELDS = frozenset(
    {
        "email_body",
        "email_content",
        "email_html",
        "email_text",
        "body",
        "html_body",
        "document_content",
        "document_text",
        "document_body",
        "ocr_text",
        "raw_document",
        "raw_email",
        "full_content",
        "content",
    }
)
ALLOWED_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}

correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id",
    default=None,
)


def get_correlation_id() -> str | None:
    """Retourne le correlation id attaché au contexte courant."""

    return correlation_id_var.get()


def set_correlation_id(correlation_id: str | None) -> contextvars.Token[str | None]:
    """Attache un correlation id au contexte courant."""

    return correlation_id_var.set(correlation_id)


def reset_correlation_id(token: contextvars.Token[str | None]) -> None:
    """Restaure le contexte de correlation id précédent."""

    correlation_id_var.reset(token)


def _is_sensitive_field(field_name: str) -> bool:
    normalized = field_name.lower().replace("-", "_")
    return (
        normalized in DOCUMENT_OR_EMAIL_CONTENT_FIELDS
        or any(pattern in normalized for pattern in SENSITIVE_FIELD_PATTERNS)
    )


def mask_iban(value: str) -> str:
    """Masque tout IBAN détecté afin d'interdire les IBAN non masqués dans les logs."""

    return IBAN_PATTERN.sub(MASKED_IBAN_VALUE, value)


def mask_sensitive_data(value: Any) -> Any:
    """Nettoie une valeur avant journalisation.

    Cette fonction interdit explicitement la sortie de secrets, tokens, contenus
    complets d'emails/documents et IBAN non masqués dans les journaux.
    """

    if isinstance(value, Mapping):
        sanitized: MutableMapping[str, Any] = {}
        for key, item in value.items():
            key_as_string = str(key)
            sanitized[key_as_string] = (
                REDACTED_VALUE
                if _is_sensitive_field(key_as_string)
                else mask_sensitive_data(item)
            )
        return sanitized

    if isinstance(value, list | tuple | set | frozenset):
        return [mask_sensitive_data(item) for item in value]

    if isinstance(value, str):
        sanitized_value = mask_iban(value)
        for pattern in SENSITIVE_VALUE_PATTERNS:
            sanitized_value = pattern.sub(
                _redact_sensitive_value_match,
                sanitized_value,
            )
        return sanitized_value

    return value


def _redact_sensitive_value_match(match: re.Match[str]) -> str:
    if match.lastindex and match.lastindex > 1:
        return f"{match.group(1)}={REDACTED_VALUE}"
    return REDACTED_VALUE


class SensitiveDataFilter(logging.Filter):
    """Filtre qui masque les données sensibles sur chaque LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = mask_sensitive_data(record.msg)
        if isinstance(record.args, Mapping):
            record.args = mask_sensitive_data(record.args)
        elif record.args:
            record.args = tuple(mask_sensitive_data(arg) for arg in record.args)

        for key, value in list(record.__dict__.items()):
            if key.startswith("_") or key in {"msg", "args", "exc_info", "exc_text"}:
                continue
            if _is_sensitive_field(key):
                setattr(record, key, REDACTED_VALUE)
            else:
                setattr(record, key, mask_sensitive_data(value))
        return True


class JsonFormatter(logging.Formatter):
    """Formateur JSON pour des logs structurés et corrélables."""

    RESERVED_ATTRS = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key not in self.RESERVED_ATTRS and not key.startswith("_"):
                payload[key] = value

        return json.dumps(mask_sensitive_data(payload), ensure_ascii=False, default=str)


def _normalize_log_level(log_level: str | None, environment: str) -> str:
    if log_level:
        candidate = log_level.upper()
    elif environment.lower() in {"local", "development", "dev", "test"}:
        candidate = "DEBUG"
    else:
        candidate = DEFAULT_LOG_LEVEL
    return candidate if candidate in ALLOWED_LOG_LEVELS else DEFAULT_LOG_LEVEL


def configure_logging(log_level: str | None = None, environment: str = "local") -> None:
    """Configure les logs structurés avec un niveau piloté par l'environnement."""

    level = _normalize_log_level(log_level, environment)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(SensitiveDataFilter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(level)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Ajoute un correlation id à chaque requête et à chaque ligne de log."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())
        token = set_correlation_id(correlation_id)
        try:
            response = await call_next(request)
            response.headers[CORRELATION_ID_HEADER] = correlation_id
            return response
        finally:
            reset_correlation_id(token)


def log_connector_error(
    connector_name: str,
    operation: str,
    error: Exception,
    **context: Any,
) -> None:
    """Journalise une erreur de connecteur sans exposer de données sensibles."""

    logging.getLogger("lifepilot.connectors").error(
        "connector_error",
        extra={
            "event": "connector_error",
            "connector": connector_name,
            "operation": operation,
            "error_type": type(error).__name__,
            "context": mask_sensitive_data(context),
        },
        exc_info=error,
    )


def log_import_job(event: str, job_name: str, **context: Any) -> None:
    """Journalise les jobs d'import avec un payload structuré."""

    logging.getLogger("lifepilot.import_jobs").info(
        event,
        extra={
            "event": event,
            "job": job_name,
            "context": mask_sensitive_data(context),
        },
    )


def log_n8n_workflow(event: str, workflow_name: str, **context: Any) -> None:
    """Journalise les workflows déclenchés par n8n."""

    logging.getLogger("lifepilot.n8n").info(
        event,
        extra={
            "event": event,
            "workflow": workflow_name,
            "context": mask_sensitive_data(context),
        },
    )
