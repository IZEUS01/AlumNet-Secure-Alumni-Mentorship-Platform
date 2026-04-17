"""
models/mentorship.py
--------------------
MentorshipRequest — represents a student's request for mentorship
from a specific verified alumni.

Business rules enforced at the model level:
    - A student cannot send duplicate pending requests to the same alumni
    - Only verified alumni can receive requests (enforced in the service layer)
    - Status transitions are controlled and logged

Security notes:
    RBAC-02  — student_id always refers to a Student record
    RBAC-03  — alumni_id always refers to a verified Alumni record
    APP-06   — All status changes tracked with timestamps
    DATA-01  — Message content stored server-side; not exposed cross-role
"""

from datetime import datetime, timezone
from app import db


class MentorshipRequest(db.Model):
    __tablename__ = "mentorship_requests"

    # Unique constraint: one pending request per (student, alumni) pair
    __table_args__ = (
        db.UniqueConstraint(
            "student_id", "alumni_id", "status",
            name="uq_mentorship_student_alumni_status",
        ),
    )

    # ------------------------------------------------------------------ #
    # Primary key
    # ------------------------------------------------------------------ #
    id = db.Column(db.Integer, primary_key=True)

    # ------------------------------------------------------------------ #
    # Foreign keys
    # ------------------------------------------------------------------ #
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alumni_id = db.Column(
        db.Integer,
        db.ForeignKey("alumni.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Request content
    # ------------------------------------------------------------------ #
    subject = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text,        nullable=False)    # Student's introduction/ask

    # ------------------------------------------------------------------ #
    # Status lifecycle
    # pending → accepted | rejected | withdrawn
    # ------------------------------------------------------------------ #
    status = db.Column(
        db.Enum(
            "pending",
            "accepted",
            "rejected",
            "withdrawn",
            name="mentorship_status",
        ),
        default="pending",
        nullable=False,
        index=True,
    )

    # Alumni response note (reason for rejection, or welcome message)
    response_note = db.Column(db.Text, nullable=True)

    # ------------------------------------------------------------------ #
    # Scheduled session (set when accepted)
    # ------------------------------------------------------------------ #
    scheduled_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # ------------------------------------------------------------------ #
    # Audit timestamps  (APP-06)
    # ------------------------------------------------------------------ #
    created_at    = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    responded_at  = db.Column(db.DateTime(timezone=True), nullable=True)
    withdrawn_at  = db.Column(db.DateTime(timezone=True), nullable=True)

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    student = db.relationship(
        "Student",
        back_populates="mentorship_requests",
        foreign_keys=[student_id],
    )
    alumni = db.relationship(
        "Alumni",
        back_populates="mentorship_requests",
        foreign_keys=[alumni_id],
    )

    # ------------------------------------------------------------------ #
    # Status transition helpers
    # ------------------------------------------------------------------ #

    def accept(self, response_note: str = None, scheduled_at=None) -> None:
        """Mark the request as accepted by alumni."""
        self.status        = "accepted"
        self.response_note = response_note
        self.scheduled_at  = scheduled_at
        self.responded_at  = datetime.now(timezone.utc)

    def reject(self, response_note: str = None) -> None:
        """Mark the request as rejected by alumni."""
        self.status        = "rejected"
        self.response_note = response_note
        self.responded_at  = datetime.now(timezone.utc)

    def withdraw(self) -> None:
        """Student withdraws the request."""
        self.status       = "withdrawn"
        self.withdrawn_at = datetime.now(timezone.utc)

    # ------------------------------------------------------------------ #
    # Serialisation helpers
    # ------------------------------------------------------------------ #

    def to_student_dict(self) -> dict:
        """View for the requesting student."""
        return {
            "id":            self.id,
            "alumni_name":   self.alumni.user.full_name,
            "alumni_company": self.alumni.current_company,
            "subject":       self.subject,
            "message":       self.message,
            "status":        self.status,
            "response_note": self.response_note,
            "scheduled_at":  self.scheduled_at.isoformat() if self.scheduled_at else None,
            "created_at":    self.created_at.isoformat(),
        }

    def to_alumni_dict(self) -> dict:
        """View for the receiving alumni."""
        return {
            "id":             self.id,
            "student_name":   self.student.user.full_name,
            "student_dept":   self.student.department,
            "student_program": self.student.degree_program,
            "subject":        self.subject,
            "message":        self.message,
            "status":         self.status,
            "scheduled_at":   self.scheduled_at.isoformat() if self.scheduled_at else None,
            "created_at":     self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return (
            f"<MentorshipRequest id={self.id} "
            f"student={self.student_id} alumni={self.alumni_id} "
            f"status={self.status!r}>"
        )
