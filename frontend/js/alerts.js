/**
 * Renders the Alerts view, keeps the sidebar unread badge in sync, and
 * pops toast notifications (with an optional sound) when new alerts
 * arrive over the WebSocket.
 */

const Alerts = (() => {
  let unreadCount = 0;
  let soundEnabled = false;

  const ICONS = {
    PORT_SCAN: "⌕",
    PING_FLOOD: "⚡",
    HIGH_VOLUME: "▲",
    SUSPICIOUS_PORT: "⚠",
  };

  function init() {
    document.getElementById("clear-alerts-btn").addEventListener("click", markAllRead);
    refresh();
  }

  function setSoundEnabled(enabled) {
    soundEnabled = enabled;
  }

  async function refresh() {
    try {
      const alerts = await Api.listAlerts({ limit: 200 });
      renderList(alerts);
      const summary = await Api.alertSummary();
      updateBadge(summary.unacknowledged);
    } catch (e) {
      document.getElementById("alerts-list").innerHTML = emptyStateHtml("Couldn't load alerts.");
    }
  }

  function renderList(alerts) {
    const container = document.getElementById("alerts-list");
    if (!alerts.length) {
      container.innerHTML = emptyStateHtml("No suspicious activity detected yet. Start a capture to begin monitoring.");
      return;
    }
    container.innerHTML = alerts.map(alertHtml).join("");
    container.querySelectorAll("[data-alert-id]").forEach((el) => {
      el.addEventListener("click", () => acknowledge(el.dataset.alertId));
    });
  }

  function alertHtml(a) {
    return `
      <div class="alert-item severity-${a.severity}" data-alert-id="${a.id}" style="cursor:pointer; ${a.acknowledged ? "opacity:0.55;" : ""}">
        <div class="alert-icon">${ICONS[a.alert_type] || "!"}</div>
        <div class="alert-body">
          <div class="alert-title">
            ${Utils.escapeHtml(a.alert_type.replace(/_/g, " "))}
            <span class="badge ${Utils.severityBadgeClass(a.severity)}">${Utils.escapeHtml(a.severity)}</span>
          </div>
          <div class="alert-desc">${Utils.escapeHtml(a.description)}</div>
          <div class="alert-meta">${Utils.escapeHtml(a.source_ip)} · ${Utils.formatTime(a.timestamp)}</div>
        </div>
      </div>`;
  }

  function emptyStateHtml(message) {
    return `
      <div class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/></svg>
        <div class="empty-state-title">All clear</div>
        <div class="empty-state-desc">${Utils.escapeHtml(message)}</div>
      </div>`;
  }

  async function acknowledge(id) {
    try {
      await Api.acknowledgeAlert(id, true);
      refresh();
    } catch (e) { /* non-fatal */ }
  }

  async function markAllRead() {
    const alerts = await Api.listAlerts({ acknowledged: false, limit: 500 });
    await Promise.all(alerts.map((a) => Api.acknowledgeAlert(a.id, true)));
    refresh();
  }

  function updateBadge(count) {
    const badge = document.getElementById("alert-badge");
    unreadCount = count;
    if (count > 0) {
      badge.textContent = count > 99 ? "99+" : count;
      badge.classList.remove("hidden");
    } else {
      badge.classList.add("hidden");
    }
  }

  function handleIncomingAlert(alert) {
    showToast(alert);
    if (soundEnabled && alert.severity === "high") {
      Utils.playTone(920, 160);
    }
    updateBadge(unreadCount + 1);
    // Refresh the list lazily if the user is currently looking at it.
    if (document.getElementById("view-alerts").classList.contains("active")) {
      refresh();
    }
  }

  function showToast(alert) {
    const stack = document.getElementById("toast-stack");
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.innerHTML = `
      <div class="toast-title">${Utils.escapeHtml(alert.alert_type.replace(/_/g, " "))}</div>
      <div>${Utils.escapeHtml(alert.description)}</div>`;
    stack.appendChild(toast);
    setTimeout(() => toast.remove(), 6000);
  }

  return { init, refresh, handleIncomingAlert, setSoundEnabled };
})();
