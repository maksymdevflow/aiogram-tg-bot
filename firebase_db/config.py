import firebase_admin
from firebase_admin import credentials
from pathlib import Path
import os
import logging

PROJECT_ROOT = Path(__file__).parent.parent
CREDENTIALS_PATH = PROJECT_ROOT / "driverworkbot-firebase-adminsdk-fbsvc-ee0dfba989.json"

DATABASE_URL = os.getenv(
    "FIREBASE_DATABASE_URL",
    "https://botjobfincar-default-rtdb.europe-west1.firebasedatabase.app/"
)

logger = logging.getLogger(__name__)
if DATABASE_URL:
    logger.info(f"Using Firebase Database URL: {DATABASE_URL}")

if not firebase_admin._apps:
    cred = credentials.Certificate(str(CREDENTIALS_PATH))
    firebase_admin.initialize_app(
        cred,
        {
            "databaseURL": DATABASE_URL
        }
    )
