from datetime import datetime
from typing import List, Optional, Any

from fastapi import FastAPI, Body
from pydantic import BaseModel, Field


app = FastAPI(
    title="Mock E-commerce Integration APIs",
    description=(
        "Mock CRM, Inventory, and Analytics APIs for the integration assignment. "
        "These are used by Java producers and Python consumers."
    ),
    version="1.0.0",
)


# -----------------------------
# CRM MODELS & ENDPOINTS
# -----------------------------


class CustomerCreate(BaseModel):
    name: str = Field(..., example="John Doe")
    email: str = Field(..., example="john.doe@example.com")


class Customer(CustomerCreate):
    id: int = Field(..., example=1)
    created_at: datetime = Field(..., example="2024-01-01T12:00:00Z")


customers_db: List[Customer] = [
    Customer(id=1, name="Alice Smith", email="alice@example.com", created_at=datetime(2024, 1, 1, 10, 0, 0)),
    Customer(id=2, name="Bob Johnson", email="bob@example.com", created_at=datetime(2024, 1, 2, 11, 30, 0)),
]


@app.get(
    "/customers",
    response_model=List[Customer],
    tags=["CRM"],
    summary="Get all customers",
)
def get_customers() -> List[Customer]:
    """
    Returns a list of mock customers.

    This simulates a CRM `/customers` REST endpoint.
    """
    return customers_db


@app.post(
    "/customers",
    response_model=Customer,
    status_code=201,
    tags=["CRM"],
    summary="Create a new customer",
)
def create_customer(payload: CustomerCreate) -> Customer:
    """
    Creates a new customer in the in-memory CRM store.

    In a real CRM this would persist to a database.
    """
    new_id = max((c.id for c in customers_db), default=0) + 1
    customer = Customer(
        id=new_id,
        name=payload.name,
        email=payload.email,
        created_at=datetime.utcnow(),
    )
    customers_db.append(customer)
    return customer


# -----------------------------
# INVENTORY MODELS & ENDPOINTS
# -----------------------------


class Product(BaseModel):
    id: int = Field(..., example=101)
    sku: str = Field(..., example="SKU-RED-SHIRT-001")
    name: str = Field(..., example="Red T-Shirt")
    stock: int = Field(..., example=150)
    price: float = Field(..., example=19.99)


products_db: List[Product] = [
    Product(id=101, sku="SKU-RED-SHIRT-001", name="Red T-Shirt", stock=150, price=19.99),
    Product(id=102, sku="SKU-BLUE-JEANS-001", name="Blue Jeans", stock=80, price=49.5),
]


@app.get(
    "/products",
    response_model=List[Product],
    tags=["Inventory"],
    summary="Get all products",
)
def get_products() -> List[Product]:
    """
    Returns a list of mock products with stock information.

    This simulates an Inventory `/products` REST endpoint.
    """
    return products_db


# -----------------------------
# ANALYTICS ENDPOINT
# -----------------------------


class AnalyticsRecord(BaseModel):
    customer_id: int = Field(..., example=1)
    product_id: int = Field(..., example=101)
    sku: Optional[str] = Field(None, example="SKU-RED-SHIRT-001")
    customer_email: Optional[str] = Field(None, example="alice@example.com")
    units: int = Field(..., example=2)
    total_value: float = Field(..., example=39.98)


class AnalyticsPayload(BaseModel):
    """
    Generic wrapper for data sent to the Analytics system.

    In a real-world scenario this could be a batch of merged records.
    """

    batch_id: str = Field(..., example="batch-20240201-0001")
    generated_at: datetime = Field(..., example="2024-02-01T10:00:00Z")
    records: List[AnalyticsRecord]


class AnalyticsAck(BaseModel):
    status: str = Field(..., example="accepted")
    message: str = Field(..., example="Batch processed successfully")
    received_records: int = Field(..., example=10)
    echo_batch_id: Optional[str] = Field(None, example="batch-20240201-0001")


@app.post(
    "/analytics/data",
    response_model=AnalyticsAck,
    status_code=202,
    tags=["Analytics"],
    summary="Receive merged analytics data",
)
def post_analytics_data(payload: AnalyticsPayload = Body(...)) -> AnalyticsAck:
    """
    Receives merged data from the integration pipeline.

    For this assignment, the endpoint simply acknowledges receipt and echoes
    the number of records. In production, this would store to a data lake or
    trigger downstream analytics jobs.
    """
    # In a real system we might write to a database or file here.
    return AnalyticsAck(
        status="accepted",
        message="Batch processed successfully (mock)",
        received_records=len(payload.records),
        echo_batch_id=payload.batch_id,
    )


# A very simple "ping" endpoint to verify the mock API is running.
@app.get("/health", tags=["System"], summary="Health check")
def health() -> dict[str, Any]:
    return {"status": "up", "service": "mock-apis"}

