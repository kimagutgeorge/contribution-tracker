from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from sqlalchemy import text

from .auth import check_credentials, issue_token, require_admin, verify_token
from .models import ZERO, Contribution, Payment, db

api = Blueprint("api", __name__)

# Numeric(14, 2) holds up to 12 digits before the decimal point.
MAX_AMOUNT = Decimal("1000000000000")


def _money(value, field):
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field} must be a number.")
    if not amount.is_finite():
        raise ValueError(f"{field} must be a number.")
    if amount < 0:
        raise ValueError(f"{field} cannot be negative.")
    if amount >= MAX_AMOUNT:
        raise ValueError(f"{field} is too large.")
    return amount


def _positive(value, field):
    amount = _money(value, field)
    if amount <= 0:
        raise ValueError(f"{field} must be more than zero.")
    return amount


def _date(value):
    try:
        return date.fromisoformat(str(value or ""))
    except ValueError:
        raise ValueError("Date must be in YYYY-MM-DD format.")


def _body():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValueError("Invalid request body.")
    return payload


def _parse_contribution(payload):
    """Validate a contribution payload. Returns (fields, first_payment)."""
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("Name is required.")
    if len(name) > 160:
        raise ValueError("Name is too long.")

    when = _date(payload.get("date"))
    pledged = bool(payload.get("pledged"))

    if pledged:
        amount = _positive(payload.get("amount"), "Pledged amount")
        first_payment = _money(payload.get("first_payment") or 0, "First payment")
    else:
        amount = _positive(payload.get("paid"), "Paid")
        first_payment = ZERO

    fields = {"name": name, "date": when, "pledged": pledged, "amount": amount}
    return fields, first_payment


def _parse_payment(payload):
    return {
        "amount": _positive(payload.get("amount"), "Payment"),
        "date": _date(payload.get("date")),
    }


def _bad_request(exc):
    return jsonify(error=str(exc)), 400


@api.get("/health")
def health():
    db.session.execute(text("SELECT 1"))
    return jsonify(status="ok")


@api.post("/auth/login")
def login():
    body = request.get_json(silent=True) or {}
    username = body.get("username") or ""
    password = body.get("password") or ""
    if not check_credentials(username, password):
        return jsonify(error="Wrong username or password."), 401
    return jsonify(token=issue_token(username), username=username)


@api.get("/auth/me")
def me():
    header = request.headers.get("Authorization", "")
    username = verify_token(header[7:]) if header.startswith("Bearer ") else None
    if not username:
        return jsonify(error="Not signed in."), 401
    return jsonify(username=username)


@api.get("/contributions")
def list_contributions():
    rows = Contribution.query.order_by(Contribution.date.desc(), Contribution.id.desc()).all()
    paid = sum((r.paid for r in rows), ZERO)
    totals = {
        "count": len(rows),
        # Money given or promised: the pledge, or more if someone paid beyond it.
        "amount": float(sum((max(Decimal(r.amount), r.paid) for r in rows), ZERO)),
        "paid": float(paid),
        "balance": float(sum((r.balance for r in rows), ZERO)),
    }
    return jsonify(items=[r.to_dict() for r in rows], totals=totals)


@api.post("/contributions")
@require_admin
def create_contribution():
    try:
        fields, first_payment = _parse_contribution(_body())
    except ValueError as exc:
        return _bad_request(exc)
    row = Contribution(**fields)
    if row.pledged and first_payment > 0:
        row.payments.append(Payment(amount=first_payment, date=row.date))
    db.session.add(row)
    db.session.commit()
    return jsonify(row.to_dict()), 201


@api.put("/contributions/<int:item_id>")
@require_admin
def update_contribution(item_id):
    row = db.session.get(Contribution, item_id)
    if row is None:
        return jsonify(error="Contribution not found."), 404
    try:
        fields, first_payment = _parse_contribution(_body())
    except ValueError as exc:
        return _bad_request(exc)

    was_pledged = row.pledged
    for key, value in fields.items():
        setattr(row, key, value)
    if was_pledged and not row.pledged:
        row.payments.clear()
    elif not was_pledged and row.pledged and first_payment > 0:
        row.payments.append(Payment(amount=first_payment, date=row.date))

    db.session.commit()
    return jsonify(row.to_dict())


@api.delete("/contributions/<int:item_id>")
@require_admin
def delete_contribution(item_id):
    row = db.session.get(Contribution, item_id)
    if row is None:
        return jsonify(error="Contribution not found."), 404
    db.session.delete(row)
    db.session.commit()
    return "", 204


@api.post("/contributions/<int:item_id>/payments")
@require_admin
def add_payment(item_id):
    row = db.session.get(Contribution, item_id)
    if row is None:
        return jsonify(error="Contribution not found."), 404
    if not row.pledged:
        return jsonify(error="Payments can only be recorded against a pledge."), 400
    try:
        fields = _parse_payment(_body())
    except ValueError as exc:
        return _bad_request(exc)
    row.payments.append(Payment(**fields))
    db.session.commit()
    return jsonify(row.to_dict()), 201


@api.put("/payments/<int:payment_id>")
@require_admin
def update_payment(payment_id):
    payment = db.session.get(Payment, payment_id)
    if payment is None:
        return jsonify(error="Payment not found."), 404
    try:
        fields = _parse_payment(_body())
    except ValueError as exc:
        return _bad_request(exc)
    for key, value in fields.items():
        setattr(payment, key, value)
    db.session.commit()
    db.session.refresh(payment.contribution)
    return jsonify(payment.contribution.to_dict())


@api.delete("/payments/<int:payment_id>")
@require_admin
def delete_payment(payment_id):
    payment = db.session.get(Payment, payment_id)
    if payment is None:
        return jsonify(error="Payment not found."), 404
    row = payment.contribution
    row.payments.remove(payment)
    db.session.commit()
    return jsonify(row.to_dict())
