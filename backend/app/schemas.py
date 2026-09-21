from __future__ import annotations

from pydantic import BaseModel, Field

from .domain.roles import Role


class CreateGameRequest(BaseModel):
    pseudo: str = Field(min_length=1, max_length=30)


class JoinGameRequest(BaseModel):
    pseudo: str = Field(min_length=1, max_length=30)


class AuthResponse(BaseModel):
    token: str
    player_id: str
    code: str


class RolesConfigRequest(BaseModel):
    config: dict[Role, int]


class PlayerPublic(BaseModel):
    id: str
    pseudo: str
    is_host: bool


class StateResponse(BaseModel):
    code: str
    status: str
    players: list[PlayerPublic]
    roles_config: dict[Role, int]
    min_players: int


class RoleInfo(BaseModel):
    role: Role
    label: str
    camp: str
    description: str


class MeResponse(BaseModel):
    player_id: str
    pseudo: str
    is_host: bool
    status: str
    role: RoleInfo | None = None
