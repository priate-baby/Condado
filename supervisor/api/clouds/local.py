from typing import Literal
import io
import tarfile
import logging
from pydantic import BaseModel, ConfigDict
import docker

from models import InTenant, Tenant
from settings import SETTINGS


# polyfill for docker-py path bug https://github.com/docker/docker-py/issues/2105
docker.api.build.process_dockerfile = lambda dockerfile, path: ('Dockerfile', dockerfile)

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
    image: docker.models.images.Image | None = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        docker_client = docker.from_env()
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
            except docker.errors.BuildError as e:
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
        self.docker_client = docker.from_env()

    def launch_tenant(self, tenant: "Tenant") -> None:
        """Launch a new tenant"""
        self.launch_containers(
            self.get_container_configs(tenant)
        )
        self.update_nginx(tenant)

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

    def launch_containers(self, containers:list[ContainerConfig])-> list[docker.models.containers.Container]:
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
            except docker.errors.APIError as e:
                if "Conflict" in e.explanation:
                    logger.warning("found existing container named %s, removing and retrying",
                                   container.formatted_name)
                    self.docker_client.containers.get(container.formatted_name).remove(force=True)
                    append_new_container(container, container_set)
        return container_set

    def update_nginx(self, tenant: "Tenant")-> None:
        """Update the nginx config"""
        def nginx_path(file:str)->str:
            return f"/etc/nginx/{file}"

        # get the nginx container
        logger.info("Updating nginx config to add new tenant %s", tenant.name)
        nginx_container = self.docker_client.containers.get("condado-condado_webserver-1") # TODO make this programmatic
        # copy the nginx config from the container
        nginx_config = self._read_from_container(nginx_container, nginx_path("nginx.conf"))

        # update the config
        injected_server = f"""
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
        pre, post = nginx_config.decode('utf-8').split("http {")
        new_config = pre + "http {\n" + injected_server + post
        logger.info(f"New nginx config: {new_config}")

        # write the new config to nginx
        self._update_in_container(nginx_container, nginx_path("nginx.conf"), new_config)
        nginx_container.exec_run("nginx -s reload")


    def _read_from_container(self,
                             container:docker.models.containers.Container,
                             file:str) -> str:
        """Read a file from a container"""
        tar, _ = container.get_archive(file)
        with io.BytesIO() as f:
            for chunk in tar:
                f.write(chunk)
            f.seek(0)
            with tarfile.open(fileobj=f) as tar:
                localfile = file.split("/")[-1]
                return tar.extractfile(localfile).read()

    def _update_in_container(self,
                             container:docker.models.containers.Container,
                             filename:str,
                             contents:str) -> None:
        """Update a file in a container"""
        pathparts = filename.rsplit("/")
        file = pathparts[-1]
        path = "/".join(pathparts[:-1])
        tarstream = io.BytesIO()
        with tarfile.open(fileobj=tarstream, mode="w") as tar:
            tarinfo = tarfile.TarInfo(file)
            tarinfo.size = len(contents)
            tar.addfile(tarinfo, io.BytesIO(bytes(contents, "utf-8")))
            container.put_archive(path, tarstream.getvalue())
