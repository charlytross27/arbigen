"""Escenario financiero de una investigación guardada, sin consultas externas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Analysis, FinancialScenario, Product
from app.modules.profitability.model import FinancialAssumptions, calculate_profitability


class FinancialScenarioWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: UUID
    sale_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    product_cost: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    shipping_cost: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    commission_pct: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    other_costs: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class FinancialScenarioRead(BaseModel):
    analysis_id: UUID
    product_id: UUID | None
    product_external_id: str | None
    product_title: str
    reference_price: Decimal
    currency: str
    sale_price: Decimal
    product_cost: Decimal
    shipping_cost: Decimal
    commission_pct: Decimal
    other_costs: Decimal
    commission_cost: Decimal
    total_cost: Decimal
    unit_profit: Decimal
    margin_pct: Decimal | None
    roi_pct: Decimal | None
    break_even_price: Decimal | None
    updated_at: datetime


def read_financial_scenario(session: Session, analysis: Analysis) -> FinancialScenarioRead | None:
    row = session.get(FinancialScenario, analysis.id)
    if row is None:
        return None
    result = calculate_profitability(FinancialAssumptions(
        sale_price=row.sale_price, product_cost=row.product_cost,
        shipping_cost=row.shipping_cost, commission_pct=row.commission_pct,
        other_costs=row.other_costs,
    ))
    return FinancialScenarioRead(
        analysis_id=row.analysis_id, product_id=row.product_id,
        product_external_id=row.product_external_id, product_title=row.product_title,
        reference_price=row.reference_price, currency=row.currency,
        sale_price=row.sale_price, product_cost=row.product_cost,
        shipping_cost=row.shipping_cost, commission_pct=row.commission_pct,
        other_costs=row.other_costs, commission_cost=result.commission_cost,
        total_cost=result.total_cost, unit_profit=result.unit_profit,
        margin_pct=result.margin_pct, roi_pct=result.roi_pct,
        break_even_price=result.break_even_price, updated_at=row.updated_at,
    )


def save_financial_scenario(
    session: Session, analysis: Analysis, payload: FinancialScenarioWrite,
) -> FinancialScenarioRead:
    product = session.scalar(select(Product).where(
        Product.id == payload.product_id, Product.analysis_id == analysis.id,
    ))
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado en esta investigación.")
    row = session.get(FinancialScenario, analysis.id)
    if row is None:
        row = FinancialScenario(analysis_id=analysis.id)
        session.add(row)
    row.product_id = product.id
    row.product_external_id = product.external_id
    row.product_title = product.title
    row.reference_price = product.price
    row.currency = product.currency
    row.sale_price = payload.sale_price
    row.product_cost = payload.product_cost
    row.shipping_cost = payload.shipping_cost
    row.commission_pct = payload.commission_pct
    row.other_costs = payload.other_costs
    session.commit()
    session.refresh(row)
    saved = read_financial_scenario(session, analysis)
    assert saved is not None
    return saved
