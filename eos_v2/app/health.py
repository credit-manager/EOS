from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["system"])


@router.get("/health/live", include_in_schema=False)
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", include_in_schema=False)
def readiness(request: Request) -> dict[str, str]:
    database = getattr(request.app.state, "database", None)
    environment = request.app.state.settings.environment
    if environment in {"staging", "production"}:
        if database is None:
            raise HTTPException(status_code=503, detail="Database is not configured")
        try:
            database.check_connection()
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Database is not ready") from exc
    return {"status": "ok"}


@router.get("/api/v1/system/info", tags=["system"])
def system_info(request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    return {
        "name": settings.app_name,
        "runtime": "v2",
        "api_version": settings.api_prefix.rsplit("/", 1)[-1],
        "environment": settings.environment,
    }
