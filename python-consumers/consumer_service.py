import json
import logging
import threading
from typing import Dict, Set, Tuple

import pika

from analytics_client import send_records
from config import settings
from models import (
    AnalyticsRecord,
    CustomerMessage,
    ProductMessage,
    make_idempotency_key,
)

logger = logging.getLogger(__name__)


class IntegrationState:
    """
    In-memory state for joining and idempotency.

    For the assignment we keep this simple. In production these would
    typically live in Redis or a database to allow horizontal scaling.
    """

    def __init__(self) -> None:
        self.customers: Dict[int, CustomerMessage] = {}
        self.products: Dict[int, ProductMessage] = {}
        self.processed_keys: Set[Tuple[int, int]] = set()


state = IntegrationState()


def _build_new_records_for_customer(customer: CustomerMessage) -> list[AnalyticsRecord]:
    records: list[AnalyticsRecord] = []
    for product_id, product in state.products.items():
        key = make_idempotency_key(customer.id, product_id)
        if key in state.processed_keys:
            continue
        record = AnalyticsRecord(
            customer_id=customer.id,
            product_id=product_id,
            sku=product.sku,
            customer_email=customer.email,
            units=1,
            total_value=product.price,
        )
        records.append(record)
        state.processed_keys.add(key)
    return records


def _build_new_records_for_product(product: ProductMessage) -> list[AnalyticsRecord]:
    records: list[AnalyticsRecord] = []
    for customer_id, customer in state.customers.items():
        key = make_idempotency_key(customer_id, product.id)
        if key in state.processed_keys:
            continue
        record = AnalyticsRecord(
            customer_id=customer_id,
            product_id=product.id,
            sku=product.sku,
            customer_email=customer.email,
            units=1,
            total_value=product.price,
        )
        records.append(record)
        state.processed_keys.add(key)
    return records


def _handle_customer_message(body: bytes) -> None:
    payload = json.loads(body.decode("utf-8"))
    customer = CustomerMessage.model_validate(payload)
    logger.info("Received customer %s (%s)", customer.id, customer.email)
    state.customers[customer.id] = customer
    records = _build_new_records_for_customer(customer)
    if records:
        logger.info(
            "Built %d analytics records from customer %s", len(records), customer.id
        )
        send_records(records)


def _handle_product_message(body: bytes) -> None:
    payload = json.loads(body.decode("utf-8"))
    product = ProductMessage.model_validate(payload)
    logger.info("Received product %s (%s)", product.id, product.sku)
    state.products[product.id] = product
    records = _build_new_records_for_product(product)
    if records:
        logger.info(
            "Built %d analytics records from product %s", len(records), product.id
        )
        send_records(records)


def _start_consumer(queue_name: str, handler) -> None:
    credentials = pika.PlainCredentials(settings.rabbitmq_username, settings.rabbitmq_password)
    parameters = pika.ConnectionParameters(
        host=settings.rabbitmq_host,
        port=settings.rabbitmq_port,
        credentials=credentials,
    )
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_qos(prefetch_count=settings.prefetch_count)

    def callback(ch, method, properties, body):  # type: ignore[no-untyped-def]
        try:
            handler(body)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error processing message from %s: %s", queue_name, exc)
            # Nack without requeue to avoid tight failure loops in this demo.
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    channel.basic_consume(queue=queue_name, on_message_callback=callback)

    logger.info("Started consumer for queue '%s'", queue_name)
    channel.start_consuming()


def start_consumers() -> None:
    """
    Start one consumer thread per queue so we can process customer and inventory
    data concurrently.
    """

    customer_thread = threading.Thread(
        target=_start_consumer,
        args=(settings.customer_queue, _handle_customer_message),
        daemon=True,
    )
    inventory_thread = threading.Thread(
        target=_start_consumer,
        args=(settings.inventory_queue, _handle_product_message),
        daemon=True,
    )

    customer_thread.start()
    inventory_thread.start()

    logger.info("Python consumers started. Waiting for messages...")
    # Keep main thread alive
    customer_thread.join()
    inventory_thread.join()

