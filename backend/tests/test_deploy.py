import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import DEFAULT_SECRET, Settings
from app.spa import mount_frontend


@pytest.fixture
def web(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>app</html>")
    (dist / "sw.js").write_text("// sw")
    (dist / "assets" / "a.js").write_text("console.log(1)")
    (tmp_path / "secreto.txt").write_text("no debe salir")
    app = FastAPI()

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    mount_frontend(app, dist)
    return TestClient(app)


def test_sirve_el_frontend_y_hace_fallback_a_index(web):
    assert web.get("/").text == "<html>app</html>"
    assert web.get("/presupuestos").text == "<html>app</html>"  # ruta de React Router
    assert web.get("/sw.js").text == "// sw"
    assert web.get("/assets/a.js").text == "console.log(1)"


def test_la_api_no_cae_en_el_fallback(web):
    assert web.get("/api/ping").json() == {"ok": True}
    assert web.get("/api/no-existe").status_code == 404


def test_no_sirve_archivos_fuera_de_la_carpeta(web):
    r = web.get("/..%2Fsecreto.txt")
    assert "no debe salir" not in r.text


def test_produccion_exige_secret_key_propio():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cookie_secure=True, secret_key=DEFAULT_SECRET)
    assert Settings(_env_file=None, cookie_secure=True, secret_key="x" * 40).cookie_secure
    assert Settings(_env_file=None, cookie_secure=False).secret_key == DEFAULT_SECRET  # desarrollo


def test_enlaces_de_correo_usan_la_url_de_render_y_se_puede_sobrescribir(monkeypatch):
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://finanzas.onrender.com")
    assert Settings(_env_file=None).app_url == "https://finanzas.onrender.com"
    assert Settings(_env_file=None, app_url="https://mi-dominio.co").app_url == "https://mi-dominio.co"


def test_url_postgres_de_render_se_normaliza():
    s = Settings(_env_file=None, database_url="postgres://u:p@host/db")
    assert s.database_url == "postgresql://u:p@host/db"
