"""
extensions.py
-------------
All Flask extension instances live here — imported by both app.py
and any module that needs them (models, routes, etc.).

This breaks the circular import:
    app.py → blueprint → model → app.py  ← circular ✗
    app.py → blueprint → model → extensions.py  ← clean ✓
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_mail import Mail
from flask_talisman import Talisman

db            = SQLAlchemy()
login_manager = LoginManager()
csrf          = CSRFProtect()
limiter       = Limiter(key_func=get_remote_address)
mail          = Mail()
