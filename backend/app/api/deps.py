from __future__ import annotations

from fastapi import Header, HTTPException, status

from ..auth import verify_token
from ..domain.errors import GameNotFoundError, PlayerNotFoundError
from ..domain.models import Game, Player
from ..state import game_service


def get_current_player(
    code: str,
    authorization: str | None = Header(default=None),
) -> tuple[Game, Player]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token manquant.")

    token = authorization.removeprefix("Bearer ").strip()
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalide.")

    if payload["game_code"] != code.upper():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalide pour cette partie.")

    try:
        return game_service.get_player(code, payload["player_id"])
    except (GameNotFoundError, PlayerNotFoundError) as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
