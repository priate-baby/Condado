from . import healthcheck
from . import tenant

ROUTERS = [
    healthcheck.router,
    tenant.router,
]