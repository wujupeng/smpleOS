import json
import tempfile
from pathlib import Path

import pytest

from aeroforge_cae_core.postprocess.visualizer import (
    ResultVisualizer,
    VisualizationConfig,
    VisualizationResult,
)
from aeroforge_cae_core.postprocess.field_extractor import (
    FieldExtractor,
    FieldExtractionConfig,
    ExtractedField,
)
from aeroforge_cae_core.postprocess.report_generator import (
    ReportGenerator,
    ReportConfig,
    ReportSection,
    ReportResult,
)


class TestResultVisualizer:
    def setup_method(self) -> None:
        self.visualizer = ResultVisualizer(working_dir=tempfile.mkdtemp())

    def test_generate_vtk_files_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            self.visualizer.generate_vtk_files("/nonexistent/dir")

    def test_generate_vtk_files(self) -> None:
        tmpdir = tempfile.mkdtemp()
        time_dir = Path(tmpdir) / "100"
        time_dir.mkdir()
        (time_dir / "U.vtk").write_text("dummy vtk")
        result = self.visualizer.generate_vtk_files(tmpdir)
        assert isinstance(result, VisualizationResult)

    def test_generate_paraview_state(self) -> None:
        tmpdir = tempfile.mkdtemp()
        output_path = os.path.join(tmpdir, "state.pvsm") if (os := __import__("os")) else ""
        pvsm = self.visualizer.generate_paraview_state(
            "/tmp/results", output_path, fields=["pressure", "velocity"]
        )
        assert Path(pvsm).exists()
        content = json.loads(Path(pvsm).read_text())
        assert len(content["ParaviewState"]["representations"]) == 2

    def test_generate_contour_data(self) -> None:
        result = self.visualizer.generate_contour_data("/tmp/results", "pressure")
        assert result["field"] == "pressure"
        assert len(result["levels"]) > 0

    def test_generate_contour_data_custom_levels(self) -> None:
        result = self.visualizer.generate_contour_data(
            "/tmp/results", "pressure", levels=[100, 200, 300]
        )
        assert result["levels"] == [100, 200, 300]

    def test_generate_vector_field_data(self) -> None:
        result = self.visualizer.generate_vector_field_data("/tmp/results", "velocity")
        assert result["field"] == "velocity"
        assert result["sample_rate"] == 1

    def test_auto_levels(self) -> None:
        levels = ResultVisualizer._auto_levels("pressure")
        assert len(levels) > 0
        levels = ResultVisualizer._auto_levels("unknown_field")
        assert len(levels) > 0

    def test_visualization_config_defaults(self) -> None:
        config = VisualizationConfig(output_dir="/tmp/out")
        assert config.format == "vtk"
        assert config.color_map == "jet"
        assert config.show_edges is False


class TestFieldExtractor:
    def setup_method(self) -> None:
        self.extractor = FieldExtractor()

    def test_extract_pressure_field(self) -> None:
        tmpdir = tempfile.mkdtemp()
        result = self.extractor.extract_pressure_field(tmpdir)
        assert result.name == "pressure"
        assert result.field_type == "scalar"
        assert result.unit == "Pa"

    def test_extract_velocity_field(self) -> None:
        tmpdir = tempfile.mkdtemp()
        result = self.extractor.extract_velocity_field(tmpdir)
        assert result.name == "velocity"
        assert result.field_type == "vector"
        assert result.unit == "m/s"

    def test_extract_stress_field(self) -> None:
        tmpdir = tempfile.mkdtemp()
        result = self.extractor.extract_stress_field(tmpdir)
        assert result.name == "stress"
        assert result.field_type == "tensor"
        assert result.unit == "Pa"

    def test_extract_temperature_field(self) -> None:
        tmpdir = tempfile.mkdtemp()
        result = self.extractor.extract_temperature_field(tmpdir)
        assert result.name == "temperature"
        assert result.field_type == "scalar"
        assert result.unit == "K"

    def test_extract_fields_not_found(self) -> None:
        config = FieldExtractionConfig(field_names=["pressure"])
        with pytest.raises(FileNotFoundError):
            self.extractor.extract_fields("/nonexistent", config)

    def test_extract_fields_multiple(self) -> None:
        tmpdir = tempfile.mkdtemp()
        config = FieldExtractionConfig(field_names=["pressure", "velocity", "temperature"])
        results = self.extractor.extract_fields(tmpdir, config)
        assert len(results) == 3

    def test_get_available_fields_not_found(self) -> None:
        assert self.extractor.get_available_fields("/nonexistent") == []

    def test_resolve_internal_name(self) -> None:
        assert FieldExtractor._resolve_internal_name("pressure") == "p"
        assert FieldExtractor._resolve_internal_name("velocity") == "U"
        assert FieldExtractor._resolve_internal_name("custom") == "custom"

    def test_field_type_map(self) -> None:
        assert FieldExtractor.FIELD_TYPE_MAP["pressure"] == "scalar"
        assert FieldExtractor.FIELD_TYPE_MAP["velocity"] == "vector"
        assert FieldExtractor.FIELD_TYPE_MAP["stress"] == "tensor"

    def test_field_unit_map(self) -> None:
        assert FieldExtractor.FIELD_UNIT_MAP["pressure"] == "Pa"
        assert FieldExtractor.FIELD_UNIT_MAP["velocity"] == "m/s"
        assert FieldExtractor.FIELD_UNIT_MAP["temperature"] == "K"


