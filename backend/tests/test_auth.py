import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import jwt
import pytest
from bson import ObjectId
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.config.settings import get_settings
from app.core.security import token_hash
from app.main import app

PASSWORD = "strong-test-password"


def register(client, email="user@example.com"):
    return client.post(
        "/api/auth/register",
        json={
            "name": " Test User ",
            "email": email,
            "password": PASSWORD,
            "device_id": "test-device",
            "device_name": "pytest",
        },
    )


def bearer(data):
    return {"Authorization": "Bearer " + data["access_token"]}


def test_register_normalization_hashing_and_me(client):
    response = register(client, " USER@EXAMPLE.COM ")
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["email"] == "user@example.com"
    assert data["user"]["name"] == "Test User"
    assert data["expires_in"] == 900
    assert "_id" not in data["user"] and "password_hash" not in data["user"]
    user = app.state.database.users.find_one({"email": "user@example.com"})
    assert user["password_hash"].startswith("$argon2id$")
    assert user["password_hash"] != PASSWORD
    session = app.state.database.user_sessions.find_one({"user_id": user["_id"]})
    assert session["refresh_token_hash"] == token_hash(data["refresh_token"])
    assert data["refresh_token"] not in str(session)
    assert session["expires_at"] > datetime.now(UTC) + timedelta(days=29)
    assert client.get("/api/auth/me", headers=bearer(data)).json() == data["user"]
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/settings").status_code == 401
    assert client.get("/api/settings", headers=bearer(data)).status_code == 200


