from __future__ import annotations

import random
import string
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from .roles import Role


class GameStatus(str, Enum):
    LOBBY = "LOBBY"
    ROLES_ASSIGNED = "ROLES_ASSIGNED"


def generate_game_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=6))


@dataclass
class Player:
    id: str
    pseudo: str
    is_host: bool = False
    role: Role | None = None

    @staticmethod
    def create(pseudo: str, is_host: bool = False) -> "Player":
        return Player(id=uuid.uuid4().hex, pseudo=pseudo, is_host=is_host)


@dataclass
class Game:
    id: str
    code: str
    status: GameStatus = GameStatus.LOBBY
    players: dict[str, Player] = field(default_factory=dict)
    roles_config: dict[Role, int] = field(default_factory=dict)
    roles_config_customized: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def create() -> "Game":
        return Game(id=uuid.uuid4().hex, code=generate_game_code())

    def pseudo_taken(self, pseudo: str) -> bool:
        return any(p.pseudo.lower() == pseudo.lower() for p in self.players.values())
