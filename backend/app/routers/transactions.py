from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Account, Transaction, TxType
from app.routers.catalog import account_out
from app.schemas import Dashboard, TransactionIn, TransactionOut, TransactionPage
from app.services import catalog, transactions
from app.services.balances import account_balances, month_totals, net_worth
from app.timeutil import month_range, today_bogota

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/transactions", response_model=TransactionPage, tags=["transactions"])
def list_transactions(
    start: date | None = Query(None, alias="from"),
    end: date | None = Query(None, alias="to"),
    account_id: int | None = None,
    category_id: int | None = None,
    type: TxType | None = None,
    q: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    items, total = transactions.list_transactions(
        db, start=start, end=end, account_id=account_id, category_id=category_id,
        type_=type, q=q, limit=limit, offset=offset,
    )
    return TransactionPage(items=items, total=total)  # type: ignore[arg-type]


@router.post("/transactions", status_code=201, response_model=TransactionOut, tags=["transactions"])
def create_transaction(body: TransactionIn, response: Response, db: Session = Depends(get_db)):
    # mismo id = mismo movimiento: el modo offline reintenta envíos cuya respuesta pudo perderse
    if body.id and (existing := db.get(Transaction, body.id)):
        response.status_code = 200
        return existing
    return transactions.save_transaction(db, body)


class BulkIn(BaseModel):
    items: list[TransactionIn] = Field(max_length=1000)


@router.post("/transactions/bulk", status_code=201, tags=["transactions"])
def create_transactions(body: BulkIn, db: Session = Depends(get_db)) -> dict[str, int]:
    return {"created": transactions.save_transactions(db, body.items)}


@router.put("/transactions/{id}", response_model=TransactionOut, tags=["transactions"])
def update_transaction(id: str, body: TransactionIn, db: Session = Depends(get_db)):
    return transactions.save_transaction(db, body, catalog.get_or_404(db, Transaction, id))


@router.delete("/transactions/{id}", status_code=204, tags=["transactions"])
def delete_transaction(id: str, db: Session = Depends(get_db)):
    db.delete(catalog.get_or_404(db, Transaction, id))
    db.commit()


@router.get("/dashboard", response_model=Dashboard, tags=["dashboard"])
def dashboard(db: Session = Depends(get_db)):
    today = today_bogota()
    balances = account_balances(db)
    income, expense = month_totals(db, *month_range(today))
    recent = db.scalars(
        select(Transaction).order_by(Transaction.date.desc(), Transaction.created_at.desc()).limit(10)
    ).all()
    return Dashboard(
        month=today.strftime("%Y-%m"),
        accounts=[account_out(a, balances) for a in db.scalars(select(Account).order_by(Account.id))],
        net_worth=net_worth(balances),
        income=income,
        expense=expense,
        recent=recent,  # type: ignore[arg-type]
    )
