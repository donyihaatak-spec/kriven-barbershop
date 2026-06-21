import hashlib
import hmac
import time

from config import ADMIN_PASSWORD

TOKEN_MAX_AGE_SECONDS = 7 * 24 * 3600


def admin_auth_enabled() -> bool:
    return bool(ADMIN_PASSWORD)


def create_admin_token() -> str:
    ts = str(int(time.time()))
    sig = hmac.new(ADMIN_PASSWORD.encode(), ts.encode(), hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"


def verify_admin_token(token: str | None) -> bool:
    if not ADMIN_PASSWORD or not token:
        return False
    try:
        ts_str, sig = token.rsplit(".", 1)
        ts = int(ts_str)
    except ValueError:
        return False
    if time.time() - ts > TOKEN_MAX_AGE_SECONDS:
        return False
    expected = hmac.new(ADMIN_PASSWORD.encode(), ts_str.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


def check_admin_password(password: str) -> bool:
    if not ADMIN_PASSWORD:
        return False
    return hmac.compare_digest(ADMIN_PASSWORD, password)
