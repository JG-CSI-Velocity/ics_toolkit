"""Tests for analyses/executive_summary.py -- ax999."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.analyses.executive_summary import analyze_executive_summary
from ics_toolkit.analysis.analyses.templates import kpi_summary


class TestAnalyzeExecutiveSummary:
    """ax999: Executive Summary."""

    def test_returns_analysis_result(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_executive_summary(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_metric_value_columns(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_executive_summary(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        assert "Metric" in result.df.columns
        assert "Value" in result.df.columns

    def test_expected_metrics_present(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_executive_summary(
            sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
        )
        metrics = set(result.df["Metric"].values)
        assert "Total ICS Accounts" in metrics
        assert "ICS Rate" in metrics
        assert "Stat O Count" in metrics
        assert "Active Rate (L12M)" in metrics
        assert "Total Swipes (L12M)" in metrics
        assert "Total Spend (L12M)" in metrics
        assert "Top Branch by Activation" in metrics
        assert "Fast Activator %" in metrics
        assert "Never Activator %" in metrics

    def test_without_prior_results(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_executive_summary(
            sample_df,
            ics_all,
            ics_stat_o,
            ics_stat_o_debit,
            sample_settings,
            prior_results=None,
        )
        assert result.error is None
        # Metrics derived from prior_results should be "N/A"
        active_row = result.df[result.df["Metric"] == "Active Rate (L12M)"]
        assert active_row["Value"].iloc[0] == "N/A"

    def test_with_prior_results(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        # Build a mock activity summary result
        activity_kpis = kpi_summary(
            [
                ("Total Accounts", 100),
                ("Active Accounts", 75),
                ("% Active", 0.75),
                ("Total Swipes", 5000),
                ("Total Spend", 150000.00),
                ("Avg Swipes per Account", 50.0),
                ("Avg Spend per Account", 1500.0),
                ("Avg Swipes per Active Account", 66.67),
                ("Avg Spend per Active Account", 2000.0),
                ("Avg Spend per Swipe", 30.0),
                ("Avg Current Balance (All)", 8500.0),
                ("Avg Current Balance (Active)", 9200.0),
            ]
        )
        mock_activity = AnalysisResult(
            name="L12M Activity Summary",
            title="test",
            df=activity_kpis,
        )

        # Build a mock personas result
        persona_df = pd.DataFrame(
            {
                "Category": ["Fast Activator", "Slow Burner", "One and Done", "Never Activator"],
                "Account Count": [40, 20, 15, 25],
                "Total M1 Swipes": [200, 0, 50, 0],
                "Total M3 Swipes": [300, 100, 0, 0],
                "% of Total": [0.40, 0.20, 0.15, 0.25],
            }
        )
        mock_personas = AnalysisResult(
            name="Activation Personas",
            title="test",
            df=persona_df,
        )

        result = analyze_executive_summary(
            sample_df,
            ics_all,
            ics_stat_o,
            ics_stat_o_debit,
            sample_settings,
            prior_results=[mock_activity, mock_personas],
        )
        assert result.error is None

        # Active rate should come from the mock
        active_row = result.df[result.df["Metric"] == "Active Rate (L12M)"]
        assert active_row["Value"].iloc[0] == "0.75"

        # Fast activator should come from the mock
        fast_row = result.df[result.df["Metric"] == "Fast Activator %"]
        assert fast_row["Value"].iloc[0] == "0.4"

    def test_total_ics_uses_dataframe_length(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_executive_summary(
            sample_df,
            ics_all,
            ics_stat_o,
            ics_stat_o_debit,
            sample_settings,
        )
        total_row = result.df[result.df["Metric"] == "Total ICS Accounts"]
        assert total_row["Value"].iloc[0] == str(len(ics_all))

    def test_stat_o_count(self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings):
        result = analyze_executive_summary(
            sample_df,
            ics_all,
            ics_stat_o,
            ics_stat_o_debit,
            sample_settings,
        )
        stat_o_row = result.df[result.df["Metric"] == "Stat O Count"]
        assert stat_o_row["Value"].iloc[0] == str(len(ics_stat_o))

    def test_empty_prior_results_list(
        self, sample_df, ics_all, ics_stat_o, ics_stat_o_debit, sample_settings
    ):
        result = analyze_executive_summary(
            sample_df,
            ics_all,
            ics_stat_o,
            ics_stat_o_debit,
            sample_settings,
            prior_results=[],
        )
        assert result.error is None
        # Derived metrics should be "N/A"
        swipes_row = result.df[result.df["Metric"] == "Total Swipes (L12M)"]
        assert swipes_row["Value"].iloc[0] == "N/A"
