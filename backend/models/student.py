"""
models/student.py
-----------------
Student profile — one-to-one extension of the User table.
Stores academic information relevant to mentorship matching.

Security notes:
    DATA-01  — Only stores non-sensitive academic data (no PII beyond what User holds)
    RBAC-02  — Profile only created/read for users with role='student'
    APP-06   — created_at for audit trail
"""

from datetime import datetime, timezone
from extensions import db


class Student(db.Model):
    __tablename__ = "students"

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
    # Academic information
    # ------------------------------------------------------------------ #
    department     = db.Column(db.String(120), nullable=False)
    degree_program = db.Column(db.String(120), nullable=False)   # e.g. BS Computer Science
    graduation_year = db.Column(db.Integer, nullable=True)        # expected graduation year
    current_semester = db.Column(db.Integer, nullable=True)       # 1–8

    # ------------------------------------------------------------------ #
    # Mentorship preferences (used to match with alumni)
    # ------------------------------------------------------------------ #
    # Comma-separated areas of interest — e.g. "Machine Learning,Web Dev"
    interests      = db.Column(db.Text, nullable=True)
    bio            = db.Column(db.Text, nullable=True)            # Short self-introduction

    # ------------------------------------------------------------------ #
    # Privacy setting — controls whether profile is visible to alumni
    # (DATA-01 — restrict unnecessary PII exposure)
    # ------------------------------------------------------------------ #
    profile_visible = db.Column(db.Boolean, default=True, nullable=False)

    # ------------------------------------------------------------------ #
    # Audit
    # ------------------------------------------------------------------ #
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    user = db.relationship("User", back_populates="student_profile")

    mentorship_requests = db.relationship(
        "MentorshipRequest",
        back_populates="student",
        cascade="all, delete-orphan",
        foreign_keys="MentorshipRequest.student_id",
    )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def get_interests_list(self) -> list[str]:
        """Return interests as a Python list."""
        if not self.interests:
            return []
        return [i.strip() for i in self.interests.split(",") if i.strip()]

    def set_interests_list(self, interests: list[str]) -> None:
        """Store a list of interests as a comma-separated string."""
        self.interests = ", ".join(interests)

    def to_public_dict(self) -> dict:
        """
        Safe serialisation for display to alumni.
        Excludes any PII not needed for mentorship matching.
        """
        return {
            "id":               self.id,
            "full_name":        self.user.full_name,
            "department":       self.department,
            "degree_program":   self.degree_program,
            "current_semester": self.current_semester,
            "interests":        self.get_interests_list(),
            "bio":              self.bio,
        }

    def __repr__(self) -> str:
        return f"<Student id={self.id} user_id={self.user_id}>"
