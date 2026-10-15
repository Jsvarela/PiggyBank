from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Loan
from app.schemas import LoanIn, LoanOut
from app.services.catalog import get_or_404

router = APIRouter(dependencies=[Depends(get_current_user)], tags=["loans"])


@router.get("/loans", response_model=list[LoanOut])
def list_loans(db: Session = Depends(get_db)):
    # pendientes primero, y entre ellos el que se cobra antes (sin fecha al final)
    return db.scalars(select(Loan).order_by(Loan.paid, Loan.due_date.is_(None), Loan.due_date, Loan.id)).all()


@router.post("/loans", status_code=201, response_model=LoanOut)
def create_loan(body: LoanIn, db: Session = Depends(get_db)):
    loan = Loan(**body.model_dump())
    db.add(loan)
    db.commit()
    return loan


@router.put("/loans/{id}", response_model=LoanOut)
def update_loan(id: int, body: LoanIn, db: Session = Depends(get_db)):
    loan = get_or_404(db, Loan, id)
    for k, v in body.model_dump().items():
        setattr(loan, k, v)
    db.commit()
    return loan


@router.delete("/loans/{id}", status_code=204)
def delete_loan(id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Loan, id))
    db.commit()
