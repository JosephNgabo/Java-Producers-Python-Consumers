from unittest.mock import MagicMock, patch
import pathlib
import sys

# Ensure the project root (where analytics_client.py lives) is on sys.path
ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from analytics_client import send_records
from models import AnalyticsRecord


@patch("analytics_client.requests.post")
def test_send_records_posts_batch(mock_post: MagicMock) -> None:
    mock_post.return_value.status_code = 202
    mock_post.return_value.raise_for_status.return_value = None

    records = [
        AnalyticsRecord(
            customer_id=1,
            product_id=101,
            sku="SKU-RED-SHIRT-001",
            customer_email="alice@example.com",
            units=1,
            total_value=19.99,
        )
    ]

    send_records(records)

    assert mock_post.called
    args, kwargs = mock_post.call_args
    assert "/analytics/data" in args[0]
    body = kwargs["json"]
    assert body["records"][0]["customer_id"] == 1

