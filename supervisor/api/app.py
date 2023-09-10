from fastapi import FastAPI
from routers.v1 import ROUTERS as v1_routes

def create_app()->FastAPI:
    app = FastAPI()

    for route in v1_routes:
        app.include_router(route, prefix="/v1")
        app.include_router(route, prefix="")
        app.include_router(route, prefix="/latest")
    return app

app = create_app()