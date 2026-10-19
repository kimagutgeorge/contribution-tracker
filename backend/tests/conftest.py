import pytest

from app import create_app
from app.models import db
from app.schema import upgrade


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "SECRET_KEY": "test-secret",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "pass123",
        }
    )
    with app.app_context():
        upgrade()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth(client):
    res = client.post("/api/auth/login", json={"username": "admin", "password": "pass123"})
    return {"Authorization": f"Bearer {res.get_json()['token']}"}
