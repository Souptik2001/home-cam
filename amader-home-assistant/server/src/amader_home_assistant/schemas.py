from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class PairRequest(BaseModel):
    code: str = Field(min_length=1, max_length=256)
    name: str = Field(min_length=1, max_length=128)


class PairResponse(BaseModel):
    token: str
    token_type: Literal["bearer"] = "bearer"


class DeviceWrite(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    platform: Literal["android", "ios"]
    push_token: str = Field(min_length=1, max_length=4096)
    enabled: bool = True


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    platform: str
    enabled: bool


class WebPushKeys(BaseModel):
    p256dh: str = Field(min_length=16, max_length=4096)
    auth: str = Field(min_length=8, max_length=1024)


class WebPushSubscriptionWrite(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    endpoint: HttpUrl
    expiration_time: int | None = None
    keys: WebPushKeys

    @field_validator("endpoint")
    @classmethod
    def require_https_endpoint(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme != "https":
            raise ValueError("web push endpoint must use HTTPS")
        return value


class VapidPublicKeyResponse(BaseModel):
    public_key: str


class DoorbellIngest(BaseModel):
    occurred_at: datetime
    event_type: str = Field(default="doorbell", min_length=1, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    id: str
    duplicate: bool


class EventResponse(BaseModel):
    id: str
    source_id: str
    event_type: str
    occurred_at: datetime
    received_at: datetime
    metadata: dict[str, Any]


class CameraConfigResponse(BaseModel):
    base_url: str
