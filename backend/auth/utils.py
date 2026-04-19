"""
auth/utils.py
-------------
Low-level security utilities for the auth module.

Covers:
    AUTH-02  — Secure password hashing (bcrypt)
    AUTH-03  — Password complexity enforcement
    AUTH-05  — Secure session token generation
    AUTH-04  — Account lockout helpers
"""

import re
import secrets
import string
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
from flask import current_app


# ------------------------------------------------------------------ #
# Password hashing  (AUTH-02)
# ------------------------------------------------------------------ #

def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password with bcrypt.
    bcrypt automatically salts — never store plaintext passwords.

    Returns the hashed password as a UTF-8 string for DB storage.
    """
    password_bytes = plain_password.encode("utf-8")
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Constant-time comparison of a plaintext password against its hash.
    Returns True if the password matches, False otherwise.
    Raises ValueError if arguments are empty/None.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# ------------------------------------------------------------------ #
# Password complexity  (AUTH-03)
# ------------------------------------------------------------------ #

def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    Enforce AlumNet password policy.

    Returns (is_valid: bool, errors: list[str])
    Policy comes from app config so it can be tightened without code changes.
    """
    errors: list[str] = []

    min_len = current_app.config.get("PASSWORD_MIN_LENGTH", 8)
    req_upper = current_app.config.get("PASSWORD_REQUIRE_UPPERCASE", True)
    req_digit = current_app.config.get("PASSWORD_REQUIRE_DIGIT", True)
    req_special = current_app.config.get("PASSWORD_REQUIRE_SPECIAL", True)

    if len(password) < min_len:
        errors.append(f"Password must be at least {min_len} characters long.")

    if req_upper and not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter.")

    if req_digit and not re.search(r"\d", password):
        errors.append("Password must contain at least one digit.")

    if req_special and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain at least one special character.")

    return (len(errors) == 0), errors


# ------------------------------------------------------------------ #
# Secure token generation  (AUTH-05)
# ------------------------------------------------------------------ #

def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure URL-safe token.
    Used for password-reset links, email verification, etc.
    """
    return secrets.token_urlsafe(length)


def generate_session_id() -> str:
    """Generate a secure random session identifier."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(64))


# ------------------------------------------------------------------ #
# Account lockout  (AUTH-04)
# ------------------------------------------------------------------ #

def is_account_locked(failed_attempts: int, lockout_until: Optional[datetime]) -> bool:
    """
    Return True if the account is currently locked.

    Lockout is active when:
      - failed_attempts >= MAX_LOGIN_ATTEMPTS AND
      - lockout_until is in the future
    """
    max_attempts = current_app.config.get("MAX_LOGIN_ATTEMPTS", 5)

    if failed_attempts < max_attempts:
        return False

    if lockout_until is None:
        return False

    now = datetime.now(timezone.utc)
    # Make lockout_until timezone-aware if it isn't already
    if lockout_until.tzinfo is None:
        lockout_until = lockout_until.replace(tzinfo=timezone.utc)

    return now < lockout_until


def calculate_lockout_until() -> datetime:
    """
    Return the datetime until which an account should be locked
    after exceeding MAX_LOGIN_ATTEMPTS.
    """
    duration = current_app.config.get("LOCKOUT_DURATION_MINUTES", 15)
    return datetime.now(timezone.utc) + timedelta(minutes=duration)


def get_lockout_remaining_seconds(lockout_until: Optional[datetime]) -> int:
    """Return seconds remaining in a lockout, or 0 if not locked."""
    if lockout_until is None:
        return 0
    now = datetime.now(timezone.utc)
    if lockout_until.tzinfo is None:
        lockout_until = lockout_until.replace(tzinfo=timezone.utc)
    remaining = (lockout_until - now).total_seconds()
    return max(0, int(remaining))


# ------------------------------------------------------------------ #
# Email sanitisation helper
# ------------------------------------------------------------------ #

def normalise_email(email: str) -> str:
    """Lowercase and strip whitespace from email addresses."""
    return email.strip().lower()

# ------------------------------------------------------------------ #
# OTP generation  (AUTH-EMAIL)
# ------------------------------------------------------------------ #

import random
from datetime import timedelta

def generate_otp(length: int = 6) -> str:
    """
    Generate a cryptographically-seeded numeric OTP.
    Uses secrets.randbelow for uniform distribution — NOT random.randint.
    """
    import secrets
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(length))


def get_otp_expiry() -> "datetime":
    """Return the OTP expiry datetime based on config."""
    from flask import current_app
    minutes = current_app.config.get("OTP_EXPIRY_MINUTES", 10)
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)
