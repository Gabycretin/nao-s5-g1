from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _create_and_fill(total_players=5):
    resp = client.post("/api/games", json={"pseudo": "Alice"})
    assert resp.status_code == 200
    data = resp.json()
    code, host_token = data["code"], data["token"]

    tokens = [host_token]
    for i in range(total_players - 1):
        r = client.post(f"/api/games/{code}/join", json={"pseudo": f"P{i}"})
        assert r.status_code == 200
        tokens.append(r.json()["token"])

    return code, tokens


def test_create_join_and_state():
    code, _tokens = _create_and_fill()
    resp = client.get(f"/api/games/{code}/state")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["players"]) == 5
    assert body["status"] == "LOBBY"


def test_only_host_can_start_and_roles_are_isolated():
    code, tokens = _create_and_fill()
    host_token, other_token = tokens[0], tokens[1]

    resp = client.patch(
        f"/api/games/{code}/roles",
        json={"config": {"LOUP_GAROU": 1, "VOYANTE": 1, "SORCIERE": 1, "VILLAGEOIS": 2}},
        headers={"Authorization": f"Bearer {host_token}"},
    )
    assert resp.status_code == 200

    forbidden = client.post(
        f"/api/games/{code}/start", headers={"Authorization": f"Bearer {other_token}"}
    )
    assert forbidden.status_code == 403

    started = client.post(
        f"/api/games/{code}/start", headers={"Authorization": f"Bearer {host_token}"}
    )
    assert started.status_code == 200
    assert started.json()["status"] == "ROLES_ASSIGNED"

    me_host = client.get(f"/api/games/{code}/me", headers={"Authorization": f"Bearer {host_token}"})
    me_other = client.get(f"/api/games/{code}/me", headers={"Authorization": f"Bearer {other_token}"})
    assert me_host.status_code == 200
    assert me_other.status_code == 200

    valid_roles = {"LOUP_GAROU", "VOYANTE", "SORCIERE", "VILLAGEOIS"}
    assert me_host.json()["role"]["role"] in valid_roles
    assert me_other.json()["role"]["role"] in valid_roles


def test_me_rejects_missing_or_invalid_token():
    code, _tokens = _create_and_fill()

    resp = client.get(f"/api/games/{code}/me")
    assert resp.status_code == 401

    resp = client.get(f"/api/games/{code}/me", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


def test_start_fails_below_minimum_players():
    resp = client.post("/api/games", json={"pseudo": "Solo"})
    data = resp.json()
    code, token = data["code"], data["token"]

    started = client.post(f"/api/games/{code}/start", headers={"Authorization": f"Bearer {token}"})
    assert started.status_code == 422
