import json
import os
import tempfile
from pathlib import Path

import pytest

from aeroforge_cae_core.openfoam.adapter import (
    JobResult,
    OpenFOAMAdapter,
    SolverProcessInfo,
    SolverStatus,
)
from aeroforge_cae_core.openfoam.case_manager import (
    CaseFileManager,
    DEFAULT_CONTROL_DICT,
    DEFAULT_FV_SCHEMES,
    DEFAULT_FV_SOLUTION,
    DEFAULT_TURBULENCE_PROPERTIES,
)


class TestCaseFileManager:
    def setup_method(self) -> None:
        self.manager = CaseFileManager()
        self.tmpdir = tempfile.mkdtemp()

    def test_create_case_structure(self) -> None:
        case_dir = os.path.join(self.tmpdir, "test_case")
        self.manager.create_case_structure(case_dir)
        assert (Path(case_dir) / "system").is_dir()
        assert (Path(case_dir) / "constant").is_dir()
        assert (Path(case_dir) / "0").is_dir()

    def test_write_control_dict(self) -> None:
        case_dir = os.path.join(self.tmpdir, "test_case")
        self.manager.create_case_structure(case_dir)
        self.manager.write_control_dict(case_dir, {"endTime": 2000})
        content = (Path(case_dir) / "system" / "controlDict").read_text()
        assert "endTime" in content
        assert "2000" in content

    def test_write_fv_schemes(self) -> None:
        case_dir = os.path.join(self.tmpdir, "test_case")
        self.manager.create_case_structure(case_dir)
        self.manager.write_fv_schemes(case_dir)
        content = (Path(case_dir) / "system" / "fvSchemes").read_text()
        assert "ddtSchemes" in content
        assert "steadyState" in content

    def test_write_fv_solution(self) -> None:
        case_dir = os.path.join(self.tmpdir, "test_case")
        self.manager.create_case_structure(case_dir)
        self.manager.write_fv_solution(case_dir)
        content = (Path(case_dir) / "system" / "fvSolution").read_text()
        assert "solvers" in content
        assert "GAMG" in content

    def test_write_turbulence_properties(self) -> None:
        case_dir = os.path.join(self.tmpdir, "test_case")
        self.manager.create_case_structure(case_dir)
        self.manager.write_turbulence_properties(case_dir)
        content = (Path(case_dir) / "constant" / "turbulenceProperties").read_text()
        assert "kOmegaSST" in content

    def test_write_boundary_conditions(self) -> None:
        case_dir = os.path.join(self.tmpdir, "test_case")
        self.manager.create_case_structure(case_dir)
        bc = {"type": "fixedValue", "value": "uniform (0 0 0)"}
        self.manager.write_boundary_conditions(case_dir, "0", "U", bc)
        assert (Path(case_dir) / "0" / "U").exists()

    def test_default_control_dict_values(self) -> None:
        assert DEFAULT_CONTROL_DICT["application"] == "simpleFoam"
        assert DEFAULT_CONTROL_DICT["startTime"] == 0
        assert DEFAULT_CONTROL_DICT["deltaT"] == 1

    def test_default_fv_schemes_values(self) -> None:
        assert DEFAULT_FV_SCHEMES["ddtSchemes"]["default"] == "steadyState"

    def test_default_fv_solution_values(self) -> None:
        assert "SIMPLE" in DEFAULT_FV_SOLUTION
        assert "relaxationFactors" in DEFAULT_FV_SOLUTION

    def test_default_turbulence_properties_values(self) -> None:
        assert DEFAULT_TURBULENCE_PROPERTIES["simulationType"] == "RAS"
        assert DEFAULT_TURBULENCE_PROPERTIES["RAS"]["model"] == "kOmegaSST"

    def test_serialize_openfoam_dict(self) -> None:
        data = {"key1": "value1", "key2": 42, "key3": True}
        result = self.manager._serialize_openfoam_dict(data)
        assert "key1    value1;" in result
        assert "key2    42;" in result
        assert "key3    true;" in result

    def test_serialize_nested_dict(self) -> None:
        data = {"outer": {"inner": "val"}}
        result = self.manager._serialize_openfoam_dict(data)
        assert "outer" in result
        assert "inner    val;" in result

    def test_parse_openfoam_dict(self) -> None:
        content = "key1    value1;\nkey2    42;\nkey3    true;"
        result = self.manager._parse_openfoam_dict(content)
        assert result["key1"] == "value1"
        assert result["key2"] == 42
        assert result["key3"] is True

    def test_try_parse_value_int(self) -> None:
        assert CaseFileManager._try_parse_value("42") == 42

    def test_try_parse_value_float(self) -> None:
        assert CaseFileManager._try_parse_value("3.14") == pytest.approx(3.14)

    def test_try_parse_value_bool(self) -> None:
        assert CaseFileManager._try_parse_value("true") is True
        assert CaseFileManager._try_parse_value("false") is False

    def test_try_parse_value_string(self) -> None:
        assert CaseFileManager._try_parse_value("hello") == "hello"

    def test_try_parse_value_list(self) -> None:
        result = CaseFileManager._try_parse_value("(1 2 3)")
        assert result == [1, 2, 3]

    def test_read_case_dict_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            self.manager.read_case_dict(self.tmpdir, "nonexistent/file")


