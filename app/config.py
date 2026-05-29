from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PROVIDER_ENGAGEMENT_SERVICE_POSTGRES__")

    host: str = "localhost"
    port: int = 5432
    name: str = "provider_engagement_service_db"
    username: str = "provider_engagement_service"
    password: str = "postgres"
    require_ssl: bool = False
    ssl_ca_file: str | None = None
    ssl_verify_hostname: bool = True
    pool_size: int = 40
    max_overflow: int = 20
    pool_timeout: int = 3
    pool_recycle_seconds: int = 3600
    pool_pre_ping: bool = True


class SnsPublishingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PROVIDER_ENGAGEMENT_SERVICE_SNS_PUBLISHING__")

    internal_sns_topic_arn: str = "arn:aws:sns:us-east-1:000000000000:test-provider-engagement-internal-topic"
    public_sns_topic_arn: str = "arn:aws:sns:us-east-1:000000000000:test-events-topic"
    pubsub_message_uri_host: str = "https://provider-engagement.local"


class SnsClientSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PROVIDER_ENGAGEMENT_SERVICE_SNS_CLIENT__")

    region_name: str = "us-east-1"
    endpoint_url: str | None = None


class ApprovalServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PROVIDER_ENGAGEMENT_SERVICE_APPROVAL_SERVICE__")

    host: str = "https://juvenal.local"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PROVIDER_ENGAGEMENT_SERVICE_", extra="ignore")

    name: str = Field(default="provider_engagement_service", validation_alias="NAME")
    environment: str = Field(default="local", validation_alias="ENVIRONMENT")
    service_type: str = Field(default="backend", validation_alias="SERVICE_TYPE")
    outbox_event_factory_enabled: bool = Field(default=True, alias="OUTBOX_EVENT_FACTORY__ENABLED")
    outbox_event_factory_enabled_for_encrypted: bool = Field(
        default=True, alias="OUTBOX_EVENT_FACTORY__ENABLED_FOR_ENCRYPTED"
    )

    postgres: PostgresSettings = PostgresSettings()
    sns_publishing: SnsPublishingSettings = SnsPublishingSettings()
    sns_client: SnsClientSettings = SnsClientSettings()
    approval_service: ApprovalServiceSettings = ApprovalServiceSettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
