from fastapi import FastAPI

# mongo
import motor
from beanie import init_beanie

from routers.v1 import ROUTERS as v1_routes
from models import DOCUMENT_MODELS

def create_app()->FastAPI:
    app = FastAPI()
    # add routers
    for route in v1_routes:
        app.include_router(route, prefix="/v1")
        app.include_router(route, prefix="", include_in_schema=False)
        app.include_router(route, prefix="/latest", include_in_schema=False)
    return app

app = create_app()

@app.on_event("startup")
async def start_db():
    # init mongo
    client = motor.motor_asyncio.AsyncIOMotorClient(
    "mongodb://condado:condado@condado_supervisor_db:27017")
    await init_beanie(client.database, document_models=DOCUMENT_MODELS)