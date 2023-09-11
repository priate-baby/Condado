from . import healthcheck
from . import tenent

ROUTERS = [
    healthcheck.router,
    tenent.router,
]