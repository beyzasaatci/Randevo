import base64
import hashlib
import hmac
import json
import secrets
import time

from app.core.config import get_settings


def normalize_phone(phone_number: str) -> str:
    compact = "".join(character for character in phone_number if character.isdigit())
    if compact.startswith("00"):
        compact = compact[2:]
    if compact.startswith("90") and len(compact) == 12:
        digits = "+" + compact
    elif compact.startswith("0") and len(compact) == 11:
        digits = "+90" + compact[1:]
    elif compact.startswith("5") and len(compact) == 10:
        digits = "+90" + compact
    else:
        digits = "+" + compact
    if not digits.startswith("+") or not digits[1:].isdigit() or not 8 <= len(digits[1:]) <= 15:
        raise ValueError("Geçerli bir telefon numarası girin.")
    return digits


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def digest_otp(phone_number: str, code: str) -> str:
    settings = get_settings()
    return hmac.new(settings.secret_key.encode(), f"{phone_number}:{code}".encode(), hashlib.sha256).hexdigest()


def create_customer_token(customer_id: str) -> str:
    settings = get_settings()
    payload = {"sub": customer_id, "exp": int(time.time()) + 3600}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(settings.secret_key.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def verify_customer_token(token: str) -> str:
    settings = get_settings()
    try:
        encoded, signature = token.split(".", 1)
        expected = hmac.new(settings.secret_key.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if payload["exp"] < time.time():
            raise ValueError
        return str(payload["sub"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise ValueError("Geçersiz veya süresi dolmuş oturum.") from None