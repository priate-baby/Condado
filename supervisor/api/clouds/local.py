from typing import TYPE_CHECKING
import docker

# polyfill for docker-py path bug https://github.com/docker/docker-py/issues/2105
docker.api.build.process_dockerfile = lambda dockerfile, path: ('Dockerfile', dockerfile)

if TYPE_CHECKING:
    from supervisor.api.models import tenant
# manage the local cloud

# for each tenant
# create the new tenant docker containers and start them
# update the nginx config to have that tenant
# restart nginx

class LocalCloud:


    def __init__(self):
        self.docker_client = docker.from_env()
        self.context = "/tenants/default" # TODO make this programmatic

    def create_tenant_api_image(self, tenant: "tenant") -> docker.models.images.Image:
        """Build a docker image for the tenant api"""

        dockerfile_guts = f"""
        FROM python:3.11
        WORKDIR /app
        COPY requirements.txt /app/requirements.txt
        RUN pip install -r requirements.txt
        """
        image_name = f"condado_{tenant.url_name}_api"
        image, _ = self.docker_client.images.build(
            path=self.context,
            dockerfile=dockerfile_guts,
            tag=image_name,
            pull=True,
        )
        return image

    def create_tenant_containers(self, tenant):
        # create the docker containers for the tenant
        pass