# routes/__init__.py
# Route blueprints — import and register via app.py

from .student    import student_bp
from .alumni     import alumni_bp
from .admin      import admin_bp
from .mentorship import mentorship_bp

__all__ = ["student_bp", "alumni_bp", "admin_bp", "mentorship_bp"]
