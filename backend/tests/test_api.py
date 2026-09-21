from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _create_and_fill(total_players=5):
    resp = client.post("/api/games")
    assert resp.status_code == 200
    data = resp.json()
    code, host_token = data["code"], data["token"]

    tokens = []
    for i in range(total_players):
        r = client.post(f"/api/games/{code}/join", json={"pseudo": f"P{i}"})
        assert r.status_code == 200
        tokens.append(r.json()["token"])

    return code, host_token, tokens


def test_create_has_no_players_until_joins():
    resp = client.post("/api/games")
    code = resp.json()["code"]

    state = client.get(f"/api/games/{code}/state").json()
    assert state["players"] == []

    client.post(f"/api/games/{code}/join", json={"pseudo": "Alice"})
    state = client.get(f"/api/games/{code}/state").json()
    assert len(state["players"]) == 1
    assert state["players"][0]["pseudo"] == "Alice"


def test_only_host_can_configure_and_start_and_roles_are_isolated():
    code, host_token, tokens = _create_and_fill()

    resp = client.patch(
        f"/api/games/{code}/roles",
        json={"config": {"LOUP_GAROU": 1, "VOYANTE": 1, "SORCIERE": 1, "VILLAGEOIS": 2}},
        headers={"Authorization": f"Bearer {host_token}"},
    )
    assert resp.status_code == 200

    # A player token cannot configure roles or start the game.
    forbidden = client.patch(
        f"/api/games/{code}/roles",
        json={"config": {"VILLAGEOIS": 5}},
        headers={"Authorization": f"Bearer {tokens[0]}"},
    )
    assert forbidden.status_code == 403

    forbidden_start = client.post(
        f"/api/games/{code}/start", headers={"Authorization": f"Bearer {tokens[0]}"}
    )
    assert forbidden_start.status_code == 403

    started = client.post(
        f"/api/games/{code}/start", headers={"Authorization": f"Bearer {host_token}"}
    )
    assert started.status_code == 200
    assert started.json()["status"] == "ROLES_ASSIGNED"

    # The host itself has no role: it never joined as a player.
    host_me = client.get(f"/api/games/{code}/me", headers={"Authorization": f"Bearer {host_token}"})
    assert host_me.status_code == 404

    valid_roles = {"LOUP_GAROU", "VOYANTE", "SORCIERE", "VILLAGEOIS"}
    for token in tokens:
        me = client.get(f"/api/games/{code}/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["role"]["role"] in valid_roles


def test_me_rejects_missing_or_invalid_token():
    code, _host_token, tokens = _create_and_fill()

    resp = client.get(f"/api/games/{code}/me")
    assert resp.status_code == 401

    resp = client.get(f"/api/games/{code}/me", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401

    resp = client.get(f"/api/games/{code}/me", headers={"Authorization": f"Bearer {tokens[0]}"})
    assert resp.status_code == 200


def test_start_fails_below_minimum_players():
    resp = client.post("/api/games")
    data = resp.json()
    code, host_token = data["code"], data["token"]

    started = client.post(f"/api/games/{code}/start", headers={"Authorization": f"Bearer {host_token}"})
    assert started.status_code == 422
