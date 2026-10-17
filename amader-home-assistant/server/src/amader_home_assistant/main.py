from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import secrets
import time
from collections import OrderedDict, deque
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from amader_home_assistant.config import Settings
from amader_home_assistant.database import (
    build_engine,
    build_session_factory,
    create_schema,
    database_is_ready,
)
from amader_home_assistant.models import (
    DoorbellEvent,
    NotificationDeliveryAttempt,
    PairedDevice,
    PairedSession,
)
from amader_home_assistant.push import (
    PushMessage,
    PushSender,
    create_push_sender,
    create_web_push_sender,
    validate_web_push_endpoint,
)
from amader_home_assistant.schemas import (
    CameraConfigResponse,
    DeviceResponse,
    DeviceWrite,
    DoorbellIngest,
    EventResponse,
    IngestResponse,
    PairRequest,
    PairResponse,
    VapidPublicKeyResponse,
    WebPushSubscriptionWrite,
)

ReadinessChecker = Callable[[], bool]
bearer_scheme = HTTPBearer(auto_error=False)


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def create_app(
    readiness_checker: ReadinessChecker | None = None,
    *,
    settings: Settings | None = None,
    push_sender: PushSender | None = None,
    web_push_sender: PushSender | None = None,
) -> FastAPI:
    settings = settings or Settings()
    engine = build_engine(settings.database_url)
    session_factory = build_session_factory(engine)
    push_sender = push_sender or create_push_sender(settings)
    web_push_sender = web_push_sender or create_web_push_sender(settings)
    readiness_checker = readiness_checker or (lambda: database_is_ready(engine))
    pairing_attempts: OrderedDict[str, deque[float]] = OrderedDict()
    pairing_attempts_lock = Lock()
    trusted_proxy_networks = tuple(
        ipaddress.ip_network(network) for network in settings.trusted_proxy_networks
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        create_schema(engine)
        yield
        engine.dispose()

    app = FastAPI(title="Amader Home Assistant", version="1.0.0", lifespan=lifespan)
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.push_sender = push_sender
    app.state.web_push_sender = web_push_sender
    app.state.pairing_attempts = pairing_attempts

    if settings.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self'; style-src 'self'; script-src 'self'; "
            "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        )
        if request.url.path == "/sw.js":
            response.headers["Cache-Control"] = "no-cache"
            response.headers["Service-Worker-Allowed"] = "/"
        return response

    def get_db() -> Iterator[Session]:
        with session_factory() as db:
            yield db

    def require_session(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
        db: Session = Depends(get_db),
    ) -> PairedSession:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        token_hash = hash_secret(credentials.credentials)
        paired_session = db.scalar(
            select(PairedSession).where(
                PairedSession.token_hash == token_hash,
                PairedSession.active.is_(True),
            )
        )
        if paired_session is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return paired_session

    @app.get("/health/live")
    def health_live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    def health_ready() -> JSONResponse:
        if readiness_checker():
            return JSONResponse(status_code=200, content={"status": "ok"})
        return JSONResponse(status_code=503, content={"status": "unavailable"})

    def pairing_client_key(request: Request) -> str:
        peer = request.client.host if request.client is not None else "unknown"
        try:
            peer_address = ipaddress.ip_address(peer)
        except ValueError:
            return peer
        if any(peer_address in network for network in trusted_proxy_networks):
            forwarded = request.headers.get("CF-Connecting-IP")
            if forwarded:
                try:
                    return str(ipaddress.ip_address(forwarded.strip()))
                except ValueError:
                    pass
        return str(peer_address)

    @app.post(
        "/api/v1/pair", response_model=PairResponse, status_code=status.HTTP_201_CREATED
    )
    def pair(
        payload: PairRequest, request: Request, db: Session = Depends(get_db)
    ) -> PairResponse:
        client_key = pairing_client_key(request)
        now = time.monotonic()
        with pairing_attempts_lock:
            stale_keys = [
                key
                for key, values in pairing_attempts.items()
                if not values or now - values[-1] >= 60
            ]
            for key in stale_keys:
                pairing_attempts.pop(key, None)
            attempts = pairing_attempts.get(client_key)
            if attempts is None:
                while len(pairing_attempts) >= settings.pairing_rate_limit_max_clients:
                    pairing_attempts.popitem(last=False)
                attempts = deque()
                pairing_attempts[client_key] = attempts
            else:
                pairing_attempts.move_to_end(client_key)
            while attempts and now - attempts[0] >= 60:
                attempts.popleft()
            if len(attempts) >= settings.pairing_attempts_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="too many pairing attempts",
                    headers={"Retry-After": "60"},
                )
            attempts.append(now)

        configured_code = settings.pairing_code.get_secret_value()
        if not configured_code:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="pairing is not configured",
            )
        if not hmac.compare_digest(payload.code, configured_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid pairing code",
            )

        token = secrets.token_urlsafe(32)
        paired_session = PairedSession(
            name=payload.name,
            token_hash=hash_secret(token),
            pairing_code_hash=hash_secret(configured_code),
        )
        db.add(paired_session)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="pairing code has already been used; rotate it to pair again",
            ) from None
        return PairResponse(token=token)

    @app.post(
        "/api/v1/devices",
        response_model=DeviceResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def register_device(
        payload: DeviceWrite,
        paired_session: PairedSession = Depends(require_session),
        db: Session = Depends(get_db),
    ) -> PairedDevice:
        device = db.scalar(
            select(PairedDevice).where(PairedDevice.push_token == payload.push_token)
        )
        if device is None:
            device = PairedDevice(session_id=paired_session.id, **payload.model_dump())
            db.add(device)
        else:
            device.session_id = paired_session.id
            for key, value in payload.model_dump().items():
                setattr(device, key, value)
        db.commit()
        db.refresh(device)
        return device

    @app.put("/api/v1/devices/{device_id}", response_model=DeviceResponse)
    def update_device(
        device_id: str,
        payload: DeviceWrite,
        paired_session: PairedSession = Depends(require_session),
        db: Session = Depends(get_db),
    ) -> PairedDevice:
        device = db.scalar(
            select(PairedDevice).where(
                PairedDevice.id == device_id,
                PairedDevice.session_id == paired_session.id,
            )
        )
        if device is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        for key, value in payload.model_dump().items():
            setattr(device, key, value)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="push token is already registered",
            ) from None
        db.refresh(device)
        return device

    @app.get("/api/v1/push/vapid-public-key", response_model=VapidPublicKeyResponse)
    def vapid_public_key(
        _paired_session: PairedSession = Depends(require_session),
    ) -> VapidPublicKeyResponse:
        if not web_push_sender.enabled or not settings.web_push_vapid_public_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="web push is not configured",
            )
        return VapidPublicKeyResponse(public_key=settings.web_push_vapid_public_key)

    @app.post(
        "/api/v1/push/subscriptions",
        response_model=DeviceResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def register_web_push_subscription(
        payload: WebPushSubscriptionWrite,
        paired_session: PairedSession = Depends(require_session),
        db: Session = Depends(get_db),
    ) -> PairedDevice:
        endpoint = str(payload.endpoint)
        try:
            validate_web_push_endpoint(
                endpoint, {host.lower() for host in settings.web_push_allowed_hosts}
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from None
        subscription = json.dumps(
            {
                "endpoint": endpoint,
                "expirationTime": payload.expiration_time,
                "keys": payload.keys.model_dump(),
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        device = None
        for candidate in db.scalars(
            select(PairedDevice).where(PairedDevice.platform == "web")
        ):
            try:
                if json.loads(candidate.push_token).get("endpoint") == endpoint:
                    device = candidate
                    break
            except (json.JSONDecodeError, AttributeError):
                continue
        if device is None:
            device = PairedDevice(
                session_id=paired_session.id,
                name=payload.name,
                platform="web",
                push_token=subscription,
                enabled=True,
            )
            db.add(device)
        else:
            device.session_id = paired_session.id
            device.name = payload.name
            device.push_token = subscription
            device.enabled = True
        db.commit()
        db.refresh(device)
        return device

    @app.post("/api/v1/session/disconnect", status_code=status.HTTP_204_NO_CONTENT)
    def disconnect_session(
        paired_session: PairedSession = Depends(require_session),
        db: Session = Depends(get_db),
    ) -> Response:
        devices = db.scalars(
            select(PairedDevice).where(PairedDevice.session_id == paired_session.id)
        ).all()
        for device in devices:
            device.enabled = False
        paired_session.active = False
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/api/v1/events", response_model=list[EventResponse])
    def list_events(
        limit: int = Query(default=50, ge=1, le=200),
        _paired_session: PairedSession = Depends(require_session),
        db: Session = Depends(get_db),
    ) -> list[EventResponse]:
        events = db.scalars(
            select(DoorbellEvent)
            .order_by(
                DoorbellEvent.occurred_at.desc(), DoorbellEvent.received_at.desc()
            )
            .limit(limit)
        ).all()
        return [
            EventResponse(
                id=event.id,
                source_id=event.source_id,
                event_type=event.event_type,
                occurred_at=as_utc(event.occurred_at),
                received_at=as_utc(event.received_at),
                metadata=event.payload_metadata,
            )
            for event in events
        ]

    @app.get("/api/v1/camera/config", response_model=CameraConfigResponse)
    def camera_config(
        _paired_session: PairedSession = Depends(require_session),
    ) -> CameraConfigResponse:
        return CameraConfigResponse(base_url=settings.camera_base_url)

    @app.post(
        "/api/v1/ingest/doorbell",
        response_model=IngestResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def ingest_doorbell(
        request: Request,
        source_id: str = Header(alias="X-Doorbell-Source"),
        timestamp_header: str = Header(alias="X-Doorbell-Timestamp"),
        nonce: str = Header(alias="X-Doorbell-Nonce", min_length=1, max_length=128),
        signature: str = Header(alias="X-Doorbell-Signature"),
        db: Session = Depends(get_db),
    ) -> IngestResponse | JSONResponse:
        secret = settings.doorbell_hmac_secrets.get(source_id)
        if secret is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        try:
            timestamp = int(timestamp_header)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from None
        if abs(int(time.time()) - timestamp) > settings.hmac_max_age_seconds:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > settings.max_ingest_body_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail="request body is too large",
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="invalid content length",
                ) from None

        body_parts: list[bytes] = []
        body_size = 0
        async for chunk in request.stream():
            body_size += len(chunk)
            if body_size > settings.max_ingest_body_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail="request body is too large",
                )
            body_parts.append(chunk)
        body = b"".join(body_parts)
        canonical = b".".join(
            [source_id.encode(), str(timestamp).encode(), nonce.encode(), body]
        )
        expected = hmac.new(secret.encode(), canonical, hashlib.sha256).hexdigest()
        supplied = signature.removeprefix("sha256=")
        if not hmac.compare_digest(expected, supplied):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        try:
            payload = DoorbellIngest.model_validate_json(body)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=exc.errors(include_url=False),
            ) from None

        existing = db.scalar(
            select(DoorbellEvent).where(
                DoorbellEvent.source_id == source_id,
                DoorbellEvent.nonce == nonce,
            )
        )
        if existing is not None:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"id": existing.id, "duplicate": True},
            )

        event = DoorbellEvent(
            source_id=source_id,
            nonce=nonce,
            event_type=payload.event_type,
            occurred_at=payload.occurred_at,
            payload_metadata=payload.metadata,
        )
        db.add(event)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = db.scalar(
                select(DoorbellEvent).where(
                    DoorbellEvent.source_id == source_id,
                    DoorbellEvent.nonce == nonce,
                )
            )
            if existing is None:
                raise
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"id": existing.id, "duplicate": True},
            )
        db.refresh(event)

        devices = db.scalars(
            select(PairedDevice).where(PairedDevice.enabled.is_(True))
        ).all()
        message = PushMessage(
            title="Someone is at the door",
            body="The doorbell was pressed.",
            data={
                "event_id": event.id,
                "event_type": event.event_type,
                "route": "/camera",
                "camera_url": settings.camera_base_url,
            },
        )
        for device in devices:
            device_sender = web_push_sender if device.platform == "web" else push_sender
            attempt = NotificationDeliveryAttempt(
                event_id=event.id,
                device_id=device.id,
                status="pending" if device_sender.enabled else "disabled",
                error=None
                if device_sender.enabled
                else f"{device.platform} push sender is not configured",
            )
            db.add(attempt)
            db.commit()
            if not device_sender.enabled:
                continue
            try:
                result = await run_in_threadpool(
                    device_sender.send, device.push_token, message
                )
                attempt.status = "sent"
                attempt.provider_message_id = result.provider_message_id
            except Exception as exc:  # noqa: BLE001 - provider boundary must not lose event
                attempt.status = "failed"
                attempt.error = str(exc)[:500]
            db.commit()

        return IngestResponse(id=event.id, duplicate=False)

    web_root = Path(__file__).with_name("web")
    app.mount("/", StaticFiles(directory=web_root, html=True), name="pwa")
    return app


app = create_app()
