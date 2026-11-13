"""API de calcul de factures.

Petite API volontairement simple : l'objet du projet est la CHAÎNE DE
SÉCURITÉ qui l'entoure (scans, SBOM, signature, politiques d'admission).
Le code suit néanmoins les bonnes pratiques : validation stricte des entrées,
arithmétique décimale exacte (jamais de float pour de l'argent), aucune
donnée sensible dans les logs, en-têtes de sécurité HTTP.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, ConfigDict, Field

from invoice_api import __version__

CENT = Decimal("0.01")

# Taux de TVA par pays (en %) — l'API refuse tout pays non listé
VAT_RATES: dict[str, Decimal] = {
    "BJ": Decimal("18"),  # Bénin
    "CI": Decimal("18"),  # Côte d'Ivoire
    "SN": Decimal("18"),  # Sénégal
    "TG": Decimal("18"),  # Togo
    "FR": Decimal("20"),  # France
}

Money = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]


class Line(BaseModel):
    model_config = ConfigDict(extra="forbid")  # refuse tout champ inattendu

    description: str = Field(min_length=1, max_length=200)
    quantity: Annotated[Decimal, Field(gt=0, le=1_000_000, decimal_places=3)]
    unit_price: Money
    discount_percent: Annotated[Decimal, Field(ge=0, le=100)] = Decimal("0")


class InvoiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    country: str = Field(pattern=r"^[A-Z]{2}$")
    lines: list[Line] = Field(min_length=1, max_length=500)


class LineResult(BaseModel):
    description: str
    total_excl_tax: Decimal


class InvoiceResult(BaseModel):
    country: str
    vat_rate_percent: Decimal
    lines: list[LineResult]
    total_excl_tax: Decimal
    vat_amount: Decimal
    total_incl_tax: Decimal


app = FastAPI(
    title="Invoice API",
    version=__version__,
    description="Calcul de factures HT / TVA / TTC.",
)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.middleware("http")
async def security_headers(request: Request, call_next) -> Response:
    """En-têtes HTTP de sécurité recommandés par l'OWASP."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


def round_money(value: Decimal) -> Decimal:
    """Arrondi comptable au centime (0,005 -> 0,01)."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/vat-rates")
def vat_rates() -> dict[str, Decimal]:
    return VAT_RATES


@app.post("/invoices/compute", response_model=InvoiceResult)
def compute(invoice: InvoiceRequest) -> InvoiceResult:
    rate = VAT_RATES.get(invoice.country)
    if rate is None:
        raise HTTPException(status_code=422, detail=f"Pays non pris en charge : {invoice.country}")
    lines = []
    for line in invoice.lines:
        gross = line.quantity * line.unit_price
        net = round_money(gross * (Decimal(100) - line.discount_percent) / Decimal(100))
        lines.append(LineResult(description=line.description, total_excl_tax=net))
    total = sum((line.total_excl_tax for line in lines), Decimal("0"))
    vat = round_money(total * rate / Decimal(100))
    return InvoiceResult(
        country=invoice.country,
        vat_rate_percent=rate,
        lines=lines,
        total_excl_tax=total,
        vat_amount=vat,
        total_incl_tax=total + vat,
    )
