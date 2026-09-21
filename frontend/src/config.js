// Defaults to the page's own hostname so it works whether the site is opened
// via localhost or via the host machine's LAN IP (e.g. from a player's phone).
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || `${window.location.protocol}//${window.location.hostname}:8000`;

export const WS_BASE_URL = API_BASE_URL.replace(/^http/, "ws");
