from enum import Enum
from beanie import Document

class Cloud(str, Enum):
    aws = "aws"
    azure = "azure"
    gcp = "gcp"
    akamai = "akamai"

class Tenent(Document):
    name: str
    cloud: Cloud