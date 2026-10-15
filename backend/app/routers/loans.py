from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.errors import DomainError
from app.models import Loan
from app.schemas import LoanIn, LoanOut, PaymentIn
from app.services.catalog import get_or_404

router = APIRouter(dependencies=[Depends(get_current_user)], tags=["loans"])


def _save(db: Session, loan: Loan, data: dict) -> Loan:
    for k, v in data.items():
        setattr(loan, k, v)
    loan.paid = loan.received >= loan.expected_amount  # nunca se guarda a mano: sale de los abonos
    db.add(loan)
    db.commit()
    return loan


@router.get("/loans", response_model=list[LoanOut])
def list_loans(db: Session = Depends(get_db)):
    # pendientes primero, y entre ellos el que vence antes (sin fecha al final)
    return db.scalars(select(Loan).order_by(Loan.paid, Loan.due_date.is_(None), Loan.due_date, Loan.id)).all()


@router.post("/loans", status_code=201, response_model=LoanOut)
def create_loan(body: LoanIn, db: Session = Depends(get_db)):
    return _save(db, Loan(), body.model_dump())


@router.put("/loans/{id}", response_model=LoanOut)
def update_loan(id: int, body: LoanIn, db: Session = Depends(get_db)):
    return _save(db, get_or_404(db, Loan, id), body.model_dump())


@router.post("/loans/{id}/payments", response_model=LoanOut)
def add_payment(id: int, body: PaymentIn, db: Session = Depends(get_db)):
    loan = get_or_404(db, Loan, id)
    if loan.received + body.amount > loan.expected_amount:
        raise DomainError(f"Solo faltan {loan.expected_amount - loan.received} por abonar")
    return _save(db, loan, {"received": loan.received + body.amount})


@router.delete("/loans/{id}", status_code=204)
def delete_loan(id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Loan, id))
    db.commit()
