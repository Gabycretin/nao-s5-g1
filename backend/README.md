# Backend — NAO Loup-Garou

API FastAPI qui gère le **lobby** d'une partie de Loup-Garou : création de partie, arrivée des joueurs, configuration des rôles par l'hôte, tirage aléatoire, et consultation du rôle secret de chacun.

Tout est stocké **en mémoire** (aucune base de données) — les parties disparaissent si le serveur redémarre, ce qui est volontaire pour ce MVP : le site ne sert qu'en tout début de partie.

### Hôte vs joueurs

Deux types de participants, structurellement séparés :

- **L'hôte** : le PC/écran de la salle qui crée la partie. Il configure la répartition des rôles et démarre la partie, mais **ne reçoit jamais de rôle** et ne compte pas dans le nombre de joueurs.
- **Les joueurs** : les téléphones qui rejoignent ensuite avec le code de partie. Ce sont eux qui reçoivent un rôle et comptent pour `MIN_PLAYERS`.

Un `Game` a un seul `host_id` (généré à la création, jamais stocké dans `players`) et un dictionnaire `players` qui ne contient que les joueurs réels. Les actions réservées à l'hôte (`PATCH /roles`, `POST /start`) vérifient `caller_id == game.host_id` ; elles échouent avec 403 pour n'importe quel joueur, même le tout premier arrivé.

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

