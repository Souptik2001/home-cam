from collections.abc import Callable

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from amader_home_assistant.config import Settings
from amader_home_assistant.readiness import DatabaseReadinessChecker

ReadinessChecker = Callable[[], bool]


def create_app(readiness_checker: ReadinessChecker | None = None) -> FastAPI:
    if readiness_checker is None:
        readiness_checker = DatabaseReadinessChecker(Settings().database_url)

    app = FastAPI(title="Amader Home Assistant")

    @app.get("/health/live")
    def health_live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    def health_ready() -> JSONResponse:
        if readiness_checker():
            return JSONResponse(status_code=200, content={"status": "ok"})
        return JSONResponse(status_code=503, content={"status": "unavailable"})

    return app


app = create_app()
