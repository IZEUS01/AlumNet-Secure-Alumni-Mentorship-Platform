"""
models/alumni.py
----------------
Alumni profile — one-to-one extension of the User table.
Holds professional/academic background and verification status.

Security notes:
    AUTH-08  — Alumni must be verified before accessing mentorship features
    DATA-02  — verification_documents stored as references, not raw blobs
    DATA-03  — file paths point to secure server-side storage (not web-accessible)
    RBAC-03  — Only verified alumni (role='verified_alumni') can accept mentorship
    APP-06   — verified_at / verified_by tracked for admin audit trail
"""

from datetime import datetime, timezone
from app import db


class Alumni(db.Model):
    __tablename__ = "alumni"

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
    # Academic background (provided at registration)
    # ------------------------------------------------------------------ #
    department        = db.Column(db.String(120), nullable=False)
    degree_program    = db.Column(db.String(120), nullable=False)   # e.g. BS Computer Science
    graduation_year   = db.Column(db.Integer,     nullable=False)
    gik_roll_number   = db.Column(db.String(20),  nullable=True)    # University ID (for verification)

    # ------------------------------------------------------------------ #
    # Professional information
    # ------------------------------------------------------------------ #
    current_company    = db.Column(db.String(200), nullable=True)
    current_job_title  = db.Column(db.String(150), nullable=True)
    industry           = db.Column(db.String(120), nullable=True)
    years_of_experience = db.Column(db.Integer,    nullable=True)
    linkedin_url       = db.Column(db.String(300), nullable=True)
    bio                = db.Column(db.Text,         nullable=True)

    # ------------------------------------------------------------------ #
    # Mentorship availability
    # ------------------------------------------------------------------ #
    # Comma-separated expertise areas — e.g. "AI,Cloud,Backend"
    expertise_areas     = db.Column(db.Text,    nullable=True)
    is_accepting_mentees = db.Column(db.Boolean, default=False, nullable=False)
    max_mentees          = db.Column(db.Integer, default=3,      nullable=False)

    # ------------------------------------------------------------------ #
    # Verification status  (AUTH-08, RBAC-03)
    # Admin reviews documents and flips is_verified + updates User.role
    # ------------------------------------------------------------------ #
    is_verified  = db.Column(db.Boolean, default=False, nullable=False)
    verified_at  = db.Column(db.DateTime(timezone=True), nullable=True)
    verified_by  = db.Column(                                          # Admin user_id
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    rejection_reason = db.Column(db.Text, nullable=True)              # Set if rejected

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
    user = db.relationship(
        "User",
        back_populates="alumni_profile",
        foreign_keys=[user_id],
    )
    verifier = db.relationship(
        "User",
        foreign_keys=[verified_by],
    )
    verification_documents = db.relationship(
        "VerificationDocument",
        back_populates="alumni",
        cascade="all, delete-orphan",
    )
    mentorship_requests = db.relationship(
        "MentorshipRequest",
        back_populates="alumni",
        cascade="all, delete-orphan",
        foreign_keys="MentorshipRequest.alumni_id",
    )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def get_expertise_list(self) -> list[str]:
        if not self.expertise_areas:
            return []
        return [e.strip() for e in self.expertise_areas.split(",") if e.strip()]

    def set_expertise_list(self, areas: list[str]) -> None:
        self.expertise_areas = ", ".join(areas)

    def to_public_dict(self) -> dict:
        """
        Safe serialisation for student-facing profile cards.
        Omits PII such as roll number, exact verification details.
        """
        return {
            "id":                   self.id,
            "full_name":            self.user.full_name,
            "department":           self.department,
            "degree_program":       self.degree_program,
            "graduation_year":      self.graduation_year,
            "current_company":      self.current_company,
            "current_job_title":    self.current_job_title,
            "industry":             self.industry,
            "years_of_experience":  self.years_of_experience,
            "linkedin_url":         self.linkedin_url,
            "bio":                  self.bio,
            "expertise_areas":      self.get_expertise_list(),
            "is_accepting_mentees": self.is_accepting_mentees,
            "is_verified":          self.is_verified,
        }

    def to_admin_dict(self) -> dict:
        """
        Full serialisation for admin panel review.
        Includes PII and verification details (RBAC-05).
        """
        base = self.to_public_dict()
        base.update({
            "email":            self.user.email,
            "gik_roll_number":  self.gik_roll_number,
            "verified_at":      self.verified_at.isoformat() if self.verified_at else None,
            "verified_by":      self.verified_by,
            "rejection_reason": self.rejection_reason,
        })
        return base

    def __repr__(self) -> str:
        return (
            f"<Alumni id={self.id} user_id={self.user_id} "
            f"verified={self.is_verified}>"
        )
