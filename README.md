## Scalable Systems Integration Assignment (Java Producers + Python Consumers)

This project implements an end-to-end **integration pipeline** for an e-commerce platform using:

- **Java / Spring Boot** for producer services
- **Python** for consumer/processing services
- **RabbitMQ** as the message broker



  
## Figure: End‑to‑end integration from CRM/Inventory → Java producers → RabbitMQ → Python consumers → Analytics

<img width="1536" height="1024" alt="Architecture diagram" src="https://github.com/user-attachments/assets/1eea4d28-6550-4d85-9f85-564afcc2a3fc" />


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

  <img width="1512" height="907" alt="Screenshot 2026-02-04 at 16 23 35" src="https://github.com/user-attachments/assets/1b51fb33-46f3-448e-a08f-9984774967f6" />
  
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
<img width="1506" height="486" alt="Screenshot 2026-02-04 at 16 27 17" src="https://github.com/user-attachments/assets/7db93872-05ce-48e5-a05a-5cd5c93cedb3" />


2. **Run the Java producers**:

```bash
cd "Java Producers + Python Consumers/java-producers"
mvn clean package
mvn spring-boot:run
```
<img width="1149" height="894" alt="Screenshot 2026-02-04 at 16 29 05" src="https://github.com/user-attachments/assets/8ee75df9-219a-4723-9c31-d801af9b79b0" />


3. **Verify messages in RabbitMQ UI**:

- Open `http://localhost:15672` (user: `guest`, password: `guest`).
- Go to the **Queues and Streams** tab.
- You should see queues:
  - `customer_data`
  - `inventory_data`
- Their **Ready** message counts will increase as the scheduled jobs run.
  
<img width="1510" height="413" alt="Screenshot 2026-02-04 at 16 29 23" src="https://github.com/user-attachments/assets/37188b77-3309-4d16-bf44-6e0d27531fb8" />

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

### Task 4 – Scalability & Performance

This integration is designed to comfortably handle **10,000+ records per hour** by combining bulk/paginated API access with asynchronous messaging. The Java producers fetch customers and products in batches (or pages) from the CRM and Inventory APIs, then push lightweight JSON messages into RabbitMQ; this decouples external API latency from downstream processing and allows the consumers to scale independently. For inventory export, bulk endpoints or paginated calls (e.g. 1,000 products per page with parallel page fetches) keep total export time well under **5 minutes**, while RabbitMQ easily sustains thousands of messages per second on modest hardware.

The Python consumers run as horizontally scalable workers that read from `customer_data` and `inventory_data`, merge records in memory, enforce **idempotency** using composite keys, and send batched analytics payloads with retries. To scale to **10+ systems**, the same pattern is extended by adding topics/queues per system and, in higher‑volume environments, moving to a partitioned event bus such as **Kafka** with consumer groups. Around each external system, concerns such as **rate limiting, caching, and circuit breakers** (e.g. via an API Gateway and Resilience4j) protect upstream services and prevent cascading failures. For very large and heterogeneous landscapes, this custom pipeline can be complemented by integration platforms such as **Apache NiFi** or **MuleSoft**, which provide visual flow orchestration, centralized monitoring, and governance while still following an event‑driven architecture.


### Task 5 – Integration Concept in a Polyglot Environment

This pipeline uses a **polyglot** design where Java and Python each do what they are best at. Spring Boot services act as **producers**, periodically calling the CRM (`/customers`) and Inventory (`/products`) REST APIs, transforming the responses into JSON messages and publishing them to RabbitMQ queues (`customer_data`, `inventory_data`). RabbitMQ decouples producers from consumers and buffers load. A Python service runs two **asynchronous consumers** that subscribe to those queues, validate and store customer/product data in memory, merge it into `AnalyticsRecord` objects for each `(customer_id, product_id)` pair, enforce **idempotency** using a set of processed keys, and finally send batched payloads to the Analytics system via `POST /analytics/data` with retry logic.

