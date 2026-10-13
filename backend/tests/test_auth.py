import pytest

CREDS = {"email": "yo@example.com", "password": "clave-segura-123"}

PROTECTED = [
    "/api/auth/me",
    "/api/accounts",
    "/api/categories",
    "/api/transactions",
    "/api/dashboard",
]


@pytest.mark.parametrize("path", PROTECTED)
def test_rutas_protegidas_devuelven_401_sin_sesion(client, path):
    assert client.get(path).status_code == 401


def test_no_se_puede_registrar_un_segundo_usuario(client):
    assert client.post("/api/auth/register", json=CREDS).status_code == 201
    r = client.post("/api/auth/register", json={**CREDS, "email": "otro@example.com"})
    assert r.status_code == 403


def test_login_crea_cookie_httponly_y_permite_acceso(client):
    client.post("/api/auth/register", json=CREDS)
    r = client.post("/api/auth/login", json=CREDS)
    assert r.status_code == 200
    assert "httponly" in r.headers["set-cookie"].lower()
    assert client.get("/api/auth/me").json()["email"] == CREDS["email"]


def test_login_con_clave_incorrecta(client):
    client.post("/api/auth/register", json=CREDS)
    r = client.post("/api/auth/login", json={**CREDS, "password": "incorrecta-123"})
    assert r.status_code == 401


def test_logout_cierra_la_sesion(authed):
    assert authed.post("/api/auth/logout").status_code == 204
    assert authed.get("/api/auth/me").status_code == 401


def test_login_tiene_rate_limit(client):
    client.post("/api/auth/register", json=CREDS)
    bad = {**CREDS, "password": "incorrecta-123"}
    codes = [client.post("/api/auth/login", json=bad).status_code for _ in range(7)]
    assert codes[:5] == [401] * 5
    assert 429 in codes[5:]


def test_clave_muy_corta_se_rechaza(client):
    r = client.post("/api/auth/register", json={**CREDS, "password": "corta"})
    assert r.status_code == 422
