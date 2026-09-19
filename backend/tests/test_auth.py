import pytest

from app.services.auth import create_customer_token, digest_otp, normalize_phone, verify_customer_token


def test_normalize_phone_accepts_turkish_international_format() -> None:
    assert normalize_phone("+90 555 123 45 67") == "+905551234567"
    assert normalize_phone("0090 555 123 45 67") == "+905551234567"


def test_normalize_phone_rejects_invalid_value() -> None:
    with pytest.raises(ValueError):
        normalize_phone("123")


def test_otp_digest_is_deterministic_and_phone_bound() -> None:
    first = digest_otp("+905551234567", "123456")
    assert first == digest_otp("+905551234567", "123456")
    assert first != digest_otp("+905551234568", "123456")


def test_customer_token_round_trip() -> None:
    token = create_customer_token("00000000-0000-0000-0000-000000000001")
    assert verify_customer_token(token) == "00000000-0000-0000-0000-000000000001"


def test_customer_token_rejects_tampering() -> None:
    token = create_customer_token("00000000-0000-0000-0000-000000000001")
    encoded, _ = token.split(".", 1)
    with pytest.raises(ValueError):
        verify_customer_token(f"{encoded}.tampered")