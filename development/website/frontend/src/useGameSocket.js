import { useEffect, useRef } from "react";
import { WS_BASE_URL } from "./config";

// Subscribes to the lobby's WebSocket and forwards every parsed {event, data}
// message to onEvent. Re-created only when `code` changes.
export function useGameSocket(code, onEvent) {
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!code) return undefined;

    const socket = new WebSocket(`${WS_BASE_URL}/ws/games/${code}`);
    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        onEventRef.current(parsed);
      } catch {
        // ignore malformed frames
      }
    };

    return () => socket.close();
  }, [code]);
}
