# security/__init__.py
# Security module — exposes all helpers for easy import.

from .input_validation import (
    sanitise_string,
    sanitise_text,
    validate_and_normalise_email,
    validate_url,
    validate_linkedin_url,
    validate_integer,
    validate_choice,
    sanitise_filename,
)
from .headers    import register_security_headers, EXTRA_SECURITY_HEADERS
from .csrf       import get_csrf_token, validate_csrf_token, csrf_exempt_api
from .rate_limiter import (
    LOGIN_LIMIT, REGISTER_LIMIT, UPLOAD_LIMIT,
    apply_login_limit, apply_register_limit, apply_upload_limit, apply_admin_limit,
)
from .logging    import (
    SecurityEvent,
    log_security_event,
    log_login_success,
    log_login_failure,
    log_rbac_denied,
    log_file_upload,
    log_file_rejected,
    log_admin_action,
)

__all__ = [
    # input_validation
    "sanitise_string", "sanitise_text",
    "validate_and_normalise_email", "validate_url",
    "validate_linkedin_url", "validate_integer",
    "validate_choice", "sanitise_filename",
    # headers
    "register_security_headers", "EXTRA_SECURITY_HEADERS",
    # csrf
    "get_csrf_token", "validate_csrf_token", "csrf_exempt_api",
    # rate_limiter
    "LOGIN_LIMIT", "REGISTER_LIMIT", "UPLOAD_LIMIT",
    "apply_login_limit", "apply_register_limit",
    "apply_upload_limit", "apply_admin_limit",
    # logging
    "SecurityEvent", "log_security_event",
    "log_login_success", "log_login_failure", "log_rbac_denied",
    "log_file_upload", "log_file_rejected", "log_admin_action",
]