def test_duplicate_email_and_invalid_registration(client):
    assert register(client).status_code == 201
    assert register(client, "USER@example.com").status_code == 409
    assert app.state.database.users.count_documents({}) == 1
    response = client.post(
        "/api/auth/register",
        json={
            "name": "X",
            "email": "bad-email",
            "password": "short-secret",
        },
    )
    assert response.status_code == 422
    assert "short-secret" not in response.text
    assert (
        client.post(
            "/api/auth/register",
            json={
                "name": " ",
                "email": "valid@example.com",
                "password": PASSWORD,
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/auth/register",
            json={
                "name": "X",
                "email": "valid@example.com",
                "password": "short",
            },
        ).status_code
        == 422
    )


def test_login_valid_invalid_and_inactive(client):
    data = register(client).json()
    payload = {"email": "USER@EXAMPLE.COM", "password": PASSWORD}
    assert client.post("/api/auth/login", json=payload).status_code == 200
    bad = client.post("/api/auth/login", json={**payload, "password": "wrong"})
    missing = client.post("/api/auth/login", json={**payload, "email": "missing@example.com"})
    assert bad.status_code == missing.status_code == 401
    assert bad.json() == missing.json() == {"detail": "E-mail ou senha inválidos."}
    app.state.database.users.update_one(
        {"_id": ObjectId(data["user"]["id"])}, {"$set": {"active": False}}
    )
    assert client.post("/api/auth/login", json=payload).json() == bad.json()
    assert client.get("/api/auth/me", headers=bearer(data)).status_code == 401
    assert (
        client.post(
            "/api/auth/refresh",
            json={
                "refresh_token": data["refresh_token"],
            },
        ).status_code
        == 401
    )


def test_refresh_rotation_logout_and_replay(client):
    data = register(client).json()
    response = client.post("/api/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert response.status_code == 200
    rotated = response.json()
    assert rotated["refresh_token"] != data["refresh_token"]
    assert rotated["access_token"] != data["access_token"]
    assert (
        client.post(
            "/api/auth/refresh",
            json={
                "refresh_token": data["refresh_token"],
            },
        ).status_code
        == 401
    )
    assert client.get("/api/auth/me", headers=bearer(rotated)).status_code == 200
    assert (
        client.post(
            "/api/auth/logout",
            json={
                "refresh_token": rotated["refresh_token"],
            },
        ).status_code
        == 204
    )
    assert client.get("/api/auth/me", headers=bearer(rotated)).status_code == 401
    assert client.get("/api/auth/me", headers=bearer(data)).status_code == 401
    assert (
        client.post(
            "/api/auth/refresh",
            json={
                "refresh_token": rotated["refresh_token"],
            },
        ).status_code
        == 401
    )


def test_refresh_atomic_concurrency(client):
    data = register(client).json()
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(
                lambda _: (
                    client.post(
                        "/api/auth/refresh",
                        json={
                            "refresh_token": data["refresh_token"],
                        },
                    ).status_code
                ),
                range(2),
            )
        )
    assert sorted(responses) == [200, 401]


def test_expired_and_tampered_tokens(client):
    data = register(client).json()
    key = get_settings().jwt_secret_key.get_secret_value()
    claims = jwt.decode(data["access_token"], key, algorithms=["HS256"], audience="ligapro-mobile")
    claims["exp"] = int(datetime.now(UTC).timestamp()) - 1
    expired = jwt.encode(claims, key, algorithm="HS256")
    assert (
        client.get("/api/auth/me", headers={"Authorization": "Bearer " + expired}).status_code
        == 401
    )
    tampered = jwt.encode(
        {**claims, "exp": int(datetime.now(UTC).timestamp()) + 600},
        "different-test-key-" * 4,
        algorithm="HS256",
    )
    assert (
        client.get("/api/auth/me", headers={"Authorization": "Bearer " + tampered}).status_code
        == 401
    )
    app.state.database.user_sessions.update_one(
        {"refresh_token_hash": token_hash(data["refresh_token"])},
        {"$set": {"expires_at": datetime.now(UTC) - timedelta(seconds=1)}},
    )
    assert (
        client.post(
            "/api/auth/refresh",
            json={
                "refresh_token": data["refresh_token"],
            },
        ).status_code
        == 401
    )


@pytest.mark.parametrize("endpoint", ["login", "register", "google", "refresh"])
def test_rate_limits(client, endpoint):
    config = get_settings()
    old = config.auth_rate_limit_per_minute
    config.auth_rate_limit_per_minute = 1
    payloads = {
        "login": {"email": "missing@example.com", "password": PASSWORD},
        "register": {"name": "User", "email": "user@example.com", "password": PASSWORD},
        "google": {"id_token": "invalid"},
        "refresh": {"refresh_token": "invalid" * 8},
    }
    try:
        with patch("app.services.auth.id_token.verify_oauth2_token", side_effect=ValueError()):
            client.post("/api/auth/" + endpoint, json=payloads[endpoint])
            response = client.post("/api/auth/" + endpoint, json=payloads[endpoint])
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "60"
    finally:
        config.auth_rate_limit_per_minute = old


@pytest.fixture(scope="module")
def google_signer():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Google test cert")])
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    response = Mock(
        status=200,
        data=json.dumps(
            {
                "test-key": cert.public_bytes(serialization.Encoding.PEM).decode(),
            }
        ).encode(),
    )
    return key, Mock(return_value=response)


def google_token(google_signer, **changes):
    key, _ = google_signer
    now = int(datetime.now(UTC).timestamp())
    payload = {
        "iss": "https://accounts.google.com",
        "aud": get_settings().google_web_client_id,
        "sub": "google-user-123",
        "email": "google@example.com",
        "email_verified": True,
        "name": "Google User",
        "iat": now - 30,
        "exp": now + 300,
    }
    return jwt.encode({**payload, **changes}, key, algorithm="RS256", headers={"kid": "test-key"})


def test_google_signature_identity_and_existing_account(client, google_signer):
    _, transport = google_signer
    with patch("app.services.auth.GoogleTransport", return_value=transport):
        first = client.post("/api/auth/google", json={"id_token": google_token(google_signer)})
        assert first.status_code == 200
        assert first.json()["user"]["auth_provider"] == "google"
        assert first.json()["user"]["email_verified"] is True
        second = client.post("/api/auth/google", json={"id_token": google_token(google_signer)})
        assert second.json()["user"]["id"] == first.json()["user"]["id"]
        assert app.state.database.users.count_documents({}) == 1
    transport.assert_called()


@pytest.mark.parametrize(
    "changes",
    [
        {"iss": "https://attacker.example"},
        {"aud": "wrong-client"},
        {"exp": 1},
        {"email_verified": False},
        {"sub": ""},
    ],
)
def test_google_invalid_claims(client, google_signer, changes):
    with patch("app.services.auth.GoogleTransport", return_value=google_signer[1]):
        response = client.post(
            "/api/auth/google",
            json={
                "id_token": google_token(google_signer, **changes),
            },
        )
    assert response.status_code == 401
    assert app.state.database.users.count_documents({}) == 0


def test_google_invalid_signature_and_no_automatic_link(client, google_signer):
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    claims = jwt.decode(google_token(google_signer), options={"verify_signature": False})
    bad = jwt.encode(claims, other_key, algorithm="RS256", headers={"kid": "test-key"})
    with patch("app.services.auth.GoogleTransport", return_value=google_signer[1]):
        assert client.post("/api/auth/google", json={"id_token": bad}).status_code == 401
        assert register(client, "google@example.com").status_code == 201
        response = client.post("/api/auth/google", json={"id_token": google_token(google_signer)})
    assert response.status_code == 409
    assert app.state.database.users.count_documents({}) == 1
    assert app.state.database.users.find_one({})["auth_provider"] == "local"


def test_google_configuration_missing(client):
    config = get_settings()
    old = config.google_web_client_id
    config.google_web_client_id = None
    try:
        assert client.post("/api/auth/google", json={"id_token": "test"}).status_code == 503
    finally:
        config.google_web_client_id = old


def test_logout_revokes_session_even_after_concurrent_rotation(client):
    original = register(client).json()
    rotated = client.post(
        "/api/auth/refresh",
        json={
            "refresh_token": original["refresh_token"],
        },
    ).json()
    assert (
        client.post(
            "/api/auth/logout",
            headers=bearer(original),
            json={
                "refresh_token": original["refresh_token"],
            },
        ).status_code
        == 204
    )
    assert client.get("/api/auth/me", headers=bearer(rotated)).status_code == 401
