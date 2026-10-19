from sqlalchemy import inspect, text

from app.models import db
from app.schema import upgrade


def _create(client, auth, **body):
    res = client.post("/api/contributions", json=body, headers=auth)
    assert res.status_code == 201, res.get_json()
    return res.get_json()


def _pay(client, auth, item_id, amount, day):
    res = client.post(
        f"/api/contributions/{item_id}/payments",
        json={"amount": amount, "date": day},
        headers=auth,
    )
    assert res.status_code == 201, res.get_json()
    return res.get_json()


def test_login_rejects_bad_password(client):
    res = client.post("/api/auth/login", json={"username": "admin", "password": "nope"})
    assert res.status_code == 401


def test_me_with_token(client, auth):
    res = client.get("/api/auth/me", headers=auth)
    assert res.get_json() == {"username": "admin"}


def test_writes_need_auth(client):
    body = {"name": "A", "date": "2026-10-01", "paid": 100}
    assert client.post("/api/contributions", json=body).status_code == 401
    assert client.put("/api/contributions/1", json=body).status_code == 401
    assert client.delete("/api/contributions/1").status_code == 401
    pay = {"amount": 1, "date": "2026-10-01"}
    assert client.post("/api/contributions/1/payments", json=pay).status_code == 401
    assert client.put("/api/payments/1", json=pay).status_code == 401
    assert client.delete("/api/payments/1").status_code == 401
    bad = {"Authorization": "Bearer forged"}
    assert client.post("/api/contributions", json=body, headers=bad).status_code == 401


def test_one_off_contribution_is_paid_in_full(client, auth):
    item = _create(client, auth, name="Jane", date="2026-10-01", paid=500, amount=9999)
    assert item["amount"] == 500
    assert item["paid"] == 500
    assert item["balance"] == 0
    assert item["payments"] == []


def test_pledge_installments_history(client, auth):
    pledge = _create(client, auth, name="John", date="2026-10-01", pledged=True, amount=1000)
    assert pledge["paid"] == 0 and pledge["balance"] == 1000

    _pay(client, auth, pledge["id"], 300, "2026-10-02")
    _pay(client, auth, pledge["id"], 200, "2026-10-05")
    item = _pay(client, auth, pledge["id"], 800, "2026-10-09")

    assert [(p["date"], p["amount"], p["balance_after"]) for p in item["payments"]] == [
        ("2026-10-02", 300, 700),
        ("2026-10-05", 200, 500),
        ("2026-10-09", 800, 0),
    ]
    assert item["paid"] == 1300
    assert item["balance"] == 0
    assert item["overpaid"] == 300


def test_history_is_sorted_by_date_not_entry_order(client, auth):
    pledge = _create(client, auth, name="John", date="2026-10-01", pledged=True, amount=1000)
    _pay(client, auth, pledge["id"], 100, "2026-10-20")
    item = _pay(client, auth, pledge["id"], 400, "2026-10-03")
    assert [p["balance_after"] for p in item["payments"]] == [600, 500]


def test_first_payment_on_create(client, auth):
    item = _create(
        client, auth, name="A", date="2026-10-01", pledged=True, amount=1000, first_payment=250
    )
    assert item["payments"] == [
        {"id": item["payments"][0]["id"], "date": "2026-10-01", "amount": 250, "balance_after": 750}
    ]


def test_edit_and_delete_payment(client, auth):
    pledge = _create(client, auth, name="A", date="2026-10-01", pledged=True, amount=1000)
    item = _pay(client, auth, pledge["id"], 300, "2026-10-02")
    pid = item["payments"][0]["id"]

    res = client.put(f"/api/payments/{pid}", json={"amount": 450, "date": "2026-10-03"}, headers=auth)
    assert res.get_json()["paid"] == 450
    assert res.get_json()["payments"][0]["date"] == "2026-10-03"

    res = client.delete(f"/api/payments/{pid}", headers=auth)
    assert res.get_json()["paid"] == 0
    assert client.delete(f"/api/payments/{pid}", headers=auth).status_code == 404


def test_cannot_add_payment_to_one_off(client, auth):
    item = _create(client, auth, name="A", date="2026-10-01", paid=100)
    res = client.post(
        f"/api/contributions/{item['id']}/payments",
        json={"amount": 10, "date": "2026-10-02"},
        headers=auth,
    )
    assert res.status_code == 400


