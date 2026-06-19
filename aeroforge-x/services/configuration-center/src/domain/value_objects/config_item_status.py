from enum import Enum


class ConfigItemStatus(str, Enum):
    DRAFT = "draft"
    RELEASED = "released"
    BASELINED = "baselined"
    OBSOLETE = "obsolete"