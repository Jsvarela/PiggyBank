from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.services import statement

router = APIRouter(dependencies=[Depends(get_current_user)], tags=["import"])


class PreviewIn(BaseModel):
    text: str
    account_id: int
    mapping: statement.Mapping | None = None


@router.post("/import/csv/preview", response_model=statement.StatementPreview)
def preview(body: PreviewIn, db: Session = Depends(get_db)):
    """Sin `mapping` devuelve los encabezados y una sugerencia; con `mapping`, las filas interpretadas."""
    return statement.preview_statement(db, body.text, body.account_id, body.mapping)
