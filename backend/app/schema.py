from sqlalchemy import inspect, text

from .models import db


def upgrade():
    """Create missing tables and apply small in-place migrations. Safe to rerun."""
    db.create_all()

    # v1 stored a single `paid` figure on each contribution. Pledges now keep a
    # payment history, so move any amount paid into a first payment and drop it.
    columns = {c["name"] for c in inspect(db.engine).get_columns("contributions")}
    if "paid" in columns:
        db.session.execute(
            text(
                "INSERT INTO payments (contribution_id, amount, date, created_at) "
                "SELECT id, paid, date, created_at FROM contributions "
                "WHERE pledged AND paid > 0"
            )
        )
        db.session.execute(text("ALTER TABLE contributions DROP COLUMN paid"))
        db.session.commit()
