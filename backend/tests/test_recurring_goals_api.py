import pytest

from tests.test_api import mk_account, mk_category, mk_tx


def rule_body(account, category, **kw):
    return {"type": "expense", "amount": 1000, "account_id": account["id"], "category_id": category["id"],
            "description": "Netflix", "frequency": "monthly", "start_date": "2026-01-15", **kw}


@pytest.mark.parametrize("method,path", [
    ("get", "/api/recurring"), ("get", "/api/recurring/upcoming"), ("post", "/api/sync"),
    ("get", "/api/savings-goals"), ("post", "/api/savings-goals/1/contribute"),
])
def test_rutas_exigen_sesion(client, method, path):
    assert getattr(client, method)(path).status_code == 401


def test_crear_regla_y_sync_via_api_es_idempotente(authed):
    a, cat = mk_account(authed), mk_category(authed)
    r = authed.post("/api/recurring", json=rule_body(a, cat, start_date="2026-01-15", end_date="2026-03-20"))
    assert r.status_code == 201 and r.json()["next_run_date"] == "2026-01-15"
    assert authed.post("/api/sync").json() == {"created": 3}
    assert authed.post("/api/sync").json() == {"created": 0}
    txs = authed.get("/api/transactions").json()
    assert txs["total"] == 3 and all(t["recurring_rule_id"] == r.json()["id"] for t in txs["items"])


def test_validaciones_de_regla(authed):
    a, b, cat = mk_account(authed), mk_account(authed, name="Otra"), mk_category(authed)
    base = rule_body(a, cat)
    assert authed.post("/api/recurring", json={**base, "amount": 0}).status_code == 422
    assert authed.post("/api/recurring", json={**base, "frequency": "cada-rato"}).status_code == 422
    assert authed.post("/api/recurring", json={**base, "end_date": "2025-01-01"}).status_code == 422
    assert authed.post("/api/recurring", json={**base, "category_id": None}).status_code == 422
    assert authed.post("/api/recurring", json={**base, "to_account_id": b["id"]}).status_code == 422
    transfer = {**base, "type": "transfer", "category_id": None, "to_account_id": b["id"]}
    assert authed.post("/api/recurring", json=transfer).status_code == 201
    assert authed.post("/api/recurring", json={**transfer, "to_account_id": a["id"]}).status_code == 422


def test_borrar_regla_conserva_lo_generado(authed):
    a, cat = mk_account(authed), mk_category(authed)
    r = authed.post("/api/recurring", json=rule_body(a, cat, end_date="2026-02-20")).json()
    authed.post("/api/sync")
    assert authed.delete(f"/api/recurring/{r['id']}").status_code == 204
    txs = authed.get("/api/transactions").json()
    assert txs["total"] == 2 and all(t["recurring_rule_id"] is None for t in txs["items"])


def test_editar_regla_no_reescribe_el_pasado(authed):
    a, cat = mk_account(authed), mk_category(authed)
    r = authed.post("/api/recurring", json=rule_body(a, cat, end_date="2026-02-20")).json()
    authed.post("/api/sync")
    r2 = authed.put(f"/api/recurring/{r['id']}", json=rule_body(a, cat, amount=2000, end_date="2026-02-20"))
    assert r2.status_code == 200 and r2.json()["amount"] == 2000
    assert {t["amount"] for t in authed.get("/api/transactions").json()["items"]} == {1000}
    assert authed.post("/api/sync").json() == {"created": 0}


def test_metas_flujo_completo(authed):
    banco = mk_account(authed, initial_balance=500_000)
    ahorro = mk_account(authed, name="Ahorro", type="savings", initial_balance=0)
    g = authed.post("/api/savings-goals", json={"name": "Viaje", "target_amount": 400_000, "account_id": ahorro["id"]})
    assert g.status_code == 201
    goal = g.json()
    assert (goal["saved"], goal["percent"], goal["monthly_suggested"]) == (0, 0, None)
    r = authed.post(f"/api/savings-goals/{goal['id']}/contribute", json={"amount": 100_000, "from_account_id": banco["id"]})
    assert r.status_code == 201
    (g2,) = authed.get("/api/savings-goals").json()
    assert (g2["saved"], g2["percent"], g2["remaining"]) == (100_000, 25, 300_000)
    saldos = {a["name"]: a["balance"] for a in authed.get("/api/accounts").json()}
    assert saldos == {"Banco": 400_000, "Ahorro": 100_000}


def test_aporte_sin_cuenta_en_la_meta_da_422(authed):
    banco = mk_account(authed)
    goal = authed.post("/api/savings-goals", json={"name": "Moto", "target_amount": 1000}).json()
    r = authed.post(f"/api/savings-goals/{goal['id']}/contribute", json={"amount": 10, "from_account_id": banco["id"]})
    assert r.status_code == 422


def test_validaciones_de_meta_y_borrado(authed):
    assert authed.post("/api/savings-goals", json={"name": "x", "target_amount": 0}).status_code == 422
    assert authed.post("/api/savings-goals", json={"name": "x", "target_amount": 10, "account_id": 999}).status_code == 404
    banco = mk_account(authed)
    ahorro = mk_account(authed, name="Ahorro", type="savings")
    goal = authed.post("/api/savings-goals", json={"name": "Viaje", "target_amount": 1000, "account_id": ahorro["id"]}).json()
    authed.post(f"/api/savings-goals/{goal['id']}/contribute", json={"amount": 10, "from_account_id": banco["id"]})
    assert authed.delete(f"/api/savings-goals/{goal['id']}").status_code == 204
    t = authed.get("/api/transactions").json()["items"][0]  # el aporte sigue como transferencia
    assert t["type"] == "transfer" and t["goal_id"] is None


def test_edicion_de_movimiento_conserva_el_vinculo_con_la_meta(authed):
    banco = mk_account(authed)
    ahorro = mk_account(authed, name="Ahorro", type="savings")
    goal = authed.post("/api/savings-goals", json={"name": "V", "target_amount": 1000, "account_id": ahorro["id"]}).json()
    authed.post(f"/api/savings-goals/{goal['id']}/contribute", json={"amount": 10, "from_account_id": banco["id"], "date": "2026-03-01"})
    t = authed.get("/api/transactions").json()["items"][0]
    body = {"type": "transfer", "amount": 20, "date": "2026-03-01", "account_id": banco["id"], "to_account_id": ahorro["id"]}
    assert authed.put(f"/api/transactions/{t['id']}", json=body).json()["goal_id"] == goal["id"]
    assert authed.get("/api/savings-goals").json()[0]["saved"] == 20


def test_mk_tx_sigue_funcionando(authed):
    a, cat = mk_account(authed), mk_category(authed)
    assert mk_tx(authed, type="expense", amount=5, date="2026-03-01", account_id=a["id"], category_id=cat["id"])["recurring_rule_id"] is None
