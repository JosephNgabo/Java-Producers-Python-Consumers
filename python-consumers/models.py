from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field


class CustomerMessage(BaseModel):
    id: int
    name: str
    email: str
    created_at: str


class ProductMessage(BaseModel):
    id: int
    sku: str
    name: str
    stock: int
    price: float


class AnalyticsRecord(BaseModel):
    customer_id: int
    product_id: int
    sku: Optional[str] = None
    customer_email: Optional[str] = None
    units: int
    total_value: float


class AnalyticsPayload(BaseModel):
    batch_id: str = Field(
        default_factory=lambda: f"batch-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    )
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    records: List[AnalyticsRecord]


def make_idempotency_key(customer_id: int, product_id: int) -> Tuple[int, int]:
    """
    Composite key for idempotency (customer + product).

    The consumer will keep a set of these keys and skip already processed
    combinations so that re-delivered or duplicate messages do not
    create duplicate analytics records.
    """

    return customer_id, product_id

