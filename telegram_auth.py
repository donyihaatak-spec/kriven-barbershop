import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


def validate_webapp_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = 86400,
) -> dict | None:
    if not init_data or not bot_token:
        return None

    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None

        auth_date = int(parsed.get("auth_date", "0"))
        if auth_date and time.time() - auth_date > max_age_seconds:
            return None

        check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        calculated = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(calculated, received_hash):
            return None

        user_raw = parsed.get("user")
        if not user_raw:
            return None
        return json.loads(user_raw)
    except (ValueError, json.JSONDecodeError, TypeError):
        return None
