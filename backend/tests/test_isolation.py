"""Dos personas usando la app a la vez: ninguna puede ver ni tocar lo de la otra, por ninguna ruta."""

import pytest

from tests.test_api import mk_account, mk_category, mk_tx


def datos_de_a(a):
    banco = mk_account(a, name="Banco A", initial_balance=1_000_000)
    ahorro = mk_account(a, name="Ahorro A", type="savings")
    gasto = mk_category(a, name="Gasto A")
    mk_category(a, kind="income", name="Ingreso A")
    tx = mk_tx(a, type="expense", amount=30_000, date="2026-03-05", account_id=banco["id"], category_id=gasto["id"], description="Secreto de A")
    budget = a.put("/api/budgets", json={"category_id": gasto["id"], "limit_amount": 100_000}).json()
    rule = a.post("/api/recurring", json={"type": "expense", "amount": 900_000, "account_id": banco["id"], "category_id": gasto["id"],
                                          "description": "Arriendo A", "frequency": "monthly", "start_date": "2026-01-15"}).json()
    goal = a.post("/api/savings-goals", json={"name": "Meta A", "target_amount": 500_000, "account_id": ahorro["id"]}).json()
    a.post(f"/api/savings-goals/{goal['id']}/contribute", json={"amount": 100_000, "from_account_id": banco["id"], "date": "2026-03-06"})
    return {"banco": banco, "ahorro": ahorro, "gasto": gasto, "tx": tx, "budget": budget, "rule": rule, "goal": goal}


def test_los_listados_de_b_no_incluyen_nada_de_a(authed, otro):
    datos_de_a(authed)
    assert otro.get("/api/accounts").json() == []
    assert otro.get("/api/transactions").json()["total"] == 0
    assert otro.get("/api/budgets").json() == []
    assert otro.get("/api/recurring").json() == []
    assert otro.get("/api/savings-goals").json() == []
    nombres = {c["name"] for c in otro.get("/api/categories").json()}
    assert "Gasto A" not in nombres and "Ingreso A" not in nombres
    assert {"Comida", "Salario"} <= nombres  # B tiene sus propias categorías por defecto


def test_b_no_puede_ver_editar_ni_borrar_lo_de_a(authed, otro):
    d = datos_de_a(authed)
    cuenta = {"name": "x", "type": "bank", "initial_balance": 0}
    assert otro.put(f"/api/accounts/{d['banco']['id']}", json=cuenta).status_code == 404
    assert otro.delete(f"/api/accounts/{d['banco']['id']}").status_code == 404
    assert otro.put(f"/api/categories/{d['gasto']['id']}", json={"name": "x", "kind": "expense"}).status_code == 404
    assert otro.delete(f"/api/categories/{d['gasto']['id']}").status_code == 404
    tx = {"type": "expense", "amount": 1, "date": "2026-03-05", "account_id": d["banco"]["id"], "category_id": d["gasto"]["id"]}
    assert otro.put(f"/api/transactions/{d['tx']['id']}", json=tx).status_code == 404
    assert otro.delete(f"/api/transactions/{d['tx']['id']}").status_code == 404
    assert otro.delete(f"/api/budgets/{d['budget']['id']}").status_code == 404
    regla = {"type": "expense", "amount": 1, "account_id": d["banco"]["id"], "category_id": d["gasto"]["id"],
             "frequency": "monthly", "start_date": "2026-01-15"}
    assert otro.put(f"/api/recurring/{d['rule']['id']}", json=regla).status_code == 404
    assert otro.delete(f"/api/recurring/{d['rule']['id']}").status_code == 404
    assert otro.put(f"/api/savings-goals/{d['goal']['id']}", json={"name": "x", "target_amount": 1}).status_code == 404
    assert otro.delete(f"/api/savings-goals/{d['goal']['id']}").status_code == 404
    # y nada de lo de A cambió
    assert authed.get("/api/transactions").json()["total"] >= 2
    assert [a["name"] for a in authed.get("/api/accounts").json()] == ["Banco A", "Ahorro A"]


@pytest.mark.parametrize("ruta", ["accounts", "categories", "transactions", "budgets", "recurring", "savings-goals"])
def test_ids_ajenos_dan_404_igual_que_los_inexistentes(authed, otro, ruta):
    d = datos_de_a(authed)
    # no se debe poder distinguir "existe pero es de otra persona" de "no existe"
    ajeno = {"accounts": d["banco"]["id"], "categories": d["gasto"]["id"], "transactions": d["tx"]["id"],
             "budgets": d["budget"]["id"], "recurring": d["rule"]["id"], "savings-goals": d["goal"]["id"]}[ruta]
    inexistente = "00000000-0000-4000-8000-000000000000" if ruta == "transactions" else 987654
    assert otro.delete(f"/api/{ruta}/{ajeno}").status_code == otro.delete(f"/api/{ruta}/{inexistente}").status_code == 404


