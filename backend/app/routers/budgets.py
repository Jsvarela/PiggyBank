from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Budget
from app.schemas import MONTH, BudgetIn, BudgetOut, BudgetStatus, MonthlyReport
from app.services import budgets, catalog
from app.timeutil import today_bogota

router = APIRouter(dependencies=[Depends(get_current_user)], tags=["budgets"])


def _month(month: str | None) -> str:
    return month or today_bogota().strftime("%Y-%m")


@router.get("/budgets", response_model=list[BudgetOut])
def list_budgets(db: Session = Depends(get_db)):
    return db.scalars(select(Budget).order_by(Budget.id)).all()


@router.put("/budgets", response_model=BudgetOut)
def save_budget(body: BudgetIn, db: Session = Depends(get_db)):
    return budgets.save_budget(db, body)


@router.delete("/budgets/{id}", status_code=204)
def delete_budget(id: int, db: Session = Depends(get_db)):
    db.delete(catalog.get_or_404(db, Budget, id))
    db.commit()


@router.get("/budgets/status", response_model=list[BudgetStatus])
def status(month: str | None = Query(None, pattern=MONTH), db: Session = Depends(get_db)):
    return budgets.budget_status(db, _month(month), today_bogota())


@router.get("/reports/monthly", response_model=MonthlyReport)
def monthly(month: str | None = Query(None, pattern=MONTH), db: Session = Depends(get_db)):
    return budgets.monthly_report(db, _month(month))
