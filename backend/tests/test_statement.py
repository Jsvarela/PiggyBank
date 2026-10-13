from tests.test_api import mk_account, mk_category, mk_tx

BANCO_CO = "Fecha;Descripción;Valor\n05/10/2026;COMPRA EXITO;-45.300,00\n06/10/2026;NÓMINA;2.000.000,00\n"
BASE = {"date_col": 0, "description_col": 1, "amount_col": 2, "date_format": "dmy", "decimal": ","}


def preview(c, text, account, mapping=None):
    body = {"text": text, "account_id": account["id"]}
    if mapping is not None:
        body["mapping"] = mapping
    return c.post("/api/import/csv/preview", json=body)


def test_exige_sesion(client):
    assert client.post("/api/import/csv/preview", json={}).status_code == 401
    assert client.post("/api/transactions/bulk", json={"items": []}).status_code == 401


def test_sin_mapeo_devuelve_encabezados_y_sugerencia(authed):
    a = mk_account(authed)
    r = preview(authed, BANCO_CO, a).json()
    assert r["delimiter"] == ";" and r["headers"] == ["Fecha", "Descripción", "Valor"]
    assert len(r["sample"]) == 2 and r["rows"] == []
    assert r["suggested"]["date_col"] == 0 and r["suggested"]["amount_col"] == 2


def test_formato_colombiano_punto_de_miles_y_coma_decimal(authed):
    a = mk_account(authed)
    rows = preview(authed, BANCO_CO, a, BASE).json()["rows"]
    assert [(x["date"], x["amount"], x["type"], x["description"]) for x in rows] == [
        ("2026-10-05", 45300, "expense", "COMPRA EXITO"),
        ("2026-10-06", 2_000_000, "income", "NÓMINA"),
    ]


def test_columnas_de_debito_y_credito_con_comillas_y_bom(authed):
    a = mk_account(authed)
    text = '﻿Date,Details,Debit,Credit\n"2026-10-05","Cafe, centro",12000,\n2026-10-06,Salary,,500000\n'
    m = {"date_col": 0, "description_col": 1, "debit_col": 2, "credit_col": 3, "date_format": "ymd", "decimal": "."}
    rows = preview(authed, text, a, m).json()["rows"]
    assert [(x["amount"], x["type"], x["description"]) for x in rows] == [
        (12000, "expense", "Cafe, centro"), (500000, "income", "Salary")]


def test_tarjeta_de_credito_con_signo_invertido(authed):
    a = mk_account(authed, type="credit_card")
    text = "Fecha;Detalle;Monto\n05/10/2026;COMPRA;30.000\n06/10/2026;PAGO;-30.000\n"
    rows = preview(authed, text, a, {**BASE, "invert_sign": True}).json()["rows"]
    assert [(x["type"], x["amount"]) for x in rows] == [("expense", 30000), ("income", 30000)]


def test_filas_malas_traen_error_y_no_frenan_al_resto(authed):
    a = mk_account(authed)
    text = "Fecha;Desc;Valor\n31/02/2026;X;-100\n05/10/2026;Y;\n05/10/2026;Z\n06/10/2026;OK;-250\n"
    rows = preview(authed, text, a, BASE).json()["rows"]
    assert [bool(x["error"]) for x in rows] == [True, True, True, False]
    assert rows[3]["amount"] == 250


def test_dinero_se_redondea_sin_float(authed):
    a = mk_account(authed)
    text = "Fecha;Desc;Valor\n05/10/2026;A;-1.234,50\n05/10/2026;B;-0,49\n05/10/2026;C;(2.500,00)\n"
    rows = preview(authed, text, a, BASE).json()["rows"]
    assert [(x["amount"], x["type"]) for x in rows[:1]] == [(1235, "expense")]  # 0,5 sube
    assert rows[1]["error"]  # 0,49 se redondea a 0: monto vacío
    assert (rows[2]["amount"], rows[2]["type"]) == (2500, "expense")  # paréntesis = negativo


def test_marca_duplicados_contra_lo_existente_sin_distinguir_mayusculas(authed):
    a, cat = mk_account(authed), mk_category(authed)
    mk_tx(authed, type="expense", amount=45300, date="2026-10-05", account_id=a["id"], category_id=cat["id"], description="compra exito")
    rows = preview(authed, BANCO_CO, a, BASE).json()["rows"]
    assert [x["duplicate"] for x in rows] == [True, False]


def test_filas_identicas_en_el_archivo_no_son_duplicadas_entre_si(authed):
    a, cat = mk_account(authed), mk_category(authed)
    text = "Fecha;Desc;Valor\n05/10/2026;CAFE;-3.000\n05/10/2026;CAFE;-3.000\n"
    assert [x["duplicate"] for x in preview(authed, text, a, BASE).json()["rows"]] == [False, False]
    mk_tx(authed, type="expense", amount=3000, date="2026-10-05", account_id=a["id"], category_id=cat["id"], description="CAFE")
    # ya existe uno: solo consume una de las dos filas
    assert [x["duplicate"] for x in preview(authed, text, a, BASE).json()["rows"]] == [True, False]


def test_duplicado_solo_cuenta_en_la_misma_cuenta(authed):
    a, otra, cat = mk_account(authed), mk_account(authed, name="Otra"), mk_category(authed)
    mk_tx(authed, type="expense", amount=45300, date="2026-10-05", account_id=otra["id"], category_id=cat["id"], description="COMPRA EXITO")
    assert preview(authed, BANCO_CO, a, BASE).json()["rows"][0]["duplicate"] is False


def test_cuenta_inexistente_y_mapeo_con_columna_fuera_de_rango(authed):
    assert authed.post("/api/import/csv/preview", json={"text": BANCO_CO, "account_id": 999, "mapping": BASE}).status_code == 404
    a = mk_account(authed)
    assert preview(authed, BANCO_CO, a, {**BASE, "amount_col": 9}).status_code == 422
    assert preview(authed, BANCO_CO, a, {"date_col": 0, "date_format": "dmy", "decimal": ","}).status_code == 422  # sin monto


def test_carga_masiva_es_todo_o_nada(authed):
    a, gasto = mk_account(authed), mk_category(authed)
    ingreso = mk_category(authed, kind="income", name="Salario")
    ok = {"type": "expense", "amount": 100, "date": "2026-10-05", "account_id": a["id"], "category_id": gasto["id"]}
    r = authed.post("/api/transactions/bulk", json={"items": [ok, {**ok, "type": "income", "category_id": ingreso["id"]}]})
    assert r.status_code == 201 and r.json() == {"created": 2}
    malo = {**ok, "category_id": ingreso["id"]}  # categoría de ingreso en un gasto
    assert authed.post("/api/transactions/bulk", json={"items": [ok, malo]}).status_code == 422
    assert authed.get("/api/transactions").json()["total"] == 2  # no entró ninguno de la segunda tanda
    assert authed.post("/api/transactions/bulk", json={"items": [ok] * 1001}).status_code == 422
