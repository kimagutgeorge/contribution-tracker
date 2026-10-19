from datetime import datetime, timezone
from decimal import Decimal

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

ZERO = Decimal("0")


def utcnow():
    return datetime.now(timezone.utc)


class Payment(db.Model):
    """One installment paid towards a pledge."""

    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    contribution_id = db.Column(
        db.Integer,
        db.ForeignKey("contributions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    contribution = db.relationship("Contribution", back_populates="payments")


class Contribution(db.Model):
    __tablename__ = "contributions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    date = db.Column(db.Date, nullable=False)
    # Pledge: the pledged total. One-off payment: the amount paid.
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    pledged = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    # Only pledges have payments; a one-off contribution is paid in full by definition.
    payments = db.relationship(
        "Payment",
        back_populates="contribution",
        cascade="all, delete-orphan",
        order_by=(Payment.date, Payment.id),
        lazy="selectin",
    )

    @property
    def paid(self):
        if not self.pledged:
            return Decimal(self.amount)
        return sum((Decimal(p.amount) for p in self.payments), ZERO)

    @property
    def balance(self):
        if not self.pledged:
            return ZERO
        return max(Decimal(self.amount) - self.paid, ZERO)

    @property
    def overpaid(self):
        if not self.pledged:
            return ZERO
        return max(self.paid - Decimal(self.amount), ZERO)

    def payment_history(self):
        """Payments oldest first, each with the balance left after it."""
        remaining = Decimal(self.amount)
        history = []
        for p in sorted(self.payments, key=lambda p: (p.date, p.id or 0)):
            remaining -= Decimal(p.amount)
            history.append(
                {
                    "id": p.id,
                    "date": p.date.isoformat(),
                    "amount": float(p.amount),
                    "balance_after": float(max(remaining, ZERO)),
                }
            )
        return history

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "date": self.date.isoformat(),
            "amount": float(self.amount),
            "pledged": self.pledged,
            "paid": float(self.paid),
            "balance": float(self.balance),
            "overpaid": float(self.overpaid),
            "payments": self.payment_history() if self.pledged else [],
        }
