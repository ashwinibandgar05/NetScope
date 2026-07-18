from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.packet import Packet
from app.models.session import CaptureSession

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/sessions")
async def list_sessions(db: Session = Depends(get_db)):
    sessions = db.query(CaptureSession).order_by(CaptureSession.started_at.desc()).all()
    return [
        {
            "id": s.id,
            "started_at": s.started_at,
            "ended_at": s.ended_at,
            "interface": s.interface,
            "total_packets": s.total_packets,
            "status": s.status,
        }
        for s in sessions
    ]


@router.get("/sessions/{session_id}")
async def session_detail(session_id: int, db: Session = Depends(get_db)):
    session = db.query(CaptureSession).get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    packet_count = db.query(Packet).filter(Packet.session_id == session_id).count()
    return {
        "id": session.id,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "interface": session.interface,
        "status": session.status,
        "packet_count": packet_count,
    }


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(CaptureSession).get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.query(Packet).filter(Packet.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"status": "deleted"}