class TestReportGenerator:
    def setup_method(self) -> None:
        self.generator = ReportGenerator(working_dir=tempfile.mkdtemp())

    def test_generate_html_report(self) -> None:
        config = ReportConfig(title="Test Report", report_type="test", output_format="html")
        sections = [
            ReportSection(title="Section 1", content="Content 1", order=1, data={"key": "value"}),
            ReportSection(title="Section 2", content="Content 2", order=2),
        ]
        result = self.generator.generate_report(config, sections)
        assert result.format == "html"
        assert result.title == "Test Report"
        assert Path(result.report_path).exists()
        assert result.file_size_bytes > 0
        assert "Section 1" in result.sections
        assert "Section 2" in result.sections

    def test_generate_json_report(self) -> None:
        config = ReportConfig(title="JSON Report", report_type="test", output_format="json")
        sections = [ReportSection(title="Data", content="Some data", order=1)]
        result = self.generator.generate_report(config, sections)
        assert result.format == "json"
        content = json.loads(Path(result.report_path).read_text())
        assert content["title"] == "JSON Report"

    def test_generate_pdf_placeholder(self) -> None:
        config = ReportConfig(title="PDF Report", report_type="test", output_format="pdf")
        sections = [ReportSection(title="Data", content="Some data", order=1)]
        result = self.generator.generate_report(config, sections)
        assert result.format == "pdf"

    def test_generate_cfd_report(self) -> None:
        result = self.generator.generate_cfd_report(
            "/tmp/results",
            {"solver": "simpleFoam", "cl": 0.5, "cd": 0.02},
        )
        assert "CFD" in result.title
        assert result.file_size_bytes > 0

    def test_generate_fea_report(self) -> None:
        result = self.generator.generate_fea_report(
            "/tmp/results",
            {"problem_type": "linear_elasticity", "max_stress": 150e6},
        )
        assert "FEA" in result.title
        assert result.file_size_bytes > 0

    def test_report_config_defaults(self) -> None:
        config = ReportConfig(title="Test", report_type="test")
        assert config.output_format == "html"
        assert config.include_summary is True
        assert config.include_methodology is True

    def test_report_section_ordering(self) -> None:
        config = ReportConfig(title="Test", report_type="test")
        sections = [
            ReportSection(title="C", content="c", order=3),
            ReportSection(title="A", content="a", order=1),
            ReportSection(title="B", content="b", order=2),
        ]
        result = self.generator.generate_report(config, sections)
        assert result.sections == ["A", "B", "C"]

    def test_html_report_contains_data_table(self) -> None:
        config = ReportConfig(title="Data Test", report_type="test", output_format="html")
        sections = [
            ReportSection(title="Results", content="Data below", order=1, data={"param1": 42, "param2": 3.14}),
        ]
        result = self.generator.generate_report(config, sections)
        html = Path(result.report_path).read_text()
        assert "param1" in html
        assert "42" in html