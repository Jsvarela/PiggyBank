from app.schemas import MAX_MONEY
from tests.test_api import mk_account, mk_category

MAS = MAX_MONEY + 1


def test_el_tope_es_exacto_en_javascript():
    # por encima de 2^53 el navegador redondea y mostraría un monto falso
    assert MAX_MONEY < 2**53


def test_movimiento_con_monto_enorme_da_422_no_500(authed):
    a, cat = mk_account(authed), mk_category(authed)
    base = {"type": "expense", "date": "2026-03-01", "account_id": a["id"], "category_id": cat["id"]}
    for monto in (MAS, 10**19):  # 10**19 antes provocaba un error 500 en la base de datos
        assert authed.post("/api/transactions", json={**base, "amount": monto}).status_code == 422
    r = authed.post("/api/transactions", json={**base, "amount": MAX_MONEY})
    assert r.status_code == 201 and r.json()["amount"] == MAX_MONEY  # el tope mismo sí entra, exacto


def test_saldo_inicial_acepta_deuda_pero_con_tope(authed):
    for saldo in (MAX_MONEY, -MAX_MONEY):
        assert authed.post("/api/accounts", json={"name": "x", "type": "bank", "initial_balance": saldo}).status_code == 201
    for saldo in (MAS, -MAS, 10**19):
        assert authed.post("/api/accounts", json={"name": "x", "type": "bank", "initial_balance": saldo}).status_code == 422


def test_metas_presupuestos_y_aportes_tienen_tope(authed):
    cat = mk_category(authed)
    a, ahorro = mk_account(authed), mk_account(authed, name="Ahorro", type="savings")
    assert authed.post("/api/savings-goals", json={"name": "m", "target_amount": MAS}).status_code == 422
    assert authed.put("/api/budgets", json={"category_id": cat["id"], "limit_amount": MAS}).status_code == 422
    goal = authed.post("/api/savings-goals", json={"name": "m", "target_amount": MAX_MONEY, "account_id": ahorro["id"]})
    assert goal.status_code == 201
    r = authed.post(f"/api/savings-goals/{goal.json()['id']}/contribute", json={"amount": MAS, "from_account_id": a["id"]})
    assert r.status_code == 422


def test_reglas_recurrentes_tienen_tope(authed):
    a, cat = mk_account(authed), mk_category(authed)
    body = {"type": "expense", "account_id": a["id"], "category_id": cat["id"], "frequency": "monthly", "start_date": "2099-01-01"}
    assert authed.post("/api/recurring", json={**body, "amount": MAS}).status_code == 422
    assert authed.post("/api/recurring", json={**body, "amount": MAX_MONEY}).status_code == 201


def test_importar_extracto_marca_el_monto_enorme_como_error_de_fila(authed):
    a = mk_account(authed)
    text = "Fecha;Desc;Valor\n05/10/2026;GRANDE;-1.000.000.000.000.000\n06/10/2026;NORMAL;-1.000\n"
    m = {"date_col": 0, "description_col": 1, "amount_col": 2, "date_format": "dmy", "decimal": ","}
    rows = authed.post("/api/import/csv/preview", json={"text": text, "account_id": a["id"], "mapping": m}).json()["rows"]
    assert rows[0]["error"] and "grande" in rows[0]["error"].lower()
    assert rows[1]["error"] is None and rows[1]["amount"] == 1000
