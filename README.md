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

