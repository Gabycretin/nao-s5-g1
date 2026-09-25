from __future__ import annotations

import random

from ..config import MIN_PLAYERS
from ..nao.controller import NaoController
from .errors import (
    GameNotFoundError,
    InvalidGameStateError,
    InvalidPseudoError,
    InvalidRolesConfigError,
    NotHostError,
    PlayerNotFoundError,
    PseudoTakenError,
)
from .models import Game, GameStatus, Player
from .roles import Role, suggest_role_config


class GameService:
    """Owns every game in memory and enforces the lobby -> roles-assigned rules.

    No persistence: games live only for the lifetime of the server process,
    which matches the "one-shot before the game starts" scope of the site.
    """

    def __init__(self, nao_controller: NaoController) -> None:
        self._games: dict[str, Game] = {}
        self._nao = nao_controller

    def create_game(self) -> tuple[Game, str]:
        """Creates a game for a host device (the PC). The host is never a
        player: it never receives a role and doesn't count towards MIN_PLAYERS.
        Only players who `join_game` afterwards (the phones) play.
        """
        game = Game.create()
        game.roles_config = suggest_role_config(0)
        self._games[game.code] = game
        self._nao.announce_game_created(game.code)
        return game, game.host_id

    def join_game(self, code: str, pseudo: str) -> tuple[Game, Player]:
        game = self._get_game(code)
        if game.status != GameStatus.LOBBY:
            raise InvalidGameStateError("La partie a déjà démarré.")

        clean_pseudo = pseudo.strip()
        if not clean_pseudo:
            raise InvalidPseudoError("Le pseudo ne peut pas être vide.")
        if game.pseudo_taken(clean_pseudo):
            raise PseudoTakenError(f"Le pseudo '{clean_pseudo}' est déjà pris dans cette partie.")

        player = Player.create(clean_pseudo)
        game.players[player.id] = player
        if not game.roles_config_customized:
            game.roles_config = suggest_role_config(len(game.players))
        return game, player

    def update_roles_config(self, code: str, caller_id: str, config: dict[Role, int]) -> Game:
        game = self._get_game(code)
        self._require_host(game, caller_id)
        if game.status != GameStatus.LOBBY:
            raise InvalidGameStateError("La partie a déjà démarré.")
        if any(count < 0 for count in config.values()):
            raise InvalidRolesConfigError("Le nombre de joueurs par rôle ne peut pas être négatif.")

        game.roles_config = {role: config.get(role, 0) for role in Role}
        game.roles_config_customized = True
        return game

    def start_game(self, code: str, caller_id: str) -> Game:
        game = self._get_game(code)
        self._require_host(game, caller_id)
        if game.status != GameStatus.LOBBY:
            raise InvalidGameStateError("La partie a déjà démarré.")
        if len(game.players) < MIN_PLAYERS:
            raise InvalidRolesConfigError(
                f"Il faut au moins {MIN_PLAYERS} joueurs pour démarrer "
                f"(actuellement {len(game.players)})."
            )

        total_roles = sum(game.roles_config.values())
        if total_roles != len(game.players):
            raise InvalidRolesConfigError(
                f"La distribution des rôles ({total_roles}) ne correspond pas "
                f"au nombre de joueurs ({len(game.players)})."
            )

        role_pool: list[Role] = []
        for role, count in game.roles_config.items():
            role_pool.extend([role] * count)
        random.shuffle(role_pool)

        for player, role in zip(game.players.values(), role_pool):
            player.role = role

        game.status = GameStatus.ROLES_ASSIGNED
        self._nao.announce_roles_assigned(game.code)
        return game

    def get_state(self, code: str) -> Game:
        return self._get_game(code)

    def get_player(self, code: str, player_id: str) -> tuple[Game, Player]:
        game = self._get_game(code)
        player = game.players.get(player_id)
        if player is None:
            raise PlayerNotFoundError("Joueur introuvable dans cette partie.")
        return game, player

    def require_host(self, code: str, caller_id: str) -> Game:
        game = self._get_game(code)
        self._require_host(game, caller_id)
        return game

    def _get_game(self, code: str) -> Game:
        game = self._games.get(code.upper())
        if game is None:
            raise GameNotFoundError(f"Aucune partie avec le code '{code}'.")
        return game

    def _require_host(self, game: Game, caller_id: str) -> None:
        if caller_id != game.host_id:
            raise NotHostError("Seul l'hôte peut effectuer cette action.")
