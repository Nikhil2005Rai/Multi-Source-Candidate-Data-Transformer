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

## Run

Default canonical output:

```bash
python main.py --input samples/candidates.csv samples/github_profiles.json --id-map samples/identity_map.json --config configs/default.json --output outputs/default_output.json
```

Custom projected output:

```bash
python main.py --input samples/candidates.csv samples/github_profiles.json --id-map samples/identity_map.json --config configs/custom_projection.json --output outputs/custom_output.json
```

Live GitHub API request:

```bash
python main.py --input samples/candidates.csv --github nikhilrai --id-map samples/identity_map.json --config configs/custom_projection.json
```

You can also pass a profile URL:

```bash
python main.py --github https://github.com/octocat --config configs/custom_projection.json
```

For higher GitHub rate limits, set `GITHUB_TOKEN` or pass `--github-token`.

Print to stdout by omitting `--output`.

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
- Statistical confidence modeling

These are useful production extensions, but they add risk and noise for this
assignment's core evaluation criteria.
