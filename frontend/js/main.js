/**
 * Application bootstrap: wires up view navigation, the live clock,
 * keyboard shortcuts, the History view, and starts the WebSocket feed.
 * This is the only file that runs on DOMContentLoaded — everything else
 * exposes an init()/refresh() the modules above call into.
 */

(() => {
  const PAGE_TITLES = {
    dashboard: "Dashboard",
    analyzer: "Packet Analyzer",
    alerts: "Alerts",
    history: "History",
    settings: "Settings",
  };

  function switchView(viewName) {
    document.querySelectorAll(".nav-item[data-view]").forEach((item) => {
      item.classList.toggle("active", item.dataset.view === viewName);
    });
    document.querySelectorAll(".view").forEach((view) => {
      view.classList.toggle("active", view.id === `view-${viewName}`);
    });
    document.getElementById("page-title").textContent = PAGE_TITLES[viewName] || viewName;

    if (viewName === "history") History.refresh();
    if (viewName === "alerts") Alerts.refresh();
  }

  function initNavigation() {
    document.querySelectorAll(".nav-item[data-view]").forEach((item) => {
      item.addEventListener("click", () => switchView(item.dataset.view));
    });
  }

  function initClock() {
    const clockEl = document.getElementById("clock");
    const tick = () => { clockEl.textContent = Utils.formatTime(new Date()); };
    tick();
    setInterval(tick, 1000);
  }

  function initConnectionStatus() {
    LiveFeed.on("statusChange", (connected) => {
      const el = document.getElementById("connection-status");
      const label = document.getElementById("connection-status-label");
      el.classList.toggle("connected", connected);
      label.textContent = connected ? "Live" : "Reconnecting...";
    });
  }

  function initLiveFeedBindings() {
    LiveFeed.on("packet", (packet) => {
      PacketTable.prependLivePacket(packet);
    });
    LiveFeed.on("alert", (alert) => {
      Alerts.handleIncomingAlert(alert);
    });
    LiveFeed.connect();
  }

  function initKeyboardShortcuts() {
    const overlay = document.getElementById("shortcuts-overlay");
    document.getElementById("shortcuts-btn").addEventListener("click", () => overlay.classList.add("open"));
    overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.classList.remove("open"); });

    document.addEventListener("keydown", (e) => {
      const tag = (e.target.tagName || "").toLowerCase();
      const typing = tag === "input" || tag === "select" || tag === "textarea";

      if (e.key === "Escape") {
        overlay.classList.remove("open");
        PacketTable.closeDetailPanel();
        return;
      }
      if (typing) return;

      if (e.key === "/") {
        e.preventDefault();
        switchView("analyzer");
        document.getElementById("packet-search").focus();
      } else if (e.key === "?") {
        overlay.classList.add("open");
      } else if (e.key === "1") {
        switchView("dashboard");
      } else if (e.key === "2") {
        switchView("analyzer");
      } else if (e.key === "3") {
        switchView("alerts");
      } else if (e.key.toLowerCase() === "c") {
        document.getElementById("capture-toggle").click();
      }
    });
  }

  function safeInit(name, fn) {
    try {
      fn();
    } catch (err) {
      console.error(`NetScope: ${name} failed to initialize`, err);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    safeInit("navigation", initNavigation);
    safeInit("clock", initClock);
    safeInit("connection status", initConnectionStatus);
    safeInit("keyboard shortcuts", initKeyboardShortcuts);

    // Live feed connects first and independently — a dashboard chart
    // failing to render should never take down the WebSocket link.
    safeInit("live feed", initLiveFeedBindings);

    safeInit("dashboard", () => Dashboard.init());
    safeInit("packet table", () => PacketTable.init());
    safeInit("alerts", () => Alerts.init());
    safeInit("settings", () => Settings.init());
    safeInit("history", () => History.init());
  });
})();

/**
 * History view — kept in this file since it's small and mostly declarative.
 */
const History = (() => {
  function init() {
    // no persistent listeners needed beyond refresh(), called on view switch
  }

  async function refresh() {
    const container = document.getElementById("history-list");
    try {
      const sessions = await Api.listSessions();
      if (!sessions.length) {
        container.innerHTML = `
          <div class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3v5h5"/><path d="M3.05 13A9 9 0 1 0 6 5.3L3 8"/><path d="M12 7v5l4 2"/></svg>
            <div class="empty-state-title">No capture sessions yet</div>
            <div class="empty-state-desc">Start a capture from the Dashboard to create your first session.</div>
          </div>`;
        return;
      }
      container.innerHTML = sessions.map(sessionHtml).join("");
      container.querySelectorAll("[data-delete-session]").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
          e.stopPropagation();
          await Api.deleteSession(btn.dataset.deleteSession);
          refresh();
        });
      });
    } catch (e) {
      container.innerHTML = `<div class="empty-state"><div class="empty-state-desc">Couldn't load capture history.</div></div>`;
    }
  }

  function sessionHtml(s) {
    const duration = s.ended_at
      ? Math.round((new Date(s.ended_at) - new Date(s.started_at)) / 1000)
      : null;
    return `
      <div class="session-card">
        <div>
          <div style="font-weight:600; font-size:13px;">
            Session #${s.id}
            <span class="session-status-badge ${s.status}">${Utils.escapeHtml(s.status)}</span>
          </div>
          <div class="session-meta" style="margin-top:6px;">
            <span>Started ${Utils.escapeHtml(new Date(s.started_at).toLocaleString())}</span>
            <span>${Utils.formatNumber(s.total_packets)} packets</span>
            <span>${s.interface ? Utils.escapeHtml(s.interface) : "default interface"}</span>
            ${duration !== null ? `<span>${duration}s</span>` : ""}
          </div>
        </div>
        <div style="display:flex; gap:8px;">
          <button class="btn btn-sm" onclick="window.open(Api.exportUrl('csv', ${s.id}), '_blank')">Export</button>
          <button class="btn btn-sm btn-danger" data-delete-session="${s.id}">Delete</button>
        </div>
      </div>`;
  }

  return { init, refresh };
})();
