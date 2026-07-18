"""Aggregate queries over persisted packets — top talkers, protocol mix, ports."""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.packet import Packet


def protocol_distribution(db: Session) -> list[dict]:
    rows = (
        db.query(Packet.protocol, func.count(Packet.id))
        .group_by(Packet.protocol)
        .order_by(func.count(Packet.id).desc())
        .all()
    )
    return [{"protocol": proto or "OTHER", "count": count} for proto, count in rows]


def top_ips(db: Session, column, limit: int = 10) -> list[dict]:
    rows = (
        db.query(column, func.count(Packet.id))
        .group_by(column)
        .order_by(func.count(Packet.id).desc())
        .limit(limit)
        .all()
    )
    return [{"ip": ip, "count": count} for ip, count in rows if ip]


def most_active_ports(db: Session, limit: int = 10) -> list[dict]:
    rows = (
        db.query(Packet.dst_port, func.count(Packet.id))
        .filter(Packet.dst_port.isnot(None))
        .group_by(Packet.dst_port)
        .order_by(func.count(Packet.id).desc())
        .limit(limit)
        .all()
    )
    return [{"port": port, "count": count} for port, count in rows]


def total_bandwidth(db: Session) -> int:
    total = db.query(func.coalesce(func.sum(Packet.length), 0)).scalar()
    return int(total or 0)


def traffic_stats(db: Session) -> dict:
    return {
        "protocol_distribution": protocol_distribution(db),
        "top_source_ips": top_ips(db, Packet.src_ip),
        "top_destination_ips": top_ips(db, Packet.dst_ip),
        "most_active_ports": most_active_ports(db),
        "total_bandwidth_bytes": total_bandwidth(db),
    }
