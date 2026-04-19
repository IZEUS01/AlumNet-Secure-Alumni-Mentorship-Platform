"""
models/user.py — Base User model
Adds account_status for admin approval gate.
"""

from datetime import datetime, timezone
from flask_login import UserMixin
from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id        = db.Column(db.Integer, primary_key=True)
    email     = db.Column(db.String(254), unique=True, nullable=False, index=True)
    username  = db.Column(db.String(80),  unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(255), nullable=False)

    # AUTH-02 — hashed only, never plaintext
    password_hash = db.Column(db.String(128), nullable=False)

    # RBAC-01, RBAC-06 — stored server-side, clients cannot change
    role = db.Column(
        db.Enum("student", "unverified_alumni", "verified_alumni", "admin",
                name="user_roles"),
        nullable=False, default="student",
    )

    # ✅ NEW: Admin approval gate
    # pending  → newly registered, cannot log in yet
    # approved → admin approved, login allowed
    # rejected → admin rejected, login blocked
    account_status = db.Column(
        db.Enum("pending", "approved", "rejected", name="account_statuses"),
        nullable=False, default="pending",
    )
    rejection_reason = db.Column(db.Text, nullable=True)  # set when rejected

    # AUTH-04 — account lockout
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    lockout_until         = db.Column(db.DateTime(timezone=True), nullable=True)

    email_verified = db.Column(db.Boolean, default=True, nullable=False)

    # APP-06 — audit
    is_active  = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc), nullable=False)
    last_login = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    student_profile = db.relationship("Student", back_populates="user",
                                      uselist=False, cascade="all, delete-orphan")
    alumni_profile  = db.relationship("Alumni",  back_populates="user",
                                      uselist=False, cascade="all, delete-orphan",
                                      foreign_keys="Alumni.user_id")
    admin_profile   = db.relationship("Admin",   back_populates="user",
                                      uselist=False, cascade="all, delete-orphan")
    audit_logs      = db.relationship("AuditLog", back_populates="user",
                                      cascade="all, delete-orphan")

    def get_id(self):             return str(self.id)
    def is_admin(self):           return self.role == "admin"
    def is_verified_alumni(self): return self.role == "verified_alumni"
    def is_student(self):         return self.role == "student"
    def is_approved(self):        return self.account_status == "approved"

    def __repr__(self):
        return f"<User id={self.id} username={self.username!r} role={self.role!r} status={self.account_status!r}>"
