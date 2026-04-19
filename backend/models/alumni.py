"""
models/alumni.py
----------------
Alumni profile — one-to-one extension of the User table.
Holds professional/academic background and verification status.
"""

from datetime import datetime, timezone
from extensions import db


class Alumni(db.Model):
    __tablename__ = "alumni"

    id      = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        unique=True, nullable=False, index=True,
    )

    # Academic background (provided at registration)
    department      = db.Column(db.String(120), nullable=False)
    degree_program  = db.Column(db.String(120), nullable=True)
    graduation_year = db.Column(db.Integer,     nullable=False)
    gik_roll_number = db.Column(db.String(20),  nullable=True)

    # Professional information
    current_company    = db.Column(db.String(200), nullable=True)
    current_job_title  = db.Column(db.String(150), nullable=True)
    industry           = db.Column(db.String(120), nullable=True)
    years_of_experience = db.Column(db.Integer,   nullable=True)

    # ✅ NEW optional professional links
    linkedin_url = db.Column(db.String(300), nullable=True)
    github_url   = db.Column(db.String(300), nullable=True)
    work_email   = db.Column(db.String(254), nullable=True)

    # ✅ NEW: alumni can mark themselves as not currently working
    not_currently_working = db.Column(db.Boolean, default=False, nullable=False)

    bio = db.Column(db.Text, nullable=True)

    # Mentorship / connection availability
    expertise_areas      = db.Column(db.Text,    nullable=True)
    is_accepting_mentees = db.Column(db.Boolean, default=True, nullable=False)
    max_mentees          = db.Column(db.Integer, default=3,    nullable=False)

    # Verification status
    is_verified      = db.Column(db.Boolean, default=False, nullable=False)
    verified_at      = db.Column(db.DateTime(timezone=True), nullable=True)
    verified_by      = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    # Audit
    created_at = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="alumni_profile", foreign_keys=[user_id])
    verifier = db.relationship("User", foreign_keys=[verified_by])
    verification_documents = db.relationship(
        "VerificationDocument", back_populates="alumni", cascade="all, delete-orphan"
    )
    mentorship_requests = db.relationship(
        "MentorshipRequest", back_populates="alumni",
        cascade="all, delete-orphan", foreign_keys="MentorshipRequest.alumni_id",
    )
    # ✅ NEW: work history entries
    work_experiences = db.relationship(
        "WorkExperience", back_populates="alumni",
        cascade="all, delete-orphan", order_by="WorkExperience.start_year.desc()",
    )

    # Helpers
    def get_expertise_list(self):
        if not self.expertise_areas:
            return []
        return [e.strip() for e in self.expertise_areas.split(",") if e.strip()]

    def set_expertise_list(self, areas):
        self.expertise_areas = ", ".join(areas)

    def to_public_dict(self):
        return {
            "id":                    self.id,
            "full_name":             self.user.full_name,
            "department":            self.department,
            "degree_program":        self.degree_program,
            "graduation_year":       self.graduation_year,
            "current_company":       self.current_company if not self.not_currently_working else None,
            "current_job_title":     self.current_job_title if not self.not_currently_working else None,
            "not_currently_working": self.not_currently_working,
            "industry":              self.industry,
            "years_of_experience":   self.years_of_experience,
            "linkedin_url":          self.linkedin_url,
            "github_url":            self.github_url,
            "bio":                   self.bio,
            "expertise_areas":       self.get_expertise_list(),
            "is_accepting_mentees":  self.is_accepting_mentees,
            "is_verified":           self.is_verified,
            "work_history":          [w.to_dict() for w in self.work_experiences],
        }

    def to_admin_dict(self):
        base = self.to_public_dict()
        base.update({
            "email":            self.user.email,
            "work_email":       self.work_email,
            "gik_roll_number":  self.gik_roll_number,
            "verified_at":      self.verified_at.isoformat() if self.verified_at else None,
            "verified_by":      self.verified_by,
            "rejection_reason": self.rejection_reason,
            "account_status":   self.user.account_status,
        })
        return base

    def __repr__(self):
        return f"<Alumni id={self.id} user_id={self.user_id} verified={self.is_verified}>"
