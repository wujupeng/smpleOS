import tempfile
from pathlib import Path

import pytest

from aeroforge_cae_core.mesh.generator_base import (
    MeshFormat,
    MeshGenerationParams,
    MeshGenerationResult,
    MeshGeneratorBase,
    MeshQualityMetrics,
    MeshType,
)
from aeroforge_cae_core.mesh.structured import StructuredMeshGenerator
from aeroforge_cae_core.mesh.unstructured import UnstructuredMeshGenerator
from aeroforge_cae_core.mesh.quality import MeshQualityChecker, QualityReport, QualityThresholds


class TestMeshGenerationParams:
    def test_defaults(self) -> None:
        params = MeshGenerationParams(
            source_geometry="/tmp/model.step",
            mesh_type=MeshType.STRUCTURED,
        )
        assert params.target_element_size == 0.01
        assert params.growth_rate == 1.2
        assert params.boundary_layer_layers == 5
        assert params.n_proc == 1

    def test_custom_values(self) -> None:
        params = MeshGenerationParams(
            source_geometry="/tmp/model.step",
            mesh_type=MeshType.UNSTRUCTURED,
            target_element_size=0.005,
            max_element_size=0.05,
            n_proc=4,
        )
        assert params.target_element_size == 0.005
        assert params.n_proc == 4


class TestMeshQualityMetrics:
    def test_defaults(self) -> None:
        metrics = MeshQualityMetrics()
        assert metrics.orthogonality_min == 0.0
        assert metrics.skewness_max == 0.0
        assert metrics.aspect_ratio_max == 0.0


class TestMeshGenerationResult:
    def test_defaults(self) -> None:
        result = MeshGenerationResult(
            output_path="/tmp/mesh",
            mesh_type=MeshType.STRUCTURED,
        )
        assert result.node_count == 0
        assert result.element_count == 0
        assert result.quality_metrics is None
        assert result.error_message is None


class TestStructuredMeshGenerator:
    def setup_method(self) -> None:
        self.generator = StructuredMeshGenerator(working_dir=tempfile.mkdtemp())

    def test_generate(self) -> None:
        tmpdir = tempfile.mkdtemp()
        geo_file = Path(tmpdir) / "model.step"
        geo_file.write_text("dummy")
        params = MeshGenerationParams(
            source_geometry=str(geo_file),
            mesh_type=MeshType.STRUCTURED,
        )
        result = self.generator.generate(params)
        assert result.mesh_type == MeshType.STRUCTURED
        assert result.output_path is not None

    def test_generate_block_mesh(self) -> None:
        result = self.generator.generate_block_mesh(
            domain_bounds={"x": [0, 1], "y": [0, 1], "z": [0, 1]},
            divisions={"x": 10, "y": 10, "z": 10},
        )
        assert result.node_count == 11 * 11 * 11
        assert result.element_count == 10 * 10 * 10
        assert result.quality_metrics is not None
        assert result.quality_metrics.orthogonality_min == 1.0

    def test_generate_block_mesh_with_grading(self) -> None:
        result = self.generator.generate_block_mesh(
            domain_bounds={"x": [0, 2], "y": [0, 1], "z": [0, 1]},
            divisions={"x": 20, "y": 10, "z": 10},
            grading={"x": [1.0, 1.2]},
        )
        assert result.element_count == 20 * 10 * 10

    def test_estimate_resources(self) -> None:
        tmpdir = tempfile.mkdtemp()
        geo_file = Path(tmpdir) / "model.step"
        geo_file.write_text("dummy")
        params = MeshGenerationParams(
            source_geometry=str(geo_file),
            mesh_type=MeshType.STRUCTURED,
        )
        result = self.generator.estimate_resources(params)
        assert result["generator_type"] == "structured"
        assert result["parallelizable"] is True

    def test_validate_geometry_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            self.generator.validate_geometry("/nonexistent/model.step")

    def test_validate_geometry(self) -> None:
        tmpdir = tempfile.mkdtemp()
        geo_file = Path(tmpdir) / "model.step"
        geo_file.write_text("dummy geometry data")
        result = self.generator.validate_geometry(str(geo_file))
        assert result["valid"] is True
        assert result["file_size_mb"] > 0

    def test_estimate_mesh_size(self) -> None:
        tmpdir = tempfile.mkdtemp()
        geo_file = Path(tmpdir) / "model.step"
        geo_file.write_text("x" * 10000)
        params = MeshGenerationParams(
            source_geometry=str(geo_file),
            mesh_type=MeshType.STRUCTURED,
            target_element_size=0.01,
        )
        result = self.generator.estimate_mesh_size(params)
        assert "estimated_node_count" in result
        assert "estimated_element_count" in result
        assert "estimated_memory_mb" in result


