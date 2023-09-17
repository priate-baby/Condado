import yaml
from pathlib import Path
from fastapi import FastAPI

from settings import SETTINGS

app = FastAPI()

@app.get("/")
async def root():
    # feature flag for test-dockers customer
    possible_file = Path("bla/blabla/somefile.yml")
    file_value = (
        None if not possible_file.exists()
        else yaml.safe_load(possible_file.read_text())["some_value"]
    )
    return {"message": f"Hello World from {SETTINGS.name}! The possible value is {file_value}"}