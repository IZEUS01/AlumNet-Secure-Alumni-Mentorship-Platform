"""
security/headers.py
-------------------
Security response headers applied to every outgoing response.

Flask-Talisman (initialised in app.py) handles HSTS, CSP, and
HTTPS enforcement. This module adds an after_request hook for any
additional headers Talisman doesn't cover, plus a helper to register
the hook.

Covers:
    APP-04  — Enforce HTTPS / secure headers for all communications
    Threat  — Information Disclosure (suppress server fingerprinting)
"""

from flask import Flask, Response


# ------------------------------------------------------------------ #
# Additional security headers not covered by Talisman
# ------------------------------------------------------------------ #

EXTRA_SECURITY_HEADERS = {
    # Prevent browsers from MIME-sniffing away from the declared content type
    "X-Content-Type-Options": "nosniff",

    # Clickjacking protection (belt-and-suspenders alongside CSP frame-ancestors)
    "X-Frame-Options": "DENY",

    # Don't send the Referrer header to cross-origin destinations
    "Referrer-Policy": "strict-origin-when-cross-origin",

    # Limit browser features accessible to this origin
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",

    # Remove server version fingerprinting
    "Server": "AlumNet",
    "X-Powered-By": "",       # Suppress framework/version info
}


# ------------------------------------------------------------------ #
# Registration helper
# ------------------------------------------------------------------ #

def register_security_headers(app: Flask) -> None:
    """
    Register an after_request hook that injects additional security
    headers into every response.

    Call this from create_app() after Talisman is initialised.
    """

    @app.after_request
    def add_security_headers(response: Response) -> Response:
        for header, value in EXTRA_SECURITY_HEADERS.items():
            if value:
                response.headers[header] = value
            elif header in response.headers:
                # Remove headers we want to suppress (e.g. X-Powered-By)
                del response.headers[header]
        return response
