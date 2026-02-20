"""Tests for exports/pptx.py -- PPTX report generation."""

import pandas as pd
import pytest
from pptx import Presentation

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.exports.pptx import (
    SECTION_MAP,
    _build_analysis_lookup,
    _build_simple_pptx,
    write_pptx_report,
)


@pytest.fixture
def mock_analyses():
    """Create mock analysis results matching SECTION_MAP names."""
    return [
        AnalysisResult(
            name="Total ICS Accounts",
            title="ICS Accounts - Total Dataset",
            df=pd.DataFrame({"Count": [100]}),
            sheet_name="01_Total",
        ),
        AnalysisResult(
            name="Open ICS Accounts",
            title="ICS Accounts - Open Accounts",
            df=pd.DataFrame({"Count": [80]}),
            sheet_name="02_Open",
        ),
        AnalysisResult(
            name="Bad Analysis",
            title="Failed",
            df=pd.DataFrame(),
            error="Something broke",
        ),
    ]


class TestBuildAnalysisLookup:
    def test_builds_lookup(self, mock_analyses):
        lookup = _build_analysis_lookup(mock_analyses)
        assert "Total ICS Accounts" in lookup
        assert "Open ICS Accounts" in lookup

    def test_excludes_errored(self, mock_analyses):
        lookup = _build_analysis_lookup(mock_analyses)
        assert "Bad Analysis" not in lookup

    def test_empty_list(self):
        assert _build_analysis_lookup([]) == {}


class TestBuildSimplePptx:
    def test_creates_file(self, sample_settings, tmp_path):
        lookup = {
            "Total ICS Accounts": AnalysisResult(
                name="Total ICS Accounts",
                title="ICS Accounts - Total Dataset",
                df=pd.DataFrame({"Count": [100]}),
                sheet_name="01_Total",
            ),
        }
        path = tmp_path / "test.pptx"
        _build_simple_pptx(sample_settings, lookup, path)
        assert path.exists()

    def test_has_title_slide(self, sample_settings, tmp_path):
        path = tmp_path / "test.pptx"
        _build_simple_pptx(sample_settings, {}, path)

        prs = Presentation(str(path))
        assert len(prs.slides) >= 1
        title_slide = prs.slides[0]
        assert "ICS Accounts Analysis" in title_slide.shapes.title.text

    def test_with_analyses(self, sample_settings, tmp_path):
        lookup = {
            "Total ICS Accounts": AnalysisResult(
                name="Total ICS Accounts",
                title="ICS Accounts - Total Dataset",
                df=pd.DataFrame({"Count": [100]}),
                sheet_name="01_Total",
            ),
        }
        path = tmp_path / "test_analyses.pptx"
        _build_simple_pptx(sample_settings, lookup, path)

        prs = Presentation(str(path))
        # Title slide + at least one analysis slide
        assert len(prs.slides) >= 2


class TestWritePptxReport:
    def test_creates_file(self, sample_settings, mock_analyses, tmp_path):
        path = tmp_path / "test.pptx"
        result = write_pptx_report(sample_settings, mock_analyses, output_path=path)
        assert result.exists()

    def test_auto_generates_path(self, sample_settings, mock_analyses):
        sample_settings.output_dir.mkdir(parents=True, exist_ok=True)
        result = write_pptx_report(sample_settings, mock_analyses)
        assert result.exists()
        assert "ICS_Analysis" in result.name

    def test_no_analyses(self, sample_settings, tmp_path):
        path = tmp_path / "no_analyses.pptx"
        result = write_pptx_report(
            sample_settings,
            [],
            output_path=path,
        )
        assert result.exists()


class TestSectionMap:
    def test_has_expected_sections(self):
        expected = {
            "Summary",
            "Source Analysis",
            "DM Source Deep-Dive",
            "Demographics",
            "Activity Analysis",
            "Cohort Analysis",
            "Performance",
            "Portfolio Health",
            "Strategic Insights",
            "Executive Summary",
        }
        assert set(SECTION_MAP.keys()) == expected

    def test_all_lists_nonempty(self):
        for section, names in SECTION_MAP.items():
            assert len(names) > 0, f"Section {section} is empty"
