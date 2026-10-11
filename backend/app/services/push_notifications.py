"""Durable five-minute reminders, independent of open browser sessions."""

import hashlib
import json
import logging
from datetime import timedelta
from math import ceil

from pymongo.errors import DuplicateKeyError
from pywebpush import WebPushException, webpush

from app.models.game import utcnow

logger = logging.getLogger(__name__)


def send_match_reminders(repo, settings, now=None):
    if (
        not settings.web_push_private_key
        or not settings.web_push_public_key
        or not settings.web_push_subject
    ):
        return
    now = now or utcnow()
    db = repo.database
    # At most thirty seconds late at the normal maintenance cadence; retry until kickoff.
    for collection in ("matches", "competition_matches", "friendly_matches"):
        matches = repo.many(
            collection,
            {"status": "scheduled", "date": {"$gt": now, "$lte": now + timedelta(minutes=5)}},
            limit=None,
        )
        for match in matches:
            for club_id in (match["home_club_id"], match["away_club_id"]):
                club = repo.find("clubs", {"_id": club_id, "active": {"$ne": False}})
                if not club or not club.get("owner_user_id"):
                    continue
                for subscription in repo.many(
                    "push_subscriptions", {"user_id": str(club["owner_user_id"])}, limit=None
                ):
                    key = f"{collection}:{match['_id']}:{match['date'].isoformat()}"
                    key += f":{subscription['_id']}"
                    identity = hashlib.sha256(key.encode()).hexdigest()
                    try:
                        claim = db.push_deliveries.update_one(
                            {
                                "_id": identity,
                                "sent": {"$ne": True},
                                "$or": [
                                    {"lease_until": {"$exists": False}},
                                    {"lease_until": {"$lte": now}},
                                ],
                            },
                            {
                                "$set": {
                                    "lease_until": now + timedelta(seconds=60),
                                    "expires_at": match["date"] + timedelta(days=7),
                                }
                            },
                            upsert=True,
                        )
                    except DuplicateKeyError:
                        continue
                    if not claim.modified_count and not claim.upserted_id:
                        continue
                    try:
                        minutes = ceil((match["date"] - now).total_seconds() / 60)
                        webpush(
                            subscription_info=subscription["subscription"],
                            data=json.dumps(
                                {
                                    "title": "Sua partida vai começar",
                                    "body": f"{club['name']}: partida em {minutes} minuto(s).",
                                    "match_id": str(match["_id"]),
                                }
                            ),
                            vapid_private_key=settings.web_push_private_key.get_secret_value(),
                            vapid_claims={"sub": settings.web_push_subject},
                            ttl=max(1, int((match["date"] - now).total_seconds())),
                            timeout=10,
                        )
                        db.push_deliveries.update_one({"_id": identity}, {"$set": {"sent": True}})
                    except WebPushException as exc:
                        if exc.response is not None and exc.response.status_code in (404, 410):
                            db.push_subscriptions.delete_one({"_id": subscription["_id"]})
                        logger.warning("Push reminder failed (%s)", type(exc).__name__)
                    except Exception as exc:
                        logger.warning("Push reminder failed (%s)", type(exc).__name__)
