from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import TypedDict

from .config import TOKEN_SECRET


class TokenPayload(TypedDict):
    game_code: str
    player_id: str


def _sign(data: bytes) -> str:
    signature = hmac.new(TOKEN_SECRET.encode(), data, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(signature).decode().rstrip("=")


def issue_token(game_code: str, player_id: str) -> str:
    payload = json.dumps(
        {"game_code": game_code, "player_id": player_id}, separators=(",", ":")
    ).encode()
    body = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    return f"{body}.{_sign(payload)}"


def verify_token(token: str) -> TokenPayload | None:
    try:
        body, signature = token.split(".", 1)
        padded_body = body + "=" * (-len(body) % 4)
        payload = base64.urlsafe_b64decode(padded_body.encode())
        if not hmac.compare_digest(signature, _sign(payload)):
            return None
        data = json.loads(payload)
        return {"game_code": data["game_code"], "player_id": data["player_id"]}
    except (ValueError, KeyError, json.JSONDecodeError):
        return None
