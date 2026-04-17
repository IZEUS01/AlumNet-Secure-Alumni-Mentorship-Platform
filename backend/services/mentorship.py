"""
services/mentorship.py
-----------------------
Business-logic service for mentorship requests.

Keeps route handlers thin — all rules and DB operations live here.

Business rules:
    - A student cannot send a duplicate pending request to the same alumni
    - Only verified alumni can receive requests (RBAC-03, RBAC-04)
    - A student can withdraw their own pending request only
    - Alumni can accept or reject only requests addressed to them
    - Accepted requests count against the alumni's max_mentees cap

Security controls:
    RBAC-03  — Unverified alumni blocked from receiving requests
    RBAC-04  — Only verified alumni can respond
    APP-01   — Input validated before DB write
    APP-06   — All state changes logged
"""

from datetime import datetime, timezone

from flask import current_app
from sqlalchemy.exc import IntegrityError

from app import db
from models.student import Student
from models.alumni import Alumni
from models.mentorship import MentorshipRequest
from security.input_validation import sanitise_string, sanitise_text
from security.logging import log_security_event, SecurityEvent


# ------------------------------------------------------------------ #
# Send a mentorship request (student action)
# ------------------------------------------------------------------ #

def send_mentorship_request(
    student_user_id: int,
    alumni_id: int,
    subject: str,
    message: str,
) -> MentorshipRequest:
    """
    Create a new mentorship request from a student to a verified alumni.

    Raises:
        ValueError  — validation failure or business rule violation
        PermissionError — alumni is not verified (RBAC-03)
    """
    # ---- Validate inputs (APP-01) ---- #
    subject = sanitise_string(subject, max_length=255)
    message = sanitise_text(message, max_length=2000)

    if not subject:
        raise ValueError("Subject is required.")
    if not message:
        raise ValueError("Message is required.")

    # ---- Resolve student profile ---- #
    student = Student.query.filter_by(user_id=student_user_id).first()
    if not student:
        raise ValueError("Student profile not found.")

    # ---- Resolve and validate alumni (RBAC-03) ---- #
    alumni = Alumni.query.get(alumni_id)
    if not alumni:
        raise ValueError("Alumni not found.")
    if not alumni.is_verified:
        raise PermissionError(
            "Mentorship requests can only be sent to verified alumni."
        )
    if not alumni.is_accepting_mentees:
        raise ValueError("This alumni is not currently accepting mentorship requests.")

    # ---- Duplicate-request prevention ---- #
    existing = MentorshipRequest.query.filter_by(
        student_id=student.id,
        alumni_id=alumni.id,
        status="pending",
    ).first()
    if existing:
        raise ValueError(
            "You already have a pending request with this alumni."
        )

    # ---- Check alumni mentee capacity ---- #
    active_count = MentorshipRequest.query.filter_by(
        alumni_id=alumni.id, status="accepted"
    ).count()
    if active_count >= alumni.max_mentees:
        raise ValueError("This alumni has reached their maximum number of mentees.")

    # ---- Create request ---- #
    req = MentorshipRequest(
        student_id=student.id,
        alumni_id=alumni.id,
        subject=subject,
        message=message,
        status="pending",
    )
    db.session.add(req)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("A duplicate request already exists.")

    log_security_event(
        SecurityEvent.LOGIN_SUCCESS,   # reuse INFO level — no dedicated constant needed
        user_id=student_user_id,
        extra={"action": "MENTORSHIP_REQUEST_SENT",
               "alumni_id": alumni_id, "request_id": req.id},
    )

    return req


# ------------------------------------------------------------------ #
# Withdraw a request (student action)
# ------------------------------------------------------------------ #

def withdraw_mentorship_request(
    student_user_id: int,
    request_id: int,
) -> MentorshipRequest:
    """
    Allow a student to withdraw their own pending request.

    Raises ValueError if the request doesn't belong to them or is not pending.
    """
    student = Student.query.filter_by(user_id=student_user_id).first()
    if not student:
        raise ValueError("Student profile not found.")

    req = MentorshipRequest.query.filter_by(
        id=request_id, student_id=student.id
    ).first()
    if not req:
        raise ValueError("Request not found.")
    if req.status != "pending":
        raise ValueError(f"Cannot withdraw a request with status '{req.status}'.")

    req.withdraw()
    db.session.commit()

    current_app.logger.info(
        "MENTORSHIP_WITHDRAWN student_user_id=%s request_id=%s",
        student_user_id, request_id,
    )
    return req


# ------------------------------------------------------------------ #
# List requests for a student
# ------------------------------------------------------------------ #

def get_student_requests(
    student_user_id: int,
    status: str | None = None,
) -> list[MentorshipRequest]:
    """Return all mentorship requests made by a student, optionally filtered by status."""
    student = Student.query.filter_by(user_id=student_user_id).first()
    if not student:
        return []

    query = MentorshipRequest.query.filter_by(student_id=student.id)
    if status:
        query = query.filter_by(status=status)

    return query.order_by(MentorshipRequest.created_at.desc()).all()


# ------------------------------------------------------------------ #
# List requests for an alumni (verified only — RBAC-04)
# ------------------------------------------------------------------ #

def get_alumni_requests(
    alumni_user_id: int,
    status: str | None = "pending",
) -> list[MentorshipRequest]:
    """
    Return mentorship requests addressed to the given alumni.
    Only call this for verified alumni (RBAC-04 enforced in route layer).
    """
    alumni = Alumni.query.filter_by(user_id=alumni_user_id).first()
    if not alumni:
        return []

    query = MentorshipRequest.query.filter_by(alumni_id=alumni.id)
    if status:
        query = query.filter_by(status=status)

    return query.order_by(MentorshipRequest.created_at.desc()).all()
