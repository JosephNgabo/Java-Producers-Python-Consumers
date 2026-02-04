from pydantic import BaseModel


class Settings(BaseModel):
    """
    Simple runtime configuration for the Python consumers.

    In a real project this would typically read from environment variables.
    For this assignment we keep it static and easy to explain.
    """

    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_username: str = "guest"
    rabbitmq_password: str = "guest"

    customer_queue: str = "customer_data"
    inventory_queue: str = "inventory_data"

    analytics_base_url: str = "http://localhost:8000"
    analytics_endpoint: str = "/analytics/data"

    prefetch_count: int = 10


settings = Settings()

