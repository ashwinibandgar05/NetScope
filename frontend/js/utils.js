/**
 * Small shared helpers used across the dashboard modules.
 * Kept dependency-free on purpose.
 */

const Utils = (() => {
  function formatTime(dateLike) {
    const d = new Date(dateLike);
    if (isNaN(d.getTime())) return "--:--:--";
    return d.toLocaleTimeString("en-US", { hour12: false });
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
    return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
  }

  function formatNumber(n) {
    return new Intl.NumberFormat("en-US").format(n);
  }

  function debounce(fn, delay) {
    let timer = null;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), delay);
    };
  }

  function protocolBadgeClass(protocol) {
    const map = { TCP: "badge-tcp", UDP: "badge-udp", ICMP: "badge-icmp", ARP: "badge-arp" };
    return map[protocol] || "badge-other";
  }

  function severityBadgeClass(severity) {
    return `badge-severity-${(severity || "low").toLowerCase()}`;
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function downloadBlob(content, filename, mime) {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function playTone(frequency = 880, durationMs = 140) {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = frequency;
      osc.type = "sine";
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + durationMs / 1000);
      osc.connect(gain).connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + durationMs / 1000);
    } catch (e) {
      // Audio not available (autoplay policy, etc.) — fail silently.
    }
  }

  return {
    formatTime, formatBytes, formatNumber, debounce,
    protocolBadgeClass, severityBadgeClass, escapeHtml,
    downloadBlob, playTone,
  };
})();
