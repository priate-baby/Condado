from fastapi import APIRouter
from models import Tenent

router = APIRouter()

@router.post("/tenent")
async def create_tenent(tenent: Tenent):
    """Create a new tenent"""
    await tenent.create()
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