from pkgutil import iter_modules
from importlib import import_module
import routers

all_routes = iter_modules(routers.__path__)
mapped_routes = []
for (path_str, name, _) in all_routes:
    route = {
        "name": name,
        "version": 0,
    }
    try:
        route["version"] = int(name.split("_v")[-1])
    except ValueError:
        pass
    route["module"] = import_module(f"routers.{name}")
    mapped_routes.append(route)

