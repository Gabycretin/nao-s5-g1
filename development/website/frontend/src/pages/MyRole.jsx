import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getMe, loadSession } from "../api";

export default function MyRole() {
  const { code } = useParams();
  const navigate = useNavigate();
  const [session] = useState(() => loadSession());

  const [me, setMe] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!session || session.code !== code) {
      navigate("/");
      return;
    }
    getMe(code, session.token)
      .then(setMe)
      .catch((err) => setError(err.message));
  }, [code, session, navigate]);

  if (error) {
    return (
      <main className="page">
        <p className="error">{error}</p>
      </main>
    );
  }

  if (!me) {
    return (
      <main className="page">
        <p>Chargement…</p>
      </main>
    );
  }

  if (!me.role) {
    return (
      <main className="page">
        <p>Les rôles n'ont pas encore été distribués.</p>
      </main>
    );
  }

  return (
    <main className="page role-page">
      <p className="pseudo">{me.pseudo}</p>
      <h1>{me.role.label}</h1>
      <span className={`camp camp-${me.role.camp.toLowerCase()}`}>
        {me.role.camp === "LOUPS" ? "Camp des Loups" : "Camp du Village"}
      </span>
      <p className="description">{me.role.description}</p>
      <p className="hint">Gardez votre rôle secret. Vous pouvez revenir sur cette page à tout moment.</p>
    </main>
  );
}
