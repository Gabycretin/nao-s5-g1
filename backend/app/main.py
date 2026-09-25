from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.games import router as games_router
from .api.ws import router as ws_router

# INFO is otherwise silenced by the root logger's default WARNING level,
# which would hide every StubNaoController announcement.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

app = FastAPI(title="NAO Loup-Garou — Distribution des rôles")

# Wildcard origin: dev/LAN setup only. Players join from phones on the same
# Wi-Fi as the host machine, which may serve the frontend from any local IP.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(games_router)
app.include_router(ws_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
