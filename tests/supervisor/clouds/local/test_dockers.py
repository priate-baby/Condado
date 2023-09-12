import pytest
import docker
from clouds.local import LocalCloud
from models import Intenant

class TestDockers:

    def test_makes_images(self):
        client = docker.from_env()
        image = None
        with pytest.raises(docker.errors.ImageNotFound):
            client.images.get("condado_test_dockers_api")
        try:
            tenant = Intenant(name="test dockers", cloud="aws")
            cloud = LocalCloud()
            image = cloud.create_tenant_api_image(tenant)

            assert image in client.images.list()
        finally:
            if image:
                client.images.remove(image.id, force=True)