from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health/live", include_in_schema=False)
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", include_in_schema=False)
def readiness() -> dict[str, str]:
    # Dependency checks are deliberately added by the infrastructure slice,
    # not hidden inside the liveness endpoint.
    return {"status": "ok"}


@router.get("/api/v1/system/info", tags=["system"])
def system_info() -> dict[str, object]:
    return {
        "name": "EOS Dynamic Business Platform",
        "runtime": "v2",
        "api_version": "v1",
    }
