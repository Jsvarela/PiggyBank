import logging
import re

import pytest
from fastapi.testclient import TestClient

from app import mailer
from app.config import settings
from app.main import app
from app.security import create_purpose_token, create_token
from tests.test_api import mk_account, mk_category, mk_tx

CREDS = {"email": "yo@example.com", "password": "clave-segura-123"}
NEW = "otra-clave-muy-larga-456"


@pytest.fixture
def mails(monkeypatch):
    """Activa el correo y captura lo que se enviaría."""
    sent: list[tuple[str, str, str]] = []
    monkeypatch.setattr(settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(mailer, "_deliver", lambda to, subject, body: sent.append((to, subject, body)))
    return sent


def token_in(mail: tuple[str, str, str]) -> str:
    return re.search(r"token=([\w.\-]+)", mail[2]).group(1)


def login(client, password=CREDS["password"]):
    return client.post("/api/auth/login", json={"email": CREDS["email"], "password": password})


# ---------- primer arranque ----------
def test_registrar_crea_las_categorias_por_defecto(client):
    # en producción nadie corre el script de seed: sin esto no se podría registrar ni un gasto
    client.post("/api/auth/register", json=CREDS)
    client.post("/api/auth/login", json=CREDS)
    names = {c["name"] for c in client.get("/api/categories").json()}
    assert {"Comida", "Transporte", "Salario", "Otros", "Otros ingresos"} <= names


def test_config_publica_no_expone_secretos(client):
    r = client.get("/api/config")
    assert r.status_code == 200
    assert set(r.json()) == {"email_enabled", "analytics_url", "registration"}


# ---------- recuperar contraseña ----------
def test_olvide_mi_clave_no_revela_si_el_correo_existe(authed, mails):
    a = authed.post("/api/auth/forgot-password", json={"email": "nadie@example.com"})
    b = authed.post("/api/auth/forgot-password", json={"email": CREDS["email"]})
    assert a.status_code == b.status_code == 204
    assert [m[0] for m in mails] == [CREDS["email"]]  # solo el real recibe correo


def test_restablecer_clave_de_punta_a_punta(authed, client, mails):
    client.post("/api/auth/logout")
    client.post("/api/auth/forgot-password", json={"email": CREDS["email"]})
    token = token_in(mails[-1])
    assert client.post("/api/auth/reset-password", json={"token": token, "password": NEW}).status_code == 204
    assert login(client).status_code == 401  # la clave vieja ya no sirve
    assert login(client, NEW).status_code == 200
    # el enlace es de un solo uso
    assert client.post("/api/auth/reset-password", json={"token": token, "password": "tercera-clave-789"}).status_code == 422


def test_restablecer_cierra_las_sesiones_abiertas(authed, mails):
    viejo = authed.cookies["session"]
    authed.post("/api/auth/forgot-password", json={"email": CREDS["email"]})
    authed.post("/api/auth/reset-password", json={"token": token_in(mails[-1]), "password": NEW})
    otro = TestClient(app, cookies={"session": viejo})
    assert otro.get("/api/auth/me").status_code == 401


def test_tokens_invalidos_se_rechazan(authed, client):
    # expirado, de otro propósito (una cookie de sesión) o basura
    caducado = create_purpose_token(1, "reset", 0, minutes=-1)
    sesion = create_token(1, 0)
    for t in (caducado, sesion, "basura"):
        r = client.post("/api/auth/reset-password", json={"token": t, "password": NEW})
        assert r.status_code == 422, t[:12]
    assert client.post("/api/auth/reset-password", json={"token": caducado, "password": "corta"}).status_code == 422


def test_sin_correo_configurado_no_se_envia_nada(authed, monkeypatch):
    sent = []
    monkeypatch.setattr(mailer, "_deliver", lambda *a: sent.append(a))
    assert authed.post("/api/auth/forgot-password", json={"email": CREDS["email"]}).status_code == 204
    assert sent == []


def test_olvide_mi_clave_tiene_rate_limit(client, mails):
    codes = [client.post("/api/auth/forgot-password", json={"email": "x@example.com"}).status_code for _ in range(7)]
    assert 429 in codes and codes[0] == 204


# ---------- verificar correo ----------
def test_verificacion_de_correo(client, mails):
    client.post("/api/auth/register", json=CREDS)
    assert [m[0] for m in mails] == [CREDS["email"]]  # se envía al registrarse
    login(client)
    assert client.get("/api/auth/me").json()["email_verified"] is False
    assert client.post("/api/auth/verify-email", json={"token": token_in(mails[0])}).status_code == 204
    assert client.get("/api/auth/me").json()["email_verified"] is True
    assert client.post("/api/auth/verify-email", json={"token": "basura"}).status_code == 422


def test_reenviar_verificacion(client, mails):
    client.post("/api/auth/register", json=CREDS)
    login(client)
    assert client.post("/api/auth/send-verification").status_code == 204
    assert len(mails) == 2
    client.post("/api/auth/verify-email", json={"token": token_in(mails[-1])})
    assert client.post("/api/auth/send-verification").status_code == 204
    assert len(mails) == 2  # ya verificado: no reenvía


# ---------- cambiar clave y cerrar sesión en todos lados ----------
def test_cambiar_clave(authed, client):
    body = {"current_password": CREDS["password"], "new_password": NEW}
    assert authed.post("/api/auth/change-password", json={**body, "current_password": "incorrecta-123"}).status_code == 403
    assert authed.post("/api/auth/change-password", json={**body, "new_password": "corta"}).status_code == 422
    viejo = authed.cookies["session"]
    assert authed.post("/api/auth/change-password", json=body).status_code == 204
    assert authed.get("/api/auth/me").status_code == 200  # este dispositivo sigue dentro
    assert TestClient(app, cookies={"session": viejo}).get("/api/auth/me").status_code == 401  # los demás no
    client.cookies.clear()
    assert login(client).status_code == 401 and login(client, NEW).status_code == 200


def test_cerrar_sesion_en_todos_los_dispositivos(authed):
    token = authed.cookies["session"]
    assert authed.post("/api/auth/logout-all").status_code == 204
    assert TestClient(app, cookies={"session": token}).get("/api/auth/me").status_code == 401


def test_logout_normal_solo_cierra_este_dispositivo(authed):
    token = authed.cookies["session"]
    authed.post("/api/auth/logout")
    assert authed.get("/api/auth/me").status_code == 401
    assert TestClient(app, cookies={"session": token}).get("/api/auth/me").status_code == 200


# ---------- borrar cuenta ----------
def test_borrar_cuenta_pide_la_clave_y_no_toca_nada_si_falla(authed):
    mk_tx(authed, type="expense", amount=5, date="2026-03-01", account_id=mk_account(authed)["id"], category_id=mk_category(authed)["id"])
    assert authed.request("DELETE", "/api/auth/account", json={"password": "incorrecta-123"}).status_code == 403
    assert authed.get("/api/transactions").json()["total"] == 1


def test_borrar_cuenta_elimina_todo_y_deja_registrar_de_nuevo(authed):
    a = mk_account(authed)
    cat = mk_category(authed, name="Mía")
    mk_tx(authed, type="expense", amount=5, date="2026-03-01", account_id=a["id"], category_id=cat["id"])
    authed.put("/api/budgets", json={"category_id": cat["id"], "limit_amount": 100})
    authed.post("/api/savings-goals", json={"name": "Meta", "target_amount": 10})
    r = authed.request("DELETE", "/api/auth/account", json={"password": CREDS["password"]})
    assert r.status_code == 204
    assert authed.get("/api/auth/me").status_code == 401
    # instalación limpia: se puede crear un usuario nuevo y no queda nada del anterior
    assert authed.post("/api/auth/register", json={"email": "nuevo@example.com", "password": NEW}).status_code == 201
    authed.post("/api/auth/login", json={"email": "nuevo@example.com", "password": NEW})
    assert authed.get("/api/accounts").json() == []
    assert authed.get("/api/transactions").json()["total"] == 0
    assert authed.get("/api/savings-goals").json() == []
    assert "Mía" not in {c["name"] for c in authed.get("/api/categories").json()}


# ---------- errores del cliente (seguimiento de errores) ----------
def test_registra_errores_del_navegador_en_el_log(client, caplog):
    payload = {"message": "TypeError: x is undefined", "stack": "at Foo (app.js:1)", "url": "/presupuestos"}
    with caplog.at_level(logging.ERROR, logger="finanzas.client"):
        assert client.post("/api/client-errors", json=payload).status_code == 204
    assert "TypeError: x is undefined" in caplog.text and "/presupuestos" in caplog.text


def test_errores_del_cliente_tienen_limites(client):
    assert client.post("/api/client-errors", json={"message": "x" * 3000}).status_code == 422
    codes = [client.post("/api/client-errors", json={"message": "e"}).status_code for _ in range(40)]
    assert 429 in codes  # no se puede inundar el log