class TestOpenFOAMAdapter:
    def setup_method(self) -> None:
        self.adapter = OpenFOAMAdapter(
            openfoam_dir="/opt/openfoam",
            working_dir=tempfile.mkdtemp(),
        )

    def test_init(self) -> None:
        assert self.adapter._n_proc == 1
        assert self.adapter.case_manager is not None

    def test_solver_status_enum(self) -> None:
        assert SolverStatus.IDLE == "idle"
        assert SolverStatus.RUNNING == "running"
        assert SolverStatus.COMPLETED == "completed"
        assert SolverStatus.FAILED == "failed"
        assert SolverStatus.CANCELLED == "cancelled"

    def test_solver_process_info_defaults(self) -> None:
        info = SolverProcessInfo()
        assert info.pid is None
        assert info.status == SolverStatus.IDLE
        assert info.cpu_percent == 0.0
        assert info.memory_mb == 0.0

    def test_job_result_defaults(self) -> None:
        result = JobResult(job_id="test", case_dir="/tmp", status=SolverStatus.IDLE)
        assert result.residuals == []
        assert result.force_coefficients == {}
        assert result.convergence_data == {}
        assert result.error_message is None

    def test_write_case_files(self) -> None:
        case_dir = tempfile.mkdtemp()
        self.adapter.write_case_files(
            case_dir,
            control_dict={"endTime": 500},
            fv_schemes={"ddtSchemes": {"default": "steadyState"}},
            fv_solution={"SIMPLE": {"nNonOrthogonalCorrectors": 0}},
            turbulence_properties={"RAS": {"model": "kOmegaSST"}},
        )
        assert (Path(case_dir) / "system" / "controlDict").exists()
        assert (Path(case_dir) / "system" / "fvSchemes").exists()
        assert (Path(case_dir) / "system" / "fvSolution").exists()
        assert (Path(case_dir) / "constant" / "turbulenceProperties").exists()

    def test_parse_results_empty(self) -> None:
        case_dir = tempfile.mkdtemp()
        result = self.adapter.parse_results(case_dir)
        assert result["residuals"] == []
        assert result["force_coefficients"] == {}

    def test_parse_results_with_residuals(self) -> None:
        case_dir = tempfile.mkdtemp()
        residuals_dir = Path(case_dir) / "postProcessing" / "residuals" / "100"
        residuals_dir.mkdir(parents=True)
        (residuals_dir / "residuals.dat").write_text("# Time\n0.001 0.01 0.02\n0.002 0.005 0.01\n")
        result = self.adapter.parse_results(case_dir)
        assert len(result["residuals"]) == 2
        assert result["residuals"][0]["values"] == [pytest.approx(0.001), pytest.approx(0.01), pytest.approx(0.02)]

    def test_parse_results_with_forces(self) -> None:
        case_dir = tempfile.mkdtemp()
        forces_dir = Path(case_dir) / "postProcessing" / "forces" / "100"
        forces_dir.mkdir(parents=True)
        (forces_dir / "coefficient.dat").write_text("0.5\n0.6\n0.7\n")
        result = self.adapter.parse_results(case_dir)
        assert "coefficient" in result["force_coefficients"]
        assert result["force_coefficients"]["coefficient"] == [pytest.approx(0.5), pytest.approx(0.6), pytest.approx(0.7)]

    def test_get_status_not_found(self) -> None:
        import asyncio
        with pytest.raises(ValueError, match="Job not found"):
            asyncio.get_event_loop().run_until_complete(self.adapter.get_status("nonexistent"))

    def test_stop_solver_not_found(self) -> None:
        import asyncio
        with pytest.raises(ValueError, match="Job not found"):
            asyncio.get_event_loop().run_until_complete(self.adapter.stop_solver("nonexistent"))

    def test_build_env(self) -> None:
        env = self.adapter._build_env()
        assert "FOAM_INSTALL_DIR" in env or "WM_PROJECT_DIR" not in env