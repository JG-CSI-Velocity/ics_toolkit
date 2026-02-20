# feat: Referral Intelligence Engine

> A separate pipeline within ICS Toolkit that analyzes credit union referral data files to produce repeatable influence scoring, network inference, and staff multiplier reports.

## Overview

Add a new `referral` CLI subcommand and pipeline to ICS Toolkit that ingests a **separate referral data file** (distinct from the existing ICS analysis dump) and produces an **8-artifact intelligence report**. This is NOT an extension of the existing `ref_source.py` analyses -- it operates on a completely different dataset with its own columns, loader, and analytical layers.

**Relationship to existing `ref_source.py` (ax73-ax80):**
- `analyze` command examines **account-level** REF data from the ICS dump (balances, debit status, swipes)
- `referral` command examines **referral-level** data from a separate tracking file (referrer identity, influence, timing)
- They are **complementary**, not competing. CLI help text must clarify this distinction.

**CLI:** `python -m ics_toolkit referral data/referral_file.xls`

**Source file columns (8 fields):**

| Column | Purpose | Null Handling |
|--------|---------|---------------|
| Referrer Name | Existing account holder who made the referral | Null -> grouped as `"UNKNOWN"`, included in staff/branch metrics, **excluded from influence scoring** |
| Issue Date | Date the referral was issued | Null -> included in volume counts, **excluded from temporal analysis** (burst, velocity, recency) |
| Referral Code | Raw code (decoded additively in Layer 3) | Null -> classified as `"MANUAL"` channel |
| Purchase Manager | Staff member who processed the referral | Null -> grouped as `"UNASSIGNED"`, excluded from staff multiplier scoring |
| Branch | Branch where referral was processed | Null -> grouped as `"UNKNOWN"`, excluded from branch density artifact |
| Account Holder | New account holder (the referred person) | Null -> **log warning**, keep row (use MRDB hash as identifier) |
| MRDB Account Hash | **Primary key** -- unique account ID | Null -> **raise DataError** (row is unusable without PK) |
| Cert ID | Certificate identifier -- confirms completion | **Validation only**: warn if missing, but never used in analysis or scoring |

**Duplicate MRDB handling:** Per data model rules, each row = one completed event. If the same MRDB Account Hash appears multiple times with different Cert IDs, these are **distinct events** (e.g., different products). If same MRDB + same Cert ID, log a warning but keep all rows (do NOT deduplicate).

