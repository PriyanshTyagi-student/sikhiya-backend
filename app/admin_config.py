# Admin credentials for local development
# IMPORTANT: Do not commit real credentials. Prefer environment variables in production.

import os

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "sikhiyaconnect@gmail.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin@sikhiya007")
ADMIN_NAME = os.getenv("ADMIN_NAME", "Sikhiya Admin")
