import hashlib
import hmac
import time

TOKEN_MAX_AGE_SECONDS = 7 * 24 * 3600


def get_admin_password() -> str:
    from settings_store import get_admin_password as _get

    return _get()


def admin_auth_enabled() -> bool:
    return bool(get_admin_password())


def create_admin_token() -> str:
    password = get_admin_password()
    ts = str(int(time.time()))
    sig = hmac.new(password.encode(), ts.encode(), hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"


def verify_admin_token(token: str | None) -> bool:
    password = get_admin_password()
    if not password or not token:
        return False
    try:
        ts_str, sig = token.rsplit(".", 1)
        ts = int(ts_str)
    except ValueError:
        return False
    if time.time() - ts > TOKEN_MAX_AGE_SECONDS:
        return False
    expected = hmac.new(password.encode(), ts_str.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


def check_admin_password(password: str) -> bool:
    stored = get_admin_password()
    if not stored:
        return False
    return hmac.compare_digest(stored, password)
