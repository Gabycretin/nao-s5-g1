from __future__ import annotations

from fastapi import Header, HTTPException, status

from ..auth import verify_token
from ..domain.errors import GameNotFoundError, NotHostError, PlayerNotFoundError
from ..domain.models import Game, Player
from ..state import game_service


def _authenticated_principal(code: str, authorization: str | None) -> str:
    """Verifies the bearer token and returns the caller's id (host or player)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token manquant.")

    token = authorization.removeprefix("Bearer ").strip()
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalide.")

    if payload["game_code"] != code.upper():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalide pour cette partie.")

    return payload["player_id"]


def get_current_host(
    code: str,
    authorization: str | None = Header(default=None),
) -> Game:
    principal_id = _authenticated_principal(code, authorization)
    try:
        return game_service.require_host(code, principal_id)
    except GameNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except NotHostError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc


def get_current_player(
    code: str,
    authorization: str | None = Header(default=None),
) -> tuple[Game, Player]:
    principal_id = _authenticated_principal(code, authorization)
    try:
        return game_service.get_player(code, principal_id)
    except (GameNotFoundError, PlayerNotFoundError) as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
