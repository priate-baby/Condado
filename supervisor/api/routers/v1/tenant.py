from pymongo import errors
from fastapi import APIRouter, HTTPException
from models import InTenant, Tenant
from clouds.local import LocalCloud

router = APIRouter()

@router.post("/tenant")
async def create_tenant(tenant: InTenant):
    """Create a new tenant"""
    try:
        tenant = Tenant(**tenant.dict())
        await tenant.create()
    except errors.DuplicateKeyError as e:
        raise HTTPException(status_code=409, detail="tenant with that name already exists")
    LocalCloud().launch_tenant(tenant)
    return tenant

@router.delete("/tenant/{tenant_id}")
async def delete_tenant(tenant_id: str):
    """Delete a tenant by ID"""
    tenant = await Tenant.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="tenant not found")
    LocalCloud().drop_tenant(tenant)
    await tenant.delete()
    return {"success": True}

@router.get("/tenant/{tenant_id}")
async def get_tenant(tenant_id: str):
    """Get a tenant by ID"""
    found = await Tenant.get(tenant_id)
    if not found:
        return {"error": "tenant not found"}
    return found

@router.get("/tenants")
async def tenants_index():
    """List all tenants"""
    tenants = await Tenant.find_all().to_list()
    return tenants