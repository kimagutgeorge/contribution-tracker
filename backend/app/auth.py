import hmac
from functools import wraps

from flask import current_app, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="admin-auth")


def check_credentials(username, password):
    cfg = current_app.config
    user_ok = hmac.compare_digest(str(username), cfg["ADMIN_USERNAME"])
    pass_ok = hmac.compare_digest(str(password), cfg["ADMIN_PASSWORD"])
    return user_ok and pass_ok


def issue_token(username):
    return _serializer().dumps({"sub": username})


def verify_token(token):
    try:
        data = _serializer().loads(token, max_age=current_app.config["TOKEN_MAX_AGE"])
    except (BadSignature, SignatureExpired):
        return None
    return data.get("sub")


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        token = header[7:] if header.startswith("Bearer ") else ""
        if not token or not verify_token(token):
            return jsonify(error="Please sign in again."), 401
        return view(*args, **kwargs)

    return wrapper