def test_switching_type(client, auth):
    item = _create(client, auth, name="A", date="2026-10-01", paid=400)

    # One-off to pledge: what was paid becomes the first installment.
    body = {"name": "A", "date": "2026-10-01", "pledged": True, "amount": 1000, "first_payment": 400}
    res = client.put(f"/api/contributions/{item['id']}", json=body, headers=auth).get_json()
    assert res["paid"] == 400 and res["balance"] == 600 and len(res["payments"]) == 1

    # Editing the pledge again must not add another payment.
    res = client.put(f"/api/contributions/{item['id']}", json=body, headers=auth).get_json()
    assert len(res["payments"]) == 1

    # Pledge to one-off: payments are dropped.
    body = {"name": "A", "date": "2026-10-01", "pledged": False, "paid": 700}
    res = client.put(f"/api/contributions/{item['id']}", json=body, headers=auth).get_json()
    assert res["amount"] == 700 and res["payments"] == []


def test_totals(client, auth):
    _create(client, auth, name="Jane", date="2026-10-01", paid=500)
    p = _create(client, auth, name="John", date="2026-10-02", pledged=True, amount=1000)
    _pay(client, auth, p["id"], 250.5, "2026-10-03")
    over = _create(client, auth, name="Ann", date="2026-10-03", pledged=True, amount=100)
    _pay(client, auth, over["id"], 150, "2026-10-04")

    data = client.get("/api/contributions").get_json()
    assert [i["name"] for i in data["items"]] == ["Ann", "John", "Jane"]
    assert data["totals"] == {"count": 3, "amount": 1650, "paid": 900.5, "balance": 749.5}


def test_deleting_pledge_removes_payments(client, auth):
    p = _create(client, auth, name="A", date="2026-10-01", pledged=True, amount=100)
    _pay(client, auth, p["id"], 50, "2026-10-02")
    assert client.delete(f"/api/contributions/{p['id']}", headers=auth).status_code == 204
    assert db.session.execute(text("SELECT COUNT(*) FROM payments")).scalar() == 0


def test_validation(client, auth):
    cases = [
        {"date": "2026-10-01", "paid": 1},
        {"name": "A", "date": "01/10/2026", "paid": 1},
        {"name": "A", "date": "2026-10-01", "paid": 0},
        {"name": "A", "date": "2026-10-01", "paid": "abc"},
        {"name": "A", "date": "2026-10-01", "paid": "NaN"},
        {"name": "A", "date": "2026-10-01", "paid": -5},
        {"name": "A", "date": "2026-10-01", "pledged": True, "amount": 0},
        {"name": "A", "date": "2026-10-01", "pledged": True, "amount": 10, "first_payment": -1},
        {"name": "A", "date": "2026-10-01", "paid": 1e15},
    ]
    for body in cases:
        res = client.post("/api/contributions", json=body, headers=auth)
        assert res.status_code == 400, body

    p = _create(client, auth, name="A", date="2026-10-01", pledged=True, amount=100)
    for body in [{"amount": 0, "date": "2026-10-01"}, {"amount": 5, "date": "x"}, {"amount": 5}]:
        res = client.post(f"/api/contributions/{p['id']}/payments", json=body, headers=auth)
        assert res.status_code == 400, body


def test_upgrade_moves_old_paid_column_into_payments(app):
    db.drop_all()
    with db.engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE contributions (id INTEGER PRIMARY KEY, name VARCHAR(160) NOT NULL, "
            "date DATE NOT NULL, amount NUMERIC(14,2) NOT NULL, pledged BOOLEAN NOT NULL, "
            "paid NUMERIC(14,2) NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)"
        ))
        conn.execute(text(
            "INSERT INTO contributions VALUES "
            "(1, 'Pledger', '2026-10-01', 1000, 1, 300, '2026-10-01 00:00:00', '2026-10-01 00:00:00'),"
            "(2, 'One off', '2026-10-02', 50, 0, 50, '2026-10-02 00:00:00', '2026-10-02 00:00:00'),"
            "(3, 'Unpaid', '2026-10-03', 80, 1, 0, '2026-10-03 00:00:00', '2026-10-03 00:00:00')"
        ))

    upgrade()
    upgrade()  # second run is a no-op

    cols = {c["name"] for c in inspect(db.engine).get_columns("contributions")}
    assert "paid" not in cols
    rows = db.session.execute(text("SELECT contribution_id, amount FROM payments")).all()
    assert [(r[0], float(r[1])) for r in rows] == [(1, 300.0)]
