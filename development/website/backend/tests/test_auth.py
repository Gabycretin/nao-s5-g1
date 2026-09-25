from app.auth import issue_token, verify_token


def test_round_trip():
    token = issue_token("ABC123", "player-1")
    payload = verify_token(token)
    assert payload == {"game_code": "ABC123", "player_id": "player-1"}


def test_tampered_token_rejected():
    token = issue_token("ABC123", "player-1")
    body, signature = token.split(".", 1)
    tampered = f"{body}.{signature[:-1]}x"
    assert verify_token(tampered) is None


def test_garbage_token_rejected():
    assert verify_token("not-a-valid-token") is None
