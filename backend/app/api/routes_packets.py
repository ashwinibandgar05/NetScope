import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.capture.sniffer import PacketSniffer
from app.database.session import get_db
from app.models.packet import Packet
from app.schemas.packet import PacketOut
from app.services.capture_service import capture_service
from app.services.export_service import to_csv, to_json

router = APIRouter(prefix="/packets", tags=["packets"])


@router.post("/start")
async def start_capture(interface: Optional[str] = None):
    if capture_service.is_running():
        raise HTTPException(status_code=409, detail="Capture already running")
    loop = asyncio.get_running_loop()
    session_id = capture_service.start(loop, interface=interface)
    return {"status": "started", "session_id": session_id, "interface": interface}


@router.post("/stop")
async def stop_capture():
    if not capture_service.is_running():
        raise HTTPException(status_code=409, detail="No capture in progress")
    capture_service.stop()
    return {"status": "stopped"}


@router.get("/status")
async def capture_status():
    return {
        "running": capture_service.is_running(),
        "session_id": capture_service.active_session_id,
        "interface": capture_service.interface,
    }


@router.get("/interfaces")
async def list_interfaces():
    return {"interfaces": PacketSniffer.list_interfaces()}


@router.get("/live")
async def live_packets(limit: int = Query(default=100, le=1000)):
    """Snapshot of the most recent packets held in memory (fast, no DB hit)."""
    return capture_service.recent_packets(limit=limit)


@router.get("/", response_model=list[PacketOut])
async def query_packets(
    db: Session = Depends(get_db),
    protocol: Optional[str] = None,
    src_ip: Optional[str] = None,
    dst_ip: Optional[str] = None,
    search: Optional[str] = None,
    session_id: Optional[int] = None,
    sort_by: str = Query(default="timestamp"),
    sort_dir: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, le=500),
):
    q = db.query(Packet)
    if protocol:
        q = q.filter(Packet.protocol == protocol.upper())
    if src_ip:
        q = q.filter(Packet.src_ip == src_ip)
    if dst_ip:
        q = q.filter(Packet.dst_ip == dst_ip)
    if session_id:
        q = q.filter(Packet.session_id == session_id)
    if search:
        like = f"%{search}%"
        q = q.filter((Packet.src_ip.like(like)) | (Packet.dst_ip.like(like)) | (Packet.raw_summary.like(like)))

    sort_column = getattr(Packet, sort_by, Packet.timestamp)
    q = q.order_by(sort_column.desc() if sort_dir == "desc" else sort_column.asc())

    q = q.offset((page - 1) * page_size).limit(page_size)
    return q.all()


@router.get("/{packet_id}", response_model=PacketOut)
async def get_packet(packet_id: int, db: Session = Depends(get_db)):
    packet = db.query(Packet).get(packet_id)
    if not packet:
        raise HTTPException(status_code=404, detail="Packet not found")
    return packet


@router.get("/export/csv", response_class=PlainTextResponse)
async def export_csv(session_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Packet)
    if session_id:
        q = q.filter(Packet.session_id == session_id)
    content = to_csv(q.order_by(Packet.timestamp.desc()).limit(50000).all())
    return PlainTextResponse(content, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=netscope_packets.csv"
    })


@router.get("/export/json", response_class=PlainTextResponse)
async def export_json(session_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Packet)
    if session_id:
        q = q.filter(Packet.session_id == session_id)
    content = to_json(q.order_by(Packet.timestamp.desc()).limit(50000).all())
    return PlainTextResponse(content, media_type="application/json", headers={
        "Content-Disposition": "attachment; filename=netscope_packets.json"
    })
