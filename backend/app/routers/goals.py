from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import SavingsGoal
from app.schemas import ContributionIn, GoalIn, GoalOut, TransactionOut
from app.services import catalog, goals
from app.timeutil import today_bogota

router = APIRouter(dependencies=[Depends(get_current_user)], tags=["goals"])


@router.get("/savings-goals", response_model=list[GoalOut])
def list_goals(db: Session = Depends(get_db)):
    today = today_bogota()
    return [goals.goal_progress(db, g, today) for g in db.scalars(select(SavingsGoal).order_by(SavingsGoal.id))]


@router.post("/savings-goals", status_code=201, response_model=GoalOut)
def create_goal(body: GoalIn, db: Session = Depends(get_db)):
    return goals.goal_progress(db, goals.save_goal(db, body), today_bogota())


@router.put("/savings-goals/{id}", response_model=GoalOut)
def update_goal(id: int, body: GoalIn, db: Session = Depends(get_db)):
    goal = goals.save_goal(db, body, catalog.get_or_404(db, SavingsGoal, id))
    return goals.goal_progress(db, goal, today_bogota())


@router.delete("/savings-goals/{id}", status_code=204)
def delete_goal(id: int, db: Session = Depends(get_db)):
    goals.delete_goal(db, catalog.get_or_404(db, SavingsGoal, id))


@router.post("/savings-goals/{id}/contribute", status_code=201, response_model=TransactionOut)
def contribute(id: int, body: ContributionIn, db: Session = Depends(get_db)):
    goal = catalog.get_or_404(db, SavingsGoal, id)
    return goals.contribute(db, goal, body.from_account_id, body.amount, body.date or today_bogota())
