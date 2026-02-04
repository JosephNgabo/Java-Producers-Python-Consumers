## Scalable Systems Integration Assignment (Java Producers + Python Consumers)

This project implements an end-to-end **integration pipeline** for an e-commerce platform using:

- **Java / Spring Boot** for producer services
- **Python** for consumer/processing services
- **RabbitMQ** as the message broker

It is designed to demonstrate:

- Reliable, scalable integrations between multiple systems
- Asynchronous, message-driven processing
- Retries, idempotency, and monitoring

### Tech Stack (Proposed)

- **Java**: 21 (LTS)
- **Spring Boot**: 3.3.x
- **Build tool**: Maven
- **Message broker**: RabbitMQ 3.13 (Docker image: `rabbitmq:3.13-management`)
- **Python**: 3.12
- **Python libraries** (initial):
  - `pika` (RabbitMQ client)
  - `requests` (HTTP calls)
  - `pydantic` (data models / validation)
  - `tenacity` (retries) – optional

### High-Level Architecture

- **Mock CRM & Inventory APIs** (HTTP):
  - Expose `/customers` and `/products` endpoints with sample data.
- **Java Producers**:
  - Periodically fetch data from CRM and Inventory.
  - Publish messages to RabbitMQ queues:
    - `customer_data`
    - `inventory_data`
  - Implement retry logic for failed API calls and publishing.
- **Python Consumers**:
  - Consume messages from `customer_data` and `inventory_data`.
  - Merge customer and inventory data into a unified JSON format.
  - Ensure idempotency when processing messages.
  - Send merged data to the Analytics API (`/analytics/data`).

Detailed run instructions, architecture diagrams, and testing strategy will be added as the implementation progresses.

### Task 1 – Mock APIs (CRM, Inventory, Analytics)

We use a small **FastAPI** service (in `mock-apis/`) to provide:

- `GET /customers` – list of mock CRM customers.
- `POST /customers` – create a new mock customer.
- `GET /products` – list of mock inventory products.
- `POST /analytics/data` – accepts merged analytics data and returns an ACK.
- `GET /health` – simple health check.

Run via Docker:

```bash
cd "Java Producers + Python Consumers"
docker compose up --build
```

Once running:

- Open the interactive **OpenAPI/Swagger UI** at: `http://localhost:8000/docs`
- Or use simple curl calls, for example:

```bash
curl http://localhost:8000/customers

curl -X POST http://localhost:8000/customers \
  -H "Content-Type: application/json" \
  -d '{"name": "Charlie Brown", "email": "charlie@example.com"}'

curl http://localhost:8000/products

curl -X POST http://localhost:8000/analytics/data \
  -H "Content-Type: application/json" \
  -d '{
        "batch_id": "batch-20240201-0001",
        "generated_at": "2024-02-01T10:00:00Z",
        "records": [
          {
            "customer_id": 1,
            "product_id": 101,
            "sku": "SKU-RED-SHIRT-001",
            "customer_email": "alice@example.com",
            "units": 2,
            "total_value": 39.98
          }
        ]
      }'
```

These endpoints and schemas are what the Java producers and Python consumers will integrate with.

### Task 2 – Java Producers (CRM & Inventory → RabbitMQ)

The `java-producers` Spring Boot application:

- Periodically calls:
  - `GET http://localhost:8000/customers`
  - `GET http://localhost:8000/products`
- Publishes the responses as JSON messages into RabbitMQ queues:
  - `customer_data`
  - `inventory_data`
- Uses **Spring Retry** to retry failed HTTP calls with exponential backoff.

#### How to run the producers

1. **Start infrastructure** (RabbitMQ + mock APIs):

```bash
cd "Java Producers + Python Consumers"
docker compose up --build
```

2. **Run the Java producers**:

```bash
cd "Java Producers + Python Consumers/java-producers"
mvn clean package
mvn spring-boot:run
```

3. **Verify messages in RabbitMQ UI**:

- Open `http://localhost:15672` (user: `guest`, password: `guest`).
- Go to the **Queues and Streams** tab.
- You should see queues:
  - `customer_data`
  - `inventory_data`
- Their **Ready** message counts will increase as the scheduled jobs run.

You can click a queue → **Get messages** to see the JSON payloads.  
In the repository you can include a screenshot (for example `docs/rabbitmq-queues.png`) showing `customer_data` and `inventory_data` with non-zero message counts to demonstrate that the producers are working end-to-end.

### Task 3 – Python Consumers (RabbitMQ → Analytics)

The `python-consumers` service:

- Consumes JSON messages from:
  - `customer_data` (customer events)
  - `inventory_data` (product/stock events)
- Keeps an in-memory store of customers and products.
- Builds merged `AnalyticsRecord` objects for each `(customer_id, product_id)` pair.
- Tracks processed `(customer_id, product_id)` keys to ensure **idempotency**.
- Sends batches of merged records to `POST /analytics/data` with retry logic.

#### How to run the Python consumers

In a new terminal:

You should see logs such as:

- `Started consumer for queue 'customer_data'`
- `Started consumer for queue 'inventory_data'`
- `Received customer ...`, `Received product ...`
- `Built N analytics records from ...`

#### How to verify data reaches the Analytics system

In another terminal, tail the mock Analytics API logs:

cd "Java Producers + Python Consumers"
docker compose logs -f mock-apis
POST /analytics/data HTTP/1.1" 202 Accepted

### Scalability & Performance

This integration is designed to comfortably handle **10,000+ records per hour** by combining bulk/paginated API access with asynchronous messaging. The Java producers fetch customers and products in batches (or pages) from the CRM and Inventory APIs, then push lightweight JSON messages into RabbitMQ; this decouples external API latency from downstream processing and allows the consumers to scale independently. For inventory export, bulk endpoints or paginated calls (e.g. 1,000 products per page with parallel page fetches) keep total export time well under **5 minutes**, while RabbitMQ easily sustains thousands of messages per second on modest hardware.

The Python consumers run as horizontally scalable workers that read from `customer_data` and `inventory_data`, merge records in memory, enforce **idempotency** using composite keys, and send batched analytics payloads with retries. To scale to **10+ systems**, the same pattern is extended by adding topics/queues per system and, in higher‑volume environments, moving to a partitioned event bus such as **Kafka** with consumer groups. Around each external system, concerns such as **rate limiting, caching, and circuit breakers** (e.g. via an API Gateway and Resilience4j) protect upstream services and prevent cascading failures. For very large and heterogeneous landscapes, this custom pipeline can be complemented by integration platforms such as **Apache NiFi** or **MuleSoft**, which provide visual flow orchestration, centralized monitoring, and governance while still following an event‑driven architecture.