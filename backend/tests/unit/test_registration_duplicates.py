from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from app.repositories.auth import AuthRepository
from app.schemas.auth import GoogleRequest, RegisterRequest
from app.services.auth import AuthService


@pytest.mark.parametrize(
    ("email_exists", "name_exists", "message"),
    [
        (True, False, "Este e-mail já está cadastrado."),
        (False, True, "Este nome já está cadastrado. Escolha outro nome."),
    ],
)
def test_duplicates_do_not_create_user_or_session(email_exists, name_exists, message):
    repo = Mock(spec=AuthRepository)
    repo.get_by_email.return_value = {"_id": "existing"} if email_exists else None
    repo.get_by_name.return_value = {"_id": "existing"} if name_exists else None
    service = AuthService(repo, Mock())
    body = RegisterRequest(name=" User ", email=" USER@example.com ", password="password123")
    with patch("app.services.auth.hash_password") as hash_password:
        with pytest.raises(HTTPException) as error:
            service.register(body)
        hash_password.assert_not_called()
    assert error.value.status_code == 409
    assert error.value.detail == message
    repo.get_by_email.assert_called_once_with("user@example.com")
    if not email_exists:
        repo.get_by_name.assert_called_once_with("User")
    repo.create_user.assert_not_called()
    repo.create_session.assert_not_called()


@pytest.mark.parametrize("field", ["email", "name_key"])
def test_concurrent_duplicate_returns_the_matching_message(field):
    repo = Mock(spec=AuthRepository)
    repo.get_by_email.return_value = None
    repo.get_by_name.return_value = None
    repo.create_user.side_effect = DuplicateKeyError(
        "duplicate", details={"keyPattern": {field: 1}}
    )
    service = AuthService(repo, Mock())
    with patch("app.services.auth.hash_password", return_value="hash"):
        with pytest.raises(HTTPException) as error:
            service.register(
                RegisterRequest(name="User", email="user@example.com", password="password123")
            )
    assert error.value.status_code == 409
    assert error.value.detail == (
        "Este e-mail já está cadastrado."
        if field == "email"
        else "Este nome já está cadastrado. Escolha outro nome."
    )
    repo.create_session.assert_not_called()


def test_new_registration_stores_normalized_name_and_preserves_display_name():
    repo = Mock(spec=AuthRepository)
    repo.get_by_email.return_value = None
    repo.get_by_name.return_value = None
    service = AuthService(repo, Mock())
    service.issue_session = Mock(return_value="session")
    with patch("app.services.auth.hash_password", return_value="hash"):
        result = service.register(
            RegisterRequest(name=" Test User ", email="user@example.com", password="password123")
        )
    document = repo.create_user.call_args.args[0]
    assert document["name"] == "Test User"
    assert document["name_key"] == "test user"
    assert result == "session"


def test_name_lookup_matches_legacy_accounts_and_escapes_regex_characters():
    database = Mock()
    database.__getitem__ = Mock(return_value=Mock())
    repo = AuthRepository(database)
    repo.get_by_name("User.*")
    query, projection = repo.users.find_one.call_args.args
    assert query["$or"][0] == {"name_key": "user.*"}
    assert query["$or"][1] == {"name": {"$regex": r"^User\.\*$", "$options": "i"}}
    assert projection == {"_id": 1}


@pytest.mark.parametrize("provider", ["local", "google"])
def test_repository_normalizes_and_indexes_names_for_every_registration(provider):
    database = Mock()
    database.__getitem__ = Mock(return_value=Mock())
    repo = AuthRepository(database)
    repo.users.find_one.return_value = None
    result = repo.create_user(
        {"name": " Gabriel ", "email": " USER@EXAMPLE.COM ", "auth_provider": provider}
    )
    assert result["name"] == "Gabriel"
    assert result["name_key"] == "gabriel"
    assert result["email"] == "user@example.com"
    repo.users.insert_one.assert_called_once()


@pytest.mark.parametrize("provider", ["local", "google"])
def test_repository_blocks_names_already_used_including_legacy_users(provider):
    database = Mock()
    database.__getitem__ = Mock(return_value=Mock())
    repo = AuthRepository(database)
    repo.users.find_one.return_value = {"_id": "existing"}
    with pytest.raises(DuplicateKeyError) as error:
        repo.create_user(
            {"name": "Gabriel", "email": "another@example.com", "auth_provider": provider}
        )
    assert error.value.details["keyPattern"] == {"name_key": 1}
    repo.users.insert_one.assert_not_called()


def test_google_duplicate_name_returns_validation_error_without_session():
    repo = Mock(spec=AuthRepository)
    repo.get_by_google_id.return_value = None
    repo.get_by_email.return_value = None
    repo.create_user.side_effect = DuplicateKeyError(
        "duplicate", details={"keyPattern": {"name_key": 1}}
    )
    service = AuthService(repo, Mock(google_web_client_id="client"))
    identity = {
        "sub": "google-user",
        "email": "user@example.com",
        "email_verified": True,
        "name": "Gabriel",
    }
    with patch("app.services.auth.id_token.verify_oauth2_token", return_value=identity):
        with pytest.raises(HTTPException) as error:
            service.google(GoogleRequest(id_token="token"))
    assert error.value.status_code == 409
    assert error.value.detail == "Este nome já está cadastrado. Escolha outro nome."
    repo.create_session.assert_not_called()
