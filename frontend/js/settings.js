/**
 * Settings view: populates the interface dropdown, wires up toggles,
 * and persists runtime settings (refresh rate, packet limit, thresholds)
 * to the backend.
 */

const Settings = (() => {
  let soundToggleOn = false;

  function init() {
    loadInterfaces();
    loadSettings();

    document.getElementById("sound-toggle").addEventListener("click", (e) => {
      soundToggleOn = !soundToggleOn;
      e.target.classList.toggle("on", soundToggleOn);
      Alerts.setSoundEnabled(soundToggleOn);
    });

    document.getElementById("save-settings-btn").addEventListener("click", save);
  }

  async function loadInterfaces() {
    const select = document.getElementById("interface-select");
    const autoOption = `<option value="">Auto-detect (recommended)</option>`;
    try {
      const { interfaces } = await Api.listInterfaces();
      select.innerHTML = autoOption + (interfaces.length
        ? interfaces.map((i) => `<option value="${Utils.escapeHtml(i)}">${Utils.escapeHtml(i)}</option>`).join("")
        : "");
    } catch (e) {
      select.innerHTML = autoOption;
    }
  }

  async function loadSettings() {
    try {
      const s = await Api.getSettings();
      document.getElementById("refresh-rate-input").value = s.refresh_rate_ms;
      document.getElementById("packet-limit-input").value = s.packet_limit;
    } catch (e) { /* use defaults already in the DOM */ }
  }

  async function save() {
    const payload = {
      refresh_rate_ms: parseInt(document.getElementById("refresh-rate-input").value, 10) || 1000,
      packet_limit: parseInt(document.getElementById("packet-limit-input").value, 10) || 5000,
      port_scan_threshold: 15,
      ping_flood_threshold: 50,
    };
    try {
      await Api.updateSettings(payload);
      Dashboard.setPollInterval(payload.refresh_rate_ms);
      flashSaved();
    } catch (e) {
      // fail silently; settings aren't mission-critical
    }
  }

  function flashSaved() {
    const btn = document.getElementById("save-settings-btn");
    const original = btn.textContent;
    btn.textContent = "Saved ✓";
    setTimeout(() => { btn.textContent = original; }, 1500);
  }

  function selectedInterface() {
    return document.getElementById("interface-select").value || null;
  }

  return { init, selectedInterface };
})();
