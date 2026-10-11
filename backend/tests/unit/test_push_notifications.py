import base64
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from pydantic import SecretStr, ValidationError
from pymongo.errors import DuplicateKeyError
from pywebpush import WebPushException

from app.controllers.push import Subscription, subscribe, unsubscribe
from app.services.push_notifications import send_match_reminders


def setup():
    repo = Mock()
    now = datetime(2026, 10, 11, tzinfo=UTC)
    match = {
        "_id": "match",
        "date": now + timedelta(minutes=5),
        "home_club_id": "club",
        "away_club_id": "bot",
    }
    subscription = {
        "_id": "device",
        "subscription": {"endpoint": "https://fcm.googleapis.com/test"},
    }
    repo.many.side_effect = lambda collection, *args, **kwargs: (
        [match]
        if collection == "matches"
        else [subscription]
        if collection == "push_subscriptions"
        else []
    )
    repo.find.side_effect = lambda collection, query: (
        {"name": "Clube", "owner_user_id": "user"} if query["_id"] == "club" else None
    )
    repo.database.push_deliveries.update_one.return_value = SimpleNamespace(
        modified_count=0, upserted_id="claim"
    )
    settings = SimpleNamespace(
        web_push_public_key="public",
        web_push_private_key=SecretStr("private"),
        web_push_subject="mailto:test@example.com",
    )
    return repo, settings, now, match


def test_reminder_uses_five_minute_window_and_marks_success():
    repo, settings, now, match = setup()
    with patch("app.services.push_notifications.webpush") as send:
        send_match_reminders(repo, settings, now)
    send.assert_called_once()
    assert send.call_args.kwargs["ttl"] == 300
    assert repo.many.call_args_list[0].args[1]["date"] == {"$gt": now, "$lte": match["date"]}
    assert repo.database.push_deliveries.update_one.call_args.args[1] == {"$set": {"sent": True}}


def test_duplicate_claim_skips_delivery():
    repo, settings, now, _ = setup()
    repo.database.push_deliveries.update_one.side_effect = DuplicateKeyError("already sent")
    with patch("app.services.push_notifications.webpush") as send:
        send_match_reminders(repo, settings, now)
    send.assert_not_called()


def test_expired_subscription_is_removed_but_network_failure_can_retry():
    repo, settings, now, _ = setup()
    with patch(
        "app.services.push_notifications.webpush",
        side_effect=WebPushException("expired", response=SimpleNamespace(status_code=410)),
    ):
        send_match_reminders(repo, settings, now)
    repo.database.push_subscriptions.delete_one.assert_called_once_with({"_id": "device"})
    assert repo.database.push_deliveries.update_one.call_count == 1


def test_missing_keys_does_not_query_database():
    repo, settings, now, _ = setup()
    settings.web_push_private_key = None
    send_match_reminders(repo, settings, now)
    repo.many.assert_not_called()


def subscription(endpoint="https://fcm.googleapis.com/test"):
    return Subscription(
        endpoint=endpoint,
        keys={
            name: base64.urlsafe_b64encode(bytes(size)).decode()
            for name, size in (("auth", 16), ("p256dh", 65))
        },
    )


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://fcm.googleapis.com/test",
        "https://127.0.0.1/test",
        "https://fcm.googleapis.com.evil.com/test",
        "https://user@fcm.googleapis.com/test",
    ],
)
def test_untrusted_push_endpoints_are_rejected(endpoint):
    with pytest.raises(ValidationError):
        subscription(endpoint)


def test_subscription_is_bound_to_authenticated_user():
    db = Mock()
    body = subscription()
    subscribe(body, SimpleNamespace(id="user"), db)
    assert db.push_subscriptions.update_one.call_args.args[1]["$set"]["user_id"] == "user"
    unsubscribe(body, SimpleNamespace(id="user"), db)
    assert db.push_subscriptions.delete_one.call_args.args[0]["user_id"] == "user"


def test_rescheduled_match_has_a_new_delivery_identity():
    repo, settings, now, match = setup()
    with patch("app.services.push_notifications.webpush"):
        send_match_reminders(repo, settings, now)
        first = repo.database.push_deliveries.update_one.call_args_list[0].args[0]["_id"]
        repo.database.push_deliveries.reset_mock()
        match["date"] += timedelta(minutes=10)
        send_match_reminders(repo, settings, now + timedelta(minutes=10))
        second = repo.database.push_deliveries.update_one.call_args_list[0].args[0]["_id"]
    assert first != second


def test_temporary_network_failure_keeps_subscription_for_retry():
    repo, settings, now, _ = setup()
    with patch("app.services.push_notifications.webpush", side_effect=TimeoutError()):
        send_match_reminders(repo, settings, now)
    repo.database.push_subscriptions.delete_one.assert_not_called()
    assert repo.database.push_deliveries.update_one.call_count == 1
