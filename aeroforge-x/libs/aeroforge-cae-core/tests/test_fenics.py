import pytest

from aeroforge_cae_core.fenics.adapter import FEniCSAdapter, FEniCSJobResult, FEniCSStatus
from aeroforge_cae_core.fenics.mesh_converter import MeshConverter, MeshFormat, MeshConversionResult
from aeroforge_cae_core.fenics.problem_builder import (
    BoundaryConditionType,
    ProblemBuilder,
    ProblemDefinition,
    ProblemType,
)
from aeroforge_cae_core.fenics.result_extractor import FieldData, ResultExtractor


class TestFEniCSAdapter:
    def setup_method(self) -> None:
        self.adapter = FEniCSAdapter()

    def test_init(self) -> None:
        assert self.adapter._working_dir is not None

    @pytest.mark.asyncio
    async def test_solve_creates_job(self) -> None:
        job_id = await self.adapter.solve({"problem_type": "linear_elasticity"})
        assert job_id is not None
        assert len(job_id) > 0

    @pytest.mark.asyncio
    async def test_get_status(self) -> None:
        job_id = await self.adapter.solve({"problem_type": "thermal"})
        status = await self.adapter.get_status(job_id)
        assert status == FEniCSStatus.PREPARING

    @pytest.mark.asyncio
    async def test_get_status_not_found(self) -> None:
        with pytest.raises(ValueError, match="Job not found"):
            await self.adapter.get_status("nonexistent")

    @pytest.mark.asyncio
    async def test_get_result(self) -> None:
        job_id = await self.adapter.solve({"problem_type": "modal"})
        result = await self.adapter.get_result(job_id)
        assert isinstance(result, FEniCSJobResult)
        assert result.job_id == job_id

    @pytest.mark.asyncio
    async def test_get_result_not_found(self) -> None:
        with pytest.raises(ValueError, match="Job not found"):
            await self.adapter.get_result("nonexistent")

    @pytest.mark.asyncio
    async def test_cancel(self) -> None:
        job_id = await self.adapter.solve({"problem_type": "buckling"})
        await self.adapter.cancel(job_id)
        status = await self.adapter.get_status(job_id)
        assert status == FEniCSStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_completed_fails(self) -> None:
        job_id = await self.adapter.solve({"problem_type": "thermal"})
        await self.adapter.cancel(job_id)
        with pytest.raises(ValueError, match="Cannot cancel"):
            await self.adapter.cancel(job_id)

    @pytest.mark.asyncio
    async def test_list_jobs(self) -> None:
        j1 = await self.adapter.solve({"problem_type": "thermal"})
        j2 = await self.adapter.solve({"problem_type": "modal"})
        jobs = await self.adapter.list_jobs()
        assert j1 in jobs
        assert j2 in jobs

    def test_fenics_status_enum(self) -> None:
        assert FEniCSStatus.IDLE == "idle"
        assert FEniCSStatus.SOLVING == "solving"
        assert FEniCSStatus.COMPLETED == "completed"
        assert FEniCSStatus.FAILED == "failed"

    def test_fenics_job_result_defaults(self) -> None:
        result = FEniCSJobResult(job_id="test", status=FEniCSStatus.IDLE, problem_type="thermal")
        assert result.results == {}
        assert result.error_message is None
        assert result.solve_time_seconds == 0.0
        assert result.dof_count == 0


class TestMeshConverter:
    def setup_method(self) -> None:
        self.converter = MeshConverter()

    def test_supported_conversions(self) -> None:
        assert "stl" in MeshConverter.SUPPORTED_CONVERSIONS["step"]
        assert "xdmf" in MeshConverter.SUPPORTED_CONVERSIONS["msh"]

    def test_detect_format_step(self) -> None:
        from pathlib import Path
        result = self.converter._detect_format(Path("model.step"))
        assert result == MeshFormat.STEP

    def test_detect_format_stl(self) -> None:
        from pathlib import Path
        result = self.converter._detect_format(Path("model.stl"))
        assert result == MeshFormat.STL

    def test_detect_format_msh(self) -> None:
        from pathlib import Path
        result = self.converter._detect_format(Path("model.msh"))
        assert result == MeshFormat.GMSH

    def test_detect_format_unknown(self) -> None:
        from pathlib import Path
        result = self.converter._detect_format(Path("model.xyz"))
        assert result is None

    def test_convert_unsupported(self) -> None:
        import tempfile
        tmpdir = tempfile.mkdtemp()
        from pathlib import Path
        step_file = Path(tmpdir) / "model.step"
        step_file.write_text("dummy")
        with pytest.raises(ValueError, match="not supported"):
            self.converter.convert(str(step_file), MeshFormat.VTK)

    def test_convert_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            self.converter.convert("/nonexistent/model.step", MeshFormat.STL)

    def test_get_supported_output_formats(self) -> None:
        formats = self.converter.get_supported_output_formats(MeshFormat.STEP)
        assert "stl" in formats
        assert "msh" in formats
        assert "xdmf" in formats

    def test_estimate_conversion_resources(self) -> None:
        import tempfile
        tmpdir = tempfile.mkdtemp()
        from pathlib import Path
        step_file = Path(tmpdir) / "model.step"
        step_file.write_text("x" * 1024)
        result = self.converter.estimate_conversion_resources(str(step_file), MeshFormat.STL)
        assert "input_file_size_mb" in result
        assert "estimated_memory_mb" in result
        assert "estimated_time_seconds" in result


