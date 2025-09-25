from __future__ import annotations

import json
from collections import defaultdict
from typing import Dict, Set

from app.core.auth import AUTH_COOKIE_NAME, INTERNAL_JWT_ALGORITHM, INTERNAL_JWT_SECRET
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jwt import InvalidTokenError
from jwt import decode as jwt_decode

router = APIRouter()

# In-memory websocket registry mapping userId to a set of active sockets
_ws_connections: Dict[str, Set[WebSocket]] = defaultdict(set)


def _get_user_id_from_websocket(websocket: WebSocket) -> str:
    token = websocket.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        raise RuntimeError("Missing token")
    try:
        claims = jwt_decode(
            token,
            INTERNAL_JWT_SECRET,
            algorithms=[INTERNAL_JWT_ALGORITHM],
            options={"require": ["exp", "iat"]},
        )
        user_id = str(claims.get("id") or "")
        if not user_id:
            raise RuntimeError("Invalid token payload")
        return user_id
    except InvalidTokenError as e:
        raise RuntimeError("Invalid token") from e


async def broadcast_job_update_to_user(user_id: str, job_doc: dict) -> None:
    if not user_id:
        return
    sockets = list(_ws_connections.get(user_id, set()))
    if not sockets:
        return
    payload = json.dumps({"type": "job.update", "job": job_doc}, default=str)
    for ws in sockets:
        try:
            await ws.send_text(payload)
        except Exception:
            try:
                _ws_connections[user_id].discard(ws)
            except Exception:
                pass


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        user_id = _get_user_id_from_websocket(websocket)
    except Exception:
        await websocket.close(code=4401)
        return
    _ws_connections[user_id].add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        try:
            _ws_connections[user_id].discard(websocket)
            if not _ws_connections[user_id]:
                _ws_connections.pop(user_id, None)
        except Exception:
            pass
