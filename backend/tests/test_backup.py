import csv
import io

from tests.test_api import mk_account, mk_category, mk_tx


def seed(c):
    banco = mk_account(c, initial_balance=1_000_000)
    ahorro = mk_account(c, name="Ahorro", type="savings", initial_balance=0)
    comida = mk_category(c)
    hogar = mk_category(c, name="Hogar")
    mk_category(c, name="Arriendo", parent_id=hogar["id"])
    mk_tx(c, type="expense", amount=18_000, date="2026-10-01", account_id=banco["id"],
          category_id=comida["id"], description="Almuerzo", tags=["trabajo"])
    mk_tx(c, type="transfer", amount=50_000, date="2026-10-02", account_id=banco["id"], to_account_id=ahorro["id"])
    c.put("/api/budgets", json={"category_id": comida["id"], "limit_amount": 200_000})
    c.post("/api/recurring", json={"type": "expense", "amount": 900_000, "account_id": banco["id"],
                                    "category_id": hogar["id"], "description": "Arriendo",
                                    "frequency": "monthly", "start_date": "2099-01-05"})
    goal = c.post("/api/savings-goals", json={"name": "Viaje", "target_amount": 500_000, "account_id": ahorro["id"]}).json()
    c.post(f"/api/savings-goals/{goal['id']}/contribute", json={"amount": 100_000, "from_account_id": banco["id"], "date": "2026-10-03"})


def snapshot(c):
    return {
        "balances": sorted((a["name"], a["balance"]) for a in c.get("/api/accounts").json()),
        "tx": sorted((t["date"], t["amount"], t["type"], t["goal_id"] is not None) for t in c.get("/api/transactions?limit=200").json()["items"]),
        "goals": [(g["name"], g["saved"]) for g in c.get("/api/savings-goals").json()],
        "budgets": [(b["category_name"], b["limit"], b["spent"]) for b in c.get("/api/budgets/status?month=2026-10").json()],
        "rules": [(r["description"], r["amount"], r["next_run_date"]) for r in c.get("/api/recurring").json()],
        "cats": sorted((c_["name"], c_["parent_id"] is not None) for c_ in c.get("/api/categories").json()),
    }


def test_exportar_exige_sesion(client):
    for path in ("/api/export/transactions.csv", "/api/export/backup.json"):
        assert client.get(path).status_code == 401
    assert client.post("/api/import/backup", json={}).status_code == 401


def test_csv_de_movimientos(authed):
    seed(authed)
    r = authed.get("/api/export/transactions.csv")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))))
    assert len(rows) == 3
    almuerzo = next(x for x in rows if x["descripcion"] == "Almuerzo")
    assert (almuerzo["fecha"], almuerzo["tipo"], almuerzo["monto"], almuerzo["cuenta"], almuerzo["categoria"], almuerzo["etiquetas"]) == (
        "2026-10-01", "expense", "18000", "Banco", "Comida", "trabajo")
    transfer = next(x for x in rows if x["tipo"] == "transfer" and x["fecha"] == "2026-10-02")
    assert (transfer["cuenta"], transfer["cuenta_destino"], transfer["categoria"]) == ("Banco", "Ahorro", "")


def test_csv_neutraliza_formulas(authed):
    a, cat = mk_account(authed), mk_category(authed)
    mk_tx(authed, type="expense", amount=1, date="2026-10-01", account_id=a["id"], category_id=cat["id"], description="=HYPERLINK(\"http://x\")")
    text = authed.get("/api/export/transactions.csv").content.decode("utf-8-sig")
    assert "'=HYPERLINK" in text and ',=HYPERLINK' not in text


def test_respaldo_ida_y_vuelta_conserva_todo(authed):
    seed(authed)
    antes = snapshot(authed)
    backup = authed.get("/api/export/backup.json").json()
    assert backup["version"] == 1 and "password_hash" not in str(backup)
    r = authed.post("/api/import/backup", json=backup)
    assert r.status_code == 200, r.text
    assert snapshot(authed) == antes
    # restaurar dos veces da lo mismo (no acumula)
    assert authed.post("/api/import/backup", json=backup).status_code == 200
    assert snapshot(authed) == antes


def test_restaurar_reemplaza_lo_que_hubiera(authed):
    seed(authed)
    backup = authed.get("/api/export/backup.json").json()
    antes = snapshot(authed)
    extra = mk_account(authed, name="Sobrante")
    cat = mk_category(authed, name="Sobrante")
    mk_tx(authed, type="expense", amount=7, date="2026-10-09", account_id=extra["id"], category_id=cat["id"])
    authed.post("/api/import/backup", json=backup)
    assert snapshot(authed) == antes


def test_respaldo_invalido_no_destruye_datos(authed):
    seed(authed)
    antes = snapshot(authed)
    backup = authed.get("/api/export/backup.json").json()
    backup["transactions"][0]["account_id"] = 99999  # referencia a una cuenta que no existe
    assert authed.post("/api/import/backup", json=backup).status_code == 422
    assert snapshot(authed) == antes
    assert authed.post("/api/import/backup", json={"version": 1, "accounts": "nada"}).status_code == 422
    assert snapshot(authed) == antes


def test_respaldo_de_otra_version_se_rechaza(authed):
    backup = authed.get("/api/export/backup.json").json()
    assert authed.post("/api/import/backup", json={**backup, "version": 2}).status_code == 422
