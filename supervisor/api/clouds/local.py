from typing import TYPE_CHECKING
from io import StringIO
import docker

if TYPE_CHECKING:
    from supervisor.api.models import Tenent
# manage the local cloud

# for each tenent
# create the new tenent docker containers and start them
# update the nginx config to have that tenent
# restart nginx

class LocalCloud:


    def __init__(self):
        self.docker_client = docker.from_env()
        self.context = "/tenents/deafault" # TODO make this programmatic

    def create_tenent_api_image(self, tenent: "Tenent") -> docker.models.images.Image:
        """Build a docker image for the tenent api"""

        dockerfile_guts = f"""
        FROM python:3.11
        WORKDIR /app
        COPY requirements.txt requirements.txt
        RUN pip install -r requirements.txt
        RUN uvicorn main:app --host
        """
        image_name = f"condado_{tenent.domain}_api"
        return self.docker_client.images.build(
            path=self.context,
            fileobj=StringIO(dockerfile_guts),
            tag=image_name,
            pull=True,
        )

    def create_tenent_containers(self, tenent):
        # create the docker containers for the tenent
        pass