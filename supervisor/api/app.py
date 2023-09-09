from fastapi import FastAPI
import version_router
from routers import hello_v1, hello_v2

def create_app()->FastAPI:
    app = FastAPI()

    app.include_router(hello_v1.router, prefix="/v1")
    app.include_router(hello_v2.router)
    app.include_router(hello_v2.router, prefix="/v2")
    app.include_router(hello_v2.router, prefix="/latest")

    return app

app = create_app()