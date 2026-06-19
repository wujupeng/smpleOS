from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ReportSection:
    title: str
    content: str
    subsections: list[ReportSection] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    order: int = 0


@dataclass
class ReportConfig:
    title: str
    report_type: str
    output_format: str = "html"
    include_summary: bool = True
    include_methodology: bool = True
    include_results: bool = True
    include_conclusions: bool = True
    template_path: str | None = None


@dataclass
class ReportResult:
    report_path: str
    format: str
    title: str
    generated_at: str
    sections: list[str] = field(default_factory=list)
    file_size_bytes: int = 0


class ReportGenerator:
    def __init__(self, working_dir: str = "/tmp/aeroforge/reports") -> None:
        self._working_dir = Path(working_dir)
        self._working_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        config: ReportConfig,
        sections: list[ReportSection],
        output_dir: str | None = None,
    ) -> ReportResult:
        out_dir = Path(output_dir) if output_dir else self._working_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_title = config.title.replace(" ", "_").lower()

        if config.output_format == "html":
            file_path = out_dir / f"{safe_title}_{timestamp}.html"
            content = self._generate_html(config, sections)
        elif config.output_format == "pdf":
            file_path = out_dir / f"{safe_title}_{timestamp}.json"
            content = self._generate_pdf_placeholder(config, sections)
        else:
            file_path = out_dir / f"{safe_title}_{timestamp}.json"
            content = self._generate_json(config, sections)

        file_path.write_text(content, encoding="utf-8")

        result = ReportResult(
            report_path=str(file_path),
            format=config.output_format,
            title=config.title,
            generated_at=datetime.now(timezone.utc).isoformat(),
            sections=[s.title for s in sorted(sections, key=lambda s: s.order)],
            file_size_bytes=file_path.stat().st_size,
        )

        logger.info("Generated %s report: %s (%d bytes)",
                     config.output_format.upper(), file_path, result.file_size_bytes)
        return result

    def generate_cfd_report(
        self,
        results_dir: str,
        analysis_config: dict[str, Any],
        output_dir: str | None = None,
    ) -> ReportResult:
        sections = [
            ReportSection(
                title="Analysis Summary",
                content="CFD analysis results summary",
                order=1,
                data=analysis_config,
            ),
            ReportSection(
                title="Methodology",
                content="Computational Fluid Dynamics analysis using OpenFOAM",
                order=2,
                data={
                    "solver": analysis_config.get("solver", "simpleFoam"),
                    "turbulence_model": analysis_config.get("turbulence_model", "kOmegaSST"),
                    "mesh_type": analysis_config.get("mesh_type", "unstructured"),
                },
            ),
            ReportSection(
                title="Results",
                content="Aerodynamic coefficients and flow field analysis",
                order=3,
                data={
                    "lift_coefficient": analysis_config.get("cl", 0.0),
                    "drag_coefficient": analysis_config.get("cd", 0.0),
                    "moment_coefficient": analysis_config.get("cm", 0.0),
                },
            ),
            ReportSection(
                title="Conclusions",
                content="CFD analysis completed successfully",
                order=4,
            ),
        ]

        config = ReportConfig(
            title="CFD Analysis Report",
            report_type="cfd",
            output_format="html",
        )
        return self.generate_report(config, sections, output_dir)

    def generate_fea_report(
        self,
        results_dir: str,
        analysis_config: dict[str, Any],
        output_dir: str | None = None,
    ) -> ReportResult:
        sections = [
            ReportSection(
                title="Analysis Summary",
                content="FEA analysis results summary",
                order=1,
                data=analysis_config,
            ),
            ReportSection(
                title="Methodology",
                content="Finite Element Analysis using FEniCS",
                order=2,
                data={
                    "problem_type": analysis_config.get("problem_type", "linear_elasticity"),
                    "element_type": analysis_config.get("element_type", "tet4"),
                    "mesh_nodes": analysis_config.get("mesh_nodes", 0),
                },
            ),
            ReportSection(
                title="Results",
                content="Structural analysis results",
                order=3,
                data={
                    "max_stress": analysis_config.get("max_stress", 0.0),
                    "max_displacement": analysis_config.get("max_displacement", 0.0),
                    "safety_factor": analysis_config.get("safety_factor", 0.0),
                },
            ),
            ReportSection(
                title="Conclusions",
                content="FEA analysis completed successfully",
                order=4,
            ),
        ]

        config = ReportConfig(
            title="FEA Analysis Report",
            report_type="fea",
            output_format="html",
        )
        return self.generate_report(config, sections, output_dir)

    def _generate_html(self, config: ReportConfig, sections: list[ReportSection]) -> str:
        sorted_sections = sorted(sections, key=lambda s: s.order)
        sections_html = ""
        for section in sorted_sections:
            data_rows = ""
            if section.data:
                for key, value in section.data.items():
                    data_rows += f"<tr><td>{key}</td><td>{value}</td></tr>"

            sections_html += f"""
            <div class="section">
                <h2>{section.title}</h2>
                <p>{section.content}</p>
                {"<table><tr><th>Parameter</th><th>Value</th></tr>" + data_rows + "</table>" if data_rows else ""}
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{config.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        h2 {{ color: #3498db; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>{config.title}</h1>
    <p>Generated: {datetime.now(timezone.utc).isoformat()}</p>
    {sections_html}
</body>
</html>"""

    def _generate_pdf_placeholder(self, config: ReportConfig, sections: list[ReportSection]) -> str:
        return json.dumps({
            "format": "pdf",
            "title": config.title,
            "note": "PDF generation requires weasyprint or reportlab. This is a placeholder.",
            "sections": [{"title": s.title, "content": s.content} for s in sections],
        }, indent=2)

    def _generate_json(self, config: ReportConfig, sections: list[ReportSection]) -> str:
        return json.dumps({
            "title": config.title,
            "report_type": config.report_type,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sections": [
                {
                    "title": s.title,
                    "content": s.content,
                    "data": s.data,
                    "order": s.order,
                }
                for s in sorted(sections, key=lambda s: s.order)
            ],
        }, indent=2)