class TestProblemBuilder:
    def test_build_linear_elasticity(self) -> None:
        problem = (
            ProblemBuilder()
            .set_problem_type(ProblemType.LINEAR_ELASTICITY)
            .set_mesh("/tmp/mesh.xdmf")
            .add_material("steel", {"E": 200e9, "nu": 0.3})
            .add_boundary_condition("fixed", BoundaryConditionType.DIRICHLET, "bottom", {"u": 0.0})
            .add_load("pressure", "pressure", "top", {"magnitude": 1e6})
            .build()
        )
        assert problem.problem_type == ProblemType.LINEAR_ELASTICITY
        assert len(problem.materials) == 1
        assert len(problem.boundary_conditions) == 1
        assert len(problem.loads) == 1
        assert "displacement" in problem.output_fields
        assert "stress" in problem.output_fields

    def test_build_thermal(self) -> None:
        problem = (
            ProblemBuilder()
            .set_problem_type(ProblemType.THERMAL)
            .set_mesh("/tmp/mesh.xdmf")
            .build()
        )
        assert "temperature" in problem.output_fields
        assert "heat_flux" in problem.output_fields

    def test_build_missing_problem_type(self) -> None:
        with pytest.raises(ValueError, match="Problem type must be set"):
            ProblemBuilder().set_mesh("/tmp/mesh.xdmf").build()

    def test_build_missing_mesh(self) -> None:
        with pytest.raises(ValueError, match="Mesh path must be set"):
            ProblemBuilder().set_problem_type(ProblemType.MODAL).build()

    def test_builder_resets_after_build(self) -> None:
        builder = ProblemBuilder()
        builder.set_problem_type(ProblemType.LINEAR_ELASTICITY).set_mesh("/tmp/mesh.xdmf").build()
        with pytest.raises(ValueError, match="Problem type must be set"):
            builder.build()

    def test_default_output_fields_modal(self) -> None:
        problem = (
            ProblemBuilder()
            .set_problem_type(ProblemType.MODAL)
            .set_mesh("/tmp/mesh.xdmf")
            .build()
        )
        assert "eigenvalues" in problem.output_fields
        assert "eigenvectors" in problem.output_fields

    def test_custom_output_field(self) -> None:
        problem = (
            ProblemBuilder()
            .set_problem_type(ProblemType.LINEAR_ELASTICITY)
            .set_mesh("/tmp/mesh.xdmf")
            .add_output_field("von_mises")
            .build()
        )
        assert "von_mises" in problem.output_fields

    def test_problem_type_enum(self) -> None:
        assert ProblemType.LINEAR_ELASTICITY == "linear_elasticity"
        assert ProblemType.THERMAL == "thermal"
        assert ProblemType.MODAL == "modal"
        assert ProblemType.BUCKLING == "buckling"

    def test_bc_type_enum(self) -> None:
        assert BoundaryConditionType.DIRICHLET == "dirichlet"
        assert BoundaryConditionType.NEUMANN == "neumann"
        assert BoundaryConditionType.ROBIN == "robin"


class TestResultExtractor:
    def setup_method(self) -> None:
        self.extractor = ResultExtractor()

    def test_extract_fields_dir_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            self.extractor.extract_fields("/nonexistent/dir")

    def test_extract_stress(self) -> None:
        import tempfile
        tmpdir = tempfile.mkdtemp()
        from pathlib import Path
        sigma_dir = Path(tmpdir) / "sigma"
        sigma_dir.mkdir()
        (sigma_dir / "von_mises.dat").write_text("0.0")
        result = self.extractor.extract_stress(tmpdir)
        assert "fields" in result

    def test_extract_displacement(self) -> None:
        import tempfile
        tmpdir = tempfile.mkdtemp()
        result = self.extractor.extract_displacement(tmpdir)
        assert "fields" in result

    def test_extract_temperature(self) -> None:
        import tempfile
        tmpdir = tempfile.mkdtemp()
        result = self.extractor.extract_temperature(tmpdir)
        assert "fields" in result

    def test_get_available_fields_empty(self) -> None:
        assert self.extractor.get_available_fields("/nonexistent") == []

    def test_infer_field_type(self) -> None:
        assert ResultExtractor._infer_field_type("stress") == "scalar"
        assert ResultExtractor._infer_field_type("displacement") == "vector"
        assert ResultExtractor._infer_field_type("temperature") == "scalar"

    def test_infer_component_count(self) -> None:
        assert ResultExtractor._infer_component_count("displacement") == 3
        assert ResultExtractor._infer_component_count("stress") == 6
        assert ResultExtractor._infer_component_count("temperature") == 1

    def test_infer_unit(self) -> None:
        assert ResultExtractor._infer_unit("stress") == "Pa"
        assert ResultExtractor._infer_unit("displacement") == "m"
        assert ResultExtractor._infer_unit("temperature") == "K"

    def test_field_data_creation(self) -> None:
        fd = FieldData(name="stress", field_type="scalar", component_count=6,
                        data_shape=[100], min_value=0.0, max_value=200e6, unit="Pa")
        assert fd.name == "stress"
        assert fd.unit == "Pa"