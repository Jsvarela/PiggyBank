from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Invite
from tests.test_api import mk_account

CREDS = {"email": "nueva@example.com", "password": "clave-nueva-123"}


def nueva_invitacion(admin):
    r = admin.post("/api/auth/invites")
    assert r.status_code == 201, r.text
    return r.json()


def registrar(client, code, **extra):
    return client.post("/api/auth/register", json={**CREDS, **({"invite_code": code} if code is not None else {}), **extra})


def test_el_primer_usuario_se_registra_sin_codigo_y_es_administrador(client):
    assert client.get("/api/config").json()["registration"] == "first"
    assert client.post("/api/auth/register", json={"email": "yo@example.com", "password": "clave-segura-123"}).status_code == 201
    client.post("/api/auth/login", json={"email": "yo@example.com", "password": "clave-segura-123"})
    assert client.get("/api/auth/me").json()["is_admin"] is True
    assert client.get("/api/config").json()["registration"] == "invite"


def test_despues_del_primero_se_exige_invitacion(authed, client):
    from fastapi.testclient import TestClient

    from app.main import app

    c = TestClient(app)
    assert registrar(c, None).status_code == 403
    assert registrar(c, "codigo-inventado").status_code == 403
    assert registrar(c, "").status_code == 403


def test_una_invitacion_valida_crea_cuenta_normal_con_sus_categorias(authed):
    from fastapi.testclient import TestClient

    from app.main import app

    inv = nueva_invitacion(authed)
    c = TestClient(app)
    assert registrar(c, inv["code"]).status_code == 201
    c.post("/api/auth/login", json=CREDS)
    me = c.get("/api/auth/me").json()
    assert me["is_admin"] is False
    assert {"Comida", "Salario"} <= {x["name"] for x in c.get("/api/categories").json()}


def test_la_invitacion_sirve_una_sola_vez(authed):
    from fastapi.testclient import TestClient

    from app.main import app

    code = nueva_invitacion(authed)["code"]
    assert registrar(TestClient(app), code).status_code == 201
    r = registrar(TestClient(app), code, email="otra2@example.com")
    assert r.status_code == 403


def test_invitacion_vencida_o_revocada_no_sirve(authed, engine):
    from fastapi.testclient import TestClient

    from app.main import app

    vencida = nueva_invitacion(authed)
    with Session(engine) as s:
        s.execute(update(Invite).where(Invite.id == vencida["id"]).values(expires_at=datetime.now(UTC) - timedelta(minutes=1)))
        s.commit()
    assert registrar(TestClient(app), vencida["code"]).status_code == 403

    revocada = nueva_invitacion(authed)
    assert authed.delete(f"/api/auth/invites/{revocada['id']}").status_code == 204
    assert registrar(TestClient(app), revocada["code"]).status_code == 403


def test_correo_repetido_se_rechaza_y_no_gasta_la_invitacion(authed):
    from fastapi.testclient import TestClient

    from app.main import app

    code = nueva_invitacion(authed)["code"]
    r = registrar(TestClient(app), code, email="yo@example.com")  # el correo del administrador
    assert r.status_code == 409
    assert registrar(TestClient(app), code).status_code == 201  # la invitación seguía libre


def test_el_codigo_no_se_guarda_en_claro(authed, engine):
    inv = nueva_invitacion(authed)
    with Session(engine) as s:
        guardado = s.scalar(select(Invite.code_hash).where(Invite.id == inv["id"]))
    assert guardado != inv["code"] and len(guardado) == 64


def test_solo_el_administrador_maneja_invitaciones(authed, otro):
    inv = nueva_invitacion(authed)
    assert otro.post("/api/auth/invites").status_code == 403
    assert otro.get("/api/auth/invites").status_code == 403
    assert otro.delete(f"/api/auth/invites/{inv['id']}").status_code == 403


def test_lista_de_invitaciones_con_estado(authed, otro):
    # `otro` ya consumió una invitación
    pendiente = nueva_invitacion(authed)
    lista = {i["id"]: i for i in authed.get("/api/auth/invites").json()}
    assert lista[pendiente["id"]]["status"] == "pendiente"
    usadas = [i for i in lista.values() if i["status"] == "usada"]
    assert [i["used_by_email"] for i in usadas] == ["otra@example.com"]
    assert "code" not in lista[pendiente["id"]]  # el código solo se ve al crearla


def test_el_administrador_no_puede_borrar_su_cuenta_si_hay_otros_usuarios(authed, otro):
    r = authed.request("DELETE", "/api/auth/account", json={"password": "clave-segura-123"})
    assert r.status_code == 409
    assert authed.get("/api/auth/me").status_code == 200


def test_un_usuario_normal_si_puede_borrar_su_cuenta_y_la_invitacion_no_revive(authed, otro):
    mk_account(otro, name="Mía")
    assert otro.request("DELETE", "/api/auth/account", json={"password": "otra-clave-segura-1"}).status_code == 204
    # el administrador sigue pudiendo invitar y sus datos están
    assert authed.post("/api/auth/invites").status_code == 201
