"""
models/audit_log.py
--------------------
AuditLog — immutable record of security-relevant actions.

Every admin action, login event, role change, and file operation
is stored here for forensic purposes.

Security notes:
    APP-06   — Security logs record auth attempts and suspicious activity
    Threat   — Repudiation: Immutable Logging + Comprehensive Telemetry
    RBAC-05  — Only admins can query audit logs
"""

from datetime import datetime, timezone
from app import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    # ------------------------------------------------------------------ #
    # Primary key
    # ------------------------------------------------------------------ #
    id = db.Column(db.Integer, primary_key=True)

    # ------------------------------------------------------------------ #
    # Actor — who triggered this event (nullable for pre-auth events)
    # ------------------------------------------------------------------ #
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Event classification
    # ------------------------------------------------------------------ #
    event_type = db.Column(db.String(80),  nullable=False, index=True)   # e.g. LOGIN_SUCCESS
    target_type = db.Column(db.String(80), nullable=True)                 # e.g. "user", "alumni"
    target_id   = db.Column(db.Integer,    nullable=True)                 # ID of affected record

    # ------------------------------------------------------------------ #
    # Request context
    # ------------------------------------------------------------------ #
    ip_address = db.Column(db.String(45),  nullable=True)    # IPv4 or IPv6
    user_agent = db.Column(db.String(300), nullable=True)
    endpoint   = db.Column(db.String(200), nullable=True)    # URL path

    # ------------------------------------------------------------------ #
    # Extra detail (JSON-serialisable string)
    # ------------------------------------------------------------------ #
    detail = db.Column(db.Text, nullable=True)   # e.g. '{"reason": "wrong password"}'

    # ------------------------------------------------------------------ #
    # Timestamp  (APP-06 — immutable once written)
    # ------------------------------------------------------------------ #
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    user = db.relationship("User", back_populates="audit_logs")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "user_id":     self.user_id,
            "event_type":  self.event_type,
            "target_type": self.target_type,
            "target_id":   self.target_id,
            "ip_address":  self.ip_address,
            "endpoint":    self.endpoint,
            "detail":      self.detail,
            "created_at":  self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} event={self.event_type!r} "
            f"user_id={self.user_id} at={self.created_at}>"
        )
