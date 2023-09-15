from typing import TYPE_CHECKING
from tempfile import NamedTemporaryFile
import crossplane

if TYPE_CHECKING:
    from models import Tenant, InTenant

class NginxConfig:
    """helper for modifying the nginx config file"""

    def __init__(self, config:str):
        """utilizes a string representation of the file"""
        with NamedTemporaryFile() as f:
            f.write(config)
            f.seek(0)
            _, errors, parsed = list(crossplane.parse(f.name).values())
            if errors:
                raise ValueError("Error parsing nginx config: %s", errors)
            self.config = parsed[0]["parsed"] # groosss

    def add_tenant(self, tenant: "Tenant | InTenant")-> str:
        """Add a tenant to the nginx config
        Returns:
            the string representation of the new nginx config file contents
        """
        for d in self.config:
            if d["directive"] == "http":
                d["block"].insert(0,
                    self._build_tenant_service_dict(tenant))
        return crossplane.build(self.config)

    def _build_tenant_service_dict(self, tenant:"Tenant | InTenant") -> dict:
        """build a crossplane-compatable service dict"""
        return {
            'directive': 'server',
            'args': [],
            'block': [
                {'directive': 'listen',
                 'args': ['80']
                },
                {'directive': 'listen',
                 'args': ['[::]:80']
                },
                {'directive': 'server_name',
                 'args': [f'{tenant.url_name}.localhost']
                },
                {'directive': 'location',
                 'args': ['/'],
                 'block': [
                     {'directive': 'proxy_set_header',
                      'args': ['Host', '$host']
                     },
                     {'directive': 'proxy_set_header',
                      'args': ['X-Forwarded-For', '$remote_addr']
                     },
                     {'directive': 'proxy_set_header',
                      'args': ['X-Forwarded-Proto', '$scheme']
                     },
                     {'directive': 'proxy_pass',
                      'args': [f'http://condado_{tenant.url_name}_api:8000']
                     }
                 ]
                }
            ]
        }