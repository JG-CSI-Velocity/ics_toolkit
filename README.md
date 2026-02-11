# ICS Toolkit

Unified ICS accounts analysis pipeline. Append (organize, merge, match) raw ICS files, then run 41 analytics with Plotly charts, Excel reports, and PowerPoint decks.

## Installation

```sh
git clone https://github.com/Gilmore3088/ics_toolkit.git
cd ics_toolkit
pip install -e .
```

On Windows:

```powershell
git clone https://github.com/Gilmore3088/ics_toolkit.git
cd ics_toolkit
pip install -e .
```

Or with a virtual environment (Mac/Linux):

```sh
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Virtual environment on Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

Requires Python 3.11+.

`pip install -e .` installs all dependencies (plotly, kaleido, openpyxl, pydantic, pyyaml, typer, etc.). You must run this step before using the toolkit.

## Quick Start

Place your ODD file in the `data/` directory, then run:

```sh
python -m ics_toolkit analyze data/your-file.xlsx
```

That's it. No pre-processing needed. The pipeline automatically:

1. Reads `.xlsx`, `.xls`, or `.csv` files
2. Resolves column name aliases (e.g. `"Current Balance"` -> `"Curr Bal"`)
3. Validates required columns
4. Normalizes strings (`YES`/`Y`/`True` -> `"Yes"`)
5. Parses dates and coerces numerics
6. Discovers L12M monthly columns (e.g. `Feb24 Swipes`, `Feb24 Spend`)
7. Auto-detects cohort start from the data
8. Runs all 41 analyses, builds charts, exports reports

## Output

Reports are written to `output/` by default:

| File | Description |
|------|-------------|
| `{client_id}_ICS_Report_{date}.xlsx` | Excel workbook with formatted tables, embedded charts, cover sheet, and table of contents |
| `{client_id}_ICS_Presentation_{date}.pptx` | PowerPoint deck with chart slides organized by section |

Charts are rendered in-memory and embedded directly into both the Excel and PPTX files. No standalone image files are created.

Override the output directory:

```sh
python -m ics_toolkit analyze data/your-file.xlsx --output /path/to/reports/
```

## Required Columns

Your data file must include these columns (aliases are resolved automatically):

| Column | Accepted Aliases |
|--------|-----------------|
| `ICS Account` | `ICS Accounts`, `Ics Account`, `ICS_Account` |
| `Stat Code` | `StatCode`, `Stat_Code`, `Status Code` |
| `Debit?` | `Debit`, `DebitCard`, `Debit Card` |
| `Business?` | `Business`, `BusinessFlag`, `Business Flag` |
| `Date Opened` | `DateOpened`, `Date_Opened`, `Open Date` |
| `Prod Code` | `ProdCode`, `Prod_Code`, `Product Code` |
| `Branch` | -- |
| `Source` | -- |
| `Curr Bal` | `CurrBal`, `Curr_Bal`, `Current Balance` |

Optional: `Date Closed`, `Avg Bal`

L12M columns are discovered automatically from patterns like `Feb24 Swipes` / `Feb24 Spend`.

## CLI Options

```
python -m ics_toolkit analyze <data-file> [OPTIONS]

Options:
  --output, -o PATH         Output directory (default: output/)
  --config, -c PATH         Path to config.yaml (default: config.yaml)
  --client-id TEXT           Client identifier (auto-extracted from filename)
  --client-name TEXT         Client name for report titles
  --cohort-start TEXT        Cohort start month, YYYY-MM (auto-detected)
  --ics-not-in-dump INT      ICS accounts not in data dump (default: 0)
  --verbose, -v              Debug logging
```

### Append Pipeline

If you need to run the pre-analysis append steps (organize raw files, merge REF+DM, match against ODD):

```sh
python -m ics_toolkit append --base-dir ~/ICS_Files run-all
```

Individual steps:

```sh
python -m ics_toolkit append --base-dir ~/ICS_Files organize
python -m ics_toolkit append --base-dir ~/ICS_Files merge
python -m ics_toolkit append --base-dir ~/ICS_Files match
```

Add `--dry-run` to preview without making changes.

## Jupyter / REPL Usage

```python
from ics_toolkit import run_analysis

result = run_analysis("data/your-file.xlsx")
```

With options:

```python
result = run_analysis(
    "data/your-file.xlsx",
    output_dir="output/",
    client_id="1234",
    client_name="ABC Credit Union",
    cohort_start="2024-01",
)
```

Access results programmatically:

```python
for analysis in result.analyses:
    if analysis.error is None:
        print(f"{analysis.name}: {len(analysis.df)} rows")

# Access a specific chart
fig = result.charts.get("Cohort Activation")
if fig:
    fig.show()
