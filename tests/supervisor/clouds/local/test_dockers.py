from time import sleep
import pytest
import docker
import requests

from clouds.local import LocalCloud
from models import InTenant

class TestDockers:


    def test_launch_tenant(self):
        client = docker.from_env()
        #with pytest.raises(docker.errors.ImageNotFound):
        #    client.images.get("condado_test-dockers_api")
        try:
            tenant = InTenant(name="test dockers", cloud="aws")
            cloud = LocalCloud()
            containers = cloud.launch_tenant(tenant)
            # hack for passing nginx
            resp = requests.get("http://host.docker.internal")
            assert resp.status_code == 200

        finally:
            for container in containers:
                container.stop()
                _ = container.wait()
            for image in sum([client.images.list(name=f"condado_test-dockers_{x}") for x in ("api","db",)],[]):
                client.images.remove(image.id, force=True)