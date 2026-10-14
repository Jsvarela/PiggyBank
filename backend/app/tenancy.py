"""Aislamiento entre usuarios: cada persona ve y toca SOLO sus datos.

En vez de acordarse de filtrar por dueño en cada consulta (hay decenas), el filtro se aplica aquí, una vez:
  - todo SELECT/UPDATE/DELETE de un modelo `Owned` recibe `WHERE user_id = <usuario de la sesión>`;
  - todo objeto nuevo recibe su `user_id` solo (el cliente nunca lo manda);
  - si la sesión no tiene usuario, tocar datos con dueño LANZA ERROR: jamás devuelve "todo".
El usuario de la sesión se fija en `db.info["user_id"]` (ver deps.get_current_user).
Importar este módulo registra los eventos; app.models lo importa, así que están siempre activos.
"""

from sqlalchemy import ForeignKey, Table, event
from sqlalchemy.orm import Mapped, Session, declared_attr, mapped_column, with_loader_criteria
from sqlalchemy.sql import visitors
from sqlalchemy.sql.selectable import Join


class TenantError(RuntimeError):
    """Se intentó leer o escribir datos con dueño sin saber de qué usuario son."""


class Owned:
    """Marca los modelos cuyos datos pertenecen a un usuario."""

    @declared_attr
    def user_id(cls) -> Mapped[int]:
        return mapped_column(ForeignKey("users.id"), index=True)


def _owned_tables() -> dict[Table, type]:
    return {cls.__table__: cls for cls in Owned.__subclasses__()}


def _top_level_tables(froms) -> set[Table]:
    """Tablas que están directamente en el FROM (solas o dentro de un JOIN), no dentro de subconsultas."""
    found: set[Table] = set()
    for f in froms:
        if isinstance(f, Table):
            found.add(f)
        elif isinstance(f, Join):
            found |= _top_level_tables([f.left, f.right])
    return found


@event.listens_for(Session, "do_orm_execute")
def _scope_to_user(state) -> None:
    if state.is_column_load or state.is_relationship_load or state.is_insert:
        return  # derivan de objetos que ya salieron de una consulta filtrada / los inserts los cubre before_flush
    owned_tables = _owned_tables()
    # Se miran las tablas de la consulta, no solo `all_mappers`: `select(count()).select_from(Modelo)`
    # no reporta ningún modelo y, confiando en eso, saldría SIN filtro (comprobado en test_tenancy).
    in_query = {el for el in visitors.iterate(state.statement) if isinstance(el, Table) and el in owned_tables}
    if not in_query:
        return
    user_id = state.session.info.get("user_id")
    if user_id is None:
        raise TenantError("Consulta sobre datos con dueño (" + ", ".join(sorted(t.name for t in in_query)) + ") sin usuario en la sesión")

    by_mapper = {m.local_table for m in state.all_mappers if issubclass(m.class_, Owned)}
    for table in in_query & by_mapper:  # el caso normal: el modelo aparece en columnas, WHERE o JOIN
        state.statement = state.statement.options(
            with_loader_criteria(owned_tables[table], owned_tables[table].user_id == user_id, include_aliases=True)
        )
    for table in in_query - by_mapper:  # solo aparece en el FROM: se filtra la tabla directamente
        top = _top_level_tables(state.statement.get_final_froms()) if state.is_select else set()
        if table not in top:
            raise TenantError(f"Forma de consulta no soportada sobre {table.name} (subconsulta o alias): no se puede aislar")
        state.statement = state.statement.where(table.c.user_id == user_id)


@event.listens_for(Session, "before_flush")
def _assign_owner(session: Session, _flush_context, _instances) -> None:
    for obj in session.new:
        if isinstance(obj, Owned) and getattr(obj, "user_id", None) is None:
            user_id = session.info.get("user_id")
            if user_id is None:
                raise TenantError(f"No se puede guardar {type(obj).__name__} sin usuario en la sesión")
            obj.user_id = user_id
