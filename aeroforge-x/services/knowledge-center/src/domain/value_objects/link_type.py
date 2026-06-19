from enum import Enum


class LinkType(str, Enum):
    DERIVES_FROM = "derives_from"
    CONSTRAINS = "constrains"
    IMPLEMENTS = "implements"
    USES_MATERIAL = "uses_material"
    PRODUCED_BY = "produced_by"
    MONITORED_BY = "monitored_by"
    MAINTAINED_BY = "maintained_by"
    AFFECTS = "affects"
    DEPENDS_ON = "depends_on"
    VERIFIED_BY = "verified_by"
    SUPERSEDES = "supersedes"

    @classmethod
    def values(cls) -> list[str]:
        return [e.value for e in cls]

    @classmethod
    def cross_center_types(cls) -> list["LinkType"]:
        return [cls.AFFECTS, cls.DEPENDS_ON, cls.VERIFIED_BY]