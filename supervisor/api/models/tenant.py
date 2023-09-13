from enum import Enum
from pydantic import BaseModel, constr, computed_field, HttpUrl
from pymongo import IndexModel
from beanie import Document, Indexed

from settings import SETTINGS

class Cloud(str, Enum):
    aws = "aws"
    azure = "azure"
    gcp = "gcp"
    akamai = "akamai"

class InTenant(BaseModel):
    name: constr(strip_whitespace=True, pattern=r"^[\a-zA-Z0-9\s]*$")
    cloud: Cloud

    @property
    def url_name(self) -> str:
        return self.name.lower().replace(" ", "-")

class Tenant(InTenant, Document):

    class Settings:
        use_revision = True

    @computed_field
    @property
    def url(self) -> HttpUrl:
        return f"https://{self.url_name}.{SETTINGS['domain']}"

    class Settings:
        indexes = [
            IndexModel("name", unique=True)
        ]