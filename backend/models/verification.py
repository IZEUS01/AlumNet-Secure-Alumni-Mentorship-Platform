"""
models/verification.py
-----------------------
VerificationDocument — stores metadata about files uploaded by alumni
as part of the identity/credential verification process.

The actual file bytes live in the server-side uploads/ directory
(never under a web-accessible static folder — DATA-04).
Only file metadata (path, type, size) is stored in the DB.

Security notes:
    DATA-02  — File type validated by magic bytes before storage
    DATA-03  — File size capped at MAX_CONTENT_LENGTH (config)
    DATA-04  — Stored path is inside backend/uploads/, not public
    RBAC-05  — Only admins can read document paths and download files
    APP-06   — Upload timestamp and reviewer tracked for audit
"""

from datetime import datetime, timezone
from extensions import db


class VerificationDocument(db.Model):
    __tablename__ = "verification_documents"

    # ------------------------------------------------------------------ #
    # Primary key
    # ------------------------------------------------------------------ #
    id = db.Column(db.Integer, primary_key=True)

    # ------------------------------------------------------------------ #
    # Foreign key — links to the alumni who uploaded the document
    # ------------------------------------------------------------------ #
    alumni_id = db.Column(
        db.Integer,
        db.ForeignKey("alumni.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Document metadata  (DATA-02, DATA-03)
    # ------------------------------------------------------------------ #
    original_filename = db.Column(db.String(255), nullable=False)   # User-supplied name (sanitised)
    stored_filename   = db.Column(db.String(255), nullable=False)   # UUID-based server name
    file_path         = db.Column(db.String(512), nullable=False)   # Absolute path on server
    mime_type         = db.Column(db.String(100), nullable=False)   # Verified via magic bytes
    file_size_bytes   = db.Column(db.Integer,     nullable=False)   # Checked against MAX_CONTENT_LENGTH

    # ------------------------------------------------------------------ #
    # Document category
    # ------------------------------------------------------------------ #
    document_type = db.Column(
        db.Enum(
            "degree_certificate",
            "transcript",
            "employment_letter",
            "national_id",
            "other",
            name="doc_types",
        ),
        nullable=False,
        default="other",
    )

    # ------------------------------------------------------------------ #
    # Review status  (RBAC-05 — admin-only action)
    # ------------------------------------------------------------------ #
    review_status = db.Column(
        db.Enum(
            "pending",
            "approved",
            "rejected",
            name="doc_review_status",
        ),
        default="pending",
        nullable=False,
    )
    reviewed_by  = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at  = db.Column(db.DateTime(timezone=True), nullable=True)
    review_notes = db.Column(db.Text, nullable=True)

    # ------------------------------------------------------------------ #
    # Audit  (APP-06)
    # ------------------------------------------------------------------ #
    uploaded_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ------------------------------------------------------------------ #
    # Relationships
    # ------------------------------------------------------------------ #
    alumni   = db.relationship("Alumni", back_populates="verification_documents")
    reviewer = db.relationship("User",   foreign_keys=[reviewed_by])

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def approve(self, admin_user_id: int, notes: str = None) -> None:
        """Admin approves this document."""
        self.review_status = "approved"
        self.reviewed_by   = admin_user_id
        self.reviewed_at   = datetime.now(timezone.utc)
        self.review_notes  = notes

    def reject(self, admin_user_id: int, notes: str = None) -> None:
        """Admin rejects this document."""
        self.review_status = "rejected"
        self.reviewed_by   = admin_user_id
        self.reviewed_at   = datetime.now(timezone.utc)
        self.review_notes  = notes

    def to_admin_dict(self) -> dict:
        """Full metadata for admin panel (RBAC-05 — never expose file_path to non-admins)."""
        return {
            "id":                self.id,
            "alumni_id":         self.alumni_id,
            "original_filename": self.original_filename,
            "document_type":     self.document_type,
            "mime_type":         self.mime_type,
            "file_size_bytes":   self.file_size_bytes,
            "review_status":     self.review_status,
            "reviewed_by":       self.reviewed_by,
            "reviewed_at":       self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_notes":      self.review_notes,
            "uploaded_at":       self.uploaded_at.isoformat(),
        }

    def to_alumni_dict(self) -> dict:
        """
        Limited view for the uploading alumni.
        file_path intentionally excluded (DATA-04).
        """
        return {
            "id":                self.id,
            "original_filename": self.original_filename,
            "document_type":     self.document_type,
            "review_status":     self.review_status,
            "uploaded_at":       self.uploaded_at.isoformat(),
        }

    def __repr__(self) -> str:
        return (
            f"<VerificationDocument id={self.id} "
            f"alumni_id={self.alumni_id} "
            f"type={self.document_type!r} "
            f"status={self.review_status!r}>"
        )
