"""
models/work_experience.py
--------------------------
WorkExperience — stores an alumni's job history.
Each alumni can have multiple work entries (past + current).

An entry with is_current=True means they still work there (end_year is NULL).
Alumni can also mark themselves as not_currently_working on their profile.
"""

from datetime import datetime, timezone
from extensions import db


class WorkExperience(db.Model):
    __tablename__ = "work_experiences"

    id = db.Column(db.Integer, primary_key=True)

    alumni_id = db.Column(
        db.Integer,
        db.ForeignKey("alumni.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Job details
    company    = db.Column(db.String(200), nullable=False)
    job_title  = db.Column(db.String(150), nullable=False)
    industry   = db.Column(db.String(120), nullable=True)
    description = db.Column(db.Text, nullable=True)

    # Duration
    start_year = db.Column(db.Integer, nullable=False)
    end_year   = db.Column(db.Integer, nullable=True)   # NULL when is_current=True
    is_current = db.Column(db.Boolean, default=False, nullable=False)

    # Audit
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    alumni = db.relationship("Alumni", back_populates="work_experiences")

    def to_dict(self):
        return {
            "id":          self.id,
            "company":     self.company,
            "job_title":   self.job_title,
            "industry":    self.industry,
            "description": self.description,
            "start_year":  self.start_year,
            "end_year":    self.end_year,
            "is_current":  self.is_current,
            "duration":    f"{self.start_year} – {'Present' if self.is_current else self.end_year}",
        }

    def __repr__(self):
        end = "Present" if self.is_current else str(self.end_year)
        return f"<WorkExperience alumni={self.alumni_id} company={self.company!r} {self.start_year}-{end}>"
