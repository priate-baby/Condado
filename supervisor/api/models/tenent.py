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

class InTenent(BaseModel):
    name: constr(strip_whitespace=True, pattern=r"^[\a-zA-Z0-9\s]*$")
    cloud: Cloud

class Tenent(InTenent, Document):

    class Settings:
        use_revision = True

    @computed_field
    @property
    def url(self) -> HttpUrl:
        url_prefix = self.name.lower().replace(" ", "-")
        return f"https://{url_prefix}.{SETTINGS['domain']}"

    class Settings:
        indexes = [
            IndexModel("name", unique=True)
        ]