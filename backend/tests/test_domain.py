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


def test_create_and_join(service):
    game, host = service.create_game("Alice")
    assert host.is_host
    assert len(game.players) == 1

    game, bob = service.join_game(game.code, "Bob")
    assert len(game.players) == 2
    assert not bob.is_host


def test_join_rejects_duplicate_pseudo(service):
    game, _ = service.create_game("Alice")
    with pytest.raises(PseudoTakenError):
        service.join_game(game.code, "alice")


def test_only_host_can_update_roles(service):
    game, _host = service.create_game("Alice")
    game, bob = service.join_game(game.code, "Bob")

    with pytest.raises(NotHostError):
        service.update_roles_config(game.code, bob.id, {Role.LOUP_GAROU: 1})


def test_start_requires_matching_role_sum(service):
    game, host = service.create_game("Alice")
    _fill_players(service, game, 4)  # 5 players total

    service.update_roles_config(
        game.code,
        host.id,
        {Role.LOUP_GAROU: 1, Role.VOYANTE: 1, Role.SORCIERE: 1, Role.VILLAGEOIS: 1},  # sums to 4
    )

    with pytest.raises(InvalidRolesConfigError):
        service.start_game(game.code, host.id)


def test_start_requires_minimum_players(service):
    game, host = service.create_game("Alice")
    service.update_roles_config(game.code, host.id, {Role.LOUP_GAROU: 1})

    with pytest.raises(InvalidRolesConfigError):
        service.start_game(game.code, host.id)


def test_start_assigns_roles_matching_config(service):
    game, host = service.create_game("Alice")
    _fill_players(service, game, 4)  # 5 players total

    config = {Role.LOUP_GAROU: 1, Role.VOYANTE: 1, Role.SORCIERE: 1, Role.VILLAGEOIS: 2}
    service.update_roles_config(game.code, host.id, config)

    game = service.start_game(game.code, host.id)

    assert game.status == GameStatus.ROLES_ASSIGNED
    assigned = [p.role for p in game.players.values()]
    expected = [role for role, count in config.items() for _ in range(count)]
    assert sorted(assigned, key=str) == sorted(expected, key=str)


def test_cannot_start_twice(service):
    game, host = service.create_game("Alice")
    _fill_players(service, game, 4)
    service.update_roles_config(
        game.code,
        host.id,
        {Role.LOUP_GAROU: 1, Role.VOYANTE: 1, Role.SORCIERE: 1, Role.VILLAGEOIS: 2},
    )
    service.start_game(game.code, host.id)

    with pytest.raises(InvalidGameStateError):
        service.start_game(game.code, host.id)


def test_join_rejected_after_start(service):
    game, host = service.create_game("Alice")
    _fill_players(service, game, 4)
    service.update_roles_config(
        game.code,
        host.id,
        {Role.LOUP_GAROU: 1, Role.VOYANTE: 1, Role.SORCIERE: 1, Role.VILLAGEOIS: 2},
    )
    service.start_game(game.code, host.id)

    with pytest.raises(InvalidGameStateError):
        service.join_game(game.code, "LateJoiner")


def test_role_suggestion_updates_until_customized(service):
    game, host = service.create_game("Alice")
    assert sum(game.roles_config.values()) == 1

    game, _bob = service.join_game(game.code, "Bob")
    assert sum(game.roles_config.values()) == 2

    service.update_roles_config(game.code, host.id, {Role.VILLAGEOIS: 2})
    game, _carol = service.join_game(game.code, "Carol")
    # Once the host customizes the config, joining players no longer overwrite it.
    assert sum(game.roles_config.values()) == 2
