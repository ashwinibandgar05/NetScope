/**
 * Owns the two Chart.js instances on the dashboard: the live packets/sec
 * line chart and the protocol distribution donut. Exposes small update()
 * functions so dashboard.js doesn't need to know about Chart.js internals.
 */

const Charts = (() => {
  let throughputChart = null;
  let protocolChart = null;

  const PROTOCOL_COLORS = {
    TCP: "#3ba7ff",
    UDP: "#35d399",
    ICMP: "#f4b740",
    ARP: "#b083f0",
    OTHER: "#6b7a8a",
  };

  function isAvailable() {
    if (typeof Chart === "undefined") {
      console.warn("NetScope: Chart.js did not load (CDN blocked or offline) — charts disabled.");
      return false;
    }
    return true;
  }

  function chartDefaults() {
    if (!isAvailable()) return;
    Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, Segoe UI, Inter, Roboto, sans-serif";
    Chart.defaults.font.size = 11;
    Chart.defaults.color = "#8b98a5";
  }

  function initThroughputChart(canvasId) {
    if (!isAvailable()) return null;
    const ctx = document.getElementById(canvasId).getContext("2d");
    throughputChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: [],
        datasets: [{
          label: "Packets/sec",
          data: [],
          borderColor: "#3ba7ff",
          backgroundColor: "rgba(59, 167, 255, 0.08)",
          borderWidth: 2,
          fill: true,
          tension: 0.35,
          pointRadius: 0,
          pointHoverRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 250 },
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: "rgba(255,255,255,0.04)" }, ticks: { maxTicksLimit: 6 } },
          y: { grid: { color: "rgba(255,255,255,0.04)" }, beginAtZero: true },
        },
      },
    });
    return throughputChart;
  }

  function initProtocolChart(canvasId) {
    if (!isAvailable()) return null;
    const ctx = document.getElementById(canvasId).getContext("2d");
    protocolChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: [],
        datasets: [{ data: [], backgroundColor: [], borderWidth: 0 }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "68%",
        plugins: { legend: { display: false } },
      },
    });
    return protocolChart;
  }

  function updateThroughput(points) {
    if (!throughputChart) return;
    throughputChart.data.labels = points.map((p) => p.label);
    throughputChart.data.datasets[0].data = points.map((p) => p.value);
    throughputChart.update("none");
  }

  function updateProtocolDistribution(distribution) {
    if (!protocolChart) return;
    const labels = distribution.map((d) => d.protocol);
    const values = distribution.map((d) => d.count);
    const colors = distribution.map((d) => PROTOCOL_COLORS[d.protocol] || PROTOCOL_COLORS.OTHER);

    protocolChart.data.labels = labels;
    protocolChart.data.datasets[0].data = values;
    protocolChart.data.datasets[0].backgroundColor = colors;
    protocolChart.update("none");

    renderLegend(distribution, colors);
  }

  function renderLegend(distribution, colors) {
    const legendEl = document.getElementById("protocol-legend");
    if (!legendEl) return;
    legendEl.innerHTML = distribution
      .map((d, i) => `
        <div class="legend-item">
          <span class="legend-swatch" style="background:${colors[i]}"></span>
          ${Utils.escapeHtml(d.protocol)} · ${Utils.formatNumber(d.count)}
        </div>`)
      .join("");
  }

  return {
    chartDefaults, initThroughputChart, initProtocolChart,
    updateThroughput, updateProtocolDistribution, PROTOCOL_COLORS,
  };
})();
