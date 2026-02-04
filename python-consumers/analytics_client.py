import logging
from typing import List

import requests
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from config import settings
from models import AnalyticsPayload, AnalyticsRecord

logger = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def _post_analytics(payload: AnalyticsPayload) -> None:
    url = settings.analytics_base_url + settings.analytics_endpoint
    response = requests.post(url, json=payload.model_dump(), timeout=5)
    response.raise_for_status()
    logger.info(
        "Sent analytics batch %s with %d records, status=%s",
        payload.batch_id,
        len(payload.records),
        response.status_code,
    )


def send_records(records: List[AnalyticsRecord]) -> None:
    """
    Wraps the retrying POST call and logs failures.
    """

    if not records:
        return

    payload = AnalyticsPayload(records=records)
    try:
        _post_analytics(payload)
    except RetryError as exc:
        logger.error(
            "Failed to send analytics batch %s after retries: %s",
            payload.batch_id,
            exc,
        )

