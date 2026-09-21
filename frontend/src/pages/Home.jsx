import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createGame, joinGame, saveSession } from "../api";

export default function Home() {
  const navigate = useNavigate();
  const [pseudo, setPseudo] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleCreate(event) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await createGame(pseudo.trim());
      saveSession({ token: data.token, code: data.code, playerId: data.player_id });
      navigate(`/games/${data.code}/lobby`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleJoin(event) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const code = joinCode.trim().toUpperCase();
      const data = await joinGame(code, pseudo.trim());
      saveSession({ token: data.token, code: data.code, playerId: data.player_id });
      navigate(`/games/${data.code}/lobby`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <h1>NAO Loup-Garou</h1>
      <p>Distribution des rôles avant de commencer la partie.</p>

      <label className="field">
        Pseudo
        <input value={pseudo} onChange={(e) => setPseudo(e.target.value)} maxLength={30} required />
      </label>

      <div className="actions-row">
        <form onSubmit={handleCreate}>
          <button type="submit" disabled={loading || !pseudo.trim()}>
            Créer une partie
          </button>
        </form>

        <form onSubmit={handleJoin} className="join-form">
          <input
            placeholder="Code de partie"
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value)}
            maxLength={6}
            required
          />
          <button type="submit" disabled={loading || !pseudo.trim() || !joinCode.trim()}>
            Rejoindre
          </button>
        </form>
      </div>

      {error && <p className="error">{error}</p>}
    </main>
  );
}
