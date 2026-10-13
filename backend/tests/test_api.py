def mk_account(c, **kw):
    body = {"name": "Banco", "type": "bank", "initial_balance": 100_000, **kw}
    r = c.post("/api/accounts", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def mk_category(c, kind="expense", name="Comida", **kw):
    r = c.post("/api/categories", json={"name": name, "kind": kind, **kw})
    assert r.status_code == 201, r.text
    return r.json()


def mk_tx(c, **kw):
    r = c.post("/api/transactions", json=kw)
    assert r.status_code == 201, r.text
    return r.json()


def test_cuenta_devuelve_saldo_calculado(authed):
    a = mk_account(authed)
    cat = mk_category(authed)
    mk_tx(authed, type="expense", amount=30_000, date="2026-03-01", account_id=a["id"], category_id=cat["id"])
    accounts = authed.get("/api/accounts").json()
    assert accounts[0]["balance"] == 70_000


def test_transferencia_valida(authed):
    a, b = mk_account(authed), mk_account(authed, name="Nequi", type="digital_wallet", initial_balance=0)
    cat = mk_category(authed)
    base = {"type": "transfer", "amount": 10, "date": "2026-03-01", "account_id": a["id"]}
    # sin cuenta destino
    assert authed.post("/api/transactions", json=base).status_code == 422
    # con categoría
    r = authed.post("/api/transactions", json={**base, "to_account_id": b["id"], "category_id": cat["id"]})
    assert r.status_code == 422
    # misma cuenta
    assert authed.post("/api/transactions", json={**base, "to_account_id": a["id"]}).status_code == 422
    assert authed.post("/api/transactions", json={**base, "to_account_id": b["id"]}).status_code == 201


def test_gasto_exige_categoria_del_tipo_correcto(authed):
    a = mk_account(authed)
    ingreso = mk_category(authed, kind="income", name="Salario")
    base = {"type": "expense", "amount": 10, "date": "2026-03-01", "account_id": a["id"]}
    assert authed.post("/api/transactions", json=base).status_code == 422
    assert authed.post("/api/transactions", json={**base, "category_id": ingreso["id"]}).status_code == 422


def test_monto_debe_ser_positivo_y_entero(authed):
    a = mk_account(authed)
    cat = mk_category(authed)
    base = {"type": "expense", "date": "2026-03-01", "account_id": a["id"], "category_id": cat["id"]}
    assert authed.post("/api/transactions", json={**base, "amount": 0}).status_code == 422
    assert authed.post("/api/transactions", json={**base, "amount": 10.5}).status_code == 422


def test_filtros_y_paginacion(authed):
    a, b = mk_account(authed), mk_account(authed, name="Efectivo", type="cash")
    comida, ocio = mk_category(authed), mk_category(authed, name="Ocio")
    for i in range(5):
        mk_tx(authed, type="expense", amount=100 + i, date=f"2026-03-0{i + 1}",
              account_id=a["id"], category_id=comida["id"], description=f"almuerzo {i}", tags=["x"])
    mk_tx(authed, type="expense", amount=7, date="2026-04-01", account_id=b["id"], category_id=ocio["id"], description="cine")
    mk_tx(authed, type="transfer", amount=9, date="2026-04-02", account_id=a["id"], to_account_id=b["id"])

    def get(**p):
        return authed.get("/api/transactions", params=p).json()

    assert get()["total"] == 7
    page = get(limit=2, offset=0)
    assert len(page["items"]) == 2 and page["total"] == 7
    assert page["items"][0]["date"] == "2026-04-02"  # más reciente primero
    assert get(type="transfer")["total"] == 1
    assert get(category_id=ocio["id"])["total"] == 1
    assert get(q="ALMUERZO")["total"] == 5
    assert get(**{"from": "2026-03-03", "to": "2026-03-04"})["total"] == 2
    # la cuenta destino de una transferencia también la incluye
    assert get(account_id=b["id"])["total"] == 2


def test_actualizar_y_borrar_movimiento(authed):
    a = mk_account(authed)
    cat = mk_category(authed)
    t = mk_tx(authed, type="expense", amount=10, date="2026-03-01", account_id=a["id"], category_id=cat["id"])
    body = {"type": "expense", "amount": 25, "date": "2026-03-02", "account_id": a["id"], "category_id": cat["id"]}
    r = authed.put(f"/api/transactions/{t['id']}", json=body)
    assert r.status_code == 200 and r.json()["amount"] == 25
    assert authed.delete(f"/api/transactions/{t['id']}").status_code == 204
    assert authed.get("/api/transactions").json()["total"] == 0


def test_no_se_borra_cuenta_con_movimientos(authed):
    a = mk_account(authed)
    cat = mk_category(authed)
    mk_tx(authed, type="expense", amount=10, date="2026-03-01", account_id=a["id"], category_id=cat["id"])
    assert authed.delete(f"/api/accounts/{a['id']}").status_code == 409
    assert authed.delete(f"/api/categories/{cat['id']}").status_code == 409
    vacia = mk_account(authed, name="Vacía")
    assert authed.delete(f"/api/accounts/{vacia['id']}").status_code == 204


def test_subcategoria_un_solo_nivel(authed):
    padre = mk_category(authed, name="Hogar")
    hija = mk_category(authed, name="Arriendo", parent_id=padre["id"])
    r = authed.post("/api/categories", json={"name": "Nieta", "kind": "expense", "parent_id": hija["id"]})
    assert r.status_code == 422
    r = authed.post("/api/categories", json={"name": "X", "kind": "income", "parent_id": padre["id"]})
    assert r.status_code == 422


def test_dashboard(authed):
    a = mk_account(authed, initial_balance=1_000)
    tarjeta = mk_account(authed, name="TC", type="credit_card", initial_balance=-400)
    comida, salario = mk_category(authed), mk_category(authed, kind="income", name="Salario")
    hoy = authed.get("/api/dashboard").json()["month"]  # YYYY-MM actual en Bogotá
    d = f"{hoy}-01"
    mk_tx(authed, type="income", amount=500, date=d, account_id=a["id"], category_id=salario["id"])
    mk_tx(authed, type="expense", amount=100, date=d, account_id=a["id"], category_id=comida["id"])
    mk_tx(authed, type="transfer", amount=300, date=d, account_id=a["id"], to_account_id=tarjeta["id"])
    dash = authed.get("/api/dashboard").json()
    assert dash["income"] == 500 and dash["expense"] == 100
    assert dash["net_worth"] == 1_000 + 500 - 100 - 400
    assert len(dash["recent"]) == 3
    assert {x["balance"] for x in dash["accounts"]} == {1_100, -100}
