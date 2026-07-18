/**
 * Handles the Packet Analyzer view: fetching packets from the REST API
 * (paginated/filtered/sorted), rendering rows, and the side-panel detail view.
 * Live packets pushed over the WebSocket are prepended when the user is
 * on page 1 with no active filters, so the table feels "live" without
 * refetching constantly.
 */

const PacketTable = (() => {
  let state = {
    page: 1,
    pageSize: 50,
    sortBy: "timestamp",
    sortDir: "desc",
    protocol: "",
    search: "",
    total: null,
  };

  let tbody, searchInput, protocolFilter, paginationInfo;

  function init() {
    tbody = document.getElementById("packet-table-body");
    searchInput = document.getElementById("packet-search");
    protocolFilter = document.getElementById("protocol-filter");
    paginationInfo = document.getElementById("pagination-info");

    searchInput.addEventListener("input", Utils.debounce(() => {
      state.search = searchInput.value.trim();
      state.page = 1;
      refresh();
    }, 350));

    protocolFilter.addEventListener("change", () => {
      state.protocol = protocolFilter.value;
      state.page = 1;
      refresh();
    });

    document.querySelectorAll("#packet-table thead th[data-sort]").forEach((th) => {
      th.addEventListener("click", () => {
        const col = th.dataset.sort;
        if (state.sortBy === col) {
          state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
        } else {
          state.sortBy = col;
          state.sortDir = "desc";
        }
        document.querySelectorAll("#packet-table thead th").forEach((h) => h.classList.remove("sorted"));
        th.classList.add("sorted");
        refresh();
      });
    });

    document.getElementById("prev-page-btn").addEventListener("click", () => {
      if (state.page > 1) { state.page -= 1; refresh(); }
    });
    document.getElementById("next-page-btn").addEventListener("click", () => {
      state.page += 1; refresh();
    });

    document.getElementById("export-csv-btn").addEventListener("click", () => {
      window.open(Api.exportUrl("csv"), "_blank");
    });
    document.getElementById("export-json-btn").addEventListener("click", () => {
      window.open(Api.exportUrl("json"), "_blank");
    });

    document.getElementById("close-panel-btn").addEventListener("click", closeDetailPanel);
    document.getElementById("side-panel-overlay").addEventListener("click", closeDetailPanel);

    refresh();
  }

  async function refresh() {
    try {
      const params = {
        page: state.page,
        page_size: state.pageSize,
        sort_by: state.sortBy,
        sort_dir: state.sortDir,
      };
      if (state.protocol) params.protocol = state.protocol;
      if (state.search) params.search = state.search;

      const packets = await Api.queryPackets(params);
      renderRows(packets);
      paginationInfo.textContent = `Page ${state.page} · ${packets.length} shown`;
    } catch (e) {
      renderEmpty("Couldn't load packets. Is the backend running?");
    }
  }

  function renderEmpty(message) {
    tbody.innerHTML = `
      <tr><td colspan="8">
        <div class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 12h4l3 8 4-16 3 8h4"/></svg>
          <div class="empty-state-title">No packets to show</div>
          <div class="empty-state-desc">${Utils.escapeHtml(message)}</div>
        </div>
      </td></tr>`;
  }

  function renderRows(packets) {
    if (!packets.length) {
      renderEmpty("Start a capture to begin seeing live traffic.");
      return;
    }
    tbody.innerHTML = packets.map(rowHtml).join("");
    tbody.querySelectorAll("tr[data-packet]").forEach((tr) => {
      tr.addEventListener("click", () => openDetailPanel(JSON.parse(tr.dataset.packet)));
    });
  }

  function rowHtml(p) {
    return `
      <tr data-packet='${Utils.escapeHtml(JSON.stringify(p))}'>
        <td>${Utils.formatTime(p.timestamp)}</td>
        <td class="primary">${Utils.escapeHtml(p.src_ip)}${p.src_port ? ":" + p.src_port : ""}</td>
        <td class="primary">${Utils.escapeHtml(p.dst_ip)}${p.dst_port ? ":" + p.dst_port : ""}</td>
        <td><span class="badge ${Utils.protocolBadgeClass(p.protocol)}">${Utils.escapeHtml(p.protocol)}</span></td>
        <td>${p.app_protocol ? Utils.escapeHtml(p.app_protocol) : "—"}</td>
        <td>${p.length}B</td>
        <td>${p.ttl ?? "—"}</td>
        <td>${p.flags ? Utils.escapeHtml(p.flags) : "—"}</td>
      </tr>`;
  }

  function prependLivePacket(packet) {
    // Only splice live traffic into the visible table when we're on the
    // default, unfiltered first page — otherwise it would fight the user's
    // current filter/sort/page state.
    if (state.page !== 1 || state.search || state.protocol) return;
    if (state.sortBy !== "timestamp" || state.sortDir !== "desc") return;

    if (tbody.querySelector(".empty-state")) {
      tbody.innerHTML = "";
    }

    const row = document.createElement("tr");
    row.className = "new-row";
    row.dataset.packet = Utils.escapeHtml(JSON.stringify(packet));
    row.innerHTML = rowHtml(packet).match(/<tr[^>]*>([\s\S]*)<\/tr>/)[1];
    row.addEventListener("click", () => openDetailPanel(packet));
    tbody.prepend(row);

    while (tbody.children.length > state.pageSize) {
      tbody.removeChild(tbody.lastChild);
    }
  }

  function openDetailPanel(packet) {
    const content = document.getElementById("side-panel-content");
    content.innerHTML = `
      <div class="detail-group">
        <div class="detail-group-label">Overview</div>
        <div class="detail-row"><span class="k">Timestamp</span><span class="v">${Utils.escapeHtml(packet.timestamp)}</span></div>
        <div class="detail-row"><span class="k">Protocol</span><span class="v">${Utils.escapeHtml(packet.protocol)}</span></div>
        <div class="detail-row"><span class="k">App Layer</span><span class="v">${Utils.escapeHtml(packet.app_protocol || "—")}</span></div>
        <div class="detail-row"><span class="k">Length</span><span class="v">${packet.length} bytes</span></div>
        <div class="detail-row"><span class="k">TTL</span><span class="v">${packet.ttl ?? "—"}</span></div>
        <div class="detail-row"><span class="k">Flags</span><span class="v">${Utils.escapeHtml(packet.flags || "—")}</span></div>
      </div>
      <div class="detail-group">
        <div class="detail-group-label">Addressing</div>
        <div class="detail-row"><span class="k">Source</span><span class="v">${Utils.escapeHtml(packet.src_ip)}${packet.src_port ? ":" + packet.src_port : ""}</span></div>
        <div class="detail-row"><span class="k">Destination</span><span class="v">${Utils.escapeHtml(packet.dst_ip)}${packet.dst_port ? ":" + packet.dst_port : ""}</span></div>
      </div>
      <div class="detail-group">
        <div class="detail-group-label">Raw Summary</div>
        <div class="raw-block">${Utils.escapeHtml(packet.raw_summary || "No summary captured")}</div>
      </div>`;

    document.getElementById("side-panel").classList.add("open");
    document.getElementById("side-panel-overlay").classList.add("open");
  }

  function closeDetailPanel() {
    document.getElementById("side-panel").classList.remove("open");
    document.getElementById("side-panel-overlay").classList.remove("open");
  }

  return { init, refresh, prependLivePacket, closeDetailPanel };
})();
