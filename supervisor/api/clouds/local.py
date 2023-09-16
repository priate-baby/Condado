from typing import Literal
import logging
from pydantic import BaseModel, ConfigDict

from utils.docker import get_client, DockerTypes
from utils.nginx import NginxConfig
from models import InTenant, Tenant
from settings import SETTINGS


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class ContainerConfig(BaseModel):
    """Config for a container"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    tenant: InTenant | Tenant
    name_format: str = "condado_{tenant}_{suffix}"
    command: str | None = None
    networks: list = ["condado"]
    suffix: Literal["db", "api"]
    dockerfile_guts: str
    environment: dict = {}
    image: DockerTypes.image | None = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        docker_client = get_client()
        if self.image is None:
            logger.info("no image provided for %s %s, building...",
                        self.tenant.name,
                        self.suffix)
            try:
                self.image, _ = docker_client.images.build(
                    path="/tenants/default", # TODO make this programmatic
                    dockerfile=self.dockerfile_guts,
                    tag=self.formatted_name,
                    pull=True,
                )
                logger.info(f"Built image {self.image.tags[0]}")
            except DockerTypes.build_error as e:
                logger.error("Error building %s image for tenant %s: %s",
                             self.suffix, self.tenant.name, e)
                raise e
    @property
    def formatted_name(self) -> str:
        """get the standardized name for the image and container"""
        return self.name_format.format(tenant=self.tenant.url_name, suffix=self.suffix)


class LocalCloud:
    """Local cloud implementation"""

    def __init__(self):
        self.docker_client = get_client()

    def launch_tenant(self, tenant: "Tenant") -> None:
        """Launch a new tenant"""
        self.launch_containers(
            self.get_container_configs(tenant)
        )
        self.nginx_add(tenant)

    def drop_tenant(self, tenant: "Tenant") -> None:
        """Bring down an existing tenant"""
        self.nginx_remove(tenant)
        configs = self.get_container_configs(tenant)
        self.tear_down_containers(configs)
        self.tear_down_images(configs)

    def get_container_configs(self, tenant: "Tenant") -> list[ContainerConfig]:
        """Get the container configs for a tenant"""
        return [
            ContainerConfig(
                tenant=tenant,
                suffix="db",
                **self._get_db_configs(tenant),
            ),
            ContainerConfig(
                tenant=tenant,
                suffix="api",
                dockerfile_guts = f"""
                FROM python:3.11
                WORKDIR /app
                COPY . /app
                COPY requirements.txt /app/requirements.txt
                RUN pip install -r requirements.txt
                """,
                environment=self._get_db_configs(tenant)["environment"],
                command="uvicorn app:app --reload --host 0.0.0.0 --port 8000",
            )
        ]

    def _get_db_configs(self, tenant:"Tenant") -> dict:
        """determines the correct db configs for the tenent"""
        envars = {
            "mongo": {
                "CONDADO_NAME": tenant.name,
                "MONGO_INITDB_ROOT_USERNAME": tenant.url_name,
                "MONGO_INITDB_ROOT_PASSWORD": tenant.url_name,
                "MONGO_INITDB_DATABASE": tenant.url_name,
            },
            "postgres": {
                "CONDADO_NAME": tenant.name,
                "POSTGRES_USER": tenant.url_name,
                "POSTGRES_PASSWORD": tenant.url_name,
                "POSTGRES_DB": tenant.url_name,
            }
        }
        return {
            "dockerfile_guts": f"FROM {SETTINGS.tenant_db_platform.value}:latest",
            "environment": envars[SETTINGS.tenant_db_platform.value]
        }

    def launch_containers(self, containers:list[ContainerConfig])-> list[DockerTypes.container]:
        """Create the tenant containers"""
        container_set = []

        def append_new_container(container: ContainerConfig,
                                 container_set: list):
            container_set.append(
                self.docker_client.containers.run(
                container.image,
                detach=True,
                name=container.formatted_name,
                environment=container.environment,
                network=container.networks[0],
                command=container.command,
            ))

        for container in containers:
            try:
                append_new_container(container, container_set)
            except DockerTypes.api_error as e:
                if "Conflict" in e.explanation:
                    logger.warning("found existing container named %s, removing and retrying",
                                   container.formatted_name)
                    self.docker_client.containers.get(container.formatted_name).remove(force=True)
                    append_new_container(container, container_set)
        return container_set

    def tear_down_containers(self, containers:list[ContainerConfig])-> None:
        """Remove the tenant containers"""
        for container in containers:
            try:
                self.docker_client.containers.get(container.formatted_name).remove(force=True)
            except DockerTypes.api_error as e:
                if "No such container" in e.explanation:
                    logger.warning("No container named %s found, skipping removal",
                                   container.formatted_name)
                else:
                    raise e
    def tear_down_images(self, containers:list[ContainerConfig])-> None:
        """Remove the tenant images"""
        for container in containers:
            try:
                self.docker_client.images.remove(container.formatted_name, force=True)
            except DockerTypes.api_error as e:
                if "No such image" in e.explanation:
                    logger.warning("No image named %s found, skipping removal",
                                   container.formatted_name)
                else:
                    raise e

    def nginx_add(self, tenant: "Tenant")-> None:
        self._update_nginx(tenant, "add")

    def nginx_remove(self, tenant: "Tenant")-> None:
        self._update_nginx(tenant, "remove")

    def _update_nginx(self,
                      tenant: "Tenant",
                      direction:Literal["add","remove"])-> None:
        """Update the nginx config and restart nginx"""

        def nginx_path(file:str)->str:
            return f"/etc/nginx/{file}"
        nginx_container = self.docker_client.containers.get("condado-condado_webserver-1") # TODO make this programmatic
        # copy the nginx config from the container and update
        config_as_string = nginx_container.cp_out(nginx_path("nginx.conf"))
        nginx_config = NginxConfig(config_as_string)
        new_config = getattr(nginx_config,f"{direction}_tenant")(tenant)

        # write the new config to nginx
        nginx_container.cp_in(nginx_path("nginx.conf"), new_config)
        nginx_container.exec_run("nginx -s reload")