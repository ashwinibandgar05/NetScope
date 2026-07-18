/**
 * Drives the Dashboard view: renders the stat cards, keeps charts and
 * top-talker lists updated on a poll loop, and owns the capture
 * start/stop control shared with the topbar.
 */

const Dashboard = (() => {
  let pollTimer = null;
  let pollIntervalMs = 1000;
  let captureRunning = false;

  const STAT_DEFS = [
    { key: "total_packets", label: "Total Packets", icon: iconLayers() },
    { key: "tcp_packets", label: "TCP Packets", icon: iconArrow("#3ba7ff") },
    { key: "udp_packets", label: "UDP Packets", icon: iconArrow("#35d399") },
    { key: "icmp_packets", label: "ICMP Packets", icon: iconArrow("#f4b740") },
    { key: "unknown_packets", label: "Unknown Packets", icon: iconArrow("#6b7a8a") },
    { key: "packets_per_second", label: "Packets / sec", icon: iconBolt(), suffix: "/s" },
  ];

  function iconLayers() {
    return `<svg viewBox="0 0 24 24" fill="none" stroke="#3ba7ff" stroke-width="2"><path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 17 9 5 9-5"/></svg>`;
  }
  function iconArrow(color) {
    return `<svg viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2"><path d="M12 5v14M19 12l-7 7-7-7"/></svg>`;
  }
  function iconBolt() {
    return `<svg viewBox="0 0 24 24" fill="none" stroke="#f4b740" stroke-width="2"><path d="M13 2 3 14h7l-1 8 10-12h-7l1-8Z"/></svg>`;
  }

  function init() {
    renderStatShells();
    Charts.chartDefaults();
    Charts.initThroughputChart("throughput-chart");
    Charts.initProtocolChart("protocol-donut-chart");

    document.getElementById("capture-toggle").addEventListener("click", toggleCapture);

    refreshAll();
    startPolling();
    syncCaptureStatus();
  }

  function renderStatShells() {
    const grid = document.getElementById("stats-grid");
    grid.innerHTML = STAT_DEFS.map((def) => `
      <div class="card stat-card">
        <div class="stat-card-top">
          <span class="stat-label">${def.label}</span>
          <span class="stat-icon">${def.icon}</span>
        </div>
        <span class="stat-value" id="stat-${def.key}">0</span>
      </div>`).join("");
  }

  function startPolling() {
    clearInterval(pollTimer);
    pollTimer = setInterval(refreshAll, pollIntervalMs);
  }

  function setPollInterval(ms) {
    pollIntervalMs = ms;
    startPolling();
  }

  async function refreshAll() {
    try {
      const [dashStats, throughput, traffic] = await Promise.all([
        Api.dashboardStats(),
        Api.throughputHistory(),
        Api.trafficStats(),
      ]);
      renderStats(dashStats);
      Charts.updateThroughput(throughput.points);
      Charts.updateProtocolDistribution(traffic.protocol_distribution);
      renderTopList("top-source-list", traffic.top_source_ips, "ip");
      renderTopList("top-ports-list", traffic.most_active_ports, "port");
      syncCaptureStatus();
    } catch (e) {
      // Backend momentarily unreachable — polling will retry next tick.
    }
  }

  function renderStats(stats) {
    STAT_DEFS.forEach((def) => {
      const el = document.getElementById(`stat-${def.key}`);
      if (!el) return;
      const value = stats[def.key] ?? 0;
      el.textContent = def.suffix
        ? `${Utils.formatNumber(Math.round(value))}${def.suffix}`
        : Utils.formatNumber(Math.round(value));
    });
  }

  function renderTopList(elementId, items, labelKind) {
    const el = document.getElementById(elementId);
    if (!items.length) {
      el.innerHTML = `<div class="empty-state" style="padding:24px 0;"><div class="empty-state-desc">No data yet</div></div>`;
      return;
    }
    const max = Math.max(...items.map((i) => i.count));
    el.innerHTML = items.map((item, idx) => {
      const label = labelKind === "ip" ? item.ip : `Port ${item.port}`;
      const pct = max ? Math.round((item.count / max) * 100) : 0;
      return `
        <div class="top-list-item">
          <span class="top-list-rank">${idx + 1}</span>
          <span class="top-list-label">${Utils.escapeHtml(label)}</span>
          <div class="top-list-bar-track"><div class="top-list-bar-fill" style="width:${pct}%"></div></div>
          <span class="top-list-count">${Utils.formatNumber(item.count)}</span>
        </div>`;
    }).join("");
  }

  async function syncCaptureStatus() {
    try {
      const status = await Api.captureStatus();
      setCaptureUiState(status.running);
    } catch (e) { /* backend not up yet */ }
  }

  async function toggleCapture() {
    const btn = document.getElementById("capture-toggle");
    btn.disabled = true;
    try {
      if (captureRunning) {
        await Api.stopCapture();
        setCaptureUiState(false);
      } else {
        const iface = Settings.selectedInterface();
        await Api.startCapture(iface);
        setCaptureUiState(true);
      }
    } catch (e) {
      alert(e.message || "Could not toggle capture. Check backend permissions (packet capture needs elevated privileges).");
    } finally {
      btn.disabled = false;
    }
  }

  function setCaptureUiState(running) {
    captureRunning = running;
    const btn = document.getElementById("capture-toggle");
    const label = document.getElementById("capture-toggle-label");
    btn.classList.toggle("is-active", running);
    label.textContent = running ? "Stop Capture" : "Start Capture";
    document.getElementById("sidebar-session-info").textContent =
      running ? "Capture in progress" : "No active session";
  }

  return { init, setPollInterval, refreshAll, syncCaptureStatus };
})();