class TestUnstructuredMeshGenerator:
    def setup_method(self) -> None:
        self.generator = UnstructuredMeshGenerator(working_dir=tempfile.mkdtemp())

    def test_generate(self) -> None:
        tmpdir = tempfile.mkdtemp()
        geo_file = Path(tmpdir) / "model.step"
        geo_file.write_text("dummy")
        params = MeshGenerationParams(
            source_geometry=str(geo_file),
            mesh_type=MeshType.UNSTRUCTURED,
        )
        result = self.generator.generate(params)
        assert result.mesh_type == MeshType.UNSTRUCTURED

    def test_generate_snappy_hex_mesh(self) -> None:
        tmpdir = tempfile.mkdtemp()
        result = self.generator.generate_snappy_hex_mesh(
            geometry_path="/tmp/wing.stl",
            case_dir=tmpdir,
        )
        assert result.output_path == tmpdir
        assert (Path(tmpdir) / "system" / "snappyHexMeshDict").exists()

    def test_generate_snappy_hex_mesh_with_params(self) -> None:
        tmpdir = tempfile.mkdtemp()
        result = self.generator.generate_snappy_hex_mesh(
            geometry_path="/tmp/wing.stl",
            case_dir=tmpdir,
            params={"max_global_cells": 10000000, "boundary_layer_count": 8},
        )
        assert (Path(tmpdir) / "system" / "snappyHexMeshDict").exists()

    def test_generate_gmsh_mesh_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            self.generator.generate_gmsh_mesh(
                geometry_path="/nonexistent/model.step",
                output_dir=tempfile.mkdtemp(),
            )

    def test_generate_gmsh_mesh(self) -> None:
        tmpdir = tempfile.mkdtemp()
        geo_file = Path(tmpdir) / "model.step"
        geo_file.write_text("dummy")
        result = self.generator.generate_gmsh_mesh(
            geometry_path=str(geo_file),
            output_dir=tempfile.mkdtemp(),
            element_size=0.005,
            algorithm="Delaunay",
        )
        assert result.mesh_type == MeshType.UNSTRUCTURED

    def test_estimate_resources(self) -> None:
        tmpdir = tempfile.mkdtemp()
        geo_file = Path(tmpdir) / "model.step"
        geo_file.write_text("dummy")
        params = MeshGenerationParams(
            source_geometry=str(geo_file),
            mesh_type=MeshType.UNSTRUCTURED,
        )
        result = self.generator.estimate_resources(params)
        assert result["generator_type"] == "unstructured"
        assert result["requires_surface_mesh"] is True


class TestMeshQualityChecker:
    def setup_method(self) -> None:
        self.checker = MeshQualityChecker()

    def test_check_quality_pass(self) -> None:
        metrics = {
            "total_cells": 1000,
            "orthogonality_min": 0.5,
            "orthogonality_max": 1.0,
            "orthogonality_avg": 0.8,
            "skewness_min": 0.0,
            "skewness_max": 0.3,
            "skewness_avg": 0.1,
            "aspect_ratio_min": 1.0,
            "aspect_ratio_max": 10.0,
            "aspect_ratio_avg": 3.0,
            "non_orthogonal_count": 10,
            "highly_skewed_count": 5,
        }
        report = self.checker.check_quality(metrics)
        assert report.passed is True
        assert report.total_cells == 1000
        assert report.non_orthogonal_percent == 1.0
        assert report.highly_skewed_percent == 0.5

    def test_check_quality_fail_orthogonality(self) -> None:
        metrics = {
            "total_cells": 1000,
            "orthogonality_min": 0.05,
            "skewness_max": 0.3,
            "aspect_ratio_max": 10.0,
            "non_orthogonal_count": 10,
            "highly_skewed_count": 5,
        }
        report = self.checker.check_quality(metrics)
        assert report.passed is False
        assert any("orthogonality" in e.lower() for e in report.errors)

    def test_check_quality_fail_skewness(self) -> None:
        metrics = {
            "total_cells": 1000,
            "orthogonality_min": 0.5,
            "skewness_max": 0.9,
            "aspect_ratio_max": 10.0,
            "non_orthogonal_count": 10,
            "highly_skewed_count": 5,
        }
        report = self.checker.check_quality(metrics)
        assert report.passed is False
        assert any("skewness" in e.lower() for e in report.errors)

    def test_check_quality_warning_aspect_ratio(self) -> None:
        metrics = {
            "total_cells": 1000,
            "orthogonality_min": 0.5,
            "skewness_max": 0.3,
            "aspect_ratio_max": 200.0,
            "non_orthogonal_count": 10,
            "highly_skewed_count": 5,
        }
        report = self.checker.check_quality(metrics)
        assert report.passed is True
        assert any("aspect ratio" in w.lower() for w in report.warnings)

    def test_custom_thresholds(self) -> None:
        thresholds = QualityThresholds(orthogonality_min=0.3, skewness_max=0.5)
        checker = MeshQualityChecker(thresholds)
        metrics = {
            "total_cells": 1000,
            "orthogonality_min": 0.2,
            "skewness_max": 0.4,
            "aspect_ratio_max": 10.0,
            "non_orthogonal_count": 10,
            "highly_skewed_count": 5,
        }
        report = checker.check_quality(metrics)
        assert report.passed is False

    def test_quality_report_defaults(self) -> None:
        report = QualityReport()
        assert report.passed is True
        assert report.warnings == []
        assert report.errors == []

    def test_get_quality_summary(self) -> None:
        metrics = {
            "total_cells": 1000,
            "orthogonality_min": 0.5,
            "orthogonality_max": 1.0,
            "orthogonality_avg": 0.8,
            "skewness_min": 0.0,
            "skewness_max": 0.3,
            "skewness_avg": 0.1,
            "aspect_ratio_min": 1.0,
            "aspect_ratio_max": 10.0,
            "aspect_ratio_avg": 3.0,
            "non_orthogonal_count": 10,
            "highly_skewed_count": 5,
        }
        report = self.checker.check_quality(metrics)
        summary = self.checker.get_quality_summary(report)
        assert summary["passed"] is True
        assert "orthogonality" in summary
        assert "skewness" in summary
        assert "aspect_ratio" in summary

    def test_check_openfoam_mesh(self) -> None:
        tmpdir = tempfile.mkdtemp()
        report = self.checker.check_openfoam_mesh(tmpdir)
        assert isinstance(report, QualityReport)