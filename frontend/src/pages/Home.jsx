import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createGame, joinGame, saveSession } from "../api";

export default function Home() {
  const navigate = useNavigate();
  const [pseudo, setPseudo] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleCreate() {
    setError(null);
    setLoading(true);
    try {
      const data = await createGame();
      saveSession({ token: data.token, code: data.code, playerId: data.id, isHost: true });
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
      saveSession({ token: data.token, code: data.code, playerId: data.id, isHost: false });
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

      <section>
        <h2>Cet écran est l'hôte</h2>
        <p className="hint">
          À utiliser sur le PC/l'écran de la salle. Il affiche le code à donner aux joueurs et
          pilote la partie, mais ne reçoit pas de rôle.
        </p>
        <button type="button" onClick={handleCreate} disabled={loading}>
          Créer une partie
        </button>
      </section>

      <section>
        <h2>Rejoindre en tant que joueur</h2>
        <p className="hint">Sur ton téléphone, avec le code donné par l'hôte.</p>
        <form onSubmit={handleJoin}>
          <label className="field">
            Pseudo
            <input value={pseudo} onChange={(e) => setPseudo(e.target.value)} maxLength={30} required />
          </label>
          <label className="field">
            Code de partie
            <input
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value)}
              maxLength={6}
              required
            />
          </label>
          <button type="submit" disabled={loading || !pseudo.trim() || !joinCode.trim()}>
            Rejoindre
          </button>
        </form>
      </section>

      {error && <p className="error">{error}</p>}
    </main>
  );
}
