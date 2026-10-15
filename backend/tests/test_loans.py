BODY = {"person": "Camila", "amount": 200_000, "expected_amount": 220_000, "due_date": "2026-12-01"}


def test_crear_listar_marcar_pagado_y_borrar(authed):
    r = authed.post("/api/loans", json=BODY)
    assert r.status_code == 201
    loan = r.json()
    assert (loan["person"], loan["expected_amount"], loan["paid"]) == ("Camila", 220_000, False)
    assert authed.put(f"/api/loans/{loan['id']}", json={**BODY, "paid": True}).json()["paid"] is True
    assert [x["id"] for x in authed.get("/api/loans").json()] == [loan["id"]]
    assert authed.delete(f"/api/loans/{loan['id']}").status_code == 204
    assert authed.get("/api/loans").json() == []


def test_orden_pendientes_primero_por_fecha(authed):
    ids = {n: authed.post("/api/loans", json={**BODY, "person": n, "due_date": d, "paid": p}).json()["id"]
           for n, d, p in [("pagado", "2026-01-01", True), ("sin fecha", None, False), ("tarde", "2026-12-01", False), ("pronto", "2026-11-01", False)]}
    orden = [x["person"] for x in authed.get("/api/loans").json()]
    assert orden == ["pronto", "tarde", "sin fecha", "pagado"]
    assert ids  # los cuatro existen


def test_validacion(authed):
    for malo in ({"amount": 0}, {"expected_amount": -1}, {"person": ""}, {"amount": 1.5}):
        assert authed.post("/api/loans", json={**BODY, **malo}).status_code == 422


def test_no_se_mezcla_entre_personas(authed, otro):
    loan = authed.post("/api/loans", json=BODY).json()
    assert otro.get("/api/loans").json() == []
    assert otro.put(f"/api/loans/{loan['id']}", json=BODY).status_code == 404
    assert otro.delete(f"/api/loans/{loan['id']}").status_code == 404
    assert len(authed.get("/api/loans").json()) == 1


def test_respaldo_incluye_prestamos(authed):
    authed.post("/api/loans", json=BODY)
    b = authed.get("/api/export/backup.json").json()
    assert b["loans"][0]["person"] == "Camila"
    authed.delete(f"/api/loans/{authed.get('/api/loans').json()[0]['id']}")
    assert authed.post("/api/import/backup", json=b).status_code == 200
    assert len(authed.get("/api/loans").json()) == 1
