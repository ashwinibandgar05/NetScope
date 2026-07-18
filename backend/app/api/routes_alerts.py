from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.alert import Alert
from app.schemas.alert import AlertAck, AlertOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/", response_model=list[AlertOut])
async def list_alerts(
    db: Session = Depends(get_db),
    severity: str | None = None,
    acknowledged: bool | None = None,
    limit: int = Query(default=100, le=1000),
):
    q = db.query(Alert)
    if severity:
        q = q.filter(Alert.severity == severity)
    if acknowledged is not None:
        q = q.filter(Alert.acknowledged == (1 if acknowledged else 0))
    return q.order_by(Alert.timestamp.desc()).limit(limit).all()


@router.patch("/{alert_id}", response_model=AlertOut)
async def acknowledge_alert(alert_id: int, payload: AlertAck, db: Session = Depends(get_db)):
    alert = db.query(Alert).get(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = 1 if payload.acknowledged else 0
    db.commit()
    db.refresh(alert)
    return alert


@router.get("/summary")
async def alert_summary(db: Session = Depends(get_db)):
    total = db.query(Alert).count()
    unacknowledged = db.query(Alert).filter(Alert.acknowledged == 0).count()
    high = db.query(Alert).filter(Alert.severity == "high").count()
    return {"total": total, "unacknowledged": unacknowledged, "high_severity": high}
