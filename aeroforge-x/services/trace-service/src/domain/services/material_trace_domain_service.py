from __future__ import annotations

from typing import Any

from ..infrastructure.neo4j.trace_graph_repository import TraceGraphRepository


class MaterialTraceDomainService:
    def __init__(self, graph_repo: TraceGraphRepository) -> None:
        self._graph_repo = graph_repo

    async def record_trace(
        self,
        supplier_code: str,
        supplier_name: str,
        batch_number: str,
        item_code: str,
        serial_number: str,
        inspection_result: str,
        work_order_code: str | None = None,
        aircraft_code: str | None = None,
        installer: str | None = None,
    ) -> None:
        await self._graph_repo.add_trace_link(
            "Supplier", {"code": supplier_code, "name": supplier_name},
            "SUPPLIED", "Batch", {"code": batch_number, "batchNumber": batch_number, "supplierCode": supplier_code},
        )
        await self._graph_repo.add_trace_link(
            "Batch", {"code": batch_number, "batchNumber": batch_number},
            "PRODUCED", "Part", {"code": item_code, "serialNumber": serial_number, "itemCode": item_code},
        )
        if inspection_result:
            await self._graph_repo.add_trace_link(
                "Part", {"code": item_code, "serialNumber": serial_number},
                "INSPECTED", "Inspection", {"code": f"INS-{serial_number}", "result": inspection_result},
            )
        if work_order_code:
            await self._graph_repo.add_trace_link(
                "Part", {"code": item_code, "serialNumber": serial_number},
                "USED_IN", "WorkOrder", {"code": work_order_code, "orderCode": work_order_code},
            )
        if aircraft_code and installer:
            await self._graph_repo.add_trace_link(
                "Part", {"code": item_code, "serialNumber": serial_number},
                "INSTALLED_IN", "Aircraft", {"code": aircraft_code, "aircraftCode": aircraft_code, "installer": installer},
            )

    async def query_trace_chain(self, serial_number: str) -> dict[str, Any]:
        paths = await self._graph_repo.find_trace_path(serial_number)
        if not paths:
            return {"serial_number": serial_number, "trace_chain": [], "status": "not_found"}
        return {"serial_number": serial_number, "trace_chain": paths, "status": "found"}

    async def batch_forward_trace(self, batch_number: str) -> dict[str, Any]:
        targets = await self._graph_repo.find_batch_forward_trace(batch_number)
        return {"batch_number": batch_number, "affected_items": targets, "direction": "forward"}

    async def batch_reverse_trace(self, aircraft_code: str) -> dict[str, Any]:
        paths = await self._graph_repo.find_batch_reverse_trace(aircraft_code)
        return {"aircraft_code": aircraft_code, "supplier_chains": paths, "direction": "reverse"}

    async def check_trace_integrity(self, serial_number: str) -> dict[str, Any]:
        broken = await self._graph_repo.detect_broken_links(serial_number)
        return {"serial_number": serial_number, "intact": len(broken) == 0, "broken_links": broken}