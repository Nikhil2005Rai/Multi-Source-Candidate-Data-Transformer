# Multi-Source Candidate Data Transformer

This project transforms messy candidate data from multiple sources into one
trustworthy candidate profile per person. The implementation emphasizes
deterministic behavior, explainable conflict resolution, provenance, and a
runtime-configurable output layer.

## Architecture

```text
Sources
  -> Parsers
  -> Normalizer
  -> Identity Resolver
  -> Merge Engine
  -> CanonicalProfile
  -> Projector
  -> Validator
  -> Output JSON
```

The internal `CanonicalProfile` is the source of truth between merge and
projection. It is never returned directly to callers. All user-visible output
passes through the projector, which supports field selection, renaming, simple
canonical paths such as `emails[0]` and `skills[].name`, missing-value behavior,
and confidence/provenance toggles.

## Supported Sources

- Recruiter CSV export
- GitHub API-compatible JSON fixture
- Live GitHub REST API lookup by username or profile URL

The repository keeps fixture-based GitHub input for deterministic tests and
demos, and also supports live GitHub API requests through `--github`.

## Setup

Open PowerShell in the project folder. For example:

```powershell
cd path\to\Eightfold
```

Option A: use the virtual environment.

```powershell
.\.venv\Scripts\activate
```

Then install dependencies from `requirements.txt`:

```powershell
pip install -r requirements.txt
```

Option B: do not use a virtual environment.

Install dependencies directly with your Python:

```powershell
pip install -r requirements.txt
```

Then run commands with:

```powershell
python main.py ...
```

If you have a `.venv` but do not want to activate it, use this instead of
`python` in every command:

```powershell
.\.venv\Scripts\python.exe main.py ...
```

## See Output In Terminal

These commands print JSON directly in the terminal. They do not write to files.

Default canonical output using CSV + GitHub fixture:

```powershell
python main.py --input samples/candidates.csv samples/github_profiles.json --id-map samples/identity_map.json --config configs/default.json
```

Custom projected output using CSV + GitHub fixture:

```powershell
python main.py --input samples/candidates.csv samples/github_profiles.json --id-map samples/identity_map.json --config configs/custom_projection.json
```

CSV + live GitHub API output:

```powershell
python main.py --input samples/candidates.csv --github Nikhil2005Rai --id-map samples/identity_map.json --config configs/custom_projection.json
```

Live GitHub API only:

```powershell
python main.py --github Nikhil2005Rai --config configs/custom_projection.json
```

You can also pass a GitHub profile URL:

```powershell
python main.py --github https://github.com/Nikhil2005Rai --config configs/custom_projection.json
```

## Write Output To Files

Use `--output` only when you want to save JSON into a file. These are the exact
commands for the provided output files.

Write default canonical output:

```powershell
python main.py --input samples/candidates.csv samples/github_profiles.json --id-map samples/identity_map.json --config configs/default.json --output outputs/default_output.json
```

Write custom projected output:

```powershell
python main.py --input samples/candidates.csv samples/github_profiles.json --id-map samples/identity_map.json --config configs/custom_projection.json --output outputs/custom_output.json
```

Write CSV + live GitHub API output:

```powershell
python main.py --input samples/candidates.csv --github Nikhil2005Rai --id-map samples/identity_map.json --config configs/default.json --output outputs/live_github_output.json
```

Rule of thumb:

```text
No --output  = print JSON in terminal
With --output = write JSON to that file
```

For higher GitHub API rate limits, set `GITHUB_TOKEN` before running a live
GitHub command:

```powershell
$env:GITHUB_TOKEN="your_token_here"
python main.py --github Nikhil2005Rai --config configs/custom_projection.json
```

## Test

```bash
python -m unittest discover -s tests
```

## Dependencies

- `phonenumbers` for E.164 phone normalization
- `pycountry` for ISO-3166 country normalization
- `pydantic` for projected output validation

## Design Choices

- Identity resolution uses explicit mapping first and normalized email fallback.
  It never fuzzy-matches by name alone because a false merge is worse than two
  honest partial profiles.
- Structured CSV fields receive higher baseline confidence than GitHub-derived
  signals. GitHub repository languages are useful but weaker evidence.
- Invalid source values do not crash the run. They are excluded from canonical
  fields and recorded as diagnostics; rejected phone values are also preserved
  in provenance with a `not_emitted` note.
- List fields such as emails, phones, and skills are unions after normalization.
  Scalar conflicts pick the highest-confidence evidence and record rejected
  conflicts in both diagnostics and provenance.

## Deliberate Descopes

- PDF/DOCX resume parsing
- LinkedIn scraping
- Async source fetching
- Fuzzy name-only identity matching
- Statistically learned / ML-based confidence modeling. The implementation does
  include deterministic, rule-based confidence scoring with source weights,
  corroboration bonuses, and conflict penalties.

These are useful production extensions, but they add risk and noise for this
assignment's core evaluation criteria.
