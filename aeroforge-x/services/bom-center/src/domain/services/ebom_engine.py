from __future__ import annotations

from typing import Any

from ..entities.bom_item import BOMItem, EBOM


class EBOMEngine:
    def generate_from_model(self, spec_id: str, model_data: dict[str, Any]) -> EBOM:
        ebom = EBOM(spec_id=spec_id)
        assembly = model_data.get("assembly", model_data)
        components = assembly.get("components", {})

        aircraft_item = BOMItem(
            item_code=self._generate_item_code("aircraft"),
            name="飞行器总装",
            bom_type="ebom",
            quantity=1,
            part_type="assembly",
        )

        if "fuselage" in components:
            fuselage = components["fuselage"]
            fuselage_item = BOMItem(
                item_code=self._generate_item_code("fuselage"),
                name="机身组件",
                bom_type="ebom",
                quantity=1,
                part_type="assembly",
                attributes=fuselage.get("parameters", {}),
            )
            self._add_sub_parts(fuselage_item, "fuselage", fuselage.get("parameters", {}))
            aircraft_item.add_child(fuselage_item)

        if "wing" in components:
            wing = components["wing"]
            wing_item = BOMItem(
                item_code=self._generate_item_code("wing"),
                name="机翼组件",
                bom_type="ebom",
                quantity=1,
                part_type="assembly",
                attributes=wing.get("parameters", {}),
            )
            self._add_sub_parts(wing_item, "wing", wing.get("parameters", {}))
            aircraft_item.add_child(wing_item)

        if "tail" in components:
            tail = components["tail"]
            tail_item = BOMItem(
                item_code=self._generate_item_code("tail"),
                name="尾翼组件",
                bom_type="ebom",
                quantity=1,
                part_type="assembly",
                attributes=tail.get("parameters", {}),
            )
            self._add_sub_parts(tail_item, "tail", tail.get("parameters", {}))
            aircraft_item.add_child(tail_item)

        ebom.set_root(aircraft_item)
        return ebom

    def _add_sub_parts(self, parent: BOMItem, component_type: str, params: dict[str, Any]) -> None:
        sub_parts = self._get_sub_parts_for_type(component_type, params)
        for sub in sub_parts:
            parent.add_child(sub)

    def _get_sub_parts_for_type(self, component_type: str, params: dict[str, Any]) -> list[BOMItem]:
        parts: list[BOMItem] = []
        if component_type == "wing":
            parts.append(BOMItem(item_code=self._generate_item_code("spar"), name="翼梁", part_type="structural", attributes={"material": "CFRP"}))
            parts.append(BOMItem(item_code=self._generate_item_code("rib"), name="肋板", part_type="structural", quantity=max(2, int(params.get("wingspan_m", 15) / 1.5)), attributes={"material": "CFRP"}))
            parts.append(BOMItem(item_code=self._generate_item_code("skin-wing"), name="机翼蒙皮", part_type="skin", attributes={"material": "CFRP prepreg"}))
        elif component_type == "fuselage":
            parts.append(BOMItem(item_code=self._generate_item_code("frame"), name="加强框", part_type="structural", quantity=4))
            parts.append(BOMItem(item_code=self._generate_item_code("skin-fuse"), name="机身蒙皮", part_type="skin", attributes={"material": "CFRP prepreg"}))
        elif component_type == "tail":
            parts.append(BOMItem(item_code=self._generate_item_code("h-spar"), name="水平尾翼梁", part_type="structural"))
            parts.append(BOMItem(item_code=self._generate_item_code("v-spar"), name="垂直尾翼梁", part_type="structural"))
        return parts

    def _generate_item_code(self, part_type: str) -> str:
        return generate_code(f"AAF-{part_type.upper()[:4]}")