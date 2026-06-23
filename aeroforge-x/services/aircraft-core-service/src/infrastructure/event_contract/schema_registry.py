from __future__ import annotations

import json
import logging
import os
from typing import Optional

try:
    import jsonschema as _jsonschema
    _HAS_JSONSCHEMA = True
except ImportError:
    _HAS_JSONSCHEMA = False

logger = logging.getLogger(__name__)


class SchemaRegistry:
    def __init__(self):
        self._schemas: dict[str, dict] = {}
        self._versions: dict[str, str] = {}

    def load_from_directory(self, path: str) -> int:
        count = 0
        if not os.path.isdir(path):
            logger.warning(f"Schema directory not found: {path}")
            return 0
        for fname in sorted(os.listdir(path)):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(path, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    schema = json.load(f)
                event_type = schema.get("title", fname.replace(".json", ""))
                version_tag = fname.split(".json")[0].split(".v")[-1] if ".v" in fname else "1.0.0"
                self._schemas[event_type] = schema
                self._versions[event_type] = version_tag
                count += 1
                logger.info(f"Loaded schema: {event_type} v{version_tag}")
            except Exception as e:
                logger.error(f"Failed to load schema {fname}: {e}")
        return count

    def get_schema(self, event_type: str) -> Optional[dict]:
        return self._schemas.get(event_type)

    def register_schema(self, event_type: str, schema: dict, version: str = "1.0.0"):
        self._schemas[event_type] = schema
        self._versions[event_type] = version

    def validate_event(self, event_type: str, payload: dict) -> tuple[bool, str]:
        if not _HAS_JSONSCHEMA:
            logger.debug("jsonschema library not available, skipping validation")
            return True, ""
        schema = self._schemas.get(event_type)
        if schema is None:
            return True, f"No schema registered for {event_type}"
        try:
            _jsonschema.validate(instance=payload, schema=schema)
            return True, ""
        except _jsonschema.ValidationError as e:
            return False, str(e.message)
        except Exception as e:
            return False, str(e)

    def list_schemas(self) -> list[dict]:
        result = []
        for event_type, schema in self._schemas.items():
            result.append({
                "event_type": event_type,
                "version": self._versions.get(event_type, "unknown"),
                "title": schema.get("title", ""),
                "properties": list(schema.get("properties", {}).keys()),
            })
        return result


schema_registry = SchemaRegistry()