def test_b_no_puede_usar_cuentas_ni_categorias_de_a_en_sus_datos(authed, otro):
    d = datos_de_a(authed)
    propia = mk_account(otro, name="Banco B")
    cat_b = mk_category(otro, name="Cat B")
    base = {"type": "expense", "amount": 10, "date": "2026-03-05"}
    assert otro.post("/api/transactions", json={**base, "account_id": d["banco"]["id"], "category_id": cat_b["id"]}).status_code == 404
    assert otro.post("/api/transactions", json={**base, "account_id": propia["id"], "category_id": d["gasto"]["id"]}).status_code == 404
    transfer = {"type": "transfer", "amount": 10, "date": "2026-03-05", "account_id": propia["id"], "to_account_id": d["banco"]["id"]}
    assert otro.post("/api/transactions", json=transfer).status_code == 404
    assert otro.put("/api/budgets", json={"category_id": d["gasto"]["id"], "limit_amount": 5}).status_code == 404
    regla = {"type": "expense", "amount": 5, "account_id": propia["id"], "category_id": d["gasto"]["id"], "frequency": "monthly", "start_date": "2099-01-01"}
    assert otro.post("/api/recurring", json=regla).status_code == 404
    assert otro.post("/api/savings-goals", json={"name": "m", "target_amount": 5, "account_id": d["ahorro"]["id"]}).status_code == 404
    meta_b = otro.post("/api/savings-goals", json={"name": "m", "target_amount": 5, "account_id": propia["id"]}).json()
    aporte = {"amount": 1, "from_account_id": d["banco"]["id"]}
    assert otro.post(f"/api/savings-goals/{meta_b['id']}/contribute", json=aporte).status_code == 404
    assert otro.post(f"/api/savings-goals/{d['goal']['id']}/contribute", json={"amount": 1, "from_account_id": propia["id"]}).status_code == 404


def test_saldos_tablero_y_resumenes_son_de_cada_quien(authed, otro):
    datos_de_a(authed)
    b = mk_account(otro, name="Mía", initial_balance=500)
    cat = mk_category(otro, name="Mi gasto")
    mk_tx(otro, type="expense", amount=100, date="2026-03-02", account_id=b["id"], category_id=cat["id"])
    dash_b = otro.get("/api/dashboard").json()
    assert dash_b["net_worth"] == 400 and [a["name"] for a in dash_b["accounts"]] == ["Mía"]
    assert [t["description"] for t in dash_b["recent"]] == [None]  # nunca "Secreto de A"
    dash_a = authed.get("/api/dashboard").json()
    assert dash_a["net_worth"] == 1_000_000 + 100_000 - 30_000  # Banco 1.000.000 + Ahorro 100.000 (saldo inicial por defecto) - el gasto; el aporte es interno
    assert otro.get("/api/budgets/status?month=2026-03").json() == []
    rep = otro.get("/api/reports/monthly?month=2026-03").json()
    assert rep["expense"] == 100 and [c["name"] for c in rep["categories"]] == ["Mi gasto"]
    assert otro.get("/api/savings-goals").json() == []


def test_exportar_y_respaldo_son_solo_del_usuario(authed, otro):
    datos_de_a(authed)
    csv = otro.get("/api/export/transactions.csv").content.decode("utf-8-sig")
    assert "Secreto de A" not in csv and "Banco A" not in csv
    respaldo_b = otro.get("/api/export/backup.json")
    assert "Banco A" not in respaldo_b.text and "Secreto de A" not in respaldo_b.text
    # restaurar el respaldo de B (reemplaza TODO lo de B) no toca nada de A
    assert otro.post("/api/import/backup", json=respaldo_b.json()).status_code == 200
    assert [a["name"] for a in authed.get("/api/accounts").json()] == ["Banco A", "Ahorro A"]
    assert authed.get("/api/transactions").json()["total"] >= 2


def test_borrar_la_cuenta_de_b_no_toca_a_a(authed, otro):
    datos_de_a(authed)
    mk_account(otro, name="Mía")
    assert otro.request("DELETE", "/api/auth/account", json={"password": "otra-clave-segura-1"}).status_code == 204
    assert [a["name"] for a in authed.get("/api/accounts").json()] == ["Banco A", "Ahorro A"]
    assert authed.get("/api/auth/me").status_code == 200
    assert otro.get("/api/auth/me").status_code == 401


def test_un_uuid_de_a_no_se_puede_reclamar_ni_pisar_desde_b(authed, otro):
    d = datos_de_a(authed)
    propia, cat = mk_account(otro, name="Mía"), mk_category(otro, name="Mi cat")
    intento = {"id": d["tx"]["id"], "type": "expense", "amount": 1, "date": "2026-03-05", "account_id": propia["id"], "category_id": cat["id"]}
    r = otro.post("/api/transactions", json=intento)
    assert r.status_code == 409 and "Secreto" not in r.text
    original = authed.get("/api/transactions").json()["items"]
    assert any(t["id"] == d["tx"]["id"] and t["amount"] == 30_000 for t in original)


def test_el_importador_solo_compara_duplicados_con_lo_propio(authed, otro):
    d = datos_de_a(authed)
    propia = mk_account(otro, name="Mía")
    texto = "Fecha;Desc;Valor\n05/03/2026;Secreto de A;-30.000\n"
    m = {"date_col": 0, "description_col": 1, "amount_col": 2, "date_format": "dmy", "decimal": ","}
    r = otro.post("/api/import/csv/preview", json={"text": texto, "account_id": propia["id"], "mapping": m}).json()
    assert r["rows"][0]["duplicate"] is False  # existe en A, pero B no lo ve
    assert otro.post("/api/import/csv/preview", json={"text": texto, "account_id": d["banco"]["id"], "mapping": m}).status_code == 404


def test_sincronizar_recurrentes_solo_toca_las_propias(authed, otro):
    datos_de_a(authed)  # A tiene una regla mensual atrasada desde enero
    assert otro.post("/api/sync").json() == {"created": 0}
    antes = authed.get("/api/transactions").json()["total"]
    assert authed.post("/api/sync").json()["created"] > 0
    assert authed.get("/api/transactions").json()["total"] > antes
    assert otro.get("/api/transactions").json()["total"] == 0
