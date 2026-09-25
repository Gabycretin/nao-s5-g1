from __future__ import annotations

from .domain.service import GameService
from .nao.controller import StubNaoController
from .ws_manager import ConnectionManager

nao_controller = StubNaoController()
game_service = GameService(nao_controller)
ws_manager = ConnectionManager()
