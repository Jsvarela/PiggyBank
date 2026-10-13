from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.services import backup

router = APIRouter(dependencies=[Depends(get_current_user)], tags=["backup"])


def _download(content: str, media_type: str, filename: str) -> Response:
    return Response(content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/export/transactions.csv")
def export_csv(db: Session = Depends(get_db)):
    # BOM para que Excel respete las tildes
    return _download("﻿" + backup.transactions_csv(db), "text/csv; charset=utf-8", "movimientos.csv")


@router.get("/export/backup.json")
def export_backup(db: Session = Depends(get_db)):
    return _download(backup.export_backup(db).model_dump_json(), "application/json", "finanzas-respaldo.json")


@router.post("/import/backup")
def import_backup(body: backup.Backup, db: Session = Depends(get_db)) -> dict[str, int]:
    """Reemplaza todos los datos actuales por los del respaldo."""
    backup.restore_backup(db, body)
    return {"transactions": len(body.transactions), "accounts": len(body.accounts)}
