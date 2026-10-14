from tests.test_api import mk_account, mk_category, mk_tx

# Postgres devuelve SUM(bigint) como Decimal y la API lo mandaba como texto ("70000"). Con SQLite nunca
# se notaba; este test existe para que la CI contra Postgres lo atrape si vuelve a pasar.


def es_entero(valor):
    return type(valor) is int  # ni str, ni float, ni Decimal, ni bool


def test_toda_cifra_que_entrega_la_api_es_un_entero(authed):
    banco = mk_account(authed, initial_balance=1_000_000)
    ahorro = mk_account(authed, name="Ahorro", type="savings", initial_balance=0)
    gasto, ingreso = mk_category(authed), mk_category(authed, kind="income", name="Salario")
    mk_tx(authed, type="expense", amount=30_000, date="2026-03-05", account_id=banco["id"], category_id=gasto["id"])
    mk_tx(authed, type="income", amount=500_000, date="2026-03-06", account_id=banco["id"], category_id=ingreso["id"])
    authed.put("/api/budgets", json={"category_id": gasto["id"], "limit_amount": 100_000})
    goal = authed.post("/api/savings-goals", json={"name": "Meta", "target_amount": 400_000, "deadline": "2099-01-01", "account_id": ahorro["id"]}).json()
    authed.post(f"/api/savings-goals/{goal['id']}/contribute", json={"amount": 100_000, "from_account_id": banco["id"], "date": "2026-03-07"})

    cuentas = authed.get("/api/accounts").json()
    assert all(es_entero(c["balance"]) for c in cuentas)

    dash = authed.get("/api/dashboard").json()
    for k in ("net_worth", "income", "expense"):
        assert es_entero(dash[k]), k
    assert all(es_entero(a["balance"]) for a in dash["accounts"])

    (b,) = authed.get("/api/budgets/status?month=2026-03").json()
    for k in ("limit", "spent", "percent", "remaining", "days_left"):
        assert es_entero(b[k]), k

    rep = authed.get("/api/reports/monthly?month=2026-03").json()
    for k in ("income", "expense", "previous_income", "previous_expense"):
        assert es_entero(rep[k]), k
    assert all(es_entero(c[k]) for c in rep["categories"] for k in ("amount", "previous", "diff"))

    (g,) = authed.get("/api/savings-goals").json()
    for k in ("saved", "remaining", "percent", "monthly_suggested"):
        assert es_entero(g[k]), k
    assert (g["saved"], g["percent"]) == (100_000, 25)
