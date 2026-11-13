from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from invoice_api.main import app, round_money

client = TestClient(app)


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_security_headers_are_set():
    headers = client.get("/health").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"


def test_compute_invoice_benin_vat():
    body = {
        "country": "BJ",
        "lines": [
            {"description": "Licence Odoo", "quantity": "2", "unit_price": "150000.00"},
            {
                "description": "Formation",
                "quantity": "1",
                "unit_price": "100000.00",
                "discount_percent": "10",
            },
        ],
    }
    result = client.post("/invoices/compute", json=body).json()
    assert Decimal(result["total_excl_tax"]) == Decimal("390000.00")
    assert Decimal(result["vat_amount"]) == Decimal("70200.00")  # 18 %
    assert Decimal(result["total_incl_tax"]) == Decimal("460200.00")


def test_decimal_arithmetic_avoids_float_errors():
    # 0.1 + 0.2 != 0.3 en float : ici le calcul est exact
    body = {
        "country": "FR",
        "lines": [
            {"description": "a", "quantity": "1", "unit_price": "0.10"},
            {"description": "b", "quantity": "1", "unit_price": "0.20"},
        ],
    }
    assert client.post("/invoices/compute", json=body).json()["total_excl_tax"] == "0.30"


def test_round_half_up():
    assert round_money(Decimal("0.005")) == Decimal("0.01")
    assert round_money(Decimal("2.344")) == Decimal("2.34")


@pytest.mark.parametrize(
    "payload",
    [
        {"country": "XX", "lines": [{"description": "a", "quantity": "1", "unit_price": "1"}]},
        {"country": "bj", "lines": [{"description": "a", "quantity": "1", "unit_price": "1"}]},
        {"country": "BJ", "lines": []},
        {"country": "BJ", "lines": [{"description": "a", "quantity": "-1", "unit_price": "1"}]},
        {
            "country": "BJ",
            "lines": [{"description": "a", "quantity": "1", "unit_price": "1"}],
            "admin": True,
        },
    ],
)
def test_invalid_input_is_rejected(payload):
    assert client.post("/invoices/compute", json=payload).status_code == 422


def test_metrics_exposed():
    client.get("/health")
    assert "http_requests_total" in client.get("/metrics").text
