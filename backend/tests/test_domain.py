import pytest

from app.domain.errors import (
    InvalidGameStateError,
    InvalidRolesConfigError,
    NotHostError,
    PseudoTakenError,
)
from app.domain.models import GameStatus
from app.domain.roles import Role
from app.domain.service import GameService
from app.nao.controller import StubNaoController


@pytest.fixture
def service():
    return GameService(StubNaoController())


def _fill_players(service, game, count):
    for i in range(count):
        service.join_game(game.code, f"joueur{i}")


def test_create_game_has_no_players(service):
    game, host_id = service.create_game()
    assert host_id == game.host_id
    assert len(game.players) == 0


def test_join_adds_a_player_not_the_host(service):
    game, host_id = service.create_game()
    game, bob = service.join_game(game.code, "Bob")

    assert len(game.players) == 1
    assert bob.id != host_id
    assert bob.id in game.players


def test_join_rejects_duplicate_pseudo(service):
    game, _host_id = service.create_game()
    service.join_game(game.code, "Alice")
    with pytest.raises(PseudoTakenError):
        service.join_game(game.code, "alice")


def test_only_host_can_update_roles(service):
    game, _host_id = service.create_game()
    game, bob = service.join_game(game.code, "Bob")

    with pytest.raises(NotHostError):
        service.update_roles_config(game.code, bob.id, {Role.LOUP_GAROU: 1})


def test_start_requires_matching_role_sum(service):
    game, host_id = service.create_game()
    _fill_players(service, game, 5)

    service.update_roles_config(
        game.code,
        host_id,
        {Role.LOUP_GAROU: 1, Role.VOYANTE: 1, Role.SORCIERE: 1, Role.VILLAGEOIS: 1},  # sums to 4
    )

    with pytest.raises(InvalidRolesConfigError):
        service.start_game(game.code, host_id)


def test_start_requires_minimum_players(service):
    game, host_id = service.create_game()
    service.update_roles_config(game.code, host_id, {Role.LOUP_GAROU: 1})

    with pytest.raises(InvalidRolesConfigError):
        service.start_game(game.code, host_id)


def test_start_assigns_roles_to_players_only(service):
    game, host_id = service.create_game()
    _fill_players(service, game, 5)

    config = {Role.LOUP_GAROU: 1, Role.VOYANTE: 1, Role.SORCIERE: 1, Role.VILLAGEOIS: 2}
    service.update_roles_config(game.code, host_id, config)

    game = service.start_game(game.code, host_id)

    assert game.status == GameStatus.ROLES_ASSIGNED
    assert len(game.players) == 5
    assigned = [p.role for p in game.players.values()]
    expected = [role for role, count in config.items() for _ in range(count)]
    assert sorted(assigned, key=str) == sorted(expected, key=str)


def test_cannot_start_twice(service):
    game, host_id = service.create_game()
    _fill_players(service, game, 5)
    service.update_roles_config(
        game.code,
        host_id,
        {Role.LOUP_GAROU: 1, Role.VOYANTE: 1, Role.SORCIERE: 1, Role.VILLAGEOIS: 2},
    )
    service.start_game(game.code, host_id)

    with pytest.raises(InvalidGameStateError):
        service.start_game(game.code, host_id)


def test_join_rejected_after_start(service):
    game, host_id = service.create_game()
    _fill_players(service, game, 5)
    service.update_roles_config(
        game.code,
        host_id,
        {Role.LOUP_GAROU: 1, Role.VOYANTE: 1, Role.SORCIERE: 1, Role.VILLAGEOIS: 2},
    )
    service.start_game(game.code, host_id)

    with pytest.raises(InvalidGameStateError):
        service.join_game(game.code, "LateJoiner")


def test_role_suggestion_updates_until_customized(service):
    game, host_id = service.create_game()
    assert sum(game.roles_config.values()) == 0

    game, _alice = service.join_game(game.code, "Alice")
    assert sum(game.roles_config.values()) == 1

    service.update_roles_config(game.code, host_id, {Role.VILLAGEOIS: 1})
    game, _bob = service.join_game(game.code, "Bob")
    # Once the host customizes the config, joining players no longer overwrite it.
    assert sum(game.roles_config.values()) == 1
