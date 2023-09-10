from fastapi import APIRouter

router = APIRouter()

@router.get("/healthcheck")
async def healthcheck():
    """Basic healthcheck endpoint for the API"""
    return {"status": "ok"
            , "version": "v1"}