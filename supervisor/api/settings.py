import yaml
from pathlib import Path

SETTINGS = yaml.load(
    Path('settings.yml').read_text(),
    Loader=yaml.FullLoader
)