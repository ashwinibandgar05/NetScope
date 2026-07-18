/**
 * Thin wrapper around fetch() for talking to the NetScope backend.
 * Centralizing this means base URL / error handling only lives in one place.
 */

const Api = (() => {
  const BASE = "/api";

  async function request(path, options = {}) {
    const res = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      throw new Error(`API ${path} failed: ${res.status} ${detail}`);
    }
    const contentType = res.headers.get("content-type") || "";
    return contentType.includes("application/json") ? res.json() : res.text();
  }

  return {
    // Capture control
    startCapture: (iface) => request(`/packets/start${iface ? `?interface=${encodeURIComponent(iface)}` : ""}`, { method: "POST" }),
    stopCapture: () => request("/packets/stop", { method: "POST" }),
    captureStatus: () => request("/packets/status"),
    listInterfaces: () => request("/packets/interfaces"),

    // Packets
    livePackets: (limit = 100) => request(`/packets/live?limit=${limit}`),
    queryPackets: (params) => request(`/packets/?${new URLSearchParams(params).toString()}`),
    getPacket: (id) => request(`/packets/${id}`),

    // Stats
    dashboardStats: () => request("/stats/dashboard"),
    throughputHistory: () => request("/stats/throughput"),
    trafficStats: () => request("/stats/traffic"),

    // Alerts
    listAlerts: (params = {}) => request(`/alerts/?${new URLSearchParams(params).toString()}`),
    acknowledgeAlert: (id, acknowledged) =>
      request(`/alerts/${id}`, { method: "PATCH", body: JSON.stringify({ acknowledged }) }),
    alertSummary: () => request("/alerts/summary"),

    // History
    listSessions: () => request("/history/sessions"),
    sessionDetail: (id) => request(`/history/sessions/${id}`),
    deleteSession: (id) => request(`/history/sessions/${id}`, { method: "DELETE" }),

    // Settings
    getSettings: () => request("/settings/"),
    updateSettings: (payload) => request("/settings/", { method: "PUT", body: JSON.stringify(payload) }),

    // Export (return raw URL — used for direct download links)
    exportUrl: (format, sessionId) =>
      `${BASE}/packets/export/${format}${sessionId ? `?session_id=${sessionId}` : ""}`,
  };
})();
