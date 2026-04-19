"""
models/__init__.py
------------------
Centralised model registry.
Import all models here so SQLAlchemy's metadata knows about every
table before db.create_all() or Alembic migrations run.
"""

from .user             import User
from .student          import Student
from .alumni           import Alumni
from .admin            import Admin
from .work_experience  import WorkExperience
from .mentorship       import MentorshipRequest
from .verification     import VerificationDocument
from .audit_log        import AuditLog

__all__ = [
    "User",
    "Student",
    "Alumni",
    "Admin",
    "WorkExperience",
    "MentorshipRequest",
    "VerificationDocument",
    "AuditLog",
]
