import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db import Base, get_db
from app.main import app
from app.models import User
from app.ratelimit import limiter


@pytest.fixture
def engine():
    """SQLite en memoria por defecto. Con TEST_DATABASE_URL (la CI) corre contra Postgres, como producción."""
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        # misma normalización de driver que usa la app: si falla en producción, falla aquí
        eng = create_engine(Settings(_env_file=None, database_url=url).database_url)
        Base.metadata.drop_all(eng)  # por si una corrida anterior quedó a medias
    else:
        eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    yield eng
    if url:
        eng.dispose()  # suelta las conexiones; las tablas se recrean limpias en la siguiente prueba
        Base.metadata.drop_all(create_engine(Settings(_env_file=None, database_url=url).database_url))


@pytest.fixture
def db(engine):
    """Sesión de servicio con un usuario ya fijado: los datos con dueño exigen saber de quién son."""
    with Session(engine) as s:
        user = User(email="servicio@example.com", password_hash="x")
        s.add(user)
        s.commit()
        s.info["user_id"] = user.id
        yield s


@pytest.fixture
def client(engine):
    maker = sessionmaker(engine)

    def override():
        with maker() as s:
            yield s

    app.dependency_overrides[get_db] = override
    limiter.reset()
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def authed(client):
    """El primer usuario (administrador): se registra sin invitación."""
    creds = {"email": "yo@example.com", "password": "clave-segura-123"}
    assert client.post("/api/auth/register", json=creds).status_code == 201
    assert client.post("/api/auth/login", json=creds).status_code == 200
    return client


@pytest.fixture
def otro(authed):
    """Una segunda persona, con su propia sesión, que entra con una invitación del administrador."""
    code = authed.post("/api/auth/invites").json()["code"]
    b = TestClient(app)
    creds = {"email": "otra@example.com", "password": "otra-clave-segura-1"}
    assert b.post("/api/auth/register", json={**creds, "invite_code": code}).status_code == 201
    assert b.post("/api/auth/login", json=creds).status_code == 200
    return b
