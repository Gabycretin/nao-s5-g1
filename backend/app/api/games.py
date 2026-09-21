from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from .. import schemas
from ..auth import issue_token
from ..config import MIN_PLAYERS
from ..domain.errors import (
    DomainError,
    GameNotFoundError,
    InvalidGameStateError,
    InvalidPseudoError,
    InvalidRolesConfigError,
    NotHostError,
    PlayerNotFoundError,
    PseudoTakenError,
)
from ..domain.models import Game, Player
from ..domain.roles import ROLE_INFO
from ..state import game_service, ws_manager
from .deps import get_current_player

router = APIRouter(prefix="/api/games", tags=["games"])

_ERROR_STATUS: dict[type[DomainError], int] = {
    GameNotFoundError: status.HTTP_404_NOT_FOUND,
    PlayerNotFoundError: status.HTTP_404_NOT_FOUND,
    PseudoTakenError: status.HTTP_409_CONFLICT,
    InvalidPseudoError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    NotHostError: status.HTTP_403_FORBIDDEN,
    InvalidGameStateError: status.HTTP_409_CONFLICT,
    InvalidRolesConfigError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def _as_http_error(exc: DomainError) -> HTTPException:
    return HTTPException(_ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST), str(exc))


def _public_state(game: Game) -> schemas.StateResponse:
    return schemas.StateResponse(
        code=game.code,
        status=game.status,
        players=[
            schemas.PlayerPublic(id=p.id, pseudo=p.pseudo, is_host=p.is_host)
            for p in game.players.values()
        ],
        roles_config=game.roles_config,
        min_players=MIN_PLAYERS,
    )


@router.post("", response_model=schemas.AuthResponse)
def create_game(body: schemas.CreateGameRequest) -> schemas.AuthResponse:
    try:
        game, host = game_service.create_game(body.pseudo)
    except DomainError as exc:
        raise _as_http_error(exc) from exc

    token = issue_token(game.code, host.id)
    return schemas.AuthResponse(token=token, player_id=host.id, code=game.code)


@router.post("/{code}/join", response_model=schemas.AuthResponse)
async def join_game(code: str, body: schemas.JoinGameRequest) -> schemas.AuthResponse:
    try:
        game, player = game_service.join_game(code, body.pseudo)
    except DomainError as exc:
        raise _as_http_error(exc) from exc

    token = issue_token(game.code, player.id)
    await ws_manager.broadcast(game.code, "player_joined", _public_state(game).model_dump(mode="json"))
    return schemas.AuthResponse(token=token, player_id=player.id, code=game.code)


@router.get("/{code}/state", response_model=schemas.StateResponse)
def get_state(code: str) -> schemas.StateResponse:
    try:
        game = game_service.get_state(code)
    except DomainError as exc:
        raise _as_http_error(exc) from exc
    return _public_state(game)


@router.patch("/{code}/roles", response_model=schemas.StateResponse)
async def update_roles(
    body: schemas.RolesConfigRequest,
    current: tuple[Game, Player] = Depends(get_current_player),
) -> schemas.StateResponse:
    game, player = current
    try:
        game = game_service.update_roles_config(game.code, player.id, body.config)
    except DomainError as exc:
        raise _as_http_error(exc) from exc

    state = _public_state(game)
    await ws_manager.broadcast(game.code, "roles_config_updated", state.model_dump(mode="json"))
    return state


@router.post("/{code}/start", response_model=schemas.StateResponse)
async def start_game(
    current: tuple[Game, Player] = Depends(get_current_player),
) -> schemas.StateResponse:
    game, player = current
    try:
        game = game_service.start_game(game.code, player.id)
    except DomainError as exc:
        raise _as_http_error(exc) from exc

    state = _public_state(game)
    await ws_manager.broadcast(game.code, "roles_assigned", state.model_dump(mode="json"))
    return state


@router.get("/{code}/me", response_model=schemas.MeResponse)
def get_me(current: tuple[Game, Player] = Depends(get_current_player)) -> schemas.MeResponse:
    game, player = current
    role_info = None
    if player.role is not None:
        info = ROLE_INFO[player.role]
        role_info = schemas.RoleInfo(
            role=player.role,
            label=info["label"],
            camp=info["camp"],
            description=info["description"],
        )
    return schemas.MeResponse(
        player_id=player.id,
        pseudo=player.pseudo,
        is_host=player.is_host,
        status=game.status,
        role=role_info,
    )
