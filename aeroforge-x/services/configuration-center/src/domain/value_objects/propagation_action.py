from enum import Enum


class PropagationAction(str, Enum):
    UPDATE_VERSION = "update_version"
    ADD_ITEM = "add_item"
    REMOVE_ITEM = "remove_item"
    MODIFY_PROPERTY = "modify_property"
    CHANGE_SUPPLIER = "change_supplier"
    RETEST = "retest"
    REVALIDATE = "revalidate"
    NOTIFY = "notify"