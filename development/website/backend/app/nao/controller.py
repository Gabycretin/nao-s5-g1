from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger("nao")


class NaoController(Protocol):
    """Abstraction between the game logic and however NAO is actually driven.

    GameService only depends on this Protocol, so a real NAOqi-backed
    implementation can replace StubNaoController later without any change
    to the game domain code.
    """

    def announce_game_created(self, code: str) -> None: ...

    def announce_roles_assigned(self, code: str) -> None: ...


class StubNaoController:
    """Default NaoController: logs instructions instead of talking to a robot."""

    def __init__(self) -> None:
        self.last_instruction: dict[str, str] | None = None

    def announce_game_created(self, code: str) -> None:
        self._emit("game_created", f"Nouvelle partie créée, code {code}.")

    def announce_roles_assigned(self, code: str) -> None:
        self._emit(
            "roles_assigned",
            "Les rôles ont été distribués, chaque joueur peut consulter son écran.",
        )

    def _emit(self, event: str, message: str) -> None:
        self.last_instruction = {"event": event, "message": message}
        logger.info("[NAO] %s: %s", event, message)
