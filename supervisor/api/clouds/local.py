from typing import TYPE_CHECKING
from io import StringIO
import docker

from settings import SETTINGS

# polyfill for docker-py path bug https://github.com/docker/docker-py/issues/2105
docker.api.build.process_dockerfile = lambda dockerfile, path: ('Dockerfile', dockerfile)

if TYPE_CHECKING:
    from supervisor.api.models import Tenant
# manage the local cloud

# for each tenant
# create the new tenant docker containers and start them
# update the nginx config to have that tenant
# restart nginx

class LocalCloud:


    def __init__(self):
        self.docker_client = docker.from_env()
        self.context = "/tenants/default" # TODO make this programmatic

    def launch_tenant(self, tenant: "Tenant"):
        """Launch a new tenant"""
        self.create_tenant_containers(tenant)
        self.update_nginx(tenant)

    def create_api_image(self, tenant: "Tenant") -> docker.models.images.Image:
        """Build a docker image for the tenant api"""

        dockerfile_guts = f"""
        FROM python:3.11
        WORKDIR /app
        COPY requirements.txt /app/requirements.txt
        RUN pip install -r requirements.txt
        """
        return self._create_raw_image(
            tenant,
            dockerfile_guts,
            "api")

    def create_db_image(self, tenant:"Tenant") -> docker.models.images.Image:
        """Build a docker image for the tenant db"""

        dockerfile_guts = f"FROM {SETTINGS['tenant_db_platform']}:latest"

        return self._create_raw_image(
            tenant,
            dockerfile_guts,
            "db")

    def _create_raw_image(self,
                          tenant: "Tenant",
                          dockerfile_guts: str,
                          suffix: str) -> docker.models.images.Image:
        """Raw create image method
        Args:
            - tenant: the tenant to create the image for
            - dockerfile_guts: the contents of the dockerfile
            - suffix: the suffix to add to the image name
        """
        image_name = f"condado_{tenant.url_name}_{suffix}"
        image, _ = self.docker_client.images.build(
            path=self.context,
            dockerfile=dockerfile_guts,
            tag=image_name,
            pull=True,
        )
        return image

    def create_tenant_containers(self, tenant)-> None:
        """Create the tenant containers"""

        # db first
        _ = self.docker_client.containers.run(
            self.create_db_image,
            detach=True,
            name=f"condado_{tenant.url_name}_db",
            environment={
                "POSTGRES_USER": tenant.url_name,
                "POSTGRES_PASSWORD": tenant.url_name,
                "POSTGRES_DB": tenant.url_name,
                "MONGO_INITDB_ROOT_USERNAME": tenant.url_name,
                "MONGO_INITDB_ROOT_PASSWORD": tenant.url_name,
                "MONGO_INITDB_DATABASE": tenant.url_name,
            },
            networks=["condado"],
        )

        # then api
        _ = self.docker_client.containers.run(
            self.create_api_image(tenant),
            detach=True,
            name=f"condado_{tenant.url_name}_api",
            environment={
                "POSTGRES_USER": tenant.url_name,
                "POSTGRES_PASSWORD": tenant.url_name,
                "POSTGRES_DB": tenant.url_name,
                "MONGO_INITDB_ROOT_USERNAME": tenant.url_name,
                "MONGO_INITDB_ROOT_PASSWORD": tenant.url_name,
                "MONGO_INITDB_DATABASE": tenant.url_name,
            },
            networks=["condado"],
            command="uvicorn supervisor.api.main:app --reload --host 0.0.0.0 --port 8000",
        )

    def update_nginx(self, tenant: "Tenant")-> None:
        """Update the nginx config"""
        # get the nginx container
        nginx_container = self.docker_client.containers.get("condado_nginx")
        # copy the nginx config from the container
        nginx_config_bits, _ = nginx_container.get_archive("/etc/nginx/conf.d/default.conf")
        nginx_config = ""
        for chunk in nginx_config_bits:
            nginx_config += chunk.decode("utf-8")
        # update the config
        injected_server = f""""
server {{
    listen       80;
    listen  [::]:80;
    server_name  {tenant.url_name}.localhost;

    location / {{
      proxy_set_header Host $host;
      proxy_set_header X-Forwarded-For $remote_addr;
      proxy_set_header X-Forwarded-Proto $scheme;
      proxy_pass http://condado_{tenant.url_name}_api:8000;
    }}
  }}"""
        pre, post = nginx_config.split("http {")
        new_config = pre + "http {\n" + injected_server + post

        # write the new config to nginx
        nginx_container.put_archive("/etc/nginx/conf.d/default.conf",bytes(new_config, "utf-8"))
        nginx_container.exec_run("nginx -s reload")