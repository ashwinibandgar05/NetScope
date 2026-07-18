"""Serializes packet query results into CSV or JSON for download."""
from __future__ import annotations

import csv
import io
import json
from typing import Sequence

from app.models.packet import Packet

_FIELDS = [
    "id", "session_id", "timestamp", "src_ip", "dst_ip", "src_port",
    "dst_port", "protocol", "app_protocol", "length", "ttl", "flags",
]


def to_csv(packets: Sequence[Packet]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_FIELDS)
    writer.writeheader()
    for p in packets:
        writer.writerow({field: getattr(p, field) for field in _FIELDS})
    return buffer.getvalue()


def to_json(packets: Sequence[Packet]) -> str:
    data = [
        {field: str(getattr(p, field)) if field == "timestamp" else getattr(p, field) for field in _FIELDS}
        for p in packets
    ]
    return json.dumps(data, indent=2)
