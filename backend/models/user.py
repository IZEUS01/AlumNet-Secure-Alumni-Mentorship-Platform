"""
models/user.py
--------------
Base User model — single table shared by all roles via a role column.
Role-specific profile data lives in Student / Alumni / Admin tables
(one-to-one relationship with this table).

Security fields implemented:
    AUTH-01  — Unique email + username identifier
    AUTH-02  — password_hash only, never plaintext
    AUTH-04  — failed_login_attempts + lockout_until for brute-force lockout
    AUTH-05  — last_login tracked for session audit
    RBAC-01  — role stored server-side as DB enum (clients cannot change it)
    RBAC-06  — role validated only from this server-side value
    APP-06   — created_at / last_login for audit trail
"""

from datetime import datetime, timezone
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    # Primary key
    id = db.Column(db.Integer, primary_key=True)

    # Identity  (AUTH-01)
    email     = db.Column(db.String(254), unique=True, nullable=False, index=True)
    username  = db.Column(db.String(80),  unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(255), nullable=False)

    # Authentication  (AUTH-02 — hashed only, never plaintext)
    password_hash = db.Column(db.String(128), nullable=False)

    # RBAC role  (RBAC-01, RBAC-06) — server-side only, clients cannot change
    role = db.Column(
        db.Enum(
            "student",
            "unverified_alumni",
            "verified_alumni",
            "admin",
            name="user_roles",
        ),
        nullable=False,
        default="student",
    )

    # Account lockout  (AUTH-04, R10)
    failed_login_attempts = db.Column(db.Integer, default=0,  nullable=False)
    lockout_until         = db.Column(db.DateTime(timezone=True), nullable=True)

    # Lifecycle / audit  (APP-06)
    is_active  = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_login = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    student_profile  = db.relationship("Student",  back_populates="user",
                                       uselist=False, cascade="all, delete-orphan")
    alumni_profile   = db.relationship("Alumni",   back_populates="user",
                                       uselist=False, cascade="all, delete-orphan")
    admin_profile    = db.relationship("Admin",    back_populates="user",
                                       uselist=False, cascade="all, delete-orphan")
    audit_logs       = db.relationship("AuditLog", back_populates="user",
                                       cascade="all, delete-orphan")

    # Flask-Login
    def get_id(self) -> str:
        return str(self.id)

    # Role helpers
    def is_admin(self) -> bool:
        return self.role == "admin"

    def is_verified_alumni(self) -> bool:
        return self.role == "verified_alumni"

    def is_unverified_alumni(self) -> bool:
        return self.role == "unverified_alumni"

    def is_student(self) -> bool:
        return self.role == "student"

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role!r}>"
