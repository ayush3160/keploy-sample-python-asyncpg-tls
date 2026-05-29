import json
import logging
from typing import Any

import boto3

from app.config import get_settings

log = logging.getLogger(__name__)


class SnsPublisher:
    """boto3-backed SNS publisher mirroring the outbox event-factory pattern.

    Outgoing payload shape:
      Message  -> {"mediaType": "<media_type>", "opaqueData": {...request-headers...}, "uri": "<resource-uri>"}
      MessageAttributes -> {"media_type": "<media_type>"}
    """

    def __init__(self) -> None:
        cfg = get_settings()
        self._topic_arn = cfg.sns_publishing.internal_sns_topic_arn
        self._public_topic_arn = cfg.sns_publishing.public_sns_topic_arn
        self._uri_host = cfg.sns_publishing.pubsub_message_uri_host
        client_kwargs: dict[str, Any] = {"region_name": cfg.sns_client.region_name}
        if cfg.sns_client.endpoint_url:
            client_kwargs["endpoint_url"] = cfg.sns_client.endpoint_url
        self._client = boto3.client("sns", **client_kwargs)

    def publish(
        self,
        media_type: str,
        resource_uri: str,
        opaque_data: dict[str, str] | None = None,
        topic_arn: str | None = None,
    ) -> None:
        topic = topic_arn or self._topic_arn
        payload = {
            "mediaType": media_type,
            "opaqueData": opaque_data or {},
            "uri": resource_uri,
        }
        try:
            self._client.publish(
                TopicArn=topic,
                Message=json.dumps(payload),
                MessageAttributes={
                    "media_type": {"DataType": "String", "StringValue": media_type},
                },
            )
        except Exception:  # noqa: BLE001 -- never fail the request on a publish error
            log.exception("sns publish failed", extra={"media_type": media_type, "uri": resource_uri})

    def message_uri(self, *parts: str) -> str:
        return self._uri_host.rstrip("/") + "/" + "/".join(p.strip("/") for p in parts)


_publisher: SnsPublisher | None = None


def get_publisher() -> SnsPublisher:
    global _publisher
    if _publisher is None:
        _publisher = SnsPublisher()
    return _publisher
