# Backend — NAO Loup-Garou

API FastAPI qui gère le **lobby** d'une partie de Loup-Garou : création de partie, arrivée des joueurs, configuration des rôles par l'hôte, tirage aléatoire, et consultation du rôle secret de chacun.

Tout est stocké **en mémoire** (aucune base de données) — les parties disparaissent si le serveur redémarre, ce qui est volontaire pour ce MVP : le site ne sert qu'en tout début de partie.

## Lancer le serveur

```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Documentation interactive générée automatiquement : http://localhost:8000/docs

## Lancer les tests

```powershell
cd backend
.venv\Scripts\python.exe -m pytest -q
```

## Architecture

Organisation en couches, du plus interne au plus externe :

```
domain/    logique métier pure (aucune dépendance à FastAPI)
nao/       abstraction pour piloter NAO plus tard
auth.py    jetons de session signés
schemas.py formats des requêtes/réponses HTTP (Pydantic)
api/       routes REST + WebSocket (branche le domaine au monde extérieur)
state.py   instances uniques partagées par toute l'app
main.py    point d'entrée FastAPI
```

Le principe central : **`domain/` ne sait rien de HTTP**. On pourrait brancher un CLI, un autre framework web, ou des tests directs dessus sans rien changer. C'est `api/` qui traduit les requêtes HTTP en appels au domaine, et les erreurs du domaine en codes HTTP.

## `domain/roles.py` — le catalogue des rôles

Deux enums :

- `Camp` (`VILLAGE` / `LOUPS`)
- `Role` (`LOUP_GAROU`, `VILLAGEOIS`, `VOYANTE`, `SORCIERE`)

`ROLE_INFO` associe à chaque rôle son libellé, son camp et sa description (affichés côté joueur).

`suggest_role_config(player_count)` calcule une répartition par défaut (~1 loup pour 4 joueurs, puis voyante, sorcière, le reste en villageois), que l'hôte peut ensuite modifier manuellement. Elle garantit toujours que la somme des rôles égale exactement le nombre de joueurs.

## `domain/models.py` — les entités

- **`Player`** : id unique, pseudo, `is_host`, `role` (`None` tant que la partie n'a pas démarré).
- **`Game`** : id interne, `code` (6 caractères, ex. `ST50R0`), `status` (`LOBBY` ou `ROLES_ASSIGNED`), dictionnaire de `players`, `roles_config` (combien de chaque rôle), et un flag `roles_config_customized`.

Ce flag est important : tant que l'hôte n'a **jamais** touché manuellement la config, elle se recalcule automatiquement à chaque nouveau joueur (via `suggest_role_config`). Dès que l'hôte modifie la config une fois, elle se fige et n'est plus écrasée par les arrivées suivantes.

## `domain/errors.py` — les erreurs métier

Une hiérarchie d'exceptions Python (`GameNotFoundError`, `PseudoTakenError`, `NotHostError`, `InvalidGameStateError`, `InvalidRolesConfigError`, `InvalidPseudoError`, `PlayerNotFoundError`) toutes héritant de `DomainError`. Le domaine lève ces erreurs sans savoir qu'elles finiront en code HTTP — c'est `api/games.py` qui fait la traduction.

## `domain/service.py` — le cœur : `GameService`

Seule classe qui possède et modifie l'état du jeu (`self._games: dict[str, Game]`). Ses méthodes, dans l'ordre du cycle de vie :

1. **`create_game(host_pseudo)`** — crée une `Game`, ajoute le créateur comme hôte, stocke la partie, prévient NAO (`announce_game_created`).
2. **`join_game(code, pseudo)`** — vérifie que la partie est encore en `LOBBY`, que le pseudo n'est pas vide ni déjà pris, ajoute le joueur, recalcule la suggestion de rôles si elle n'a pas été personnalisée.
3. **`update_roles_config(code, player_id, config)`** — réservé à l'hôte (`_require_host`), remplace la config, marque `roles_config_customized = True`.
4. **`start_game(code, player_id)`** — réservé à l'hôte. Vérifie qu'il y a au moins `MIN_PLAYERS` (5 par défaut) et que la somme des rôles configurés correspond exactement au nombre de joueurs. Construit une liste de rôles (« pool »), la mélange (`random.shuffle`), et distribue un rôle par joueur. Passe le statut à `ROLES_ASSIGNED`, prévient NAO (`announce_roles_assigned`).
5. **`get_state(code)`** / **`get_player(code, player_id)`** — lectures.

Deux méthodes privées font le travail commun : `_get_game` (recherche par code, insensible à la casse) et `_require_host` (vérifie que l'appelant est bien l'hôte).

## `nao/controller.py` — l'abstraction NAO

Un `Protocol` (interface structurelle Python) `NaoController` avec deux méthodes : `announce_game_created` et `announce_roles_assigned`. `GameService` ne connaît que cette interface, jamais une implémentation concrète — c'est de l'**injection de dépendance** simple.

L'implémentation branchée aujourd'hui est `StubNaoController` : elle se contente de logger le message (`[NAO] roles_assigned: ...`) et de garder la dernière instruction en mémoire (`self.last_instruction`). Le jour où le pont NAOqi existera, il suffira d'écrire une nouvelle classe qui respecte ce `Protocol` et de la brancher dans `state.py` — **aucun changement dans `GameService`**.

## `auth.py` — les jetons de session

Pas de base de données d'utilisateurs : à la place, un jeton signé maison (façon JWT simplifié) :

- `issue_token(game_code, player_id)` sérialise `{"game_code": ..., "player_id": ...}` en JSON, l'encode en base64, et calcule une signature HMAC-SHA256 avec un secret serveur (`TOKEN_SECRET`, à définir en variable d'environnement en production). Le jeton final est `<données>.<signature>`.
- `verify_token(token)` recalcule la signature et la compare de façon sûre (`hmac.compare_digest`, résistant aux attaques par timing) avant de faire confiance aux données.

Ce jeton est stocké côté client (`localStorage`) et envoyé dans le header `Authorization: Bearer <token>` à chaque requête qui nécessite de savoir « qui je suis ». C'est ce qui permet à un joueur de revenir consulter son rôle après un refresh, sans compte ni mot de passe.

## `schemas.py` — les formats HTTP (Pydantic)

Chaque endpoint a sa requête et/ou sa réponse typée : `CreateGameRequest`, `JoinGameRequest`, `AuthResponse`, `RolesConfigRequest`, `StateResponse`, `MeResponse`, etc. FastAPI s'en sert pour valider automatiquement les requêtes entrantes (ex. `pseudo` entre 1 et 30 caractères) et sérialiser les réponses en JSON. C'est aussi ce qui génère la doc interactive sur `/docs`.

## `api/deps.py` — la dépendance d'authentification

`get_current_player(code, authorization)` est une **dépendance FastAPI** : elle lit le header `Authorization`, vérifie le jeton, vérifie qu'il correspond bien à la partie demandée dans l'URL (`code`), puis va chercher le joueur correspondant via `game_service.get_player`. Si quoi que ce soit cloche → `HTTPException` 401 ou 404.

Astuce FastAPI utilisée : cette fonction déclare son propre paramètre `code: str`, qui se résout automatiquement depuis le `{code}` de l'URL de la route appelante, même si l'endpoint lui-même ne redéclare pas `code`. Ça évite de dupliquer ce paramètre partout.

## `api/games.py` — les routes REST

| Route | Auth requise | Fait quoi |
|---|---|---|
| `POST /api/games` | non | Crée une partie, renvoie le code + le jeton de l'hôte |
| `POST /api/games/{code}/join` | non | Rejoint, renvoie le jeton du joueur |
| `GET /api/games/{code}/state` | non | État public du lobby (joueurs, statut, config des rôles) |
| `PATCH /api/games/{code}/roles` | oui (hôte) | Modifie la répartition des rôles |
| `POST /api/games/{code}/start` | oui (hôte) | Lance le tirage des rôles |
| `GET /api/games/{code}/me` | oui | Mon pseudo, mon statut d'hôte, **mon** rôle (jamais celui des autres) |

Deux mécanismes transversaux :

- **`_ERROR_STATUS`** — dictionnaire qui mappe chaque type d'erreur métier vers un code HTTP (ex. `NotHostError` → 403, `PseudoTakenError` → 409). `_as_http_error` fait la conversion. C'est ce qui garde le domaine complètement ignorant de HTTP.
- **`_public_state`** — construit la réponse publique d'une partie à partir de l'objet `Game`. C'est volontairement la seule fonction qui a le droit de sérialiser un `Game` en réponse, pour être sûr qu'on n'y glisse jamais le rôle d'un joueur par erreur (le rôle individuel ne sort que par `/me`, jamais par `/state`).

Après chaque action qui change l'état partagé (`join`, `roles`, `start`), la route diffuse aussi l'événement correspondant sur le WebSocket (`ws_manager.broadcast`).

## `ws_manager.py` + `api/ws.py` — le temps réel du lobby

`ConnectionManager` garde en mémoire, pour chaque code de partie, l'ensemble des connexions WebSocket ouvertes (`dict[str, set[WebSocket]]`). `broadcast(code, event, data)` envoie `{"event": ..., "data": ...}` en JSON à tous les onglets connectés à cette partie.

La route `WS /ws/games/{code}` accepte la connexion, puis reste en attente (`receive_text()` en boucle) juste pour détecter la déconnexion — le client n'envoie jamais rien de son côté, ce canal ne sert qu'à **recevoir** des mises à jour (pas besoin de connaître les votes/actions puisque ce n'est pas le rôle du site).

Événements diffusés : `player_joined`, `roles_config_updated`, `roles_assigned`. Le frontend écoute ça pour rafraîchir la liste des joueurs en direct et rediriger automatiquement vers l'écran du rôle dès que l'hôte démarre.

## `state.py` — le câblage

Trois instances **uniques**, créées une seule fois au chargement du module et partagées par toute l'application :

```python
nao_controller = StubNaoController()
game_service = GameService(nao_controller)
ws_manager = ConnectionManager()
```

Choix simple (pas de framework d'injection de dépendances), suffisant pour un processus unique. Si un jour il fallait plusieurs workers Uvicorn, il faudrait déplacer l'état des parties dans un store externe (Redis, DB) partagé entre processus — actuellement, tout vit dans la mémoire d'un seul processus Python.

## `main.py` — le point d'entrée

Crée l'app FastAPI, ajoute le middleware CORS (origine `*`, volontairement permissif car c'est un usage LAN où l'IP du serveur peut varier selon le réseau), branche les deux routeurs (`games_router`, `ws_router`), configure le logging (pour que les logs `[NAO] ...` s'affichent), et expose `/health`.

## Tests (`tests/`)

- **`test_domain.py`** — teste `GameService` directement, sans passer par HTTP : répartition des rôles, rejet des actions par un non-hôte, erreurs si la config ne correspond pas au nombre de joueurs, tirage correct, impossibilité de rejoindre après démarrage.
- **`test_auth.py`** — vérifie que le jeton survit à un aller-retour et qu'un jeton trafiqué est rejeté.
- **`test_api.py`** — teste les routes HTTP via `TestClient` : création, jointures, isolation des rôles (chaque joueur ne voit que le sien), 403 pour un non-hôte, 401 sans jeton valide.

`conftest.py` ajoute le dossier `backend/` au `sys.path` pour que `import app...` fonctionne depuis les tests.

## Flux complet, de bout en bout

1. Alice crée la partie → `POST /api/games` → `GameService.create_game` → `Game` en mémoire, Alice = hôte, jeton renvoyé, NAO prévenu.
2. Bob, Carol... rejoignent → `POST /.../join` → chaque join diffuse `player_joined` sur le WebSocket → tous les onglets du lobby se mettent à jour en direct.
3. Alice ajuste la répartition → `PATCH /.../roles` → `roles_config_updated` diffusé.
4. Alice démarre → `POST /.../start` → tirage aléatoire, statut `ROLES_ASSIGNED`, `roles_assigned` diffusé → chaque onglet est redirigé vers l'écran du rôle.
5. Chaque joueur appelle `GET /.../me` avec son propre jeton → ne reçoit que **son** rôle.

## Variables d'environnement

| Variable | Défaut | Rôle |
|---|---|---|
| `MIN_PLAYERS` | `5` | Nombre minimum de joueurs pour démarrer une partie |
| `TOKEN_SECRET` | `dev-secret-change-me` | Clé de signature des jetons de session — à changer en production |

## Limites connues / hors scope actuel

- Pas de persistance : un redémarrage du serveur efface toutes les parties en cours.
- Un seul processus/worker supporté (l'état est en mémoire Python, pas partagé entre processus).
- Pas de machine à états de partie (nuit/jour/votes) : le backend s'arrête à la distribution des rôles, la suite du jeu est portée par NAO en dehors du site.
