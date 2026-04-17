"""
models/admin.py
---------------
Admin profile — one-to-one extension of the User table.
Tracks admin-specific metadata and the actions they perform.

Security notes:
    RBAC-05  — Admin accounts have elevated privileges; extra fields tracked
    APP-06   — All admin actions audited via AuditLog (separate table)
    DATA-01  — Admin profiles store only operational metadata, no extra PII
"""

from datetime import datetime, timezone
from app import db


class Admin(db.Model):
    __tablename__ = "admins"

    # ------------------------------------------------------------------ #
    # Primary key — mirrors User.id (one-to-one)
    # ------------------------------------------------------------------ #
    id      = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Operational metadata
    # ------------------------------------------------------------------ #
    department       = db.Column(db.String(120), nullable=True)    # e.g. "IT Department"
    employee_id      = db.Column(db.String(50),  nullable=True)    # Internal employee ID
    access_level     = db.Column(                                   # For future granularity
        db.Enum("super_admin", "moderator", name="admin_access_levels"),
        default="moderator",
        nullable=False,
    )

    # ------------------------------------------------------------------ #
    # Action summary counters (denormalised for dashboard performance)
    # ------------------------------------------------------------------ #
    alumni_verified_count  = db.Column(db.Integer, default=0, nullable=False)
    alumni_rejected_count  = db.Column(db.Integer, default=0, nullable=False)
    users_deactivated_count = db.Column(db.Integer, default=0, nullable=False)

    # ------------------------------------------------------------------ #
    # Audit
    # ------------------------------------------------------------------ #
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_action_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    user = db.relationship("User", back_populates="admin_profile")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def record_action(self) -> None:
        """Update the last_action_at timestamp."""
        self.last_action_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "id":                      self.id,
            "user_id":                 self.user_id,
            "full_name":               self.user.full_name,
            "email":                   self.user.email,
            "department":              self.department,
            "access_level":            self.access_level,
            "alumni_verified_count":   self.alumni_verified_count,
            "alumni_rejected_count":   self.alumni_rejected_count,
            "users_deactivated_count": self.users_deactivated_count,
            "last_action_at":          self.last_action_at.isoformat()
                                       if self.last_action_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"<Admin id={self.id} user_id={self.user_id} "
            f"level={self.access_level!r}>"
        )
