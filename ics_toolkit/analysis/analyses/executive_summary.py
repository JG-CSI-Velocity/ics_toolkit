"""Executive Summary analysis (ax999): Aggregate KPIs from prior analysis results."""

from __future__ import annotations

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult, safe_percentage
from ics_toolkit.analysis.analyses.templates import kpi_summary
from ics_toolkit.settings import AnalysisSettings as Settings


def _find_result(prior_results: list[AnalysisResult], name: str) -> AnalysisResult | None:
    """Find an AnalysisResult by name from the prior results list."""
    for r in prior_results:
        if r.name == name and r.error is None:
            return r
    return None


def _extract_kpi_value(
    result: AnalysisResult | None,
    metric_name: str,
    default: str = "N/A",
) -> str:
    """Extract a value from a KPI-style Metric/Value table."""
    if result is None or result.df.empty:
        return default
    if "Metric" not in result.df.columns or "Value" not in result.df.columns:
        return default

    match = result.df[result.df["Metric"] == metric_name]
    if match.empty:
        return default
    return str(match["Value"].iloc[0])


def _extract_top_branch(
    result: AnalysisResult | None,
    rate_col: str = "Activation Rate",
    branch_col: str = "Branch",
    default: str = "N/A",
) -> str:
    """Extract the top branch by activation rate from a grouped result."""
    if result is None or result.df.empty:
        return default
    if rate_col not in result.df.columns or branch_col not in result.df.columns:
        return default

    # Exclude Total row
    filtered = result.df[result.df[branch_col] != "Total"].copy()
    if filtered.empty:
        return default

    # Only consider numeric activation rates
    numeric_rates = pd.to_numeric(filtered[rate_col], errors="coerce")
    valid = filtered[numeric_rates.notna()]
    if valid.empty:
        return default

    best_idx = numeric_rates[valid.index].idxmax()
    branch_name = valid.loc[best_idx, branch_col]
    rate_value = numeric_rates.loc[best_idx]
    return f"{branch_name} ({rate_value:.2%})"


def _extract_persona_pct(
    result: AnalysisResult | None,
    category: str,
    default: str = "N/A",
) -> str:
    """Extract % of Total for a specific persona category."""
    if result is None or result.df.empty:
        return default
    if "Category" not in result.df.columns or "% of Total" not in result.df.columns:
        return default

    match = result.df[result.df["Category"] == category]
    if match.empty:
        return default

    val = match["% of Total"].iloc[0]
    return str(val)


def analyze_executive_summary(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
    prior_results: list[AnalysisResult] | None = None,
) -> AnalysisResult:
    """ax999: Executive Summary aggregating key metrics from prior analyses."""
    if prior_results is None:
        prior_results = []

    # Total ICS accounts
    total_ics = str(len(ics_all)) if not ics_all.empty else "N/A"

    # ICS Rate
    total_accounts = len(df)
    if total_accounts > 0 and not ics_all.empty:
        ics_rate = safe_percentage(len(ics_all), total_accounts)
    else:
        ics_rate = "N/A"

    # Stat O count
    stat_o_count = str(len(ics_stat_o)) if not ics_stat_o.empty else "N/A"

    # Active rate from activity summary (ax22)
    activity_result = _find_result(prior_results, "L12M Activity Summary")
    active_rate = _extract_kpi_value(activity_result, "% Active", "N/A")

    # Total swipes and spend
    total_swipes = _extract_kpi_value(activity_result, "Total Swipes", "N/A")
    total_spend = _extract_kpi_value(activity_result, "Total Spend", "N/A")

    # Top branch by activation (ax25 or ax36)
    branch_activity = _find_result(prior_results, "Activity by Branch")
    branch_activation = _find_result(prior_results, "Branch Activation")
    top_branch_result = branch_activation if branch_activation else branch_activity
    top_branch_rate_col = (
        "Activation Rate"
        if top_branch_result and "Activation Rate" in top_branch_result.df.columns
        else "Activation %"
    )
    top_branch = _extract_top_branch(top_branch_result, rate_col=top_branch_rate_col)

    # Personas (ax34)
    persona_result = _find_result(prior_results, "Activation Personas")
    fast_activator_pct = _extract_persona_pct(persona_result, "Fast Activator")
    never_activator_pct = _extract_persona_pct(persona_result, "Never Activator")

    metrics = [
        ("Total ICS Accounts", total_ics),
        ("ICS Rate", ics_rate),
        ("Stat O Count", stat_o_count),
        ("Active Rate (L12M)", active_rate),
        ("Total Swipes (L12M)", total_swipes),
        ("Total Spend (L12M)", total_spend),
        ("Top Branch by Activation", top_branch),
        ("Fast Activator %", fast_activator_pct),
        ("Never Activator %", never_activator_pct),
    ]

    result_df = kpi_summary(metrics)

    return AnalysisResult(
        name="Executive Summary",
        title="Executive Summary - Key ICS Metrics",
        df=result_df,
        sheet_name="99_Exec_Summary",
    )