The same design can be implemented fully in **Java/Spring Boot** without changing the architecture. Instead of Python, a Spring Boot “consumer” application would use `@RabbitListener` (or `@KafkaListener`) methods to read from `customer_data` and `inventory_data`, maintain the same join state in maps or an external store (e.g. Redis), and track processed `(customer_id, product_id)` pairs for idempotency. HTTP calls to the Analytics API would use `WebClient`/`RestTemplate` wrapped with **Spring Retry** or **Resilience4j** for timeouts, retries, and circuit breakers. In both the polyglot and all-Java versions, **async messaging**, **retries**, and **idempotency** ensure that the system is resilient to transient failures and safe against duplicate message delivery while remaining horizontally scalable.


### Task 6 – Testing & Reliability

For the Java side, I use **JUnit 5 + Mockito** to test the Spring Boot producers in isolation. The `CrmProducerService` and `InventoryProducerService` tests mock the HTTP client (`RestTemplate`) to return sample customer/product arrays and mock the `RabbitTemplate` to verify that the correct number of messages are published to the expected queues, without calling real APIs or RabbitMQ. Additional tests simulate failures by making `RestTemplate` throw exceptions and verify that the retry logic is invoked the configured number of times before giving up, which proves the retry/backoff behaviour without flakiness from real networks.

For the Python side, I use **pytest + unittest.mock**. The `analytics_client` tests patch `requests.post` so that I can assert that the client builds the correct JSON body and honours retries without hitting the real Analytics endpoint. The consumer tests construct fake customer and product messages and pass them into the handler functions, asserting that merged `AnalyticsRecord` objects are created, that idempotent keys prevent duplicates, and that the analytics client is called the expected number of times. Error paths are covered by forcing the handler to raise and checking that the message is logged and not retried endlessly. All tests can be run locally with `mvn test` for Java and `pytest` for Python, and the project is ready to be wired into a simple CI pipeline (for example a GitHub Actions workflow that runs `mvn -B test` and `pytest` on every push and collects coverage reports via JaCoCo and pytest-cov) so that regressions are caught automatically.


### Task 7 – Bonus / Stretch Goals

- **Caching API responses**:  
  The Java producers already call the CRM and Inventory APIs in bulk on a schedule. To avoid unnecessary load when multiple runs happen in a short time window, we can introduce a lightweight cache on the producer side (e.g. Spring’s `@Cacheable` with a short TTL or a simple in‑memory map keyed by endpoint + params). This means if the same export is triggered repeatedly within the TTL, the producer will reuse the cached customer/product list instead of hitting the remote APIs again.

- **Config‑driven pipelines**:  
  Both Java and Python sides are configured via external settings instead of hard‑coding values. The Spring Boot app uses `application.yml` to define CRM/Inventory base URLs, queue names, and scheduling intervals; the Python service uses `config.py` (which can be wired to environment variables) for RabbitMQ host/port, queue names, and Analytics endpoint. Adding new systems or changing endpoints/queues becomes a config change rather than a code change.

- **Logging & monitoring (Prometheus/Grafana ready)**:  
  The Java producers include Spring Boot Actuator, which exposes health and basic metrics endpoints that can be scraped by **Prometheus** and visualized in **Grafana** (e.g. HTTP call counts, error rates, JVM metrics). The Python consumers use structured logging for each received message, merge, and analytics POST. In a production setup, these logs and metrics would be shipped to a central stack (Prometheus/Grafana, ELK, or similar) to monitor throughput, failures, and retry behavior.

- **Webhook / Slack alerts on failure**:  
  The retry logic in both Java (Spring Retry) and Python (Tenacity) already surfaces repeated failures in logs. As a next step, those error paths can call a simple webhook client (e.g. Slack incoming webhook URL) when retries are exhausted—sending a small JSON payload with the system name, queue, and error details—so on‑call engineers are notified immediately without watching logs.

- **Dynamic schema / optional fields**:  
  The mock models (both Java DTOs and Python `pydantic` models) are designed to tolerate optional fields by using nullable properties and default values. In a real multi‑system environment, the consumers would use this same pattern plus versioned models (e.g. `CustomerV1`, `CustomerV2`) and feature flags to accept evolving schemas without breaking. Unknown fields are ignored, and only the subset needed for merging into `AnalyticsRecord` is required, which keeps the pipeline robust when upstream APIs add or remove optional data.
