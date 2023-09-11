from pymongo import errors
from fastapi import APIRouter, HTTPException
from models import InTenent, Tenent

router = APIRouter()

@router.post("/tenent")
async def create_tenent(tenent: InTenent):
    """Create a new tenent"""
    try:
        tenent = Tenent(**tenent.dict())
        await tenent.create()
    except errors.DuplicateKeyError as e:
        raise HTTPException(status_code=409, detail="Tenent with that name already exists")
    return tenent

@router.get("/tenent/{tenent_id}")
async def get_tenent(tenent_id: str):
    """Get a tenent by ID"""
    found = await Tenent.get(tenent_id)
    if not found:
        return {"error": "Tenent not found"}
    return found

@router.get("/tenents")
async def tenents_index():
    """List all tenents"""
    tenents = await Tenent.find_all().to_list()
    return tenents