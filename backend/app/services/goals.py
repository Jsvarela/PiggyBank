from datetime import date

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.errors import DomainError
from app.models import Account, SavingsGoal, Transaction, TxType
from app.schemas import GoalIn, GoalOut
from app.services.balances import sum_pesos
from app.services.catalog import get_or_404


def monthly_suggestion(goal: SavingsGoal, saved: int, today: date) -> int | None:
    """Lo que falta repartido en los meses que quedan (mínimo 1, redondeado hacia arriba).

    Los meses se cuentan como diferencia de meses calendario: de oct-13 a ene-13 son 3.
    """
    remaining = max(goal.target_amount - saved, 0)
    if remaining == 0:
        return 0
    if goal.deadline is None:
        return None
    months = max(1, (goal.deadline.year - today.year) * 12 + goal.deadline.month - today.month)
    return -(-remaining // months)


def goal_progress(db: Session, goal: SavingsGoal, today: date) -> GoalOut:
    saved = db.scalar(
        select(func.coalesce(sum_pesos(Transaction.amount), 0)).where(Transaction.goal_id == goal.id)
    )
    return GoalOut(
        id=goal.id, name=goal.name, target_amount=goal.target_amount, deadline=goal.deadline,
        account_id=goal.account_id, saved=saved,
        remaining=max(goal.target_amount - saved, 0),
        percent=saved * 100 // goal.target_amount,
        reached=saved >= goal.target_amount,
        monthly_suggested=monthly_suggestion(goal, saved, today),
    )


def save_goal(db: Session, data: GoalIn, goal: SavingsGoal | None = None) -> SavingsGoal:
    if data.account_id is not None:
        get_or_404(db, Account, data.account_id)
    goal = goal or SavingsGoal()
    for k, v in data.model_dump().items():
        setattr(goal, k, v)
    db.add(goal)
    db.commit()
    return goal


def delete_goal(db: Session, goal: SavingsGoal) -> None:
    # los aportes ya hechos son transferencias reales: se conservan, solo se desvinculan
    db.execute(update(Transaction).where(Transaction.goal_id == goal.id).values(goal_id=None))
    db.delete(goal)
    db.commit()


def contribute(db: Session, goal: SavingsGoal, from_account_id: int, amount: int, on: date) -> Transaction:
    """Un aporte es una transferencia hacia la cuenta de la meta, marcada con goal_id."""
    if goal.account_id is None:
        raise DomainError("Asigna una cuenta de ahorro a la meta para poder aportar")
    get_or_404(db, Account, from_account_id)
    if from_account_id == goal.account_id:
        raise DomainError("El aporte debe salir de una cuenta distinta a la de la meta")
    tx = Transaction(
        type=TxType.transfer, amount=amount, date=on, account_id=from_account_id,
        to_account_id=goal.account_id, goal_id=goal.id, description=f"Aporte a {goal.name}",
    )
    db.add(tx)
    db.commit()
    return tx
