import os

MIN_PLAYERS = int(os.environ.get("MIN_PLAYERS", "5"))
TOKEN_SECRET = os.environ.get("TOKEN_SECRET", "dev-secret-change-me")
