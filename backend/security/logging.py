"""
security/logging.py
--------------------
Structured security event logging.

All security-relevant events (logins, role changes, file uploads,
admin actions) are routed through log_security_event() so they land
in a consistent, searchable format in the application log.

Covers:
    APP-06  — Security logs record auth attempts and suspicious activity
    Threat  — Repudiation: Comprehensive Telemetry section
"""

from datetime import datetime, timezone
from flask import request, has_request_context
from flask import current_app


# ------------------------------------------------------------------ #
# Event type constants
# ------------------------------------------------------------------ #

class SecurityEvent:
    # Authentication
    LOGIN_SUCCESS         = "LOGIN_SUCCESS"
    LOGIN_FAIL            = "LOGIN_FAIL"
    LOGIN_LOCKED          = "LOGIN_LOCKED"
    LOGIN_UNKNOWN_EMAIL   = "LOGIN_UNKNOWN_EMAIL"
    LOGOUT                = "LOGOUT"
    REGISTER_SUCCESS      = "REGISTER_SUCCESS"
    PASSWORD_CHANGE       = "PASSWORD_CHANGE"

    # Access control
    RBAC_DENIED           = "RBAC_DENIED"
    ADMIN_ACCESS          = "ADMIN_ACCESS"
    ADMIN_ACCESS_DENIED   = "ADMIN_ACCESS_DENIED"

    # Verification
    ALUMNI_VERIFIED       = "ALUMNI_VERIFIED"
    ALUMNI_REJECTED       = "ALUMNI_REJECTED"

    # File operations
    FILE_UPLOAD_SUCCESS   = "FILE_UPLOAD_SUCCESS"
    FILE_UPLOAD_REJECTED  = "FILE_UPLOAD_REJECTED"

    # User management
    USER_DEACTIVATED      = "USER_DEACTIVATED"

    # Suspicious activity
    CSRF_FAILURE          = "CSRF_FAILURE"
    RATE_LIMIT_HIT        = "RATE_LIMIT_HIT"
    INVALID_INPUT         = "INVALID_INPUT"


# ------------------------------------------------------------------ #
# Core logging function
# ------------------------------------------------------------------ #

def log_security_event(
    event: str,
    user_id: int | None = None,
    extra: dict | None = None,
    level: str = "info",
) -> None:
    """
    Emit a structured security event log entry.

    All fields are written as key=value pairs so logs can be parsed
    by SIEM tools (Splunk, ELK, etc.) — Threat Model: Immutable Logging.

    Args:
        event:   One of the SecurityEvent constants.
        user_id: The acting user's ID (None for pre-auth events).
        extra:   Additional context dict (e.g. {"target_user_id": 5}).
        level:   "info" | "warning" | "critical"
    """
    ip   = request.remote_addr if has_request_context() else "N/A"
    path = request.path        if has_request_context() else "N/A"
    method = request.method    if has_request_context() else "N/A"
    ts   = datetime.now(timezone.utc).isoformat()

    parts = [
        f"SECURITY_EVENT={event}",
        f"ts={ts}",
        f"user_id={user_id}",
        f"ip={ip}",
        f"method={method}",
        f"path={path}",
    ]

    if extra:
        for k, v in extra.items():
            parts.append(f"{k}={v}")

    message = " ".join(parts)

    logger = current_app.logger
    if level == "warning":
        logger.warning(message)
    elif level == "critical":
        logger.critical(message)
    else:
        logger.info(message)


# ------------------------------------------------------------------ #
# Convenience wrappers
# ------------------------------------------------------------------ #

def log_login_success(user_id: int) -> None:
    log_security_event(SecurityEvent.LOGIN_SUCCESS, user_id=user_id)


def log_login_failure(email: str, attempts: int) -> None:
    log_security_event(
        SecurityEvent.LOGIN_FAIL,
        extra={"email": email, "attempts": attempts},
        level="warning",
    )


def log_rbac_denied(user_id: int, required_roles: tuple) -> None:
    log_security_event(
        SecurityEvent.RBAC_DENIED,
        user_id=user_id,
        extra={"required_roles": str(required_roles)},
        level="warning",
    )


def log_file_upload(user_id: int, filename: str, mime: str, size: int) -> None:
    log_security_event(
        SecurityEvent.FILE_UPLOAD_SUCCESS,
        user_id=user_id,
        extra={"filename": filename, "mime": mime, "size_bytes": size},
    )


def log_file_rejected(user_id: int, filename: str, reason: str) -> None:
    log_security_event(
        SecurityEvent.FILE_UPLOAD_REJECTED,
        user_id=user_id,
        extra={"filename": filename, "reason": reason},
        level="warning",
    )


def log_admin_action(admin_id: int, action: str, target_id: int = None) -> None:
    log_security_event(
        action,
        user_id=admin_id,
        extra={"target_id": target_id},
    )
