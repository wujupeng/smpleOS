from __future__ import annotations

import logging
from typing import Any

from src.domain.plugins.aerodynamic_database import (
    AerodynamicDatabase,
    AeroCoefficients,
    FourDimLookupTable,
    HotReloadResult,
    IntegrityCheck,
    LoadResult,
    SwitchResult,
)
from src.domain.plugins.aero_data_import.adapter_interface import (
    AeroDataImportAdapter,
    ConstraintCheck,
    RawAeroData,
)
from src.domain.plugins.aero_data_import.avl_adapter import AVLAdapter
from src.domain.plugins.aero_data_import.openfoam_adapter import OpenFOAMAdapter
from src.domain.plugins.aero_data_import.openvsp_adapter import OpenVSPAdapter

logger = logging.getLogger(__name__)


class AerodynamicDatabaseService:

    def __init__(self) -> None:
        self._aero_db = AerodynamicDatabase(
            database_id="ADB-Service",
            database_name="AerodynamicDatabaseService",
        )
        self._adapters: dict[str, AeroDataImportAdapter] = {
            "OpenVSP": OpenVSPAdapter(),
            "AVL": AVLAdapter(),
            "OpenFOAM": OpenFOAMAdapter(),
        }
        self._import_logs: list[dict[str, Any]] = []

    def load_database(
        self,
        database_id: str,
        database_name: str,
        alpha_range: tuple[float, float],
        alpha_resolution: float,
        beta_range: tuple[float, float],
        beta_resolution: float,
        mach_range: tuple[float, float],
        mach_resolution: float,
        reynolds_range: tuple[float, float],
        reynolds_resolution: float,
        coefficient_data: dict[str, Any] | None = None,
        coefficient_types: list[str] | None = None,
        data_source: str = "internal",
        quality_status: str = "draft",
        applicable_config: str = "",
        partial_coverage_dimensions: list[str] | None = None,
    ) -> LoadResult:
        result = self._aero_db.load_database(
            database_id=database_id,
            database_name=database_name,
            alpha_range=alpha_range,
            alpha_resolution=alpha_resolution,
            beta_range=beta_range,
            beta_resolution=beta_resolution,
            mach_range=mach_range,
            mach_resolution=mach_resolution,
            reynolds_range=reynolds_range,
            reynolds_resolution=reynolds_resolution,
            coefficient_data=coefficient_data,
            coefficient_types=coefficient_types,
            data_source=data_source,
            quality_status=quality_status,
            applicable_config=applicable_config,
            partial_coverage_dimensions=partial_coverage_dimensions,
        )
        if result.success:
            logger.info("Database loaded: %s (%s)", database_id, database_name)
        else:
            logger.error("Database load failed: %s — %s", database_id, result.message)
        return result

    def load_database_from_table(self, table: FourDimLookupTable) -> LoadResult:
        return self._aero_db.load_database_from_table(table)

    def switch_database(self, database_id: str) -> SwitchResult:
        result = self._aero_db.switch_database(database_id)
        if result.success:
            logger.info("Switched database: %s -> %s", result.previous_database_id, database_id)
        else:
            logger.warning("Database switch failed: %s", result.message)
        return result

    def hot_reload_database(
        self, database_id: str, new_table: FourDimLookupTable
    ) -> HotReloadResult:
        result = self._aero_db.hot_reload_database(database_id, new_table)
        if result.success:
            logger.info("Hot-reloaded database: %s", database_id)
        else:
            logger.error("Hot-reload failed: %s — %s", database_id, result.message)
        return result

    def query_coefficients(
        self, alpha: float, beta: float, mach: float, reynolds: float
    ) -> AeroCoefficients:
        return self._aero_db.query_coefficients(alpha, beta, mach, reynolds)

    def get_database_metadata(self, database_id: str) -> dict[str, Any] | None:
        if database_id not in self._aero_db.loaded_databases:
            return None
        return self._aero_db.loaded_databases[database_id].metadata

    def list_databases(self) -> list[dict[str, Any]]:
        result = []
        for db_id, table in self._aero_db.loaded_databases.items():
            meta = table.metadata
            meta["is_active"] = db_id == self._aero_db.active_database_id
            result.append(meta)
        return result

    def validate_data_integrity(self, database_id: str) -> IntegrityCheck:
        return self._aero_db.validate_data_integrity(database_id)

    def import_external_data(
        self, format_name: str, file_path: str, config: dict[str, Any] | None = None
    ) -> LoadResult:
        adapter = self._adapters.get(format_name)
        if adapter is None:
            available = list(self._adapters.keys())
            return LoadResult(
                success=False,
                database_id="",
                message=f"Unknown format '{format_name}'. Available: {available}",
            )

        try:
            raw_data = adapter.parse(file_path)
        except Exception as e:
            logger.error("Parse error for %s: %s", file_path, str(e))
            return LoadResult(
                success=False,
                database_id="",
                message=f"Parse error: {str(e)}",
            )

        constraint_check = adapter.validate_physical_constraints(raw_data)
        if not constraint_check.is_valid:
            violations = "; ".join(constraint_check.violations)
            logger.error("Constraint violations: %s", violations)
            return LoadResult(
                success=False,
                database_id="",
                message=f"Physical constraint violations: {violations}",
            )

        if constraint_check.warnings:
            for w in constraint_check.warnings:
                logger.warning("Import warning: %s", w)

        try:
            table = adapter.convert_to_internal(raw_data)
        except Exception as e:
            logger.error("Conversion error: %s", str(e))
            return LoadResult(
                success=False,
                database_id="",
                message=f"Conversion error: {str(e)}",
            )

        result = self._aero_db.load_database_from_table(table)

        self._import_logs.append({
            "format": format_name,
            "file_path": file_path,
            "database_id": table.database_id,
            "success": result.success,
            "constraint_check": {
                "is_valid": constraint_check.is_valid,
                "warnings": constraint_check.warnings,
            },
        })

        return result

    def merge_databases(
        self, source_ids: list[str], priority: str = "high_fidelity"
    ) -> LoadResult:
        if len(source_ids) < 2:
            return LoadResult(
                success=False,
                database_id="",
                message="At least 2 source databases required for merge",
            )

        sources = []
        for sid in source_ids:
            if sid not in self._aero_db.loaded_databases:
                return LoadResult(
                    success=False,
                    database_id="",
                    message=f"Source database '{sid}' not found",
                )
            sources.append(self._aero_db.loaded_databases[sid])

        primary = sources[0]
        alpha_min = min(t.alpha_range[0] for t in sources)
        alpha_max = max(t.alpha_range[1] for t in sources)
        beta_min = min(t.beta_range[0] for t in sources)
        beta_max = max(t.beta_range[1] for t in sources)
        mach_min = min(t.mach_range[0] for t in sources)
        mach_max = max(t.mach_range[1] for t in sources)
        re_min = min(t.reynolds_range[0] for t in sources)
        re_max = max(t.reynolds_range[1] for t in sources)

        alpha_res = min(t.alpha_resolution for t in sources)
        beta_res = min(t.beta_resolution for t in sources)
        mach_res = min(t.mach_resolution for t in sources)
        re_res = min(t.reynolds_resolution for t in sources)

        all_coeff_types = list(dict.fromkeys(
            ct for t in sources for ct in t.coefficient_types
        ))

        merged_id = "ADB-Merged-" + "-".join(source_ids)
        merged_name = f"Merged ({', '.join(source_ids)})"

        merged_table = FourDimLookupTable(
            database_id=merged_id,
            database_name=merged_name,
            alpha_range=(alpha_min, alpha_max),
            alpha_resolution=alpha_res,
            beta_range=(beta_min, beta_max),
            beta_resolution=beta_res,
            mach_range=(mach_min, mach_max),
            mach_resolution=mach_res,
            reynolds_range=(re_min, re_max),
            reynolds_resolution=re_res,
            coefficient_types=all_coeff_types,
            data_source="merged",
            quality_status="draft",
            applicable_config=primary.applicable_config,
        )

        for coeff_type in all_coeff_types:
            merged_data = merged_table._data[coeff_type].copy()
            source_order = sources if priority == "high_fidelity" else list(reversed(sources))

            for src in source_order:
                if coeff_type not in src._data:
                    continue
                src_data = src._data[coeff_type]
                for i_a, alpha_val in enumerate(merged_table._alpha_axis):
                    if alpha_val < src.alpha_range[0] or alpha_val > src.alpha_range[1]:
                        continue
                    for i_b, beta_val in enumerate(merged_table._beta_axis):
                        if beta_val < src.beta_range[0] or beta_val > src.beta_range[1]:
                            continue
                        for i_m, mach_val in enumerate(merged_table._mach_axis):
                            if mach_val < src.mach_range[0] or mach_val > src.mach_range[1]:
                                continue
                            for i_r, re_val in enumerate(merged_table._reynolds_axis):
                                if re_val < src.reynolds_range[0] or re_val > src.reynolds_range[1]:
                                    continue
                                val = src.query_all(alpha_val, beta_val, mach_val, re_val)
                                coeff_map = {
                                    "CL": val.CL, "CD": val.CD, "CM": val.CM,
                                    "CY": val.CY, "Cl": val.Cl, "Cn": val.Cn,
                                }
                                if coeff_type in coeff_map:
                                    merged_data[i_a, i_b, i_m, i_r] = coeff_map[coeff_type]

            merged_table.set_coefficient_data(coeff_type, merged_data)

        return self._aero_db.load_database_from_table(merged_table)

    def get_import_logs(self) -> list[dict[str, Any]]:
        return list(self._import_logs)

    @property
    def aero_database(self) -> AerodynamicDatabase:
        return self._aero_db