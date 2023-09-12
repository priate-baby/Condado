import pytest
import docker
from supervisor.api.clouds.local import LocalCloud
from supervisor.api.models import Tenent

class TestDockers:

    def test_makes_images(self):
        client = docker.from_env()
        pytest.raises(docker.errors.ImageNotFound):
            client.images.get("condado_test_dockers_api")
        try:
            tenent = Tenent(name="test dockers", cloud="aws")
            cloud = LocalCloud()
            image = cloud.create_tenent_api_image(tenent)

            assert image in client.images.list()
        finally:
            client.images.remove(image.id, force=True)