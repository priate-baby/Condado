from io import BytesIO
import tarfile
import docker

"""The docker-py package is falling into disrepair,
so we need to polyfill some things here. Long term we should fork it."""

def cp_in(self,
          path: str,
          file_contents:str) -> None:
    """write a file and contents into the container
    Args:
        path: the full path to write the file to
        file_contents: the contents of the file
    Returns: None
    """
    pathparts = path.split("/")
    file = pathparts[-1]
    parent_path = "/".join(pathparts[:-1])
    tarstream = BytesIO()
    with tarfile.open(fileobj=tarstream, mode="w") as tar:
        tarinfo = tarfile.TarInfo(file)
        tarinfo.size = len(file_contents)
        tar.addfile(tarinfo, BytesIO(bytes(file_contents, "utf-8")))
        self.put_archive(parent_path, tarstream.getvalue())

def cp_out(self,
           path: str) -> str:
    """read a file from the container
    Args:
        path: the full path to read the file from
    Returns: the contents of the file as a string
    """
    tar, _ = self.get_archive(path)
    with BytesIO() as f:
        for chunk in tar:
            f.write(chunk)
        f.seek(0)
        with tarfile.open(fileobj=f) as tar:
            localfile = path.split("/")[-1]
            return tar.extractfile(localfile).read()

docker.models.containers.Container.cp_in = cp_in
docker.models.containers.Container.cp_out = cp_out

# polyfill for docker-py path bug https://github.com/docker/docker-py/issues/2105
docker.api.build.process_dockerfile = lambda dockerfile, path: ('Dockerfile', dockerfile)

def get_client() -> docker.client.DockerClient:
    """Get a docker client"""
    return docker.from_env()

class DockerTypes:
    """shorthand docker types"""
    image = docker.models.images.Image
    container = docker.models.containers.Container
    volume = docker.models.volumes.Volume
    network = docker.models.networks.Network
    build_error = docker.errors.BuildError
    api_error = docker.errors.APIError