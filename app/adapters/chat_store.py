from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

from pymongo import ASCENDING, MongoClient
from pymongo.errors import PyMongoError

from app.core.config import get_settings


def save_message(message: dict[str, Any]) -> None:
    url = get_settings().mongodb_url
    if not url:
        return
    with suppress(PyMongoError):
        client: MongoClient[dict[str, Any]] = MongoClient(url, serverSelectionTimeoutMS=300)
        collection = client.relayroute.chat_messages
        collection.create_index([("delivery_id", ASCENDING), ("sent_at", ASCENDING)])
        collection.insert_one(message)
        client.close()


def message(*, delivery_id: str, sender_id: str, sender_role: str, text: str) -> dict[str, Any]:
    return {
        "delivery_id": delivery_id,
        "sender_id": sender_id,
        "sender_role": sender_role,
        "text": text,
        "sent_at": datetime.now(UTC),
    }
