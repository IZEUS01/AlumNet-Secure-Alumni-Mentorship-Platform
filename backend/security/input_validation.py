"""
security/input_validation.py
-----------------------------
Centralised input validation and sanitisation helpers.

Covers:
    APP-01  — All user inputs validated and sanitised server-side
    APP-02  — Output encoding to prevent XSS
    DATA-05 — No raw SQL; all DB interactions via ORM
    R02     — SQL injection prevention
    R03     — XSS prevention
"""

import re
import bleach
from email_validator import validate_email, EmailNotValidError


# ------------------------------------------------------------------ #
# Allowed HTML tags/attrs for bleach (used when HTML is permitted)
# For most fields we allow NO tags at all.
# ------------------------------------------------------------------ #

ALLOWED_TAGS: list[str]  = []          # Strip all HTML by default
ALLOWED_ATTRS: dict      = {}


# ------------------------------------------------------------------ #
# String sanitisation
# ------------------------------------------------------------------ #

def sanitise_string(value: str, max_length: int = 255) -> str:
    """
    Strip leading/trailing whitespace, enforce max length, and
    strip all HTML tags to prevent XSS (APP-02).
    """
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()[:max_length]
    return bleach.clean(value, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


def sanitise_text(value: str, max_length: int = 2000) -> str:
    """
    Like sanitise_string but for longer text fields (bio, message).
    Strips HTML, normalises whitespace.
    """
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()[:max_length]
    # Collapse multiple blank lines
    value = re.sub(r"\n{3,}", "\n\n", value)
    return bleach.clean(value, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


# ------------------------------------------------------------------ #
# Email validation
# ------------------------------------------------------------------ #

def validate_and_normalise_email(email: str) -> tuple[bool, str]:
    """
    Validate and normalise an email address.
    Returns (is_valid: bool, normalised_email_or_error: str).

    Uses email-validator for RFC 5322 compliance.
    Lowercases and strips whitespace (normalises).
    """
    if not email or not isinstance(email, str):
        return False, "Email is required."
    try:
        valid = validate_email(email.strip(), check_deliverability=False)
        return True, valid.normalized
    except EmailNotValidError as e:
        return False, str(e)


# ------------------------------------------------------------------ #
# URL validation
# ------------------------------------------------------------------ #

_URL_RE = re.compile(
    r"^https?://"                    # http:// or https://
    r"([\w\-]+\.)+[\w\-]{2,}"        # domain
    r"(:\d+)?"                       # optional port
    r"(/[\w\-._~:/?#\[\]@!$&'()*+,;=%]*)?$",  # optional path/query
    re.IGNORECASE,
)


def validate_url(url: str, require_https: bool = True) -> tuple[bool, str]:
    """
    Validate a URL string.
    Returns (is_valid, error_message_or_empty).
    """
    if not url:
        return True, ""   # Empty URLs are allowed (nullable fields)
    if not isinstance(url, str):
        return False, "URL must be a string."
    url = url.strip()
    if require_https and not url.startswith("https://"):
        return False, "URL must use HTTPS."
    if not _URL_RE.match(url):
        return False, "Invalid URL format."
    if len(url) > 500:
        return False, "URL is too long."
    return True, ""


def validate_linkedin_url(url: str) -> tuple[bool, str]:
    """Validate that a URL is a LinkedIn profile URL."""
    if not url:
        return True, ""
    url = url.strip()
    if not url.startswith("https://www.linkedin.com/in/"):
        return False, "Must be a valid LinkedIn profile URL (https://www.linkedin.com/in/...)."
    return validate_url(url)


# ------------------------------------------------------------------ #
# Integer range validation
# ------------------------------------------------------------------ #

def validate_integer(value, min_val: int = None, max_val: int = None,
                     field_name: str = "Value") -> tuple[bool, str]:
    """
    Validate that a value is an integer within an optional range.
    Returns (is_valid, error_message_or_empty).
    """
    try:
        n = int(value)
    except (TypeError, ValueError):
        return False, f"{field_name} must be a whole number."
    if min_val is not None and n < min_val:
        return False, f"{field_name} must be at least {min_val}."
    if max_val is not None and n > max_val:
        return False, f"{field_name} must be no more than {max_val}."
    return True, ""


# ------------------------------------------------------------------ #
# Enum / whitelist validation
# ------------------------------------------------------------------ #

def validate_choice(value: str, allowed: set, field_name: str = "Value") -> tuple[bool, str]:
    """
    Validate that a string value is one of an allowed set.
    Case-insensitive.
    """
    if not value or not isinstance(value, str):
        return False, f"{field_name} is required."
    if value.strip().lower() not in {a.lower() for a in allowed}:
        return False, f"{field_name} must be one of: {', '.join(sorted(allowed))}."
    return True, ""


# ------------------------------------------------------------------ #
# Filename sanitisation (for uploaded files)
# ------------------------------------------------------------------ #

_UNSAFE_FILENAME_RE = re.compile(r"[^\w\.\-]")


def sanitise_filename(filename: str) -> str:
    """
    Remove path components and non-safe characters from a filename.
    Prevents path-traversal attacks in file uploads (DATA-04).
    """
    if not filename:
        return "upload"
    # Strip directory components
    filename = filename.replace("\\", "/").split("/")[-1]
    # Remove unsafe characters
    filename = _UNSAFE_FILENAME_RE.sub("_", filename)
    # Prevent hidden files
    filename = filename.lstrip(".")
    return filename[:100] or "upload"
