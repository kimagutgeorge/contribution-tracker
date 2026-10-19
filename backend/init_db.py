"""Create or upgrade tables before the web workers start. Retries while Postgres boots."""
import sys
import time

from sqlalchemy.exc import OperationalError

from app import create_app
from app.schema import upgrade

app = create_app()

for attempt in range(1, 31):
    try:
        with app.app_context():
            upgrade()
        print("Database ready.")
        sys.exit(0)
    except OperationalError as exc:
        print(f"Waiting for database ({attempt}/30): {exc.orig}")
        time.sleep(2)

print("Could not connect to the database.")
sys.exit(1)
