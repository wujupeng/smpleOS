"""AeroForge-X v6.0 PluginRegistryService

Extensible plugin framework for v6.0:
- UQ method plugins (BayesianPINN, MCDropout, Ensemble)
- Discipline solver plugins (Cost, Manufacturing, Certification)
- Regulatory library plugins (FAA, EASA)
- Data source adapter plugins (OPC-UA, MQTT)
- NDT method adapter plugins (UT, RT, PT, MT, ET)

REQ-DFX-V6-028~032, REQ-NFR-V6-026~030
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class PluginType(str, Enum):
    UQ_METHOD = "UQMethod"
    DISCIPLINE_SOLVER = "DisciplineSolver"
    REGULATORY_LIBRARY = "RegulatoryLibrary"
    DATA_SOURCE_ADAPTER = "DataSourceAdapter"
    NDT_METHOD_ADAPTER = "NDTMethodAdapter"


class PluginStatus(str, Enum):
    REGISTERED = "Registered"
    ACTIVE = "Active"
    DISABLED = "Disabled"
    ERROR = "Error"


class IPlugin(ABC):
    @abstractmethod
    def get_plugin_id(self) -> str: ...

    @abstractmethod
    def get_plugin_type(self) -> PluginType: ...

    @abstractmethod
    def get_plugin_name(self) -> str: ...

    @abstractmethod
    def get_version(self) -> str: ...

    @abstractmethod
    def execute(self, params: dict) -> dict: ...

    @abstractmethod
    def validate_config(self, config: dict) -> bool: ...


@dataclass
class PluginDescriptor:
    plugin_id: str
    plugin_type: PluginType
    plugin_name: str
    version: str
    description: str = ""
    config_schema: dict = field(default_factory=dict)
    status: PluginStatus = PluginStatus.REGISTERED
    registered_at: str = ""
    last_executed_at: str = ""
    execution_count: int = 0
    error_count: int = 0

    def to_dict(self) -> dict:
        return {
            "plugin_id": self.plugin_id,
            "plugin_type": self.plugin_type.value,
            "plugin_name": self.plugin_name,
            "version": self.version,
            "description": self.description,
            "config_schema": self.config_schema,
            "status": self.status.value,
            "registered_at": self.registered_at,
            "last_executed_at": self.last_executed_at,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
        }


@dataclass
class PluginExecutionResult:
    plugin_id: str
    success: bool
    output: dict = field(default_factory=dict)
    error: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "plugin_id": self.plugin_id,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


class UQMethodPlugin(IPlugin):
    def __init__(self, method_name: str, method_type: str):
        self._id = f"UQ-{method_name}-{uuid.uuid4().hex[:4]}"
        self._name = method_name
        self._method_type = method_type

    def get_plugin_id(self) -> str:
        return self._id

    def get_plugin_type(self) -> PluginType:
        return PluginType.UQ_METHOD

    def get_plugin_name(self) -> str:
        return self._name

    def get_version(self) -> str:
        return "1.0.0"

    def execute(self, params: dict) -> dict:
        return {
            "method": self._method_type,
            "coefficient_of_variation": params.get("cov", 0.05),
            "is_high_uncertainty": params.get("cov", 0.05) > 0.10,
        }

    def validate_config(self, config: dict) -> bool:
        return "cov_threshold" in config


class DisciplineSolverPlugin(IPlugin):
    def __init__(self, discipline_name: str):
        self._id = f"SOLVER-{discipline_name}-{uuid.uuid4().hex[:4]}"
        self._name = discipline_name

    def get_plugin_id(self) -> str:
        return self._id

    def get_plugin_type(self) -> PluginType:
        return PluginType.DISCIPLINE_SOLVER

    def get_plugin_name(self) -> str:
        return self._name

    def get_version(self) -> str:
        return "1.0.0"

    def execute(self, params: dict) -> dict:
        return {
            "discipline": self._name,
            "objectives": params.get("objectives", {}),
            "constraints_met": True,
        }

    def validate_config(self, config: dict) -> bool:
        return "design_variables" in config


class RegulatoryLibraryPlugin(IPlugin):
    def __init__(self, regulation_name: str, authority: str):
        self._id = f"REG-{regulation_name}-{uuid.uuid4().hex[:4]}"
        self._name = regulation_name
        self._authority = authority

    def get_plugin_id(self) -> str:
        return self._id

    def get_plugin_type(self) -> PluginType:
        return PluginType.REGULATORY_LIBRARY

    def get_plugin_name(self) -> str:
        return self._name

    def get_version(self) -> str:
        return "1.0.0"

    def execute(self, params: dict) -> dict:
        return {
            "regulation": self._name,
            "authority": self._authority,
            "sections": params.get("sections", []),
        }

    def validate_config(self, config: dict) -> bool:
        return "authority" in config


class DataSourceAdapterPlugin(IPlugin):
    def __init__(self, protocol: str):
        self._id = f"DSA-{protocol}-{uuid.uuid4().hex[:4]}"
        self._protocol = protocol

    def get_plugin_id(self) -> str:
        return self._id

    def get_plugin_type(self) -> PluginType:
        return PluginType.DATA_SOURCE_ADAPTER

    def get_plugin_name(self) -> str:
        return f"{self._protocol} Adapter"

    def get_version(self) -> str:
        return "1.0.0"

    def execute(self, params: dict) -> dict:
        return {
            "protocol": self._protocol,
            "connected": True,
            "data": params.get("sample_data", {}),
        }

    def validate_config(self, config: dict) -> bool:
        return "endpoint" in config


class NDTMethodAdapterPlugin(IPlugin):
    def __init__(self, ndt_method: str):
        self._id = f"NDT-{ndt_method}-{uuid.uuid4().hex[:4]}"
        self._method = ndt_method

    def get_plugin_id(self) -> str:
        return self._id

    def get_plugin_type(self) -> PluginType:
        return PluginType.NDT_METHOD_ADAPTER

    def get_plugin_name(self) -> str:
        return f"{self._method} NDT Adapter"

    def get_version(self) -> str:
        return "1.0.0"

    def execute(self, params: dict) -> dict:
        return {
            "method": self._method,
            "result": params.get("inspection_data", {}),
            "acceptance": "Pass",
        }

    def validate_config(self, config: dict) -> bool:
        return "acceptance_criteria" in config


class PluginRegistryService:

    def __init__(self, repo=None) -> None:
        self._repo = repo
        self._plugins: dict[str, IPlugin] = {}
        self._descriptors: dict[str, PluginDescriptor] = {}

    def registerPlugin(self, plugin: IPlugin) -> PluginDescriptor:
        plugin_id = plugin.get_plugin_id()
        if plugin_id in self._plugins:
            raise ValueError(f"Plugin already registered: {plugin_id}")

        descriptor = PluginDescriptor(
            plugin_id=plugin_id,
            plugin_type=plugin.get_plugin_type(),
            plugin_name=plugin.get_plugin_name(),
            version=plugin.get_version(),
            status=PluginStatus.ACTIVE,
        )

        self._plugins[plugin_id] = plugin
        self._descriptors[plugin_id] = descriptor
        return descriptor

    def unregisterPlugin(self, plugin_id: str) -> bool:
        if plugin_id not in self._plugins:
            return False
        del self._plugins[plugin_id]
        del self._descriptors[plugin_id]
        return True

    def executePlugin(self, plugin_id: str, params: dict) -> PluginExecutionResult:
        import time as _time

        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            return PluginExecutionResult(
                plugin_id=plugin_id,
                success=False,
                error="Plugin not found",
            )

        descriptor = self._descriptors[plugin_id]
        if descriptor.status != PluginStatus.ACTIVE:
            return PluginExecutionResult(
                plugin_id=plugin_id,
                success=False,
                error=f"Plugin not active: {descriptor.status.value}",
            )

        start = _time.monotonic()
        try:
            output = plugin.execute(params)
            elapsed = (_time.monotonic() - start) * 1000.0
            descriptor.execution_count += 1
            return PluginExecutionResult(
                plugin_id=plugin_id,
                success=True,
                output=output,
                duration_ms=elapsed,
            )
        except Exception as exc:
            elapsed = (_time.monotonic() - start) * 1000.0
            descriptor.error_count += 1
            return PluginExecutionResult(
                plugin_id=plugin_id,
                success=False,
                error=str(exc),
                duration_ms=elapsed,
            )

    def enablePlugin(self, plugin_id: str) -> Optional[PluginDescriptor]:
        descriptor = self._descriptors.get(plugin_id)
        if descriptor is None:
            return None
        descriptor.status = PluginStatus.ACTIVE
        return descriptor

    def disablePlugin(self, plugin_id: str) -> Optional[PluginDescriptor]:
        descriptor = self._descriptors.get(plugin_id)
        if descriptor is None:
            return None
        descriptor.status = PluginStatus.DISABLED
        return descriptor

    def getPlugin(self, plugin_id: str) -> Optional[PluginDescriptor]:
        return self._descriptors.get(plugin_id)

    def getPluginsByType(self, plugin_type: PluginType) -> list[PluginDescriptor]:
        return [
            d for d in self._descriptors.values()
            if d.plugin_type == plugin_type
        ]

    def getAllPlugins(self) -> list[PluginDescriptor]:
        return list(self._descriptors.values())

    def validatePluginConfig(
        self, plugin_id: str, config: dict
    ) -> bool:
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            return False
        return plugin.validate_config(config)