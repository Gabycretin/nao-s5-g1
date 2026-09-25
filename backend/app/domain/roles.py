from __future__ import annotations

from enum import Enum


class Camp(str, Enum):
    VILLAGE = "VILLAGE"
    LOUPS = "LOUPS"


class Role(str, Enum):
    LOUP_GAROU = "LOUP_GAROU"
    VILLAGEOIS = "VILLAGEOIS"
    VOYANTE = "VOYANTE"
    SORCIERE = "SORCIERE"


ROLE_INFO: dict[Role, dict] = {
    Role.LOUP_GAROU: {
        "label": "Loup-Garou",
        "camp": Camp.LOUPS,
        "description": "Chaque nuit, vous vous réveillez avec les autres loups pour désigner une victime.",
    },
    Role.VILLAGEOIS: {
        "label": "Villageois",
        "camp": Camp.VILLAGE,
        "description": "Vous n'avez pas de pouvoir particulier. Démasquez les loups-garous avant qu'il ne soit trop tard.",
    },
    Role.VOYANTE: {
        "label": "Voyante",
        "camp": Camp.VILLAGE,
        "description": "Chaque nuit, vous pouvez découvrir le rôle secret d'un joueur de votre choix.",
    },
    Role.SORCIERE: {
        "label": "Sorcière",
        "camp": Camp.VILLAGE,
        "description": "Vous possédez une potion de vie et une potion de mort, à utiliser une seule fois chacune.",
    },
}


def suggest_role_config(player_count: int) -> dict[Role, int]:
    """Reasonable default distribution for a given player count.

    Kept intentionally simple (no special roles beyond the base catalog);
    the host can always override it manually before starting the game.
    """
    if player_count <= 0:
        return {role: 0 for role in Role}

    n_loups = max(1, round(player_count / 4))
    remaining = max(0, player_count - n_loups)

    n_voyante = 1 if remaining > 0 else 0
    remaining -= n_voyante

    n_sorciere = 1 if remaining > 0 else 0
    remaining -= n_sorciere

    n_villageois = remaining

    return {
        Role.LOUP_GAROU: n_loups,
        Role.VOYANTE: n_voyante,
        Role.SORCIERE: n_sorciere,
        Role.VILLAGEOIS: n_villageois,
    }
