from fastapi import FastAPI
from settings import SETTINGS

app = FastAPI()

@app.get("/")
async def root():
    return {f"message": "Hello World from {SETTINGS.name}!"}