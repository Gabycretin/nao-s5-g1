import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getState, loadSession, startGame, updateRoles } from "../api";
import { useGameSocket } from "../useGameSocket";

const ROLE_LABELS = {
  LOUP_GAROU: "Loup-Garou",
  VILLAGEOIS: "Villageois",
  VOYANTE: "Voyante",
  SORCIERE: "Sorcière",
};

export default function Lobby() {
  const { code } = useParams();
  const navigate = useNavigate();
  const [session] = useState(() => loadSession());
  const isHost = Boolean(session?.isHost);

  const [state, setState] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(() => {
    getState(code).then(setState).catch((err) => setError(err.message));
  }, [code]);

  useEffect(() => {
    if (!session || session.code !== code) {
      navigate("/");
      return;
    }
    refresh();
  }, [code, session, navigate, refresh]);

  useGameSocket(code, (message) => {
    if (message.event === "player_joined" || message.event === "roles_config_updated") {
      setState(message.data);
    }
    if (message.event === "roles_assigned") {
      if (isHost) {
        setState(message.data);
      } else {
        navigate(`/games/${code}/role`);
      }
    }
  });

  if (!state) {
    return (
      <main className="page">
        <p>Chargement…</p>
        {error && <p className="error">{error}</p>}
      </main>
    );
  }

  const started = state.status === "ROLES_ASSIGNED";
  const totalRoles = Object.values(state.roles_config).reduce((sum, n) => sum + n, 0);
  const rolesMatchPlayers = totalRoles === state.players.length;
  const hasMinPlayers = state.players.length >= state.min_players;

  async function handleRoleChange(role, value) {
    const nextConfig = { ...state.roles_config, [role]: Math.max(0, Number(value) || 0) };
    setState({ ...state, roles_config: nextConfig });
    try {
      await updateRoles(code, session.token, nextConfig);
    } catch (err) {
      setError(err.message);
      refresh();
    }
  }

  async function handleStart() {
    setBusy(true);
    setError(null);
    try {
      await startGame(code, session.token);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page">
      <h1>{isHost ? "Écran hôte" : "Salle d'attente"}</h1>
      <p className="code-display">
        Code de la partie : <strong>{state.code}</strong>
      </p>

      {started && isHost && (
        <p className="hint">
          Les rôles ont été distribués. Chaque joueur consulte le sien sur son téléphone.
        </p>
      )}

      <section>
        <h2>Joueurs ({state.players.length})</h2>
        <ul className="player-list">
          {state.players.map((p) => (
            <li key={p.id}>{p.pseudo}</li>
          ))}
        </ul>
      </section>

      {!started && (
        <section>
          <h2>Répartition des rôles</h2>
          {Object.entries(state.roles_config).map(([role, count]) => (
            <label key={role} className="field role-field">
              {ROLE_LABELS[role] || role}
              <input
                type="number"
                min={0}
                value={count}
                disabled={!isHost}
                onChange={(e) => handleRoleChange(role, e.target.value)}
              />
            </label>
          ))}
          <p>
            Total : {totalRoles} / {state.players.length} joueurs
            {!rolesMatchPlayers && <span className="error"> — doit être égal au nombre de joueurs</span>}
          </p>
          {!hasMinPlayers && (
            <p className="error">
              Minimum {state.min_players} joueurs requis (actuellement {state.players.length}).
            </p>
          )}
        </section>
      )}

      {!started && isHost && (
        <button onClick={handleStart} disabled={busy || !rolesMatchPlayers || !hasMinPlayers}>
          Démarrer la partie
        </button>
      )}
      {!started && !isHost && <p>En attente que l'hôte démarre la partie…</p>}

      {error && <p className="error">{error}</p>}
    </main>
  );
}
