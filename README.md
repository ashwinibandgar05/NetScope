# NetScope — Smart Network Packet Analyzer & Security Dashboard

A real-time network packet analyzer and security dashboard. NetScope captures live traffic from a local network interface, parses it, flags suspicious behavior with lightweight heuristics, and streams everything to a browser dashboard over WebSockets — a compact, self-hosted alternative to running Wireshark alongside a separate analytics tool.

![NetScope Dashboard]("C:\Users\ashwi\OneDrive\Documents\OneDrive\Pictures\Screenshots 1\Screenshot 2026-07-18 171942.png")
## Live Demo Screenshots

<p align="center">
  <img src="sC:\Users\ashwi\OneDrive\Documents\OneDrive\Pictures\Screenshots 1\Screenshot 2026-07-18 171942.png" width="48%">
  <img src="C:\Users\ashwi\OneDrive\Documents\OneDrive\Pictures\Screenshots 1\Screenshot 2026-07-18 172002.png" width="48%">
</p>

<p align="center">
  <img src="C:\Users\ashwi\OneDrive\Documents\OneDrive\Pictures\Screenshots 1\Screenshot 2026-07-18 172020.png" width="48%">
  <img src="C:\Users\ashwi\OneDrive\Documents\OneDrive\Pictures\Screenshots 1\Screenshot 2026-07-18 172034.png" width="48%">
  <img src="C:\Users\ashwi\OneDrive\Documents\OneDrive\Pictures\Screenshots 1\Screenshot 2026-07-18 172047.png" width="48%">
</p>

---

## Overview

| | |
|---|---|
| **Backend** | Python, FastAPI, Scapy, SQLAlchemy, SQLite, WebSockets, Asyncio |
| **Frontend** | HTML, CSS (hand-written, no framework), Vanilla JS, Chart.js |
| **Core idea** | Capture → Parse → Detect → Persist → Broadcast → Visualize |

NetScope sniffs packets with Scapy in a background thread, converts each one into a flat structured record, runs it through a sliding-window detection engine (port scans, ping floods, high-volume sources, suspicious ports), stores it in SQLite, and pushes it to every connected browser tab over a single `/ws/live` WebSocket. The dashboard renders live counters, a packets/sec line chart, a protocol-distribution donut, a searchable/sortable/paginated packet table with a detail side-panel, and a real-time alert feed with toast notifications.

---

## Architecture

```
                     ┌────────────────┐
                     │  Scapy sniffer  │  (background thread)
                     └───────┬────────┘
                             │ raw packet
                             ▼
                     ┌────────────────┐
                     │  packet parser  │  → flat dict (IP/ports/proto/TTL/flags)
                     └───────┬────────┘
                             ▼
                  ┌─────────────────────┐
                  │   capture service    │  (asyncio orchestrator)
                  └──┬────────┬────────┬─┘
                     ▼        ▼        ▼
              in-memory   SQLite    detection
               buffer    (packets)   engine
                     │        │        │
                     └────┬───┴────┬───┘
                          ▼        ▼
                    WebSocket broadcast → browser dashboard
                          │
                    REST API (FastAPI) → history, stats, export, settings
```

The backend follows a layered structure so each concern is independently testable:

- **`capture/`** — Scapy sniffer thread + packet parser. The only place scapy is imported.
- **`services/`** — business logic: capture orchestration, detection heuristics, stats aggregation, CSV/JSON export. No FastAPI or scapy imports here — pure Python + SQLAlchemy.
- **`api/`** — thin FastAPI routers that call into services. No business logic lives in a route handler.
- **`models/` / `schemas/`** — SQLAlchemy ORM models and Pydantic request/response contracts, kept separate so the DB schema can evolve without breaking the API contract.
- **`core/`** — configuration and logging, the only cross-cutting concerns.

---

## Folder Structure

```
netscope/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routers + WebSocket connection manager
│   │   ├── capture/        # scapy sniffer + packet parser
│   │   ├── core/           # settings, logging
│   │   ├── database/       # SQLAlchemy engine/session
│   │   ├── models/         # ORM models (Packet, Alert, CaptureSession)
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # capture orchestration, detection, stats, export
│   │   └── main.py         # app entrypoint
│   └── requirements.txt
└── frontend/
    ├── css/                 # base, layout, components, dashboard styles
    ├── js/                  # api client, websocket client, charts, views
    ├── assets/
    └── index.html
```

---

## Installation

**Requirements:** Python 3.10+, a modern browser. Packet capture requires elevated privileges (root on Linux/macOS, Administrator + Npcap on Windows).

```bash
cd netscope/backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
# From backend/, with elevated privileges (packet capture needs raw sockets)
sudo venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open **http://localhost:8000** — the backend serves the frontend directly, so no separate dev server is needed. Click **Start Capture** on the dashboard to begin sniffing on the default interface (or pick one under Settings first).

> Running without root/admin privileges will start the server fine, but `Start Capture` will fail with a permissions error — this is a Scapy/OS constraint, not a bug.

### Key endpoints
- `POST /api/packets/start` / `POST /api/packets/stop` — control capture
- `GET /api/packets/?protocol=TCP&search=192.168` — filtered/paginated/sorted packet query
- `GET /api/stats/dashboard` — live counters for the top cards
- `GET /api/alerts/` — suspicious activity feed
- `GET /api/packets/export/csv` / `.../export/json` — download logs
- `WS /ws/live` — real-time packet + alert stream

Interactive API docs are available at `/docs` (Swagger) once the server is running.

---

## Features

- **Live capture** with start/stop control and interface selection
- **Real-time dashboard**: total/TCP/UDP/ICMP/unknown packet counts, packets/sec
- **Charts**: live throughput line chart, protocol-distribution donut, top-IP and top-port bars
- **Packet analyzer**: searchable, sortable, paginated table with protocol filter
- **Packet detail panel**: headers, flags, TTL, length, raw summary
- **Suspicious activity detection**: port scanning, ping floods, high-volume sources, connections to known-suspicious ports — all via rolling time-window heuristics with alert cooldowns to avoid spam
- **Alerts view** with toast notifications, optional sound, and read/unread tracking
- **History**: every capture is a session in SQLite; browse, inspect, export, or delete past sessions
- **Export**: CSV and JSON, whole-history or per-session
- **Settings**: interface selection, refresh rate, packet buffer limit, sound toggle
- **Keyboard shortcuts**: `/` search, `1`/`2`/`3` view switching, `C` toggle capture, `?` shortcut help, `Esc` close panels

---

## Future Improvements

- Persist the detection engine's per-IP state across restarts (currently in-memory only)
- Add authentication for multi-user deployments
- Pcap file import/export for offline analysis in Wireshark
- GeoIP lookups for source/destination IPs
- Configurable, user-defined detection rules instead of fixed thresholds
- WebSocket message batching under very high packet rates to reduce render overhead

---

## Resume Bullet Points

- Built **NetScope**, a full-stack real-time network packet analyzer capturing and classifying live traffic with Python/Scapy, streaming parsed results to a browser dashboard over WebSockets with sub-second latency.
- Designed a layered FastAPI backend (API/services/capture/models) with SQLAlchemy + SQLite persistence, implementing a sliding-window anomaly detection engine that flags port scans, ping floods, and high-volume traffic sources in real time.
- Developed a dark-themed analytics dashboard from scratch in vanilla JS and Chart.js — live throughput charts, protocol distribution visualizations, a searchable/sortable/paginated packet table, and a real-time alert system — with no frontend framework dependency.
- Implemented CSV/JSON export, session-based capture history, and a REST + WebSocket API surface documented via FastAPI's auto-generated OpenAPI schema.