```

## Configuration

Copy `config.example.yaml` to `config.yaml` for persistent settings:

```sh
cp config.example.yaml config.yaml
```

CLI flags override config.yaml values. Config.yaml overrides defaults.

## Analyses

41 analyses organized into 10 sections:

**Summary** (7) -- Total ICS Accounts, Open ICS Accounts, ICS by Stat Code, Product Code Distribution, Debit Distribution, Debit x Prod Code, Debit x Branch

**Source** (6) -- Source Distribution, Source x Stat Code, Source x Prod Code, Source x Branch, Account Type, Source by Year

**Demographics** (8) -- Age Comparison, Closures, Open vs Close, Balance Tiers, Stat Open Close, Age vs Balance, Balance Tier Detail, Age Distribution

**Activity** (5) -- Activity Summary, Activity by Debit+Source, Activity by Balance, Activity by Branch, Monthly Trends

**Cohort** (7) -- Cohort Activation, Cohort Heatmap, Cohort Milestones, Activation Summary, Growth Patterns, Activation Personas, Branch Activation

**Strategic Insights** (2) -- Activation Funnel, Revenue Impact

**Portfolio Health** (3) -- Engagement Decay, Net Portfolio Growth, Spend Concentration

**Performance** (2) -- Days to First Use, Branch Performance Index

**Executive Summary** (1) -- Auto-generated narrative with hero KPIs, traffic-light indicators, and What / So What / Now What bullets

38 Plotly charts are embedded in the Excel and PPTX reports. The PPTX deck includes data-driven declarative slide titles (e.g. "Branch 12 leads activation at 78%") and dedicated KPI + narrative slides for the Executive Summary.

## Development

Run tests:

```sh
python -m pytest tests/ -v
```

With coverage:

```sh
python -m pytest tests/ -v --cov=ics_toolkit --cov-report=term-missing
```

Lint and format:

```sh
ruff check ics_toolkit/ tests/
ruff format ics_toolkit/ tests/
```

521 tests, 90% coverage.

## Project Structure

```
ics_toolkit/
  __init__.py              # version, run_analysis(), run_append()
  __main__.py              # python -m ics_toolkit
  cli.py                   # Typer CLI (analyze + append subcommands)
  settings.py              # Pydantic config (AppendSettings + AnalysisSettings)
  exceptions.py            # Unified exception hierarchy
  append/                  # Data preparation pipeline
    pipeline.py            #   organize -> merge -> match
    organizer.py           #   sort files into client folders
    merger.py              #   merge REF + DM files
    matcher.py             #   match against ODD
    column_detect.py       #   auto-detect column mappings
    normalizer.py          #   normalize data formats
    validation.py          #   data quality checks
    trends.py              #   trend calculations
  analysis/                # Analytics pipeline
    pipeline.py            #   load -> filter -> analyze -> chart -> export
    data_loader.py         #   read, clean, validate input data
    column_map.py          #   required columns, aliases, L12M discovery
    formatting.py          #   display + Excel number formatting
    utils.py               #   filters, enrichment helpers
    analyses/              #   41 analysis functions
      summary.py           #     ax01-ax07
      source.py            #     ax08-ax13
      demographics.py      #     ax14-ax21
      activity.py          #     ax22-ax26
      cohort.py            #     ax27-ax28 + shared helpers
      cohort_detail.py     #     ax29-ax36
      strategic.py         #     ax38-ax39 (funnel, revenue)
      portfolio.py         #     ax40-ax42 (decay, growth, concentration)
      performance.py       #     ax43-ax44 (first use, branch index)
      executive_summary.py #     ax999 (narrative + KPIs)
      benchmarks.py        #     interchange rate, traffic-light thresholds
      base.py              #     AnalysisResult, safe_percentage
      templates.py         #     crosstab builder, grand total
    charts/                #   38 Plotly chart builders
      summary.py, source.py, demographics.py, activity.py
      cohort.py, strategic.py, portfolio.py, performance.py
    exports/               #   Excel + PPTX report generators
      excel.py
      pptx.py              #     SECTION_MAP + report orchestrator
      deck_builder.py      #     DeckBuilder + SlideContent
      kpi_slides.py        #     KPI grid, narrative, declarative titles
tests/                     # 521 tests
  append/
  analysis/
```

## Troubleshooting

**`ModuleNotFoundError: No module named 'plotly'`** (or any missing module)

You cloned the repo but didn't install dependencies. Run:

```sh
pip install -e .
```

This installs everything listed in `pyproject.toml`. If you skip this step, Python can find the `ics_toolkit` package but none of its dependencies (plotly, kaleido, pandas, etc.) will be available.

**`Missing required columns: [...]`**

Your data file is missing one or more required columns. Check the Required Columns table above. Column aliases are resolved automatically, but if your file uses a non-standard name, add it to `ics_toolkit/analysis/column_map.py` in `COLUMN_ALIASES`.

**`Unsupported file type`**

Only `.csv`, `.xlsx`, and `.xls` files are supported. Convert your file to one of these formats.

**Cohort analysis returns empty results**

If `cohort_start` is not set, it auto-detects from your L12M month columns or the earliest `Date Opened`. If your data has no L12M columns and no `Date Opened`, pass it explicitly:

```sh
python -m ics_toolkit analyze data/file.xlsx --cohort-start 2024-01
```

**Charts missing from reports**

Chart rendering requires `kaleido==0.2.1`. Verify it's installed:

```sh
pip show kaleido
```

If the version is 1.0+, downgrade: `pip install kaleido==0.2.1`
