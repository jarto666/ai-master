from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.db import db


async def get_or_create_user(*, email: str, name: Optional[str] = None) -> Dict[str, Any]:
    users = db.get_collection("users")

    # Try to find existing user by email
    existing = await users.find_one({"email": email})
    if existing:
        # Update name if provided and changed
        if name and name != existing.get("name"):
            await users.update_one(
                {"_id": existing["_id"]},
                {"$set": {"name": name, "updated_at": datetime.now(tz=timezone.utc)}},
            )
            existing["name"] = name
        return existing

    # Create new user
    now = datetime.now(tz=timezone.utc)
    doc: Dict[str, Any] = {
        "email": email,
        "name": name,
        "created_at": now,
        "updated_at": now,
    }
    result = await users.insert_one(doc)
    created = await users.find_one({"_id": result.inserted_id})
    assert created is not None
    return created


