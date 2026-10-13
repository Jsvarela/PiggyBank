from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import RecurringRule
from app.schemas import RecurringIn, RecurringOut, UpcomingPayment
from app.services import catalog, recurring
from app.timeutil import today_bogota

router = APIRouter(dependencies=[Depends(get_current_user)], tags=["recurring"])


@router.post("/sync")
def sync(db: Session = Depends(get_db)) -> dict[str, int]:
    """El frontend lo llama al abrir la app: crea los movimientos recurrentes pendientes."""
    return {"created": recurring.sync_recurring(db, today_bogota())}


@router.get("/recurring", response_model=list[RecurringOut])
def list_rules(db: Session = Depends(get_db)):
    return db.scalars(select(RecurringRule).order_by(RecurringRule.id)).all()


@router.get("/recurring/upcoming", response_model=list[UpcomingPayment])
def upcoming(days: int = Query(30, ge=1, le=366), db: Session = Depends(get_db)):
    return recurring.upcoming(db, today_bogota(), days)


@router.post("/recurring", status_code=201, response_model=RecurringOut)
def create_rule(body: RecurringIn, db: Session = Depends(get_db)):
    return recurring.save_rule(db, body)


@router.put("/recurring/{id}", response_model=RecurringOut)
def update_rule(id: int, body: RecurringIn, db: Session = Depends(get_db)):
    return recurring.save_rule(db, body, catalog.get_or_404(db, RecurringRule, id))


@router.delete("/recurring/{id}", status_code=204)
def delete_rule(id: int, db: Session = Depends(get_db)):
    recurring.delete_rule(db, catalog.get_or_404(db, RecurringRule, id))
