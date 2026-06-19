from abc import ABC, abstractmethod
from typing import Any


class ActivityHandler(ABC):

    @abstractmethod
    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        pass

    async def compensate(self, input_data: dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get_handler_name(self) -> str:
        pass


class DesignRuleCheckHandler(ActivityHandler):

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        model_id = input_data.get("model_id", "")
        rule_set_id = input_data.get("rule_set_id", "")
        return {"violations": [], "model_id": model_id, "rule_set_id": rule_set_id, "status": "passed"}

    def get_handler_name(self) -> str:
        return "design.rule_check"


class CFDAnalysisHandler(ActivityHandler):

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        model_id = input_data.get("model_id", "")
        return {"simulation_id": f"cfd-sim-{model_id}", "scalar_results": {}, "status": "completed"}

    async def compensate(self, input_data: dict[str, Any]) -> None:
        pass

    def get_handler_name(self) -> str:
        return "verification.cfd_analysis"


class FEAAnalysisHandler(ActivityHandler):

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        model_id = input_data.get("model_id", "")
        return {"simulation_id": f"fea-sim-{model_id}", "scalar_results": {}, "status": "completed"}

    async def compensate(self, input_data: dict[str, Any]) -> None:
        pass

    def get_handler_name(self) -> str:
        return "verification.fea_analysis"


class MBOMTransformHandler(ActivityHandler):

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        ebom_id = input_data.get("ebom_id", "")
        return {"mbom_id": f"mbom-{ebom_id}", "status": "completed"}

    async def compensate(self, input_data: dict[str, Any]) -> None:
        pass

    def get_handler_name(self) -> str:
        return "manufacturing.mbom_transform"


class WorkOrderGenerateHandler(ActivityHandler):

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        mbom_id = input_data.get("mbom_id", "")
        return {"work_order_ids": [f"wo-{mbom_id}-1"], "status": "completed"}

    async def compensate(self, input_data: dict[str, Any]) -> None:
        pass

    def get_handler_name(self) -> str:
        return "manufacturing.work_order_generate"


class ComplianceCheckHandler(ActivityHandler):

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        matrix_id = input_data.get("compliance_matrix_id", "")
        return {"compliance_result": "passed", "matrix_id": matrix_id}

    def get_handler_name(self) -> str:
        return "certification.compliance_check"


class QualityInspectionHandler(ActivityHandler):

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        work_order_id = input_data.get("work_order_id", "")
        return {"inspection_result": "passed", "work_order_id": work_order_id}

    def get_handler_name(self) -> str:
        return "quality.inspection"


class AeroGPTDesignerHandler(ActivityHandler):

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        requirement_id = input_data.get("requirement_id", "")
        return {"design_proposal": {}, "requirement_id": requirement_id}

    def get_handler_name(self) -> str:
        return "ai.aerogpt_designer"


class AeroGPTEngineerHandler(ActivityHandler):

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        model_id = input_data.get("model_id", "")
        return {"analysis_result": {}, "model_id": model_id}

    def get_handler_name(self) -> str:
        return "ai.aerogpt_engineer"


class ActivityHandlerRegistry:
    _handlers: dict[str, ActivityHandler] = {}

    @classmethod
    def register(cls, handler: ActivityHandler) -> None:
        cls._handlers[handler.get_handler_name()] = handler

    @classmethod
    def get_handler(cls, handler_name: str) -> ActivityHandler | None:
        return cls._handlers.get(handler_name)

    @classmethod
    def get_all_handlers(cls) -> dict[str, ActivityHandler]:
        return cls._handlers.copy()


ActivityHandlerRegistry.register(DesignRuleCheckHandler())
ActivityHandlerRegistry.register(CFDAnalysisHandler())
ActivityHandlerRegistry.register(FEAAnalysisHandler())
ActivityHandlerRegistry.register(MBOMTransformHandler())
ActivityHandlerRegistry.register(WorkOrderGenerateHandler())
ActivityHandlerRegistry.register(ComplianceCheckHandler())
ActivityHandlerRegistry.register(QualityInspectionHandler())
ActivityHandlerRegistry.register(AeroGPTDesignerHandler())
ActivityHandlerRegistry.register(AeroGPTEngineerHandler())