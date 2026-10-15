BODY = {"person": "Camila", "amount": 200_000, "expected_amount": 220_000, "due_date": "2026-12-01"}


def crear(c, **kw):
    r = c.post("/api/loans", json={**BODY, **kw})
    assert r.status_code == 201, r.text
    return r.json()


def test_crear_listar_y_borrar(authed):
    loan = crear(authed)
    assert (loan["person"], loan["expected_amount"], loan["received"], loan["paid"], loan["direction"]) == ("Camila", 220_000, 0, False, "lent")
    assert [x["id"] for x in authed.get("/api/loans").json()] == [loan["id"]]
    assert authed.delete(f"/api/loans/{loan['id']}").status_code == 204
    assert authed.get("/api/loans").json() == []


def test_abonos_parciales_hasta_quedar_pagado(authed):
    loan = crear(authed)
    r = authed.post(f"/api/loans/{loan['id']}/payments", json={"amount": 100_000}).json()
    assert (r["received"], r["paid"]) == (100_000, False)
    r = authed.post(f"/api/loans/{loan['id']}/payments", json={"amount": 120_000}).json()
    assert (r["received"], r["paid"]) == (220_000, True)


def test_no_se_puede_abonar_mas_de_lo_que_falta(authed):
    loan = crear(authed, received=200_000)
    assert authed.post(f"/api/loans/{loan['id']}/payments", json={"amount": 20_001}).status_code == 422
    assert authed.post(f"/api/loans/{loan['id']}/payments", json={"amount": 0}).status_code == 422


def test_editar_el_recibido_recalcula_pagado(authed):
    loan = crear(authed)
    assert authed.put(f"/api/loans/{loan['id']}", json={**BODY, "received": 220_000}).json()["paid"] is True
    assert authed.put(f"/api/loans/{loan['id']}", json={**BODY, "received": 0}).json()["paid"] is False


def test_deuda_propia(authed):
    assert crear(authed, direction="borrowed")["direction"] == "borrowed"
    assert authed.post("/api/loans", json={**BODY, "direction": "otra"}).status_code == 422


def test_orden_pendientes_primero_por_fecha(authed):
    for n, d, rec in [("pagado", "2026-01-01", 220_000), ("sin fecha", None, 0), ("tarde", "2026-12-01", 0), ("pronto", "2026-11-01", 0)]:
        crear(authed, person=n, due_date=d, received=rec)
    assert [x["person"] for x in authed.get("/api/loans").json()] == ["pronto", "tarde", "sin fecha", "pagado"]


def test_validacion(authed):
    for malo in ({"amount": 0}, {"expected_amount": -1}, {"person": ""}, {"amount": 1.5}, {"received": -1}):
        assert authed.post("/api/loans", json={**BODY, **malo}).status_code == 422


def test_no_se_mezcla_entre_personas(authed, otro):
    loan = crear(authed)
    assert otro.get("/api/loans").json() == []
    assert otro.put(f"/api/loans/{loan['id']}", json=BODY).status_code == 404
    assert otro.post(f"/api/loans/{loan['id']}/payments", json={"amount": 1}).status_code == 404
    assert otro.delete(f"/api/loans/{loan['id']}").status_code == 404


def test_respaldo_conserva_abonos_y_acepta_respaldos_viejos(authed):
    crear(authed, received=50_000, direction="borrowed")
    b = authed.get("/api/export/backup.json").json()
    assert (b["loans"][0]["received"], b["loans"][0]["direction"]) == (50_000, "borrowed")
    assert authed.post("/api/import/backup", json=b).status_code == 200
    (loan,) = authed.get("/api/loans").json()
    assert (loan["received"], loan["direction"]) == (50_000, "borrowed")
    # un respaldo de antes de los abonos: "paid" sin "received"
    viejo = {**b, "loans": [{"person": "X", "amount": 10, "expected_amount": 10, "paid": True}]}
    assert authed.post("/api/import/backup", json=viejo).status_code == 200
    (loan,) = authed.get("/api/loans").json()
    assert (loan["received"], loan["paid"]) == (10, True)
