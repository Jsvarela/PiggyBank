from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Account, Category
from app.schemas import AccountIn, AccountOut, CategoryIn, CategoryOut
from app.services import catalog
from app.services.balances import account_balances

router = APIRouter(dependencies=[Depends(get_current_user)])


def account_out(account: Account, balances: dict[int, int]) -> AccountOut:
    out = AccountOut.model_validate(account)
    out.balance = balances[account.id]
    return out


@router.get("/accounts", response_model=list[AccountOut], tags=["accounts"])
def list_accounts(db: Session = Depends(get_db)):
    balances = account_balances(db)
    return [account_out(a, balances) for a in db.scalars(select(Account).order_by(Account.id))]


@router.post("/accounts", status_code=201, response_model=AccountOut, tags=["accounts"])
def create_account(body: AccountIn, db: Session = Depends(get_db)):
    return account_out(catalog.save_account(db, body), account_balances(db))


@router.put("/accounts/{id}", response_model=AccountOut, tags=["accounts"])
def update_account(id: int, body: AccountIn, db: Session = Depends(get_db)):
    account = catalog.get_or_404(db, Account, id)
    return account_out(catalog.save_account(db, body, account), account_balances(db))


@router.delete("/accounts/{id}", status_code=204, tags=["accounts"])
def delete_account(id: int, db: Session = Depends(get_db)):
    catalog.delete_account(db, catalog.get_or_404(db, Account, id))


@router.get("/categories", response_model=list[CategoryOut], tags=["categories"])
def list_categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.id)).all()


@router.post("/categories", status_code=201, response_model=CategoryOut, tags=["categories"])
def create_category(body: CategoryIn, db: Session = Depends(get_db)):
    return catalog.save_category(db, body)


@router.put("/categories/{id}", response_model=CategoryOut, tags=["categories"])
def update_category(id: int, body: CategoryIn, db: Session = Depends(get_db)):
    return catalog.save_category(db, body, catalog.get_or_404(db, Category, id))


@router.delete("/categories/{id}", status_code=204, tags=["categories"])
def delete_category(id: int, db: Session = Depends(get_db)):
    catalog.delete_category(db, catalog.get_or_404(db, Category, id))
