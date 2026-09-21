import { API_BASE_URL } from "./config";

const TOKEN_KEY = "nao-lg-token";
const CODE_KEY = "nao-lg-code";
const PLAYER_KEY = "nao-lg-player-id";

export function saveSession({ token, code, playerId }) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(CODE_KEY, code);
  localStorage.setItem(PLAYER_KEY, playerId);
}

export function loadSession() {
  const token = localStorage.getItem(TOKEN_KEY);
  const code = localStorage.getItem(CODE_KEY);
  const playerId = localStorage.getItem(PLAYER_KEY);
  if (!token || !code || !playerId) return null;
  return { token, code, playerId };
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(CODE_KEY);
  localStorage.removeItem(PLAYER_KEY);
}

async function request(path, { method = "GET", body, token } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const message = data?.detail || `Erreur ${response.status}`;
    throw new Error(message);
  }
  return data;
}

export function createGame(pseudo) {
  return request("/api/games", { method: "POST", body: { pseudo } });
}

export function joinGame(code, pseudo) {
  return request(`/api/games/${code}/join`, { method: "POST", body: { pseudo } });
}

export function getState(code) {
  return request(`/api/games/${code}/state`);
}

export function updateRoles(code, token, config) {
  return request(`/api/games/${code}/roles`, { method: "PATCH", token, body: { config } });
}

export function startGame(code, token) {
  return request(`/api/games/${code}/start`, { method: "POST", token });
}

export function getMe(code, token) {
  return request(`/api/games/${code}/me`, { token });
}
