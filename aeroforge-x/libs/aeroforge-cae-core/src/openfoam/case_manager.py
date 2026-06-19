from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CONTROL_DICT: dict[str, Any] = {
    "application": "simpleFoam",
    "startFrom": "startTime",
    "startTime": 0,
    "stopAt": "endTime",
    "endTime": 1000,
    "deltaT": 1,
    "writeControl": "timeStep",
    "writeInterval": 100,
    "purgeWrite": 0,
    "writeFormat": "ascii",
    "writePrecision": 6,
    "writeCompression": "off",
    "timeFormat": "general",
    "timePrecision": 6,
    "runTimeModifiable": True,
}

DEFAULT_FV_SCHEMES: dict[str, Any] = {
    "ddtSchemes": {"default": "steadyState"},
    "gradSchemes": {"default": "Gauss linear"},
    "divSchemes": {
        "default": "none",
        "div(phi,U)": "bounded Gauss upwind",
        "div(phi,k)": "bounded Gauss upwind",
        "div(phi,omega)": "bounded Gauss upwind",
        "div((nuEff*dev2(T(grad(U)))))": "Gauss linear",
    },
    "laplacianSchemes": {"default": "Gauss linear corrected"},
    "interpolationSchemes": {"default": "linear"},
    "snGradSchemes": {"default": "corrected"},
}

DEFAULT_FV_SOLUTION: dict[str, Any] = {
    "solvers": {
        "p": {
            "solver": "GAMG",
            "tolerance": 1e-06,
            "relTol": 0.01,
            "smoother": "GaussSeidel",
            "nPreSweeps": 0,
            "nPostSweeps": 2,
            "cacheAgglomeration": True,
            "nCellsInCoarsestLevel": 10,
            "agglomerator": "faceAreaPair",
            "mergeLevels": 1,
            "maxIter": 100,
        },
        "U": {
            "solver": "smoothSolver",
            "smoother": "GaussSeidel",
            "tolerance": 1e-05,
            "relTol": 0.1,
            "nSweeps": 1,
            "maxIter": 100,
        },
        "k": {
            "solver": "smoothSolver",
            "smoother": "GaussSeidel",
            "tolerance": 1e-05,
            "relTol": 0.1,
            "maxIter": 100,
        },
        "omega": {
            "solver": "smoothSolver",
            "smoother": "GaussSeidel",
            "tolerance": 1e-05,
            "relTol": 0.1,
            "maxIter": 100,
        },
    },
    "SIMPLE": {
        "nNonOrthogonalCorrectors": 0,
        "consistent": True,
        "residualControl": {
            "p": 1e-05,
            "U": 1e-05,
            "k": 1e-05,
            "omega": 1e-05,
        },
    },
    "relaxationFactors": {
        "equations": {"U": 0.7, "k": 0.7, "omega": 0.7},
        "fields": {"p": 0.3},
    },
}

DEFAULT_TURBULENCE_PROPERTIES: dict[str, Any] = {
    "simulationType": "RAS",
    "RAS": {
        "model": "kOmegaSST",
        "turbulence": True,
        "printCoeffs": True,
    },
}


class CaseFileManager:
    def create_case_structure(self, case_dir: str) -> None:
        path = Path(case_dir)
        for subdir in ("system", "constant", "0"):
            (path / subdir).mkdir(parents=True, exist_ok=True)
        logger.info("Created OpenFOAM case structure at %s", case_dir)

    def write_control_dict(self, case_dir: str, params: dict[str, Any] | None = None) -> None:
        data = {**DEFAULT_CONTROL_DICT, **(params or {})}
        self._write_openfoam_dict(case_dir, "system/controlDict", data)

    def write_fv_schemes(self, case_dir: str, params: dict[str, Any] | None = None) -> None:
        data = {**DEFAULT_FV_SCHEMES, **(params or {})}
        self._write_openfoam_dict(case_dir, "system/fvSchemes", data)

    def write_fv_solution(self, case_dir: str, params: dict[str, Any] | None = None) -> None:
        data = {**DEFAULT_FV_SOLUTION, **(params or {})}
        self._write_openfoam_dict(case_dir, "system/fvSolution", data)

    def write_turbulence_properties(self, case_dir: str, params: dict[str, Any] | None = None) -> None:
        data = {**DEFAULT_TURBULENCE_PROPERTIES, **(params or {})}
        self._write_openfoam_dict(case_dir, "constant/turbulenceProperties", data)

    def write_boundary_conditions(
        self,
        case_dir: str,
        time_dir: str,
        field_name: str,
        boundary_config: dict[str, Any],
    ) -> None:
        path = Path(case_dir) / time_dir / field_name
        path.parent.mkdir(parents=True, exist_ok=True)
        self._write_openfoam_dict(case_dir, f"{time_dir}/{field_name}", boundary_config)

    def read_case_dict(self, case_dir: str, relative_path: str) -> dict[str, Any]:
        file_path = Path(case_dir) / relative_path
        if not file_path.exists():
            raise FileNotFoundError(f"Case file not found: {file_path}")
        content = file_path.read_text()
        return self._parse_openfoam_dict(content)

    def _write_openfoam_dict(self, case_dir: str, relative_path: str, data: dict[str, Any]) -> None:
        file_path = Path(case_dir) / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        content = self._serialize_openfoam_dict(data)
        file_path.write_text(content)
        logger.debug("Wrote OpenFOAM dict to %s", file_path)

    def _serialize_openfoam_dict(self, data: dict[str, Any], indent: int = 0) -> str:
        lines: list[str] = []
        pad = "    " * indent
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{pad}{key}")
                lines.append(f"{pad}{{")
                lines.append(self._serialize_openfoam_dict(value, indent + 1))
                lines.append(f"{pad}}}")
            elif isinstance(value, list):
                str_items = " ".join(str(v) for v in value)
                lines.append(f"{pad}{key}    ({str_items});")
            elif isinstance(value, bool):
                lines.append(f"{pad}{key}    {str(value).lower()};")
            elif isinstance(value, (int, float)):
                lines.append(f"{pad}{key}    {value};")
            elif isinstance(value, str):
                lines.append(f"{pad}{key}    {value};")
        return "\n".join(lines)

    def _parse_openfoam_dict(self, content: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        lines = content.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith("//") or line.startswith("/*"):
                i += 1
                continue
            if line.endswith("{"):
                key = line[:-1].strip()
                depth = 1
                start = i + 1
                i += 1
                while i < len(lines) and depth > 0:
                    ch = lines[i].strip()
                    if ch.endswith("{"):
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                    i += 1
                inner = "\n".join(lines[start : i - 1])
                result[key] = self._parse_openfoam_dict(inner)
                continue
            if ";" in line:
                parts = line.rsplit(";", 1)[0].split(None, 1)
                if len(parts) == 2:
                    key, val = parts[0].strip(), parts[1].strip()
                    result[key] = self._try_parse_value(val)
            i += 1
        return result

    @staticmethod
    def _try_parse_value(value: str) -> Any:
        if value.startswith("(") and value.endswith(")"):
            items = value[1:-1].split()
            return [CaseFileManager._try_parse_value(v) for v in items]
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        return value