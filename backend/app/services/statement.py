"""Vista previa de un extracto bancario en CSV. No escribe nada: el usuario revisa y luego confirma."""

import csv
import datetime as dt
import io
import re
import unicodedata
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import DomainError
from app.models import Account, Transaction, TxType
from app.services.catalog import get_or_404

MAX_ROWS = 5000
_HEADER_WORDS = {
    "date": ("fecha", "date"),
    "description": ("descripcion", "detalle", "concepto", "description", "details", "referencia"),
    "amount": ("valor", "monto", "importe", "amount"),
    "debit": ("debito", "debit", "cargo", "retiro"),
    "credit": ("credito", "credit", "abono", "deposito"),
}


class Mapping(BaseModel):
    date_col: int
    description_col: int | None = None
    amount_col: int | None = None  # una columna con signo (negativo = gasto)
    debit_col: int | None = None  # o dos columnas: débito y crédito
    credit_col: int | None = None
    date_format: Literal["dmy", "mdy", "ymd"] = "dmy"
    decimal: Literal[",", "."] = ","
    invert_sign: bool = False  # tarjetas de crédito: las compras vienen en positivo
    has_header: bool = True

    @model_validator(mode="after")
    def _has_amount(self):
        if self.amount_col is None and self.debit_col is None and self.credit_col is None:
            raise ValueError("Indica la columna del monto (o las de débito y crédito)")
        return self


class PreviewRow(BaseModel):
    line: int  # número de fila en el archivo, para ubicarla
    date: dt.date | None = None
    amount: int | None = None
    type: Literal["income", "expense"] | None = None
    description: str = ""
    duplicate: bool = False
    error: str | None = None


class StatementPreview(BaseModel):
    delimiter: str
    headers: list[str]
    sample: list[list[str]]
    suggested: Mapping | None
    rows: list[PreviewRow]


def _plain(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def _delimiter(first_line: str) -> str:
    counts = {d: first_line.count(d) for d in (";", ",", "\t")}
    best = max(counts, key=lambda d: counts[d])
    return best if counts[best] else ","


def suggest_mapping(headers: list[str]) -> Mapping | None:
    found: dict[str, int] = {}
    for i, h in enumerate(headers):
        for kind, words in _HEADER_WORDS.items():
            if kind not in found and any(w in _plain(h) for w in words):
                found[kind] = i
                break
    if "date" not in found:
        return None
    if "debit" in found and "credit" in found:
        return Mapping(date_col=found["date"], description_col=found.get("description"),
                       debit_col=found["debit"], credit_col=found["credit"])
    if "amount" in found:
        return Mapping(date_col=found["date"], description_col=found.get("description"), amount_col=found["amount"])
    return None


def parse_number(raw: str, decimal: str) -> Decimal | None:
    """Número de un extracto a Decimal (nunca float). Vacío -> None; ilegible -> ValueError."""
    s = raw.strip()
    if not s:
        return None
    negative = (s.startswith("(") and s.endswith(")")) or "-" in s
    s = re.sub(r"[^\d.,]", "", s)
    if not s:
        return None
    thousands = "." if decimal == "," else ","
    try:
        value = Decimal(s.replace(thousands, "").replace(decimal, "."))
    except InvalidOperation:
        raise ValueError(f"Monto ilegible: {raw!r}") from None
    return -value if negative else value


def parse_date(raw: str, fmt: str) -> dt.date:
    parts = [int(p) for p in re.findall(r"\d+", raw)[:3]]
    if len(parts) < 3:
        raise ValueError(f"Fecha ilegible: {raw!r}")
    d, m, y = {"dmy": parts, "mdy": (parts[1], parts[0], parts[2]), "ymd": parts[::-1]}[fmt]
    try:
        return dt.date(y + 2000 if y < 100 else y, m, d)
    except ValueError:
        raise ValueError(f"Fecha inválida: {raw!r}") from None


def _to_pesos(d: Decimal) -> int:
    return int(abs(d).quantize(Decimal(1), ROUND_HALF_UP))


def _parse_row(line: int, cells: list[str], m: Mapping) -> PreviewRow:
    def cell(i: int | None) -> str:
        if i is None:
            return ""
        if i >= len(cells):
            raise ValueError("Faltan columnas en esta fila")
        return cells[i]

    row = PreviewRow(line=line)
    try:
        row.date = parse_date(cell(m.date_col), m.date_format)
        row.description = cell(m.description_col).strip()[:255]
        if m.amount_col is not None:
            n = parse_number(cell(m.amount_col), m.decimal)
            if n is not None and m.invert_sign:
                n = -n
            kind = "income" if n is not None and n > 0 else "expense"
        else:
            debit, credit = parse_number(cell(m.debit_col), m.decimal), parse_number(cell(m.credit_col), m.decimal)
            if debit and credit:
                raise ValueError("La fila tiene débito y crédito a la vez")
            n, kind = (credit, "income") if credit else (debit, "expense")
        row.amount = _to_pesos(n) if n is not None else 0
        row.type = kind
        if row.amount == 0:
            raise ValueError("Monto vacío o cero")
    except ValueError as e:
        row.error = str(e)
    return row


def preview_statement(db: Session, text: str, account_id: int, mapping: Mapping | None) -> StatementPreview:
    get_or_404(db, Account, account_id)
    text = text.lstrip("﻿")
    if not text.strip():
        raise DomainError("El archivo está vacío")
    delimiter = _delimiter(text.splitlines()[0])
    lines = [r for r in csv.reader(io.StringIO(text), delimiter=delimiter) if any(c.strip() for c in r)]
    if len(lines) > MAX_ROWS + 1:
        raise DomainError(f"El archivo tiene más de {MAX_ROWS} filas: divídelo en partes")

    has_header = mapping.has_header if mapping else True
    headers, data = (lines[0], lines[1:]) if has_header else ([f"Columna {i + 1}" for i in range(len(lines[0]))], lines)
    out = StatementPreview(delimiter=delimiter, headers=headers, sample=data[:5],
                           suggested=suggest_mapping(headers), rows=[])
    if mapping is None:
        return out

    width = len(headers)
    for col in (mapping.date_col, mapping.description_col, mapping.amount_col, mapping.debit_col, mapping.credit_col):
        if col is not None and not 0 <= col < width:
            raise DomainError(f"La columna {col + 1} no existe: el archivo tiene {width}")

    offset = 2 if has_header else 1
    out.rows = [_parse_row(i + offset, cells, mapping) for i, cells in enumerate(data)]
    _mark_duplicates(db, account_id, out.rows)
    return out


def _mark_duplicates(db: Session, account_id: int, rows: list[PreviewRow]) -> None:
    """Una fila es duplicada si ya hay un movimiento igual (fecha, monto, tipo, descripción) en la cuenta.

    Se cuenta como multiconjunto: si el archivo trae dos cafés iguales y ya existe uno, solo uno se marca.
    """
    valid = [r for r in rows if not r.error]
    if not valid:
        return
    q = select(Transaction).where(
        Transaction.account_id == account_id,
        Transaction.type.in_([TxType.income, TxType.expense]),
        Transaction.date >= min(r.date for r in valid),
        Transaction.date <= max(r.date for r in valid),
    )
    existing = Counter((t.date, t.amount, t.type.value, (t.description or "").strip().lower()) for t in db.scalars(q))
    for r in valid:
        key = (r.date, r.amount, r.type, r.description.strip().lower())
        if existing[key] > 0:
            existing[key] -= 1
            r.duplicate = True
