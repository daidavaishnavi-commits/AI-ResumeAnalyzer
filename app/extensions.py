"""Flask extension instances, created here and initialised in `create_app`."""

from __future__ import annotations

from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()
