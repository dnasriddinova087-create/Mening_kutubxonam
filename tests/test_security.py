from datetime import timedelta

from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_csrf_token,
    hash_password,
    verify_password,
)


def test_password_hashing():
    raw_pwd = "SuperSecretPassword123!"
    hashed = hash_password(raw_pwd)

    assert hashed != raw_pwd
    assert ":" in hashed  # salt:key format
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token():
    payload = {"sub": "admin_user", "role": "superadmin"}
    token = create_access_token(payload, expires_delta=timedelta(hours=1))

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "admin_user"
    assert decoded["role"] == "superadmin"

    # Invalid token check
    assert decode_access_token("invalid.token.here") is None


def test_csrf_token():
    t1 = generate_csrf_token()
    t2 = generate_csrf_token()
    assert len(t1) >= 32
    assert t1 != t2