- **`Player`** : id unique, pseudo, `role` (`None` tant que la partie n'a pas démarré). Représente uniquement un vrai joueur (téléphone) — jamais l'hôte.
- **`Game`** : id interne, `code` (6 caractères, ex. `ST50R0`), `host_id` (identité de l'écran hôte, généré à la création), `status` (`LOBBY` ou `ROLES_ASSIGNED`), dictionnaire de `players` (uniquement les vrais joueurs), `roles_config` (combien de chaque rôle), et un flag `roles_config_customized`.

Ce flag est important : tant que l'hôte n'a **jamais** touché manuellement la config, elle se recalcule automatiquement à chaque nouveau joueur (via `suggest_role_config`). Dès que l'hôte modifie la config une fois, elle se fige et n'est plus écrasée par les arrivées suivantes.

## `domain/errors.py` — les erreurs métier

Une hiérarchie d'exceptions Python (`GameNotFoundError`, `PseudoTakenError`, `NotHostError`, `InvalidGameStateError`, `InvalidRolesConfigError`, `InvalidPseudoError`, `PlayerNotFoundError`) toutes héritant de `DomainError`. Le domaine lève ces erreurs sans savoir qu'elles finiront en code HTTP — c'est `api/games.py` qui fait la traduction.

## `domain/service.py` — le cœur : `GameService`

Seule classe qui possède et modifie l'état du jeu (`self._games: dict[str, Game]`). Ses méthodes, dans l'ordre du cycle de vie :

1. **`create_game()`** — crée une `Game` avec un `host_id` généré, **sans aucun joueur**, stocke la partie, prévient NAO (`announce_game_created`). Renvoie `(game, host_id)`.
2. **`join_game(code, pseudo)`** — vérifie que la partie est encore en `LOBBY`, que le pseudo n'est pas vide ni déjà pris, ajoute le joueur, recalcule la suggestion de rôles si elle n'a pas été personnalisée.
3. **`update_roles_config(code, caller_id, config)`** — réservé à l'hôte (`_require_host`), remplace la config, marque `roles_config_customized = True`.
4. **`start_game(code, caller_id)`** — réservé à l'hôte. Vérifie qu'il y a au moins `MIN_PLAYERS` (5 par défaut, **uniquement des vrais joueurs**) et que la somme des rôles configurés correspond exactement au nombre de joueurs. Construit une liste de rôles (« pool »), la mélange (`random.shuffle`), et distribue un rôle à chaque joueur (jamais à l'hôte). Passe le statut à `ROLES_ASSIGNED`, prévient NAO (`announce_roles_assigned`).
5. **`get_state(code)`** / **`get_player(code, player_id)`** / **`require_host(code, caller_id)`** — lectures et vérification d'autorisation, utilisées par `api/deps.py`.

Deux méthodes privées font le travail commun : `_get_game` (recherche par code, insensible à la casse) et `_require_host` (compare `caller_id` à `game.host_id`).

## `nao/controller.py` — l'abstraction NAO

Un `Protocol` (interface structurelle Python) `NaoController` avec deux méthodes : `announce_game_created` et `announce_roles_assigned`. `GameService` ne connaît que cette interface, jamais une implémentation concrète — c'est de l'**injection de dépendance** simple.

L'implémentation branchée aujourd'hui est `StubNaoController` : elle se contente de logger le message (`[NAO] roles_assigned: ...`) et de garder la dernière instruction en mémoire (`self.last_instruction`). Le jour où le pont NAOqi existera, il suffira d'écrire une nouvelle classe qui respecte ce `Protocol` et de la brancher dans `state.py` — **aucun changement dans `GameService`**.

## `auth.py` — les jetons de session

Pas de base de données d'utilisateurs : à la place, un jeton signé maison (façon JWT simplifié) :

- `issue_token(game_code, player_id)` sérialise `{"game_code": ..., "player_id": ...}` en JSON, l'encode en base64, et calcule une signature HMAC-SHA256 avec un secret serveur (`TOKEN_SECRET`, à définir en variable d'environnement en production). Le jeton final est `<données>.<signature>`. Le champ `player_id` contient soit l'id d'un vrai joueur, soit `game.host_id` pour le jeton de l'hôte — c'est la comparaison à `game.host_id` côté serveur qui détermine les droits, pas le jeton lui-même.
- `verify_token(token)` recalcule la signature et la compare de façon sûre (`hmac.compare_digest`, résistant aux attaques par timing) avant de faire confiance aux données.

Ce jeton est stocké côté client (`localStorage`) et envoyé dans le header `Authorization: Bearer <token>` à chaque requête qui nécessite de savoir « qui je suis ». C'est ce qui permet à un joueur (ou à l'hôte) de revenir sur la page après un refresh sans perdre son identité, sans compte ni mot de passe.

## `schemas.py` — les formats HTTP (Pydantic)

Chaque endpoint a sa requête et/ou sa réponse typée : `JoinGameRequest`, `AuthResponse`, `RolesConfigRequest`, `StateResponse`, `MeResponse`, etc. `POST /api/games` (création) n'a pas de corps de requête — l'hôte n'a besoin de fournir aucune information. FastAPI s'en sert pour valider automatiquement les requêtes entrantes (ex. `pseudo` entre 1 et 30 caractères) et sérialiser les réponses en JSON. C'est aussi ce qui génère la doc interactive sur `/docs`.

## `api/deps.py` — les dépendances d'authentification

Deux **dépendances FastAPI**, qui partagent un petit helper `_authenticated_principal` (lit le header `Authorization`, vérifie le jeton, vérifie qu'il correspond bien à la partie demandée dans l'URL) :

- **`get_current_host(code, authorization)`** — vérifie en plus que l'id du jeton est bien `game.host_id` (via `game_service.require_host`), sinon 403. Renvoie directement le `Game`.
- **`get_current_player(code, authorization)`** — va chercher le joueur correspondant via `game_service.get_player`, sinon 404 (c'est ce qui arrive si l'hôte essaie d'appeler `/me` : il n'est pas dans `players`). Renvoie `(Game, Player)`.

Astuce FastAPI utilisée : ces fonctions déclarent leur propre paramètre `code: str`, qui se résout automatiquement depuis le `{code}` de l'URL de la route appelante, même si l'endpoint lui-même ne redéclare pas `code`. Ça évite de dupliquer ce paramètre partout.

## `api/games.py` — les routes REST

| Route | Auth requise | Fait quoi |
|---|---|---|
| `POST /api/games` | non | Crée une partie pour l'écran hôte (pas de corps), renvoie le code + le jeton hôte |
| `POST /api/games/{code}/join` | non | Un joueur rejoint avec son pseudo, renvoie son jeton |
| `GET /api/games/{code}/state` | non | État public du lobby (joueurs, statut, config des rôles) — l'hôte n'apparaît jamais dans `players` |
| `PATCH /api/games/{code}/roles` | oui (hôte) | Modifie la répartition des rôles |
| `POST /api/games/{code}/start` | oui (hôte) | Lance le tirage des rôles parmi les joueurs |
| `GET /api/games/{code}/me` | oui (joueur) | Mon pseudo, **mon** rôle (jamais celui des autres) — 404 si appelé avec le jeton de l'hôte |

Deux mécanismes transversaux :

- **`_ERROR_STATUS`** — dictionnaire qui mappe chaque type d'erreur métier vers un code HTTP (ex. `NotHostError` → 403, `PseudoTakenError` → 409). `_as_http_error` fait la conversion. C'est ce qui garde le domaine complètement ignorant de HTTP.
- **`_public_state`** — construit la réponse publique d'une partie à partir de l'objet `Game`. C'est volontairement la seule fonction qui a le droit de sérialiser un `Game` en réponse, pour être sûr qu'on n'y glisse jamais le rôle d'un joueur par erreur (le rôle individuel ne sort que par `/me`, jamais par `/state`).

Après chaque action qui change l'état partagé (`join`, `roles`, `start`), la route diffuse aussi l'événement correspondant sur le WebSocket (`ws_manager.broadcast`).

## `ws_manager.py` + `api/ws.py` — le temps réel du lobby

`ConnectionManager` garde en mémoire, pour chaque code de partie, l'ensemble des connexions WebSocket ouvertes (`dict[str, set[WebSocket]]`). `broadcast(code, event, data)` envoie `{"event": ..., "data": ...}` en JSON à tous les onglets connectés à cette partie.

La route `WS /ws/games/{code}` accepte la connexion, puis reste en attente (`receive_text()` en boucle) juste pour détecter la déconnexion — le client n'envoie jamais rien de son côté, ce canal ne sert qu'à **recevoir** des mises à jour (pas besoin de connaître les votes/actions puisque ce n'est pas le rôle du site).

Événements diffusés : `player_joined`, `roles_config_updated`, `roles_assigned`. Le frontend écoute ça pour rafraîchir la liste des joueurs en direct. Sur `roles_assigned`, les joueurs sont redirigés vers l'écran de leur rôle ; l'écran hôte, lui, reste sur le lobby (il n'a pas de rôle à afficher) et affiche simplement que la partie a démarré.

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

- **`test_domain.py`** — teste `GameService` directement, sans passer par HTTP : une partie créée n'a aucun joueur, `join_game` n'ajoute jamais l'hôte, répartition des rôles, rejet des actions par un non-hôte, erreurs si la config ne correspond pas au nombre de joueurs, tirage correct (uniquement parmi les joueurs), impossibilité de rejoindre après démarrage.
- **`test_auth.py`** — vérifie que le jeton survit à un aller-retour et qu'un jeton trafiqué est rejeté.
- **`test_api.py`** — teste les routes HTTP via `TestClient` : l'hôte n'apparaît pas dans le lobby, isolation des rôles (chaque joueur ne voit que le sien), 403 pour un joueur qui tente une action d'hôte, 404 pour l'hôte qui appelle `/me`, 401 sans jeton valide.

`conftest.py` ajoute le dossier `backend/` au `sys.path` pour que `import app...` fonctionne depuis les tests.

## Flux complet, de bout en bout

1. Le PC de la salle crée la partie → `POST /api/games` (sans corps) → `GameService.create_game` → `Game` en mémoire avec un `host_id`, jeton hôte renvoyé, NAO prévenu. Le PC affiche le code, aucun pseudo n'est demandé.
2. Alice, Bob, Carol... rejoignent depuis leur téléphone → `POST /.../join` avec leur pseudo → chaque join diffuse `player_joined` sur le WebSocket → tous les écrans (hôte + joueurs déjà connectés) se mettent à jour en direct.
3. Le PC (hôte) ajuste la répartition → `PATCH /.../roles` → `roles_config_updated` diffusé.
4. Le PC démarre → `POST /.../start` → tirage aléatoire parmi les joueurs uniquement, statut `ROLES_ASSIGNED`, `roles_assigned` diffusé → chaque téléphone est redirigé vers l'écran de son rôle, le PC reste sur le lobby.
5. Chaque joueur appelle `GET /.../me` avec son propre jeton → ne reçoit que **son** rôle. Si le PC appelait `/me` avec son jeton hôte, il recevrait 404 (il n'est pas un joueur).

## Variables d'environnement

| Variable | Défaut | Rôle |
|---|---|---|
| `MIN_PLAYERS` | `5` | Nombre minimum de joueurs pour démarrer une partie |
| `TOKEN_SECRET` | `dev-secret-change-me` | Clé de signature des jetons de session — à changer en production |

## Limites connues / hors scope actuel

- Pas de persistance : un redémarrage du serveur efface toutes les parties en cours.
- Un seul processus/worker supporté (l'état est en mémoire Python, pas partagé entre processus).
- Pas de machine à états de partie (nuit/jour/votes) : le backend s'arrête à la distribution des rôles, la suite du jeu est portée par NAO en dehors du site.