**Critical data model rules (from issue #4):**
- Each row = one **completed** new account (not a lead or submission)
- Cert ID confirms completion -- every row must have one
- MRDB Account Hash confirms uniqueness per Account Holder
- Do NOT merge or deduplicate rows -- treat each as a completed event
- Do NOT infer leads, funnels, or drop-offs

**Output artifacts (8 repeatable reports):**
1. Top Referrers (influence-ranked, configurable N, default 25)
2. Emerging Referrers (new + accelerating, not just bursting)
3. Dormant High-Value Referrers (configurable thresholds)
4. One-time vs Repeat Referrers (binary split comparison table)
5. Staff as Multipliers (processing reach, NOT influence)
6. Branch-level Influence Density (avg influence score of referrers routed through branch)
7. Referral Code Health Report (channel distribution + reliability %)
8. Overview KPIs (summary metrics, runs last, receives prior results)

**Non-negotiable influence rules:**
- Referrer Name = influence (only referrers can be ranked as influencers)
- Purchase Manager = processing only (never ranked as influencer)
- Branch = routing only (branch volume != growth; "branch density" measures avg referrer quality routed there, NOT branch production)
- Influence rewards: multiple distinct Account Holders, repeat behavior, sustained presence, network activation
- Influence does NOT reward: staff assignment, branch volume, single referrals

---

## Problem Statement / Motivation

The existing `ref_source.py` (ax73-ax80) analyzes REF-sourced accounts **within the ICS data dump** -- it answers "how do REF accounts compare to DM accounts?" But it cannot answer deeper questions like:

- **Who actually causes people to open accounts?** (influence scoring)
- **Which referrers are emerging vs dormant?** (temporal analysis)
- **Which staff amplify influence vs just process volume?** (multiplier scoring)
- **Are referrals coming from households/networks?** (network inference)
- **Which referral codes are signal vs noise?** (code health)

These questions require the **raw referral file** with referrer-level detail that does not exist in the ICS dump.

---

## Resolved Design Decisions

These were identified as gaps during SpecFlow analysis and are now resolved:

| # | Question | Decision |
|---|----------|----------|
| 1 | Duplicate MRDB Account Hash handling | Keep all rows; warn if same MRDB + same Cert ID. Each row = completed event. |
| 2 | NaN in Referrer Name | Group as `"UNKNOWN"`, include in staff/branch metrics, exclude from influence scoring |
| 3 | NaN in Issue Date | Include in volume counts, exclude from temporal analysis (burst, velocity, recency) |
| 4 | `.xls` loading strategy | `.xls` -> `engine="xlrd"`, `.xlsx` -> `engine="openpyxl"`, `.csv` -> `pd.read_csv()` |
| 5 | Dormant threshold | No referral in last `dormancy_days` (default 180), configurable in config.yaml |
| 6 | High-value threshold | `high_value_min_referrals` (default 5) unique accounts historically, configurable |
| 7 | NaN velocity for single-referral referrers | `avg_days_between.fillna(0)` before scoring; velocity component = 0 |
| 8 | Influence weights configurable? | Yes, via `referral.scoring_weights` in config.yaml. Logged at pipeline start for auditability. |
| 9 | Alias table format | Config-driven: `referral.name_aliases: {"J SMITH": "JOHN SMITH"}` in config.yaml. V1 = strip+uppercase only. |
| 10 | Layer numbering | Renumber to match execution order: L1=normalize, L2=decode, L3=temporal, L4=network, L5=scoring, L6=artifacts |
| 11 | Cert ID usage | Validation only: warn if missing. Not used in any analysis, scoring, or artifact. |
| 12 | Top N referrers | Configurable via `referral.top_n_referrers` (default 25) |
| 13 | min_max for constant series | Returns 0.5 for all values (not 0) to avoid zeroing entire score components |
| 14 | Network inference output location | Surfaced as extra columns on Top Referrers artifact: "Network Size", "Network IDs" |
| 15 | Chart-to-artifact mapping | R01, R02, R05, R06, R07 get charts (5 total). R03, R04, R08 are table-only. |
| 16 | Code prefix map per-client | Config-driven with hardcoded defaults; `referral.code_prefix_map` in config.yaml |
| 17 | Emerging vs bursting | Emerging = first appeared within `emerging_lookback_days` (default 180) + burst_count >= 2 |
| 18 | PPTX template | Reuse existing `templates/Template12.25.pptx` |
| 19 | Output file naming | `{client_id}_Referral_Intelligence_{date}.xlsx` / `.pptx` |
| 20 | Exception hierarchy | Reuse existing `DataError`, `AnalysisError`, `ExportError` from `exceptions.py` |

---

## QA / Validation Checklist (Built Into Pipeline)

Per issue #4, the pipeline must enforce these checks:

### Data Integrity (run at load time)
- [ ] Every row has a MRDB Account Hash (raise `DataError` if missing)
- [ ] Every row has a Cert ID (log warning if missing, continue)
- [ ] No future dates in Issue Date (log warning, keep rows)
- [ ] Duplicate MRDB + Cert ID pairs logged as warnings

### Logic Validation (run after scoring)
- [ ] Removing one Branch does not change top referrers materially
- [ ] High-volume staff are NOT automatically top influencers
- [ ] Referrers with only a single referral do NOT appear in "Top Referrers"
- [ ] Staff multiplier top 5 != referral volume top 5 (if they match, weights are wrong)

### Sanity Checks (logged as warnings)
- [ ] Can point to specific referrers with repeat entries
- [ ] Clustered referrals correspond to the same referrer
- [ ] Influence conclusions are explainable using only source fields
- [ ] Analysis would give the same answer next month (deterministic)

### Failure Modes to Guard Against
- Ranking Purchase Managers as influencers (explicitly prevented)
- Treating Branch volume as growth (branch = routing only)
- Ignoring Referral Code structure (decoded in Layer 2)
- Mixing operational throughput with influence (separate scoring systems)
- Changing definitions mid-analysis (config-locked weights)
- NaN propagation in scoring (all NaN handling defined per-column)

### Pass/Fail Standard
> "A small set of existing account holders consistently generate new accounts across time, independent of staff or branch assignment."
>
> If the analysis cannot demonstrate this with evidence from the file, the build is incomplete.

---

## Proposed Solution

### Architecture: Parallel Pipeline

```
ics_toolkit/
  referral/                          # NEW -- entire package
    __init__.py                      # run_referral() convenience function
    pipeline.py                      # ReferralPipelineResult, run_pipeline(), export_outputs()
    data_loader.py                   # load_referral_data() -- validates 8 required columns
    column_map.py                    # REQUIRED_COLUMNS, COLUMN_ALIASES for referral file
    normalizer.py                    # Layer 1: entity normalization (names, branches)
    code_decoder.py                  # Layer 2: referral code decoding + tagging
    temporal.py                      # Layer 3: burst detection, decay, lag analysis
    network.py                       # Layer 4: household/network inference via soft signals
    scoring.py                       # Layer 5: influence score + staff multiplier formulas
    analyses/
      __init__.py                    # REFERRAL_ANALYSIS_REGISTRY + run_all_referral_analyses()
      base.py                        # ReferralContext dataclass (bundles df + metrics for analysis fns)
      top_referrers.py               # R01: influence-ranked referrer table
      emerging_referrers.py          # R02: momentum-based emerging referrers
      dormant_referrers.py           # R03: dormant high-value referrers
      onetime_vs_repeat.py           # R04: one-time vs repeat comparison table
      staff_multipliers.py           # R05: staff multiplier scores
      branch_density.py              # R06: branch-level influence density
      code_health.py                 # R07: referral code health report
      overview.py                    # R08: summary KPIs (runs last, receives prior_results)
    charts/
      __init__.py                    # REFERRAL_CHART_REGISTRY
      top_referrers.py               # Horizontal bar: top N referrers by score
      emerging_referrers.py          # Scatter timeline: referrer x date with burst markers
      staff_multipliers.py           # Grouped bar: multiplier score vs volume
      branch_density.py              # Vertical bar: avg influence score per branch
      code_health.py                 # Stacked bar: code categories distribution
    exports/
      __init__.py
      excel.py                       # Reuse analysis.exports.excel patterns
      pptx.py                        # Reuse analysis.exports.pptx patterns + REFERRAL_SECTION_MAP
  settings.py                        # MODIFY: add ReferralSettings as 3rd key
  cli.py                             # MODIFY: add `referral` command
  __init__.py                        # MODIFY: add run_referral() convenience
tests/
  referral/                          # NEW -- mirrors referral/ structure
    __init__.py
    conftest.py                      # Synthetic 8-column fixture (50+ rows, deterministic rng)
    test_data_loader.py
    test_normalizer.py
    test_code_decoder.py
    test_scoring.py
    test_temporal.py
    test_network.py
    analyses/
      __init__.py
      test_top_referrers.py
      test_emerging_referrers.py
      test_dormant_referrers.py
      test_onetime_vs_repeat.py
      test_staff_multipliers.py
      test_branch_density.py
      test_code_health.py
      test_overview.py
    charts/
      __init__.py
      test_referral_charts.py
    exports/
      __init__.py
      test_referral_excel.py
      test_referral_pptx.py
    test_pipeline.py
    test_cli.py
```

### Key Design Decisions

1. **Reuse `AnalysisResult`** from `analysis.analyses.base` -- same dataclass for all artifacts. This lets us reuse the Excel/PPTX exporters with minimal modifications.

2. **Separate `referral/` package** -- not bolted onto `analysis/analyses/`. The data model, loader, and pipeline are fundamentally different. Clean separation prevents coupling.

3. **MRDB Account Hash is the primary key** -- bridges to ODD and Tran files. Used for `nunique` counts in all "unique accounts" metrics.

4. **Config-driven scoring weights** -- all weights and thresholds live in `config.yaml` under `referral:`, validated by Pydantic with sensible defaults. Logged at pipeline start for audit trail.

5. **Layer numbering matches execution order** (L1-L6), not the conceptual framework's numbering.

6. **ReferralContext dataclass** bundles `(df, referrer_metrics, staff_metrics, settings)` for clean analysis function signatures (avoids 5+ positional params).

---

## Technical Approach

### Phase 1: Foundation (Settings, CLI, Data Loader)

#### 1.1 ReferralSettings (modify `settings.py`)

```python
class ReferralScoringWeights(BaseModel):
    """Influence score component weights. Must sum to 1.0."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    unique_accounts: float = 0.35
    burst_count: float = 0.25
    channels_used: float = 0.20
    velocity: float = 0.10
    longevity: float = 0.10

    @model_validator(mode="after")
    def check_weights_sum(self) -> "ReferralScoringWeights":
        total = (self.unique_accounts + self.burst_count + self.channels_used
                 + self.velocity + self.longevity)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total:.4f}")
        return self


class ReferralStaffWeights(BaseModel):
    """Staff multiplier score component weights. Must sum to 1.0."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    avg_referrer_score: float = 0.60
    unique_referrers: float = 0.40

    @model_validator(mode="after")
    def check_weights_sum(self) -> "ReferralStaffWeights":
        total = self.avg_referrer_score + self.unique_referrers
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Staff weights must sum to 1.0, got {total:.4f}")
        return self


class ReferralSettings(BaseModel):
    """Settings for the referral intelligence pipeline."""
    model_config = ConfigDict(extra="forbid")

    data_file: Path | None = None
    client_id: str | None = None
    client_name: str | None = None
    output_dir: Path = Path("output/referral/")
    outputs: OutputConfig = OutputConfig()
    charts: ChartConfig = ChartConfig()
    pptx_template: Path | None = DEFAULT_PPTX_TEMPLATE

    # Scoring
    scoring_weights: ReferralScoringWeights = ReferralScoringWeights()
    staff_weights: ReferralStaffWeights = ReferralStaffWeights()

    # Thresholds
    burst_window_days: int = 14
    dormancy_days: int = 180
    high_value_min_referrals: int = 5
    emerging_min_burst_count: int = 2
    emerging_lookback_days: int = 180
    top_n_referrers: int = 25

    # Entity normalization
    name_aliases: dict[str, str] = Field(default_factory=dict)
    branch_mapping: dict[str, str] | None = None

    # Code decoding (prefix -> channel mapping)
    code_prefix_map: dict[str, str] = Field(default_factory=lambda: {
        "150A": "BRANCH_STANDARD",
        "120A": "BRANCH_STANDARD",
        "080A": "BRANCH_STANDARD",
        "100A": "BRANCH_STANDARD",
        "030A": "BRANCH_STANDARD",
        "020A": "BRANCH_STANDARD",
        "PC": "DIGITAL_PROCESS",
        "EMAIL": "EMAIL",
    })

    # Header row (for files with metadata rows above the actual header)
    header_row: int = 0


# Settings class gains third top-level key:
class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    append: AppendSettings = AppendSettings()
    analysis: AnalysisSettings = AnalysisSettings()
    referral: ReferralSettings = ReferralSettings()  # NEW

    # Existing from_yaml, for_append, for_analysis methods unchanged

    @classmethod
    def for_referral(cls, data_file: Path, **kwargs) -> "Settings":
        """Create settings for referral-only usage."""
        try:
            return cls(referral=ReferralSettings(data_file=data_file, **kwargs))
        except Exception as e:
            raise ConfigError(f"Configuration error: {e}") from e
```

#### 1.2 CLI Subcommand (modify `cli.py`)

```python
@app.command()
def referral(
    data_file: Path = typer.Argument(..., help="Path to the referral data file (.xls/.xlsx/.csv)."),
    config: Path = typer.Option(DEFAULT_CONFIG_PATH, "--config", "-c"),
    output_dir: Path = typer.Option(None, "--output", "-o"),
    client_id: str = typer.Option(None, "--client-id"),
    client_name: str = typer.Option(None, "--client-name"),
    no_charts: bool = typer.Option(False, "--no-charts"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run referral intelligence analysis and generate reports.

    Analyzes a referral tracking file to produce influence scoring,
    staff multiplier scores, network inference, and code health reports.

    NOTE: This is separate from `ics-toolkit analyze`, which examines
    account-level data from the ICS dump. The referral command examines
    referral-level data from a separate tracking file.
    """
    _setup_logging(verbose)
    from ics_toolkit.referral.pipeline import export_outputs, run_pipeline
    settings = _load_settings(config, referral={"data_file": str(data_file), ...})
    result = run_pipeline(settings.referral, skip_charts=no_charts)
    paths = export_outputs(result, skip_charts=no_charts)
    for p in paths:
        typer.echo(f"  {p}")
```

#### 1.3 Data Loader (`referral/data_loader.py`)

```python
REQUIRED_COLUMNS = [
    "Referrer Name",
    "Issue Date",
    "Referral Code",
    "Purchase Manager",
    "Branch",
    "Account Holder",
    "MRDB Account Hash",
    "Cert ID",
]

COLUMN_ALIASES = {
    "referrer": "Referrer Name",
    "referrer_name": "Referrer Name",
    "referrer name": "Referrer Name",
    "issue_date": "Issue Date",
    "issue date": "Issue Date",
    "date": "Issue Date",
    "referral_code": "Referral Code",
    "referral code": "Referral Code",
    "code": "Referral Code",
    "purchase_manager": "Purchase Manager",
    "purchase manager": "Purchase Manager",
    "staff": "Purchase Manager",
    "branch": "Branch",
    "branch_id": "Branch",
    "account_holder": "Account Holder",
    "account holder": "Account Holder",
    "new_account": "Account Holder",
    "mrdb_account_hash": "MRDB Account Hash",
    "mrdb account hash": "MRDB Account Hash",
    "mrdb": "MRDB Account Hash",
    "account_hash": "MRDB Account Hash",
    "cert_id": "Cert ID",
    "cert id": "Cert ID",
    "certificate_id": "Cert ID",
}


def load_referral_data(settings: ReferralSettings) -> pd.DataFrame:
    """Load and validate referral data file.

    Steps:
    1. Detect format by suffix: .xls -> xlrd, .xlsx -> openpyxl, .csv -> pd.read_csv
    2. Read with header_row offset (settings.header_row, default 0)
    3. Resolve column aliases (case-insensitive, underscore-normalized)
    4. Validate all REQUIRED_COLUMNS present
    5. Drop rows where MRDB Account Hash is null (raise DataError if ALL null)
    6. Warn on rows with null Cert ID
    7. Parse Issue Date as datetime (errors="coerce"), warn on NaT count
    8. Warn on future dates in Issue Date
    9. Log duplicate MRDB + Cert ID pairs
    10. Return validated DataFrame
    """
```

**Files to create/modify:**
- `ics_toolkit/referral/__init__.py`
- `ics_toolkit/referral/data_loader.py`
- `ics_toolkit/referral/column_map.py`
- Modify: `ics_toolkit/settings.py` (add `ReferralSettings`, `ReferralScoringWeights`, `ReferralStaffWeights`)
- Modify: `ics_toolkit/cli.py` (add `referral` command)
- Modify: `ics_toolkit/__init__.py` (add `run_referral()`)
- `tests/referral/__init__.py`
- `tests/referral/conftest.py` (synthetic fixture)
- `tests/referral/test_data_loader.py`
- `tests/referral/test_cli.py`

---

### Phase 2: Core Engine (Layers 1-5)

#### 2.1 Layer 1 -- Entity Normalizer (`referral/normalizer.py`)

```python
def normalize_entities(df: pd.DataFrame, settings: ReferralSettings) -> pd.DataFrame:
    """Standardize entity names. Adds canonical columns without overwriting originals.

    Name normalization rules:
    - Strip whitespace, collapse multiple spaces
    - Uppercase
    - Apply alias table if configured
    - NaN/blank -> sentinel value per column (see null handling table)

    Surname extraction:
    - Split on whitespace, take last token
    - Guard: skip suffixes ["JR", "SR", "II", "III", "IV"] -> take second-to-last
    - Guard: single-word names -> surname = full name
    - Guard: NaN -> surname = "UNKNOWN"
    """
    df = df.copy()
    df["Referrer"] = _normalize_name(df["Referrer Name"], settings.name_aliases, null_sentinel="UNKNOWN")
    df["New Account"] = _normalize_name(df["Account Holder"], settings.name_aliases, null_sentinel="UNKNOWN")
    df["Staff"] = _normalize_name(df["Purchase Manager"], settings.name_aliases, null_sentinel="UNASSIGNED")
    df["Branch Code"] = df["Branch"].fillna("UNKNOWN").astype(str).str.strip()

    if settings.branch_mapping:
        df["Branch Label"] = df["Branch Code"].map(settings.branch_mapping).fillna(df["Branch Code"])
    else:
        df["Branch Label"] = df["Branch Code"]

    # Extract surnames for network inference
    df["Referrer Surname"] = _extract_surname(df["Referrer"])
    df["Account Surname"] = _extract_surname(df["New Account"])
    return df


SUFFIXES = frozenset({"JR", "SR", "II", "III", "IV", "V"})

def _extract_surname(series: pd.Series) -> pd.Series:
    """Extract surname from full name, skipping common suffixes."""
    def _surname(name: str) -> str:
        parts = name.split()
        if len(parts) <= 1:
            return name
        if parts[-1] in SUFFIXES and len(parts) > 2:
            return parts[-2]
        return parts[-1]
    return series.apply(_surname)


def _normalize_name(series: pd.Series, aliases: dict, null_sentinel: str) -> pd.Series:
    """Strip, uppercase, collapse spaces, apply alias table."""
    import re
    normalized = series.fillna(null_sentinel).astype(str).str.strip().str.upper()
    normalized = normalized.apply(lambda n: re.sub(r"\s+", " ", n))
    normalized = normalized.replace("", null_sentinel)
    if aliases:
        upper_aliases = {k.upper(): v.upper() for k, v in aliases.items()}
        normalized = normalized.map(lambda n: upper_aliases.get(n, n))
    return normalized
```

#### 2.2 Layer 2 -- Code Decoder (`referral/code_decoder.py`)

```python
def decode_referral_codes(df: pd.DataFrame, settings: ReferralSettings) -> pd.DataFrame:
    """Decode referral codes into channel, type, reliability tags.

    Classification hierarchy (checked in order):
    1. NaN / blank / whitespace-only / "None" string -> "MANUAL"
    2. Config prefix map match (longest prefix first)
    3. Contains "EMAIL" (case-insensitive) -> "EMAIL"
    4. Fallback -> "OTHER"

    Added columns: Referral Channel, Referral Type, Referral Reliability
    """
    df = df.copy()
    # Sort prefixes by length descending for longest-match-first
    sorted_prefixes = sorted(settings.code_prefix_map.keys(), key=len, reverse=True)
    df["Referral Channel"] = df["Referral Code"].apply(
        lambda c: _classify_channel(c, sorted_prefixes, settings.code_prefix_map)
    )
    df["Referral Type"] = df["Referral Channel"].map({
        "BRANCH_STANDARD": "Standard",
        "DIGITAL_PROCESS": "Standard",
        "EMAIL": "Standard",
        "MANUAL": "Manual",
        "OTHER": "Exception",
    }).fillna("Exception")
    df["Referral Reliability"] = df["Referral Type"].map({
        "Standard": "High", "Manual": "Medium", "Exception": "Low",
    })
    return df


def _classify_channel(code, sorted_prefixes, prefix_map):
    """Classify a single referral code."""
    if pd.isna(code) or str(code).strip() in ("", "None", "none", "NONE"):
        return "MANUAL"
    code_str = str(code).strip().upper()
    for prefix in sorted_prefixes:
        if code_str.startswith(prefix.upper()):
            return prefix_map[prefix]
    if "EMAIL" in code_str:
        return "EMAIL"
    return "OTHER"
```

#### 2.3 Layer 3 -- Temporal Analysis (`referral/temporal.py`)

```python
def add_temporal_signals(df: pd.DataFrame, settings: ReferralSettings) -> pd.DataFrame:
    """Add time-based signals: inter-referral gap, burst flag, recency.

    Only operates on rows where Issue Date is not NaT.
    Rows with NaT Issue Date get NaN for all temporal columns.
    """
    df = df.sort_values(["Referrer", "Issue Date"]).copy()

    # Inter-referral gap (days since previous referral by same referrer)
    df["Days Since Last Referral"] = df.groupby("Referrer")["Issue Date"].diff().dt.days

    # Burst flag: referrals within configurable window
    df["Is Burst"] = df["Days Since Last Referral"].between(0, settings.burst_window_days)

    # Recency: days from each referral to the max date in dataset
    max_date = df["Issue Date"].max()
    df["Days Since Latest"] = (max_date - df["Issue Date"]).dt.days

    # First appearance (for emerging referrer detection)
    first_dates = df.groupby("Referrer")["Issue Date"].transform("min")
    df["Is New Referrer"] = (max_date - first_dates).dt.days <= settings.emerging_lookback_days

    return df
```

#### 2.4 Layer 4 -- Network Inference (`referral/network.py`)

```python
def infer_networks(df: pd.DataFrame) -> pd.DataFrame:
    """Soft household/network inference via shared referrer + account surname.

    A "network" is a (Referrer, Account Surname) pair. This is intentionally
    conservative -- requires TWO corroborating signals (same referrer AND
    same surname) to infer a household connection.

    Added columns: Network ID, Network Size
    """
    df = df.copy()
    network_map = (
        df.groupby(["Referrer", "Account Surname"])
        .agg(network_size=("MRDB Account Hash", "nunique"))
        .reset_index()
    )
    network_map["Network ID"] = network_map["Referrer"] + ":" + network_map["Account Surname"]
    df = df.merge(
        network_map[["Referrer", "Account Surname", "Network ID", "network_size"]],
        on=["Referrer", "Account Surname"], how="left",
    )
    df.rename(columns={"network_size": "Network Size"}, inplace=True)
    return df
```

#### 2.5 Layer 5 -- Scoring (`referral/scoring.py`)

```python
def compute_referrer_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-referrer metrics for influence scoring.

    Excludes referrers where Referrer == "UNKNOWN" (null referrer names).
    """
    scored_df = df[df["Referrer"] != "UNKNOWN"].copy()
    metrics = scored_df.groupby("Referrer").agg(
        total_referrals=("New Account", "count"),
        unique_accounts=("MRDB Account Hash", "nunique"),
        active_days=("Issue Date", lambda x: (x.max() - x.min()).days + 1 if x.notna().any() else 0),
        burst_count=("Is Burst", "sum"),
        avg_days_between=("Days Since Last Referral", "mean"),
        channels_used=("Referral Channel", "nunique"),
        branches_used=("Branch Code", "nunique"),
        first_referral=("Issue Date", "min"),
        last_referral=("Issue Date", "max"),
        network_count=("Network ID", "nunique"),
        max_network_size=("Network Size", "max"),
    ).reset_index()
    return metrics


def compute_influence_scores(
    metrics: pd.DataFrame,
    weights: "ReferralScoringWeights",
) -> pd.DataFrame:
    """Weighted composite influence score (0-100).

    Weights are logged for auditability. Version is derived from weight values.
    NaN in avg_days_between (single-referral) filled with 0 before scoring.
    """
    m = metrics.copy()
    m["avg_days_between"] = m["avg_days_between"].fillna(0)

    m["score"] = (
        weights.unique_accounts * _safe_minmax(m["unique_accounts"])
        + weights.burst_count * _safe_minmax(m["burst_count"])
        + weights.channels_used * _safe_minmax(m["channels_used"])
        + weights.velocity * _safe_minmax(1 / (m["avg_days_between"] + 1))
        + weights.longevity * _safe_minmax(m["active_days"])
    )
    m["Influence Score"] = (_safe_minmax(m["score"]) * 100).round(1)
    return m


def compute_staff_multipliers(
    df: pd.DataFrame,
    referrer_metrics: pd.DataFrame,
    weights: "ReferralStaffWeights",
) -> pd.DataFrame:
    """Staff multiplier: amplification vs volume.

    Excludes staff where Staff == "UNASSIGNED".
    Uses safe reindex to handle referrers missing from metrics (e.g., UNKNOWN).
    """
    scored_df = df[df["Staff"] != "UNASSIGNED"].copy()
    influence_lookup = referrer_metrics.set_index("Referrer")["Influence Score"]

    staff = scored_df.groupby("Staff").agg(
        referrals_processed=("New Account", "count"),
        unique_referrers=("Referrer", "nunique"),
        unique_branches=("Branch Code", "nunique"),
    ).reset_index()

    # Safe lookup: reindex with fill_value=0 for missing referrers
    staff["avg_referrer_score"] = scored_df.groupby("Staff")["Referrer"].apply(
        lambda refs: influence_lookup.reindex(refs.unique(), fill_value=0).mean()
    ).values

    staff["Multiplier Score"] = (
        weights.avg_referrer_score * _safe_minmax(staff["avg_referrer_score"])
        + weights.unique_referrers * _safe_minmax(staff["unique_referrers"])
    )
    staff["Multiplier Score"] = (staff["Multiplier Score"] * 100).round(1)
    return staff


def _safe_minmax(series: pd.Series) -> pd.Series:
    """Min-max normalize to 0-1. Returns 0.5 for constant series."""
    min_val, max_val = series.min(), series.max()
    if max_val - min_val == 0:
        return pd.Series(0.5, index=series.index)
    return (series - min_val) / (max_val - min_val)
```

**Files:**
- `ics_toolkit/referral/normalizer.py`
- `ics_toolkit/referral/code_decoder.py`
- `ics_toolkit/referral/temporal.py`
- `ics_toolkit/referral/scoring.py`
- `ics_toolkit/referral/network.py`
- `tests/referral/test_normalizer.py`
- `tests/referral/test_code_decoder.py`
- `tests/referral/test_temporal.py`
- `tests/referral/test_scoring.py`
- `tests/referral/test_network.py`

---

### Phase 3: Analysis Artifacts (Layer 6)

Each artifact follows the existing `AnalysisResult` pattern. Analysis functions receive a `ReferralContext` dataclass:

```python
@dataclass
class ReferralContext:
    """Bundles all pre-computed data for analysis functions."""
    df: pd.DataFrame               # Full enriched DataFrame (all layers applied)
    referrer_metrics: pd.DataFrame  # Per-referrer metrics + influence scores
    staff_metrics: pd.DataFrame     # Per-staff metrics + multiplier scores
    settings: ReferralSettings
```

**Analysis function signature:** `def analyze_<name>(ctx: ReferralContext) -> AnalysisResult`

**Exception:** `analyze_overview` takes an extra `prior_results: list[AnalysisResult]` kwarg.

#### Artifact Definitions

| # | Artifact | Module | Sheet Name | Key Columns | Chart? |
|---|----------|--------|------------|-------------|--------|
| R01 | Top Referrers | `top_referrers.py` | `R01_Top_Referrers` | Referrer, Influence Score, Unique Accounts, Total Referrals, Burst Count, Channels, Network Size | Horizontal bar |
| R02 | Emerging Referrers | `emerging_referrers.py` | `R02_Emerging` | Referrer, Influence Score, Burst Count, Days Active, First Referral, Last Referral | Scatter timeline |
| R03 | Dormant High-Value | `dormant_referrers.py` | `R03_Dormant` | Referrer, Historical Score, Total Referrals, Unique Accounts, Last Referral, Days Dormant | None |
| R04 | One-time vs Repeat | `onetime_vs_repeat.py` | `R04_Repeat` | Category (One-time/Repeat), Count, %, Avg Unique Accounts, Avg Influence Score, Avg Active Days | None |
| R05 | Staff Multipliers | `staff_multipliers.py` | `R05_Staff` | Staff, Multiplier Score, Referrals Processed, Unique Referrers, Avg Referrer Score, Unique Branches | Grouped bar |
| R06 | Branch Density | `branch_density.py` | `R06_Branch` | Branch, Total Referrals, Unique Referrers, Avg Influence Score, Top Referrer, Channel Mix | Vertical bar |
| R07 | Code Health | `code_health.py` | `R07_Code_Health` | Channel, Type, Reliability, Count, %, Known Code % | Stacked bar |
| R08 | Overview KPIs | `overview.py` | `R08_Overview` | Metric, Value | None |

#### Detailed Artifact Specifications

**R04 -- One-time vs Repeat Referrers** (new definition):
- Answers: "What proportion of referrers are one-time vs repeat, and how do they differ?"
- One-time = referrer with exactly 1 referral; Repeat = referrer with 2+ referrals
- Output: 2-row comparison table with Grand Total row
- Columns: Category, Count, % of Total, Avg Unique Accounts, Avg Influence Score, Avg Active Days
- Uses `append_grand_total_row()` from `analysis.analyses.templates`

**R08 -- Overview KPIs** (new definition):
- Answers: "What are the headline numbers for this referral program?"
- Runs last, receives `prior_results` for cross-artifact stats
- Output: KPI table (Metric, Value) with ~15 rows:
  - Total Referrals
  - Unique Referrers
  - Unique New Accounts
  - Repeat Referrer %
  - Avg Referrals per Referrer
  - Top Referrer Influence Score
  - Median Influence Score
  - Avg Days Between Referrals
  - Burst Referral %
  - Staff with Highest Multiplier
  - Most Active Branch
  - Dominant Referral Channel
  - Manual Code %
  - Exception Code %
  - Avg Network Size
- Uses `kpi_summary()` from `analysis.analyses.templates`

**R02 -- Emerging Referrers** (clarified):
- "Emerging" = first referral within `emerging_lookback_days` (default 180) AND `burst_count >= emerging_min_burst_count` (default 2)
- This separates "new and accelerating" from "old and bursting" (old bursters appear in R01 Top Referrers instead)

**R03 -- Dormant High-Value Referrers** (clarified):
- "Dormant" = no referral in last `dormancy_days` (default 180)
- "High-Value" = `unique_accounts >= high_value_min_referrals` (default 5) OR historical influence score in top quartile
- Ordered by historical influence score descending

**R06 -- Branch Density** (clarified):
- "Branch Influence Density" = average influence score of referrers routed through that branch
- This does NOT reward branch volume -- it measures whether a branch handles high-quality referrers
- Includes: Top Referrer (name of highest-scoring referrer at that branch), Channel Mix (% Standard/Manual/Exception)

**Files:**
- `ics_toolkit/referral/analyses/__init__.py`
- `ics_toolkit/referral/analyses/base.py` (ReferralContext)
- `ics_toolkit/referral/analyses/top_referrers.py`
- `ics_toolkit/referral/analyses/emerging_referrers.py`
- `ics_toolkit/referral/analyses/dormant_referrers.py`
- `ics_toolkit/referral/analyses/onetime_vs_repeat.py`
- `ics_toolkit/referral/analyses/staff_multipliers.py`
- `ics_toolkit/referral/analyses/branch_density.py`
- `ics_toolkit/referral/analyses/code_health.py`
- `ics_toolkit/referral/analyses/overview.py`
- `tests/referral/analyses/__init__.py`
- `tests/referral/analyses/test_*.py` (one per module)

---

### Phase 4: Charts

| Analysis | Chart Type | Description |
|----------|-----------|-------------|
| R01 Top Referrers | Horizontal bar | Top N by influence score, `config.colors[0]` fill |
| R02 Emerging Referrers | Scatter timeline | Referrer (y) x Issue Date (x), marker size = burst count |
| R05 Staff Multipliers | Grouped bar | Multiplier score (primary) vs volume (secondary axis) |
| R06 Branch Density | Vertical bar | Avg influence score per branch, sorted descending |
| R07 Code Health | Stacked bar | Code category distribution by Reliability tier |

All chart functions follow existing pattern: `chart_<name>(df: pd.DataFrame, config: ChartConfig) -> go.Figure`.

Uses same `BRAND_COLORS` from `settings.py`, same `LAYOUT_DEFAULTS` pattern (horizontal legend, 60/40 margins).

```python
# referral/charts/__init__.py
REFERRAL_CHART_REGISTRY: dict[str, Callable] = {
    "Top Referrers": chart_top_referrers,
    "Emerging Referrers": chart_emerging_referrers,
    "Staff Multipliers": chart_staff_multipliers,
    "Branch Influence Density": chart_branch_density,
    "Code Health Report": chart_code_health,
}
```

**Files:**
- `ics_toolkit/referral/charts/__init__.py`
- `ics_toolkit/referral/charts/top_referrers.py`
- `ics_toolkit/referral/charts/emerging_referrers.py`
- `ics_toolkit/referral/charts/staff_multipliers.py`
- `ics_toolkit/referral/charts/branch_density.py`
- `ics_toolkit/referral/charts/code_health.py`
- `tests/referral/charts/__init__.py`
- `tests/referral/charts/test_referral_charts.py`

---

### Phase 5: Pipeline + Exports

#### 5.1 Pipeline (`referral/pipeline.py`)

```python
@dataclass
class ReferralPipelineResult:
    settings: ReferralSettings
    df: pd.DataFrame                     # Full enriched DataFrame
    referrer_metrics: pd.DataFrame       # Per-referrer metrics + scores
    staff_metrics: pd.DataFrame          # Per-staff metrics + scores
    analyses: list[AnalysisResult]       # 8 artifacts
    charts: dict[str, go.Figure]         # 5 charts
    chart_pngs: dict[str, bytes]         # PNG renders


def run_pipeline(
    settings: ReferralSettings,
    on_progress: Callable[[int, int, str], None] | None = None,
    skip_charts: bool = False,
) -> ReferralPipelineResult:
    """Execute the referral intelligence pipeline.

    Steps:
    1. Load + validate data (data_loader.load_referral_data)
    2. Layer 1: Entity normalization (normalizer.normalize_entities)
    3. Layer 2: Code decoding (code_decoder.decode_referral_codes)
    4. Layer 3: Temporal signals (temporal.add_temporal_signals)
    5. Layer 4: Network inference (network.infer_networks)
    6. Layer 5: Scoring (scoring.compute_referrer_metrics + compute_influence_scores + compute_staff_multipliers)
    7. Log scoring weights for auditability
    8. Build ReferralContext
    9. Layer 6: Run all 8 analyses (REFERRAL_ANALYSIS_REGISTRY)
    10. Charts (REFERRAL_CHART_REGISTRY) unless skip_charts
    11. Render PNGs (reuse analysis.charts.renderer.render_all_chart_pngs)
    12. Return ReferralPipelineResult
    """


def export_outputs(
    result: ReferralPipelineResult,
    skip_charts: bool = False,
) -> list[Path]:
    """Export pipeline results to files.

    1. Write Excel report ({client_id}_Referral_Intelligence_{date}.xlsx)
    2. Write PPTX report ({client_id}_Referral_Intelligence_{date}.pptx)
    3. Save charts as HTML (optional)
    Returns list of output file paths.
    """
```

#### 5.2 Exports

```python
# referral/exports/excel.py
# Reuse NamedStyle patterns from analysis.exports.excel
# Same header, data_even, data_odd, total styles
# Chart images embedded below data tables
# Number formatting: '0.0"%"' for percentages, '#,##0' for counts, '0.0' for scores


# referral/exports/pptx.py
REFERRAL_SECTION_MAP = {
    "Referral Intelligence Overview": ["Overview KPIs"],
    "Referrer Influence": [
        "Top Referrers",
        "Emerging Referrers",
        "Dormant High-Value Referrers",
        "One-time vs Repeat Referrers",
    ],
    "Staff & Branch": [
        "Staff Multipliers",
        "Branch Influence Density",
    ],
    "Code Health": ["Code Health Report"],
}
```

**Files:**
- `ics_toolkit/referral/pipeline.py`
- `ics_toolkit/referral/exports/__init__.py`
- `ics_toolkit/referral/exports/excel.py`
- `ics_toolkit/referral/exports/pptx.py`
- `tests/referral/test_pipeline.py`
- `tests/referral/exports/__init__.py`
- `tests/referral/exports/test_referral_excel.py`
- `tests/referral/exports/test_referral_pptx.py`

---

### Phase 6: Config + Integration

- Update `config.example.yaml` with full `referral:` section and comments
- Add `xlrd` to `requirements.txt` for `.xls` support
- Verify existing `analyze` and `append` commands are unaffected (run full test suite)
- Update `pyproject.toml` if needed

---

## Test Strategy

### Test Fixtures (`tests/referral/conftest.py`)

```python
import numpy as np
import pandas as pd
import pytest
from datetime import datetime

REFERENCE_DATE = datetime(2026, 1, 15)

REFERRERS = ["JOHN SMITH", "JANE DOE", "BOB WILSON", "ALICE BROWN", "TOM JONES",
             "MARY CLARK", "DAVID HALL", "SARAH KING"]
STAFF = ["SARAH MANAGER", "MIKE HANDLER", "LISA PROCESSOR"]
BRANCHES = ["001", "002", "003"]
CODES = ["150A001", "120A002", "PC100", None, "EMAIL_Q1", "080A003", None, "UNKNOWN_XYZ"]

@pytest.fixture(scope="session")
def rng():
    return np.random.default_rng(42)

@pytest.fixture
def sample_referral_df(rng):
    """50-row deterministic referral dataset with known patterns."""
    n = 50
    return pd.DataFrame({
        "Referrer Name": rng.choice(REFERRERS, n),
        "Issue Date": pd.date_range("2025-01-01", periods=n, freq="7D"),
        "Referral Code": rng.choice(CODES, n),
        "Purchase Manager": rng.choice(STAFF, n),
        "Branch": rng.choice(BRANCHES, n),
        "Account Holder": [f"NEW_ACCOUNT_{i}" for i in range(n)],
        "MRDB Account Hash": [f"HASH_{i:04d}" for i in range(n)],
        "Cert ID": [f"CERT_{i:04d}" for i in range(n)],
    })

@pytest.fixture
def sample_referral_settings(tmp_path, sample_referral_df):
    """Write sample data to tmp xlsx and create ReferralSettings."""
    data_path = tmp_path / "test_referral.xlsx"
    sample_referral_df.to_excel(data_path, index=False)
    return ReferralSettings(data_file=data_path, output_dir=tmp_path / "output")

@pytest.fixture
def empty_referral_df():
    """Empty DataFrame with correct columns for edge-case testing."""
    return pd.DataFrame(columns=[...REQUIRED_COLUMNS...])
```

### Test Pattern Per Module

Each test module follows class-based organization:

```python
class TestAnalyzeTopReferrers:
    def test_returns_analysis_result(self, ctx):
        result = analyze_top_referrers(ctx)
        assert isinstance(result, AnalysisResult)
        assert result.error is None

    def test_has_expected_columns(self, ctx):
        result = analyze_top_referrers(ctx)
        assert "Referrer" in result.df.columns
        assert "Influence Score" in result.df.columns

    def test_sheet_name(self, ctx):
        result = analyze_top_referrers(ctx)
        assert result.sheet_name == "R01_Top_Referrers"

    def test_respects_top_n(self, ctx):
        result = analyze_top_referrers(ctx)
        assert len(result.df) <= ctx.settings.top_n_referrers

    def test_excludes_single_referral(self, ctx):
        result = analyze_top_referrers(ctx)
        assert (result.df["Total Referrals"] > 1).all()

    def test_excludes_unknown_referrer(self, ctx):
        result = analyze_top_referrers(ctx)
        assert "UNKNOWN" not in result.df["Referrer"].values

    def test_empty_input(self, empty_ctx):
        result = analyze_top_referrers(empty_ctx)
        assert isinstance(result, AnalysisResult)
        assert len(result.df) == 0
```

### Edge Case Tests (across modules)

- Single row input (1 referral, 1 referrer)
- All same referrer (one person referred everyone)
- All null referral codes (100% MANUAL channel)
- All null Issue Dates (no temporal analysis possible)
- Unicode in names (accented characters, CJK)
- Very large input (parametrize with n=10000 for performance regression)
- Future dates in Issue Date
- Duplicate MRDB + Cert ID

---

## Acceptance Criteria

### Functional
- [ ] `python -m ics_toolkit referral data/file.xls` runs full pipeline, produces Excel + PPTX
- [ ] All 8 analysis artifacts generate valid `AnalysisResult` objects
- [ ] Entity normalization handles nulls, whitespace, case variations, suffixes (JR/SR)
- [ ] Code decoder classifies codes using config-driven prefix map (longest match first)
- [ ] Influence score is 0-100 weighted composite with configurable weights validated to sum to 1.0
- [ ] Burst detection flags referrals within configurable window (default 14 days)
- [ ] Network inference assigns Network IDs via shared referrer + surname
- [ ] Staff multiplier distinguishes influence amplification from volume
- [ ] `--no-charts`, `--output`, `--client-id`, `--client-name`, `--verbose` flags work
- [ ] Existing `python -m ics_toolkit analyze` and `append` are unaffected
- [ ] `.xls` (xlrd), `.xlsx` (openpyxl), and `.csv` formats all load correctly
- [ ] Null MRDB Account Hash rows raise DataError; null in other columns handled gracefully
- [ ] Scoring weights logged at pipeline start for auditability

### Quality Gates
- [ ] 90%+ test coverage on `referral/` package
- [ ] All existing tests pass (976+ tests)
- [ ] `ruff check` and `ruff format --check` clean

---

## Implementation Phases Summary

| Phase | Scope | New Files | Modified | Est. Tests |
|-------|-------|-----------|----------|-----------|
| 1. Foundation | Settings, CLI, Data Loader | 8 | 3 | ~40 |
| 2. Core Engine | Layers 1-5 (normalize, decode, temporal, network, scoring) | 5 | 0 | ~55 |
| 3. Artifacts | 8 analysis modules + ReferralContext | 10 | 0 | ~55 |
| 4. Charts | 5 chart builders + registry | 6 | 0 | ~20 |
| 5. Pipeline + Exports | Orchestrator, Excel, PPTX | 6 | 0 | ~30 |
| 6. Config | config.example.yaml, requirements.txt, pyproject.toml | 0 | 3 | ~5 |
| **Total** | | **~35** | **~6** | **~205** |

---

## Risk Analysis

| Risk | Mitigation |
|------|------------|
| Unknown referral code format | Generic prefix classifier with config override; refine with real data |
| `.xls` binary format | Add `xlrd` dependency; detect format by suffix in data_loader |
| Name normalization merges wrong people | V1 = exact match + alias table; fuzzy matching is future enhancement |
| Scoring weights need tuning | All weights configurable via config.yaml, validated to sum to 1.0 |
| Large files (50k+ rows) slow | Vectorized pandas ops throughout; no row-level loops except surname extraction |
| NaN propagation in scoring | All NaN handling defined per-column (see null handling table in Overview) |
| Single-referral velocity = NaN | fillna(0) before scoring; single-referral referrers excluded from Top Referrers |
| Constant-series min-max = 0 | Returns 0.5 (midpoint) instead of 0 for constant series |
| Staff score crash on missing referrer | Safe reindex with fill_value=0 |

---

## Dependencies

**New:**
- `xlrd` -- required for `.xls` (legacy Excel) file reading

**Existing (no changes):**
- `pandas`, `numpy`, `plotly`, `openpyxl`, `python-pptx`, `pydantic`, `pyyaml`, `typer`, `rich`

---

## References

### Internal
- Existing REF analysis (different data source): `ics_toolkit/analysis/analyses/ref_source.py`
- Analysis registry pattern: `ics_toolkit/analysis/analyses/__init__.py`
- AnalysisResult dataclass: `ics_toolkit/analysis/analyses/base.py`
- Template helpers: `ics_toolkit/analysis/analyses/templates.py`
- Excel export: `ics_toolkit/analysis/exports/excel.py`
- PPTX export: `ics_toolkit/analysis/exports/pptx.py`
- Settings: `ics_toolkit/settings.py`
- Test fixtures: `tests/analysis/conftest.py`
- Chart renderer: `ics_toolkit/analysis/charts/renderer.py`

### Feature Spec
- GitHub: `JG-CSI-Velocity/ics_toolkit/referral-file-analysis`
- Issue #4: `JG-CSI-Velocity/ics_toolkit/issues/4` -- Build checklist with QA validation requirements
