/**
 * Manages the single WebSocket connection to /ws/live and dispatches
 * incoming packet/alert events to whichever listeners registered.
 * Handles automatic reconnection with exponential backoff.
 */

const LiveFeed = (() => {
  let socket = null;
  let reconnectAttempts = 0;
  let reconnectTimer = null;
  const listeners = { packet: [], alert: [], statusChange: [] };

  function wsUrl() {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${window.location.host}/ws/live`;
  }

  function connect() {
    clearTimeout(reconnectTimer);
    socket = new WebSocket(wsUrl());

    socket.addEventListener("open", () => {
      reconnectAttempts = 0;
      listeners.statusChange.forEach((cb) => cb(true));
    });

    socket.addEventListener("message", (event) => {
      let payload;
      try {
        payload = JSON.parse(event.data);
      } catch (e) {
        return;
      }
      if (payload.type === "packet") {
        listeners.packet.forEach((cb) => cb(payload.data));
      } else if (payload.type === "alert") {
        listeners.alert.forEach((cb) => cb(payload.data));
      }
    });

    socket.addEventListener("close", () => {
      listeners.statusChange.forEach((cb) => cb(false));
      scheduleReconnect();
    });

    socket.addEventListener("error", () => {
      socket.close();
    });
  }

  function scheduleReconnect() {
    reconnectAttempts += 1;
    const delay = Math.min(1000 * 2 ** reconnectAttempts, 15000);
    reconnectTimer = setTimeout(connect, delay);
  }

  function on(event, callback) {
    if (listeners[event]) listeners[event].push(callback);
  }

  return { connect, on };
})();
