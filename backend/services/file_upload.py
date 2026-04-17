"""
services/file_upload.py
-----------------------
Secure file upload service for alumni verification documents.

Security controls:
    DATA-02  — File type validated via magic bytes (not just extension)
    DATA-03  — File size enforced by MAX_CONTENT_LENGTH + explicit check
    DATA-04  — Files stored in backend/uploads/, not under any public/static dir
    APP-01   — Filename sanitised before storage
"""

import os
import uuid
import magic
from werkzeug.datastructures import FileStorage
from flask import current_app

from security.input_validation import sanitise_filename
from security.logging import log_file_upload, log_file_rejected


# ------------------------------------------------------------------ #
# Allowed file types — validated by magic bytes (DATA-02)
# ------------------------------------------------------------------ #

ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg":      ".jpg",
    "image/png":       ".png",
}

# Max file size (bytes) — also enforced by MAX_CONTENT_LENGTH in config (DATA-03)
MAX_FILE_SIZE = 5 * 1024 * 1024   # 5 MB


# ------------------------------------------------------------------ #
# Core upload function
# ------------------------------------------------------------------ #

def save_verification_document(
    file: FileStorage,
    uploader_user_id: int,
) -> dict:
    """
    Validate and save an uploaded verification document.

    Steps:
        1. Check file is present and has a filename
        2. Enforce file size limit (DATA-03)
        3. Detect MIME type via magic bytes — NOT file extension (DATA-02)
        4. Generate a UUID-based storage filename (prevents overwrite attacks)
        5. Save to UPLOAD_FOLDER (outside public web root — DATA-04)

    Returns a dict with stored metadata on success.
    Raises ValueError with a user-safe message on any validation failure.
    """
    if not file or not file.filename:
        raise ValueError("No file was provided.")

    # ---- Read file content once ---- #
    content = file.read()
    file_size = len(content)

    # ---- Size check (DATA-03) ---- #
    if file_size == 0:
        raise ValueError("Uploaded file is empty.")
    if file_size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE // (1024 * 1024)
        log_file_rejected(uploader_user_id, file.filename, "file_too_large")
        raise ValueError(f"File exceeds the {max_mb} MB size limit.")

    # ---- Magic-byte MIME detection (DATA-02) ---- #
    detected_mime = magic.from_buffer(content, mime=True)
    if detected_mime not in ALLOWED_MIME_TYPES:
        log_file_rejected(uploader_user_id, file.filename,
                          f"invalid_mime:{detected_mime}")
        raise ValueError(
            f"File type '{detected_mime}' is not allowed. "
            f"Accepted types: PDF, JPEG, PNG."
        )

    # ---- Sanitise original filename (APP-01) ---- #
    original_name = sanitise_filename(file.filename)

    # ---- Generate collision-safe stored filename ---- #
    extension = ALLOWED_MIME_TYPES[detected_mime]
    stored_name = f"{uuid.uuid4().hex}{extension}"

    # ---- Resolve storage path (DATA-04 — outside public dir) ---- #
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, stored_name)

    # ---- Write file ---- #
    with open(file_path, "wb") as f:
        f.write(content)

    log_file_upload(uploader_user_id, original_name, detected_mime, file_size)

    return {
        "original_filename": original_name,
        "stored_filename":   stored_name,
        "file_path":         file_path,
        "mime_type":         detected_mime,
        "file_size_bytes":   file_size,
    }


# ------------------------------------------------------------------ #
# Secure file deletion helper
# ------------------------------------------------------------------ #

def delete_document_file(file_path: str) -> bool:
    """
    Delete a stored document file from the upload directory.
    Validates the path stays inside UPLOAD_FOLDER to prevent
    path-traversal attacks (DATA-04).

    Returns True if deleted, False if file not found.
    Raises PermissionError if path escapes the upload directory.
    """
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    real_upload   = os.path.realpath(upload_folder)
    real_target   = os.path.realpath(file_path)

    # Ensure the target is inside the upload directory
    if not real_target.startswith(real_upload + os.sep):
        raise PermissionError(
            f"Attempted file deletion outside upload directory: {file_path}"
        )

    if os.path.isfile(real_target):
        os.remove(real_target)
        return True
    return False
