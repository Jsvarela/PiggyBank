from tests.test_api import mk_account, mk_category, mk_tx


def put(c, **kw):
    return c.put("/api/budgets", json=kw)


def test_rutas_de_presupuestos_exigen_sesion(client):
    assert client.get("/api/budgets/status").status_code == 401
    assert client.get("/api/reports/monthly").status_code == 401
    assert client.put("/api/budgets", json={}).status_code == 401


def test_guardar_es_idempotente_y_actualiza(authed):
    cat = mk_category(authed)
    a = put(authed, category_id=cat["id"], limit_amount=100_000, month="2026-10")
    b = put(authed, category_id=cat["id"], limit_amount=120_000, month="2026-10")
    assert a.status_code == b.status_code == 200
    assert a.json()["id"] == b.json()["id"]
    assert len(authed.get("/api/budgets").json()) == 1
    # el "por defecto" (month nulo) es otra fila
    put(authed, category_id=cat["id"], limit_amount=90_000)
    put(authed, category_id=cat["id"], limit_amount=95_000)
    assert len(authed.get("/api/budgets").json()) == 2


def test_validaciones(authed):
    gasto, ingreso = mk_category(authed), mk_category(authed, kind="income", name="Salario")
    base = {"category_id": gasto["id"], "limit_amount": 1000}
    assert put(authed, **{**base, "limit_amount": 0}).status_code == 422
    assert put(authed, **{**base, "limit_amount": 10.5}).status_code == 422
    assert put(authed, **{**base, "alert_threshold": 0}).status_code == 422
    assert put(authed, **{**base, "alert_threshold": 101}).status_code == 422
    assert put(authed, **{**base, "month": "2026-13"}).status_code == 422
    assert put(authed, **{**base, "category_id": ingreso["id"]}).status_code == 422
    assert put(authed, **{**base, "category_id": 999}).status_code == 404


def test_estado_y_resumen_por_api(authed):
    cuenta = mk_account(authed)
    cat = mk_category(authed)
    put(authed, category_id=cat["id"], limit_amount=1000)  # por defecto
    mk_tx(authed, type="expense", amount=850, date="2026-10-05", account_id=cuenta["id"], category_id=cat["id"])
    (item,) = authed.get("/api/budgets/status", params={"month": "2026-10"}).json()
    assert (item["spent"], item["percent"], item["alert"]) == (850, 85, "warning")
    assert item["category_name"] == "Comida"
    report = authed.get("/api/reports/monthly", params={"month": "2026-10"}).json()
    assert report["expense"] == 850 and report["categories"][0]["name"] == "Comida"
    assert authed.get("/api/budgets/status", params={"month": "octubre"}).status_code == 422


def test_no_se_borra_categoria_con_presupuesto(authed):
    cat = mk_category(authed)
    put(authed, category_id=cat["id"], limit_amount=1000)
    assert authed.delete(f"/api/categories/{cat['id']}").status_code == 409


def test_borrar_presupuesto(authed):
    cat = mk_category(authed)
    b = put(authed, category_id=cat["id"], limit_amount=1000).json()
    assert authed.delete(f"/api/budgets/{b['id']}").status_code == 204
    assert authed.delete(f"/api/budgets/{b['id']}").status_code == 404


def test_tendencia_de_meses_cruza_el_ano_y_rellena_con_ceros(authed):
    from tests.test_api import mk_account, mk_category, mk_tx

    a, g, i = mk_account(authed), mk_category(authed), mk_category(authed, kind="income", name="Sueldo")
    mk_tx(authed, type="expense", amount=30_000, date="2026-01-10", account_id=a["id"], category_id=g["id"])
    mk_tx(authed, type="income", amount=500_000, date="2025-12-01", account_id=a["id"], category_id=i["id"])
    r = authed.get("/api/reports/trend?month=2026-02&months=3").json()
    assert r == [
        {"month": "2025-12", "income": 500_000, "expense": 0},
        {"month": "2026-01", "income": 0, "expense": 30_000},
        {"month": "2026-02", "income": 0, "expense": 0},
    ]
    assert authed.get("/api/reports/trend?months=0").status_code == 422
